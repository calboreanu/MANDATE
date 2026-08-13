"""
Tests for MANDATE constraint policy translators (OPA/Rego and Cedar).

Covers:
- Individual predicate translation (comparison, IN, REQUIRES, FORBIDS)
- Logical operators (AND, OR, NOT)
- Complex/nested expressions
- Value type handling (string, number, boolean, duration, timestamp)
- Full policy generation with headers, helpers, and structure
- CLI translate subcommand integration
- Round-trip: parse → translate → verify structure
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from mandate.constraints import (
    parse_constraint,
    ComparisonPredicate,
    InPredicate,
    RequiresPredicate,
    ForbidsPredicate,
    AndExpr,
    OrExpr,
    NotExpr,
    Comparator,
    ConstraintError,
)
from mandate.translators.rego import (
    translate_to_rego,
    translate_constraint_to_rego,
    TranslationError,
)
from mandate.translators.cedar import (
    translate_to_cedar,
    translate_constraint_to_cedar,
)


# ── Rego: Individual Predicate Translation ───────────────────────────


class TestRegoPredicates:
    """Test Rego translation of individual predicate types."""

    def test_comparison_eq_string(self):
        ast = parse_constraint("status == 'active'")
        expr, helpers = translate_constraint_to_rego(ast)
        assert expr == 'input.status == "active"'
        assert helpers == []

    def test_comparison_ne(self):
        ast = parse_constraint("risk.score != 'HIGH'")
        expr, _ = translate_constraint_to_rego(ast)
        assert expr == 'input.risk.score != "HIGH"'

    def test_comparison_lt(self):
        ast = parse_constraint("priority < 10")
        expr, _ = translate_constraint_to_rego(ast)
        assert expr == "input.priority < 10"

    def test_comparison_le_duration(self):
        ast = parse_constraint("execution.duration <= PT4H")
        expr, _ = translate_constraint_to_rego(ast)
        assert expr == 'input.execution.duration <= "PT4H"'

    def test_comparison_gt(self):
        ast = parse_constraint("priority > 5")
        expr, _ = translate_constraint_to_rego(ast)
        assert expr == "input.priority > 5"

    def test_comparison_ge_float(self):
        ast = parse_constraint("outcome.confidence >= 0.8")
        expr, _ = translate_constraint_to_rego(ast)
        assert expr == "input.outcome.confidence >= 0.8"

    def test_comparison_contains(self):
        ast = parse_constraint("tags CONTAINS 'urgent'")
        expr, _ = translate_constraint_to_rego(ast)
        assert expr == 'contains(input.tags, "urgent")'

    def test_comparison_matches(self):
        ast = parse_constraint("filename MATCHES '^report_.*\\.pdf$'")
        expr, _ = translate_constraint_to_rego(ast)
        assert 'regex.match(' in expr
        assert 'input.filename' in expr

    def test_comparison_timestamp(self):
        ast = parse_constraint("deadline <= 2026-02-06T17:00:00-05:00")
        expr, _ = translate_constraint_to_rego(ast)
        assert expr == 'input.deadline <= "2026-02-06T17:00:00-05:00"'

    def test_comparison_boolean(self):
        ast = parse_constraint("enabled == true")
        expr, _ = translate_constraint_to_rego(ast)
        assert expr == "input.enabled == true"

    def test_comparison_boolean_false(self):
        ast = parse_constraint("debug == false")
        expr, _ = translate_constraint_to_rego(ast)
        assert expr == "input.debug == false"

    def test_in_predicate(self):
        ast = parse_constraint("data.classification IN ['UNCLASSIFIED', 'CUI']")
        expr, _ = translate_constraint_to_rego(ast)
        assert expr == 'input.data.classification in {"UNCLASSIFIED", "CUI"}'

    def test_in_predicate_numbers(self):
        ast = parse_constraint("severity IN [1, 2, 3]")
        expr, _ = translate_constraint_to_rego(ast)
        assert expr == "input.severity in {1, 2, 3}"

    def test_requires(self):
        ast = parse_constraint("REQUIRES network_access")
        expr, _ = translate_constraint_to_rego(ast)
        assert expr == '"network_access" in input.capabilities'

    def test_forbids(self):
        ast = parse_constraint("FORBIDS data_exfiltration")
        expr, _ = translate_constraint_to_rego(ast)
        assert expr == '"data_exfiltration" in input.forbidden_actions'


# ── Rego: Logical Operators ──────────────────────────────────────────


class TestRegoLogicalOps:
    """Test Rego translation of AND, OR, NOT."""

    def test_and_two_predicates(self):
        ast = parse_constraint("status == 'active' AND priority > 5")
        expr, helpers = translate_constraint_to_rego(ast)
        assert 'input.status == "active"' in expr
        assert "input.priority > 5" in expr
        assert helpers == []

    def test_and_chain(self):
        ast = parse_constraint(
            "a == 1 AND b == 2 AND c == 3"
        )
        expr, _ = translate_constraint_to_rego(ast)
        assert "input.a == 1" in expr
        assert "input.b == 2" in expr
        assert "input.c == 3" in expr

    def test_or_creates_helper(self):
        ast = parse_constraint("status == 'active' OR status == 'pending'")
        expr, helpers = translate_constraint_to_rego(ast)
        # expr should be just a helper name reference
        assert helpers  # at least one helper
        # Helper should contain two rule definitions with same name
        helper_text = helpers[0]
        assert "if {" in helper_text
        assert 'input.status == "active"' in helper_text
        assert 'input.status == "pending"' in helper_text

    def test_not_creates_helper(self):
        ast = parse_constraint("NOT FORBIDS external_api")
        expr, helpers = translate_constraint_to_rego(ast)
        assert expr.startswith("not ")
        assert len(helpers) == 1
        assert '"external_api" in input.forbidden_actions' in helpers[0]

    def test_requires_and_not_forbids(self):
        """Paper example: REQUIRES network_access AND NOT FORBIDS external_api."""
        ast = parse_constraint("REQUIRES network_access AND NOT FORBIDS external_api")
        expr, helpers = translate_constraint_to_rego(ast)
        assert '"network_access" in input.capabilities' in expr
        assert "not " in expr
        assert len(helpers) == 1

    def test_or_with_and(self):
        """Parenthesised OR inside AND."""
        ast = parse_constraint(
            "(status == 'active' OR status == 'pending') AND priority > 5"
        )
        expr, helpers = translate_constraint_to_rego(ast)
        assert "input.priority > 5" in expr
        # OR should produce a helper
        assert len(helpers) == 1


# ── Rego: Full Policy Generation ─────────────────────────────────────


class TestRegoPolicy:
    """Test full Rego policy generation."""

    def test_basic_policy_structure(self):
        policy = translate_to_rego(
            ["status == 'active'"],
            package_name="test.pkg",
            rule_name="allow",
        )
        assert "package test.pkg" in policy
        assert "import rego.v1" in policy
        assert "default allow := false" in policy
        assert "allow if {" in policy
        assert 'input.status == "active"' in policy

    def test_policy_with_mission_id(self):
        policy = translate_to_rego(
            ["FORBIDS bad_action"],
            mission_id="MANDATE-TEST-001",
        )
        assert "MANDATE-TEST-001" in policy
        assert "1 constraint(s)" in policy

    def test_multiple_constraints(self):
        policy = translate_to_rego([
            "target.scope IN ['10.0.1.0/24', 'acme.example.com']",
            "execution.duration <= PT4H",
            "FORBIDS data_exfiltration",
            "FORBIDS destructive_action",
        ])
        assert "input.target.scope in" in policy
        assert 'input.execution.duration <= "PT4H"' in policy
        assert '"data_exfiltration" in input.forbidden_actions' in policy
        assert '"destructive_action" in input.forbidden_actions' in policy
        # Comments with original constraints
        assert "# target.scope IN" in policy
        assert "# FORBIDS data_exfiltration" in policy

    def test_helpers_before_main_rule(self):
        """OR requires helper rules, which must appear before the main rule."""
        policy = translate_to_rego([
            "status == 'active' OR status == 'pending'",
            "priority > 5",
        ])
        # Helper should be defined before the allow rule
        helper_pos = policy.find("_h_")
        allow_pos = policy.find("allow if {")
        # First occurrence should be the helper definition
        assert helper_pos < allow_pos

    def test_custom_rule_name(self):
        policy = translate_to_rego(
            ["status == 'active'"],
            rule_name="enforce",
        )
        assert "default enforce := false" in policy
        assert "enforce if {" in policy

    def test_empty_constraints(self):
        policy = translate_to_rego([])
        assert "allow if {" in policy
        assert "default allow := false" in policy

    def test_invalid_constraint_raises(self):
        with pytest.raises(ConstraintError):
            translate_to_rego(["this is not valid ??? syntax"])


# ── Cedar: Individual Predicate Translation ──────────────────────────


class TestCedarPredicates:
    """Test Cedar translation of individual predicate types."""

    def test_comparison_eq_string(self):
        ast = parse_constraint("status == 'active'")
        expr = translate_constraint_to_cedar(ast)
        assert expr == 'context.status == "active"'

    def test_comparison_ne(self):
        ast = parse_constraint("risk.score != 'HIGH'")
        expr = translate_constraint_to_cedar(ast)
        assert expr == 'context.risk.score != "HIGH"'

    def test_comparison_le_duration(self):
        ast = parse_constraint("execution.duration <= PT4H")
        expr = translate_constraint_to_cedar(ast)
        assert expr == 'context.execution.duration <= "PT4H"'

    def test_comparison_ge_float(self):
        ast = parse_constraint("outcome.confidence >= 0.8")
        expr = translate_constraint_to_cedar(ast)
        assert 'decimal("0.8")' in expr

    def test_comparison_integer(self):
        ast = parse_constraint("priority > 5")
        expr = translate_constraint_to_cedar(ast)
        assert expr == "context.priority > 5"

    def test_comparison_contains(self):
        ast = parse_constraint("tags CONTAINS 'urgent'")
        expr = translate_constraint_to_cedar(ast)
        assert expr == 'context.tags.contains("urgent")'

    def test_comparison_matches(self):
        ast = parse_constraint("filename MATCHES '^report_.*'")
        expr = translate_constraint_to_cedar(ast)
        assert "like" in expr

    def test_comparison_boolean(self):
        ast = parse_constraint("enabled == true")
        expr = translate_constraint_to_cedar(ast)
        assert expr == "context.enabled == true"

    def test_comparison_timestamp(self):
        ast = parse_constraint("deadline <= 2026-02-06T17:00:00-05:00")
        expr = translate_constraint_to_cedar(ast)
        assert '"2026-02-06T17:00:00-05:00"' in expr

    def test_in_predicate(self):
        ast = parse_constraint("data.classification IN ['UNCLASSIFIED', 'CUI']")
        expr = translate_constraint_to_cedar(ast)
        assert expr == 'context.data.classification in ["UNCLASSIFIED", "CUI"]'

    def test_requires(self):
        ast = parse_constraint("REQUIRES network_access")
        expr = translate_constraint_to_cedar(ast)
        assert expr == 'context.capabilities.contains("network_access")'

    def test_forbids(self):
        ast = parse_constraint("FORBIDS data_exfiltration")
        expr = translate_constraint_to_cedar(ast)
        assert expr == 'context.forbidden_actions.contains("data_exfiltration")'


# ── Cedar: Logical Operators ─────────────────────────────────────────


class TestCedarLogicalOps:
    """Test Cedar translation of AND, OR, NOT."""

    def test_and(self):
        ast = parse_constraint("status == 'active' AND priority > 5")
        expr = translate_constraint_to_cedar(ast)
        assert "&&" in expr
        assert 'context.status == "active"' in expr
        assert "context.priority > 5" in expr

    def test_or(self):
        ast = parse_constraint("status == 'active' OR status == 'pending'")
        expr = translate_constraint_to_cedar(ast)
        assert "||" in expr
        assert 'context.status == "active"' in expr
        assert 'context.status == "pending"' in expr

    def test_not_simple(self):
        ast = parse_constraint("NOT FORBIDS external_api")
        expr = translate_constraint_to_cedar(ast)
        assert expr == '!context.forbidden_actions.contains("external_api")'

    def test_not_compound(self):
        """NOT on an AND expression should wrap in parens."""
        ast = parse_constraint("NOT (a == 1 AND b == 2)")
        expr = translate_constraint_to_cedar(ast)
        assert expr.startswith("!(")

    def test_requires_and_not_forbids(self):
        ast = parse_constraint("REQUIRES network_access AND NOT FORBIDS external_api")
        expr = translate_constraint_to_cedar(ast)
        assert 'context.capabilities.contains("network_access")' in expr
        assert '!context.forbidden_actions.contains("external_api")' in expr
        assert "&&" in expr

    def test_or_with_and(self):
        ast = parse_constraint(
            "(status == 'active' OR status == 'pending') AND priority > 5"
        )
        expr = translate_constraint_to_cedar(ast)
        assert "||" in expr
        assert "&&" in expr
        assert "context.priority > 5" in expr


# ── Cedar: Full Policy Generation ────────────────────────────────────


class TestCedarPolicy:
    """Test full Cedar policy generation."""

    def test_basic_policy_structure(self):
        policy = translate_to_cedar(
            ["status == 'active'"],
            namespace="TestNS",
        )
        assert "// MANDATE constraint policy" in policy
        assert "permit (" in policy
        assert 'action == TestNS::Action::"execute"' in policy
        assert "when {" in policy
        assert 'context.status == "active"' in policy
        assert "};" in policy

    def test_policy_with_mission_id(self):
        policy = translate_to_cedar(
            ["FORBIDS bad_action"],
            mission_id="MANDATE-TEST-001",
        )
        assert "Mission: MANDATE-TEST-001" in policy
        assert "Constraints: 1" in policy

    def test_multiple_constraints_joined_with_and(self):
        policy = translate_to_cedar([
            "target.scope IN ['10.0.1.0/24', 'acme.example.com']",
            "execution.duration <= PT4H",
            "FORBIDS data_exfiltration",
        ])
        assert "&&" in policy
        # All constraints should appear
        assert "context.target.scope in" in policy
        assert 'context.execution.duration <= "PT4H"' in policy
        assert 'context.forbidden_actions.contains("data_exfiltration")' in policy

    def test_matches_warning_comment(self):
        policy = translate_to_cedar(["filename MATCHES '^report_.*'"])
        assert "like" in policy.lower() or "MATCHES" in policy
        assert "NOTE:" in policy  # Warning about glob vs regex

    def test_forbid_effect(self):
        policy = translate_to_cedar(
            ["FORBIDS bad_action"],
            policy_effect="forbid",
        )
        assert "forbid (" in policy

    def test_custom_namespace(self):
        policy = translate_to_cedar(
            ["status == 'active'"],
            namespace="MyApp",
        )
        assert 'MyApp::Action::"execute"' in policy

    def test_custom_action_type(self):
        policy = translate_to_cedar(
            ["status == 'active'"],
            action_type="assess",
        )
        assert '"assess"' in policy

    def test_empty_constraints(self):
        policy = translate_to_cedar([])
        # Should still produce a valid policy shell
        assert "permit (" in policy
        assert ";" in policy

    def test_invalid_constraint_raises(self):
        with pytest.raises(ConstraintError):
            translate_to_cedar(["not a valid constraint ???"])


# ── Round-Trip Tests ─────────────────────────────────────────────────


class TestRoundTrip:
    """Test parse → translate → verify structure."""

    PAPER_EXAMPLES = [
        "execution.duration <= PT4H",
        "data.classification IN ['UNCLASSIFIED', 'CUI']",
        "REQUIRES network_access AND NOT FORBIDS external_api",
        "outcome.confidence >= 0.8 AND risk.score != 'HIGH'",
    ]

    def test_all_paper_examples_to_rego(self):
        """Every paper example should translate to valid Rego."""
        for text in self.PAPER_EXAMPLES:
            ast = parse_constraint(text)
            expr, helpers = translate_constraint_to_rego(ast)
            assert expr, f"Empty expression for: {text}"
            # Expression should reference input.*
            assert "input." in expr or any("input." in h for h in helpers)

    def test_all_paper_examples_to_cedar(self):
        """Every paper example should translate to valid Cedar."""
        for text in self.PAPER_EXAMPLES:
            ast = parse_constraint(text)
            expr = translate_constraint_to_cedar(ast)
            assert expr, f"Empty expression for: {text}"
            # Expression should reference context.*
            assert "context." in expr

    def test_paper_examples_full_rego_policy(self):
        policy = translate_to_rego(self.PAPER_EXAMPLES, mission_id="PAPER-EXAMPLES")
        assert "package mandate.policy" in policy
        assert "allow if {" in policy
        # All four constraints should appear as comments
        for text in self.PAPER_EXAMPLES:
            assert f"# {text}" in policy

    def test_paper_examples_full_cedar_policy(self):
        policy = translate_to_cedar(self.PAPER_EXAMPLES, mission_id="PAPER-EXAMPLES")
        assert "permit (" in policy
        assert "when {" in policy

    def test_normal_mission_constraints_rego(self):
        """Translate the constraints from examples/normal_mission.json."""
        constraints = [
            "target.scope IN ['10.0.1.0/24', 'acme.example.com']",
            "execution.duration <= PT4H",
            "FORBIDS data_exfiltration",
            "FORBIDS destructive_action",
        ]
        policy = translate_to_rego(constraints, package_name="mandate.nm001")
        assert "package mandate.nm001" in policy
        # No helpers needed for all-AND constraints
        assert "_h_" not in policy

    def test_normal_mission_constraints_cedar(self):
        constraints = [
            "target.scope IN ['10.0.1.0/24', 'acme.example.com']",
            "execution.duration <= PT4H",
            "FORBIDS data_exfiltration",
            "FORBIDS destructive_action",
        ]
        policy = translate_to_cedar(constraints)
        # All joined with &&
        assert policy.count("&&") == 3


# ── CLI Integration Tests ────────────────────────────────────────────


class TestCLITranslate:
    """Test the 'mandate translate' CLI subcommand."""

    @pytest.fixture
    def mission_path(self, tmp_path: Path) -> Path:
        mission = {
            "mission_id": "MANDATE-CLI-TEST",
            "intent": "Test the translate CLI",
            "constraints": [
                "target.scope IN ['192.168.1.0/24']",
                "FORBIDS data_exfiltration",
            ],
        }
        p = tmp_path / "mission.json"
        p.write_text(json.dumps(mission), encoding="utf-8")
        return p

    @pytest.fixture
    def mandate_path(self, tmp_path: Path) -> Path:
        """A mandate-as-code artifact with constraints in anchor."""
        artifact = {
            "mandate_id": "MANDATE-ART-001",
            "anchor": {
                "constraints": [
                    "execution.duration <= PT4H",
                    "REQUIRES network_access",
                ],
            },
        }
        p = tmp_path / "mandate.json"
        p.write_text(json.dumps(artifact), encoding="utf-8")
        return p

    def test_translate_mission_to_rego(self, mission_path: Path):
        from mandate.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["translate", str(mission_path), "-f", "rego"])
        from mandate.cli import cmd_translate
        rc = cmd_translate(args)
        assert rc == 0

    def test_translate_mission_to_cedar(self, mission_path: Path):
        from mandate.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["translate", str(mission_path), "-f", "cedar"])
        from mandate.cli import cmd_translate
        rc = cmd_translate(args)
        assert rc == 0

    def test_translate_mandate_artifact_to_rego(self, mandate_path: Path):
        from mandate.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["translate", str(mandate_path), "-f", "rego"])
        from mandate.cli import cmd_translate
        rc = cmd_translate(args)
        assert rc == 0

    def test_translate_to_file(self, mission_path: Path, tmp_path: Path):
        from mandate.cli import build_parser
        out = tmp_path / "policy.rego"
        parser = build_parser()
        args = parser.parse_args([
            "translate", str(mission_path), "-f", "rego", "-o", str(out),
        ])
        from mandate.cli import cmd_translate
        rc = cmd_translate(args)
        assert rc == 0
        assert out.exists()
        content = out.read_text()
        assert "package mandate.policy" in content
        assert "allow if {" in content

    def test_translate_cedar_to_file(self, mission_path: Path, tmp_path: Path):
        from mandate.cli import build_parser
        out = tmp_path / "policy.cedar"
        parser = build_parser()
        args = parser.parse_args([
            "translate", str(mission_path), "-f", "cedar", "-o", str(out),
        ])
        from mandate.cli import cmd_translate
        rc = cmd_translate(args)
        assert rc == 0
        assert out.exists()
        content = out.read_text()
        assert "permit (" in content

    def test_translate_nonexistent_file(self, tmp_path: Path):
        from mandate.cli import build_parser
        parser = build_parser()
        args = parser.parse_args([
            "translate", str(tmp_path / "nope.json"), "-f", "rego",
        ])
        from mandate.cli import cmd_translate
        rc = cmd_translate(args)
        assert rc == 2

    def test_translate_invalid_json(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text("not json", encoding="utf-8")
        from mandate.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["translate", str(bad), "-f", "rego"])
        from mandate.cli import cmd_translate
        rc = cmd_translate(args)
        assert rc == 2

    def test_translate_no_constraints(self, tmp_path: Path):
        empty = tmp_path / "empty.json"
        empty.write_text('{"mission_id":"X","intent":"Y"}', encoding="utf-8")
        from mandate.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["translate", str(empty), "-f", "rego"])
        from mandate.cli import cmd_translate
        rc = cmd_translate(args)
        # Should return 2 since no constraints found
        assert rc == 2

    def test_translate_custom_package(self, mission_path: Path):
        from mandate.cli import build_parser
        parser = build_parser()
        args = parser.parse_args([
            "translate", str(mission_path), "-f", "rego",
            "--package", "custom.pkg",
        ])
        from mandate.cli import cmd_translate
        # Capture output via file
        import io, sys
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        rc = cmd_translate(args)
        sys.stdout = old_stdout
        assert rc == 0
        assert "package custom.pkg" in captured.getvalue()

    def test_translate_custom_namespace(self, mission_path: Path):
        from mandate.cli import build_parser
        parser = build_parser()
        args = parser.parse_args([
            "translate", str(mission_path), "-f", "cedar",
            "--namespace", "MyOrg",
        ])
        from mandate.cli import cmd_translate
        import io, sys
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        rc = cmd_translate(args)
        sys.stdout = old_stdout
        assert rc == 0
        assert 'MyOrg::Action::"execute"' in captured.getvalue()


# ── Edge Cases ───────────────────────────────────────────────────────


class TestEdgeCases:
    """Test edge cases and unusual inputs."""

    def test_deeply_nested_and(self):
        """Chain of many ANDs should produce flat Rego body."""
        text = "a == 1 AND b == 2 AND c == 3 AND d == 4"
        policy = translate_to_rego([text])
        assert "input.a == 1" in policy
        assert "input.d == 4" in policy

    def test_deeply_nested_field_path(self):
        text = "a.b.c.d.e == 'deep'"
        ast = parse_constraint(text)
        rego_expr, _ = translate_constraint_to_rego(ast)
        assert rego_expr == 'input.a.b.c.d.e == "deep"'
        cedar_expr = translate_constraint_to_cedar(ast)
        assert cedar_expr == 'context.a.b.c.d.e == "deep"'

    def test_negative_number(self):
        text = "temperature > -10"
        ast = parse_constraint(text)
        rego_expr, _ = translate_constraint_to_rego(ast)
        assert "input.temperature > -10" in rego_expr
        cedar_expr = translate_constraint_to_cedar(ast)
        assert "context.temperature > -10" in cedar_expr

    def test_integer_in_set(self):
        text = "severity IN [1, 2, 3]"
        ast = parse_constraint(text)
        rego_expr, _ = translate_constraint_to_rego(ast)
        assert "input.severity in {1, 2, 3}" in rego_expr

    def test_single_value_in_set(self):
        text = "env IN ['prod']"
        ast = parse_constraint(text)
        rego_expr, _ = translate_constraint_to_rego(ast)
        assert 'input.env in {"prod"}' in rego_expr

    def test_or_then_and_precedence(self):
        """a OR b AND c should parse as a OR (b AND c) due to precedence."""
        text = "a == 1 OR b == 2 AND c == 3"
        ast = parse_constraint(text)
        # AND binds tighter, so right side of OR is an AND
        assert isinstance(ast, OrExpr)
        assert isinstance(ast.right, AndExpr)

    def test_multiple_or_helpers_unique_names(self):
        """Multiple OR constraints should produce uniquely named helpers."""
        policy = translate_to_rego([
            "a == 1 OR b == 2",
            "c == 3 OR d == 4",
        ])
        # Should have two distinct helper sets
        assert "_h_1" in policy
        assert "_h_2" in policy
