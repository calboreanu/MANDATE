"""
MANDATE Constraint → Cedar Policy Translator

Translates parsed MANDATE constraint ASTs into Amazon Cedar policy
statements.  Cedar uses a principal–action–resource model; MANDATE
constraints map to the ``when`` clause of a ``permit`` or ``forbid``
policy.

Context model expected by generated policies::

    context: {
        "<field.path>": <value>,             // Dotted fields as nested records
        "capabilities": ["cap1", ...],       // For REQUIRES predicates
        "forbidden_actions": ["act1", ...]   // For FORBIDS predicates
    }

Usage::

    from mandate.translators.cedar import translate_to_cedar

    constraints = [
        "target.scope IN ['10.0.1.0/24', 'acme.example.com']",
        "execution.duration <= PT4H",
        "FORBIDS data_exfiltration",
    ]
    policy = translate_to_cedar(constraints, namespace="Mandate")
    print(policy)

Produces::

    // MANDATE constraint policy
    permit (
        principal,
        action == Action::"execute",
        resource
    )
    when {
        context.target.scope in ["10.0.1.0/24", "acme.example.com"] &&
        context.execution.duration <= "PT4H" &&
        context.forbidden_actions.contains("data_exfiltration")
    };

Limitations:
    - **MATCHES**: Cedar uses ``like`` with glob-style wildcards (``*`` and
      ``?``), not regular expressions.  The translator emits ``like`` with
      the original pattern and a warning comment.  For regex-heavy constraints,
      prefer the OPA/Rego translator.
    - **Temporal values**: Durations and timestamps are emitted as opaque
      strings.  Cedar does not have built-in temporal arithmetic; use
      extension types or pre-compute numeric equivalents.
"""

from __future__ import annotations

from typing import List, Tuple

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
from mandate.translators.rego import TranslationError  # shared exception


# ── Value Formatting ─────────────────────────────────────────────────


def _cedar_field(field: FieldRef) -> str:
    """Convert a FieldRef to a Cedar context path: ``context.field.sub``."""
    return "context." + ".".join(field.parts)


def _cedar_value(value: LiteralValue) -> str:
    """Convert a LiteralValue to a Cedar literal."""
    if value.value_type == "string":
        return f'"{value.value}"'
    elif value.value_type == "number":
        if isinstance(value.value, float):
            # Cedar does not support floating-point natively; use decimal
            # extension type in production.  Here we emit as a string with
            # a comment.
            return f'decimal("{value.value}")'
        return str(value.value)
    elif value.value_type == "boolean":
        return "true" if value.value else "false"
    elif value.value_type in ("duration", "timestamp"):
        return f'"{value.value}"'
    return str(value.value)


def _cedar_set(values: SetValue) -> str:
    """Convert a SetValue to a Cedar set literal ``[v1, v2, ...]``."""
    items = ", ".join(_cedar_value(v) for v in values.values)
    return "[" + items + "]"


# ── AST → Cedar Expression Builder ──────────────────────────────────


_COMPARATOR_MAP = {
    Comparator.EQ: "==",
    Comparator.NE: "!=",
    Comparator.LT: "<",
    Comparator.LE: "<=",
    Comparator.GT: ">",
    Comparator.GE: ">=",
}


def _cedar_expr(node: Constraint) -> str:
    """
    Recursively translate a constraint AST into a Cedar condition expression.

    Cedar supports inline ``&&``, ``||``, and ``!`` so no helper rules
    are needed (unlike Rego).
    """
    if isinstance(node, ComparisonPredicate):
        field = _cedar_field(node.field)
        value = _cedar_value(node.value)

        if node.comparator == Comparator.CONTAINS:
            return f"{field}.contains({value})"
        if node.comparator == Comparator.MATCHES:
            # Cedar uses `like` with glob patterns, not regex.
            # Emit with a warning comment.
            return f'{field} like "{node.value.value}"'
        op = _COMPARATOR_MAP[node.comparator]
        return f"{field} {op} {value}"

    if isinstance(node, InPredicate):
        return f"{_cedar_field(node.field)} in {_cedar_set(node.values)}"

    if isinstance(node, RequiresPredicate):
        return f'context.capabilities.contains("{node.capability}")'

    if isinstance(node, ForbidsPredicate):
        return f'context.forbidden_actions.contains("{node.action}")'

    if isinstance(node, AndExpr):
        left = _cedar_expr(node.left)
        right = _cedar_expr(node.right)
        return f"{left} &&\n    {right}"

    if isinstance(node, OrExpr):
        left = _cedar_expr(node.left)
        right = _cedar_expr(node.right)
        return f"({left} ||\n    {right})"

    if isinstance(node, NotExpr):
        inner = _cedar_expr(node.operand)
        # Wrap in parens if it's a compound expression
        if isinstance(node.operand, (AndExpr, OrExpr)):
            return f"!({inner})"
        return f"!{inner}"

    raise TranslationError(f"Unknown constraint node: {type(node).__name__}")


# ── Public API ───────────────────────────────────────────────────────


def translate_constraint_to_cedar(constraint: Constraint) -> str:
    """
    Translate a single parsed constraint AST into a Cedar condition expression.

    Args:
        constraint: Parsed constraint AST node.

    Returns:
        A Cedar expression string suitable for use inside a ``when { ... }``
        block.
    """
    return _cedar_expr(constraint)


def translate_to_cedar(
    constraints: List[str],
    *,
    namespace: str = "Mandate",
    action_type: str = "execute",
    mission_id: str = "",
    policy_effect: str = "permit",
) -> str:
    """
    Translate a list of MANDATE constraint strings into a Cedar policy.

    All constraints are combined with ``&&`` inside a single ``when``
    clause.

    Args:
        constraints: Raw MANDATE constraint strings.
        namespace: Cedar namespace for action types (default ``Mandate``).
        action_type: The Cedar action name (default ``execute``).
        mission_id: Optional mission identifier for the policy header.
        policy_effect: ``permit`` or ``forbid`` (default ``permit``).

    Returns:
        Complete Cedar policy source as a string.

    Raises:
        mandate.constraints.ConstraintError: If any constraint string is
            syntactically invalid.
        TranslationError: If translation encounters an unsupported node type.
    """
    lines: List[str] = []

    # Header
    lines.append("// MANDATE constraint policy — auto-generated")
    if mission_id:
        lines.append(f"// Mission: {mission_id}")
    lines.append(f"// Constraints: {len(constraints)}")
    has_matches = any("MATCHES" in c for c in constraints)
    if has_matches:
        lines.append(
            '// NOTE: MATCHES translated to Cedar "like" (glob patterns, not regex)'
        )
    lines.append("")

    # Policy head
    lines.append(f"{policy_effect} (")
    lines.append("    principal,")
    lines.append(f'    action == {namespace}::Action::"{action_type}",')
    lines.append("    resource")
    lines.append(")")

    # Build when clause
    condition_parts: List[str] = []
    for text in constraints:
        ast = parse_constraint(text)
        cedar_expr = _cedar_expr(ast)
        condition_parts.append(cedar_expr)

    if condition_parts:
        lines.append("when {")
        # Join with && and indent
        joined = " &&\n    ".join(condition_parts)
        lines.append(f"    {joined}")
        lines.append("};")
    else:
        lines.append(";")

    lines.append("")
    return "\n".join(lines)
