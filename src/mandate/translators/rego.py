"""
MANDATE Constraint → OPA/Rego Policy Translator

Translates parsed MANDATE constraint ASTs into OPA/Rego policy rules.
The generated Rego evaluates constraints against an ``input`` document
with the same shape as the MANDATE evaluation state model.

Input document model expected by generated policies::

    {
        "<field.path>": <value>,          # Dotted fields flattened into nested objects
        "capabilities": ["cap1", ...],    # For REQUIRES predicates
        "forbidden_actions": ["act1", ...]  # For FORBIDS predicates
    }

Generated policies use Rego v1 syntax (``import rego.v1``).

Usage::

    from mandate.translators.rego import translate_to_rego

    constraints = [
        "target.scope IN ['10.0.1.0/24', 'acme.example.com']",
        "execution.duration <= PT4H",
        "FORBIDS data_exfiltration",
    ]
    policy = translate_to_rego(constraints, package_name="mandate.mission")
    print(policy)

Produces::

    package mandate.mission

    import rego.v1

    default allow := false

    allow if {
        # target.scope IN ['10.0.1.0/24', 'acme.example.com']
        input.target.scope in {"10.0.1.0/24", "acme.example.com"}
        # execution.duration <= PT4H
        input.execution.duration <= "PT4H"
        # FORBIDS data_exfiltration
        "data_exfiltration" in input.forbidden_actions
    }
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from mandate.constraints import (
    Constraint,
    ComparisonPredicate,
    InPredicate,
    RequiresPredicate,
    ForbidsPredicate,
    NotExpr,
    AndExpr,
    OrExpr,
    Comparator,
    FieldRef,
    LiteralValue,
    SetValue,
    parse_constraint,
)


class TranslationError(Exception):
    """Raised when a constraint cannot be translated to the target language."""
    pass


# ── Value Formatting ─────────────────────────────────────────────────


def _rego_field(field: FieldRef) -> str:
    """Convert a FieldRef to a Rego input path: ``input.field.subfield``."""
    return "input." + ".".join(field.parts)


def _rego_value(value: LiteralValue) -> str:
    """Convert a LiteralValue to a Rego literal."""
    if value.value_type == "string":
        return f'"{value.value}"'
    elif value.value_type == "number":
        if isinstance(value.value, float):
            return repr(value.value)
        return str(value.value)
    elif value.value_type == "boolean":
        return "true" if value.value else "false"
    elif value.value_type in ("duration", "timestamp"):
        # Rego treats these as opaque strings; downstream time.parse_*
        # builtins handle actual temporal comparison.
        return f'"{value.value}"'
    return str(value.value)


def _rego_set(values: SetValue) -> str:
    """Convert a SetValue to a Rego set literal ``{v1, v2, ...}``."""
    items = ", ".join(_rego_value(v) for v in values.values)
    return "{" + items + "}"


# ── AST → Rego Expression Builder ───────────────────────────────────


_COMPARATOR_MAP = {
    Comparator.EQ: "==",
    Comparator.NE: "!=",
    Comparator.LT: "<",
    Comparator.LE: "<=",
    Comparator.GT: ">",
    Comparator.GE: ">=",
}


class _RegoBuilder:
    """
    Stateful builder that translates constraint AST nodes to Rego.

    Handles OR and NOT by emitting helper rules (Rego does not have
    inline OR; ``not`` applies to rule references, not arbitrary
    expressions).
    """

    def __init__(self, prefix: str = "_h"):
        self._prefix = prefix
        self._counter = 0
        self.helpers: List[str] = []

    def _next_name(self) -> str:
        self._counter += 1
        return f"{self._prefix}_{self._counter}"

    # ── public entry point ───────────────────────────────────────

    def expr(self, node: Constraint) -> str:
        """Return a Rego expression (possibly multiline) for *node*."""
        if isinstance(node, ComparisonPredicate):
            return self._comparison(node)
        if isinstance(node, InPredicate):
            return self._in(node)
        if isinstance(node, RequiresPredicate):
            return self._requires(node)
        if isinstance(node, ForbidsPredicate):
            return self._forbids(node)
        if isinstance(node, AndExpr):
            return self._and(node)
        if isinstance(node, OrExpr):
            return self._or(node)
        if isinstance(node, NotExpr):
            return self._not(node)
        raise TranslationError(f"Unknown constraint node: {type(node).__name__}")

    # ── leaf predicates ──────────────────────────────────────────

    def _comparison(self, node: ComparisonPredicate) -> str:
        field = _rego_field(node.field)
        value = _rego_value(node.value)
        if node.comparator == Comparator.CONTAINS:
            return f"contains({field}, {value})"
        if node.comparator == Comparator.MATCHES:
            return f"regex.match({value}, {field})"
        op = _COMPARATOR_MAP[node.comparator]
        return f"{field} {op} {value}"

    def _in(self, node: InPredicate) -> str:
        return f"{_rego_field(node.field)} in {_rego_set(node.values)}"

    def _requires(self, node: RequiresPredicate) -> str:
        return f'"{node.capability}" in input.capabilities'

    def _forbids(self, node: ForbidsPredicate) -> str:
        return f'"{node.action}" in input.forbidden_actions'

    # ── logical operators ────────────────────────────────────────

    def _and(self, node: AndExpr) -> str:
        """AND is implicit in a Rego rule body (newline-separated)."""
        left = self.expr(node.left)
        right = self.expr(node.right)
        return f"{left}\n    {right}"

    def _or(self, node: OrExpr) -> str:
        """
        OR requires two rule definitions with the same head.

        We emit a helper pair and return the helper name as the
        expression to embed in the parent rule.
        """
        name = self._next_name()
        left = self.expr(node.left)
        right = self.expr(node.right)
        self.helpers.append(
            f"{name} if {{\n    {left}\n}}\n\n"
            f"{name} if {{\n    {right}\n}}"
        )
        return name

    def _not(self, node: NotExpr) -> str:
        """
        NOT requires ``not <rule_ref>`` in Rego.

        We emit a helper rule and negate the reference.
        """
        name = self._next_name()
        inner = self.expr(node.operand)
        self.helpers.append(f"{name} if {{\n    {inner}\n}}")
        return f"not {name}"


# ── Public API ───────────────────────────────────────────────────────


def translate_constraint_to_rego(
    constraint: Constraint,
    *,
    prefix: str = "_h",
) -> Tuple[str, List[str]]:
    """
    Translate a single parsed constraint AST into Rego expression(s).

    Args:
        constraint: Parsed constraint AST node.
        prefix: Prefix for generated helper rule names.

    Returns:
        A tuple of ``(main_expression, helper_rules)`` where
        *helper_rules* is a list of complete Rego rule strings that
        must be emitted before the main rule.
    """
    builder = _RegoBuilder(prefix=prefix)
    main = builder.expr(constraint)
    return main, builder.helpers


def translate_to_rego(
    constraints: List[str],
    *,
    package_name: str = "mandate.policy",
    rule_name: str = "allow",
    mission_id: str = "",
) -> str:
    """
    Translate a list of MANDATE constraint strings into an OPA/Rego policy.

    All constraints are combined with implicit AND (they all appear as
    separate lines inside a single Rego rule body).

    Args:
        constraints: Raw MANDATE constraint strings.
        package_name: Rego package declaration (default ``mandate.policy``).
        rule_name: Name of the allow rule (default ``allow``).
        mission_id: Optional mission identifier for the policy header comment.

    Returns:
        Complete Rego policy source as a string.

    Raises:
        mandate.constraints.ConstraintError: If any constraint string is
            syntactically invalid.
        TranslationError: If translation encounters an unsupported node type.
    """
    lines: List[str] = []

    # Header
    lines.append(f"package {package_name}")
    lines.append("")
    lines.append("import rego.v1")
    lines.append("")

    if mission_id:
        lines.append(f"# MANDATE mission: {mission_id}")
        lines.append(f"# Auto-generated from {len(constraints)} constraint(s)")
        lines.append("")

    lines.append(f"default {rule_name} := false")
    lines.append("")

    # Translate each constraint
    all_helpers: List[str] = []
    body_lines: List[str] = []
    helper_offset = 0

    for text in constraints:
        ast = parse_constraint(text)
        builder = _RegoBuilder(prefix="_h")
        builder._counter = helper_offset
        main_expr = builder.expr(ast)
        all_helpers.extend(builder.helpers)
        helper_offset = builder._counter

        # Comment with original constraint
        body_lines.append(f"    # {text}")
        # Each line of the expression indented inside the rule body
        for part in main_expr.split("\n"):
            stripped = part.strip()
            if stripped:
                body_lines.append(f"    {stripped}")

    # Emit helpers before the main rule
    for helper in all_helpers:
        lines.append(helper)
        lines.append("")

    # Main rule
    lines.append(f"{rule_name} if {{")
    lines.extend(body_lines)
    lines.append("}")
    lines.append("")

    return "\n".join(lines)
