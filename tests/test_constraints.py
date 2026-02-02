"""Tests for the MANDATE constraint grammar parser."""

from __future__ import annotations

import pytest

from mandate.constraints import (
    parse_constraint,
    validate_constraint,
    evaluate_constraint,
    evaluate_constraint_string,
    ConstraintError,
    EvaluationError,
    ComparisonPredicate,
    InPredicate,
    RequiresPredicate,
    ForbidsPredicate,
    AndExpr,
    OrExpr,
    NotExpr,
    Comparator,
)


class TestConstraintParsing:
    """Test constraint parsing into AST."""
    
    def test_simple_comparison_eq(self):
        ast = parse_constraint("status == 'active'")
        assert isinstance(ast, ComparisonPredicate)
        assert str(ast.field) == "status"
        assert ast.comparator == Comparator.EQ
        assert ast.value.value == "active"
    
    def test_simple_comparison_le(self):
        ast = parse_constraint("execution.duration <= PT4H")
        assert isinstance(ast, ComparisonPredicate)
        assert str(ast.field) == "execution.duration"
        assert ast.comparator == Comparator.LE
        assert ast.value.value == "PT4H"
        assert ast.value.value_type == "duration"
    
    def test_numeric_comparison(self):
        ast = parse_constraint("outcome.confidence >= 0.8")
        assert isinstance(ast, ComparisonPredicate)
        assert ast.value.value == 0.8
        assert ast.value.value_type == "number"
    
    def test_in_predicate(self):
        ast = parse_constraint("data.classification IN ['UNCLASSIFIED', 'CUI']")
        assert isinstance(ast, InPredicate)
        assert str(ast.field) == "data.classification"
        assert len(ast.values.values) == 2
        assert ast.values.values[0].value == "UNCLASSIFIED"
    
    def test_requires_predicate(self):
        ast = parse_constraint("REQUIRES network_access")
        assert isinstance(ast, RequiresPredicate)
        assert ast.capability == "network_access"
    
    def test_forbids_predicate(self):
        ast = parse_constraint("FORBIDS external_api")
        assert isinstance(ast, ForbidsPredicate)
        assert ast.action == "external_api"
    
    def test_and_expression(self):
        ast = parse_constraint("status == 'active' AND priority > 5")
        assert isinstance(ast, AndExpr)
        assert isinstance(ast.left, ComparisonPredicate)
        assert isinstance(ast.right, ComparisonPredicate)
    
    def test_or_expression(self):
        ast = parse_constraint("status == 'active' OR status == 'pending'")
        assert isinstance(ast, OrExpr)
    
    def test_not_expression(self):
        ast = parse_constraint("NOT status == 'disabled'")
        assert isinstance(ast, NotExpr)
        assert isinstance(ast.operand, ComparisonPredicate)
    
    def test_complex_expression(self):
        ast = parse_constraint("REQUIRES network_access AND NOT FORBIDS external_api")
        assert isinstance(ast, AndExpr)
        assert isinstance(ast.left, RequiresPredicate)
        assert isinstance(ast.right, NotExpr)
    
    def test_parentheses(self):
        ast = parse_constraint("(status == 'active' OR status == 'pending') AND priority > 5")
        assert isinstance(ast, AndExpr)
        assert isinstance(ast.left, OrExpr)
    
    def test_nested_field(self):
        ast = parse_constraint("risk.assessment.score != 'HIGH'")
        assert isinstance(ast, ComparisonPredicate)
        assert str(ast.field) == "risk.assessment.score"
    
    def test_boolean_values(self):
        ast = parse_constraint("enabled == true")
        assert isinstance(ast, ComparisonPredicate)
        assert ast.value.value is True
        assert ast.value.value_type == "boolean"
    
    def test_timestamp_value(self):
        ast = parse_constraint("deadline <= 2026-02-06T17:00:00-05:00")
        assert isinstance(ast, ComparisonPredicate)
        assert ast.value.value_type == "timestamp"
    
    def test_contains_comparator(self):
        ast = parse_constraint("tags CONTAINS 'urgent'")
        assert isinstance(ast, ComparisonPredicate)
        assert ast.comparator == Comparator.CONTAINS
    
    def test_matches_comparator(self):
        ast = parse_constraint("filename MATCHES '^report_.*\\.pdf$'")
        assert isinstance(ast, ComparisonPredicate)
        assert ast.comparator == Comparator.MATCHES


class TestConstraintValidation:
    """Test constraint validation."""
    
    def test_valid_constraints(self):
        valid = [
            "status == 'active'",
            "execution.duration <= PT4H",
            "data.classification IN ['UNCLASSIFIED', 'CUI']",
            "REQUIRES network_access AND NOT FORBIDS external_api",
            "outcome.confidence >= 0.8 AND risk.score != 'HIGH'",
            "(a == 1 OR b == 2) AND c == 3",
        ]
        for constraint in valid:
            assert validate_constraint(constraint), f"Should be valid: {constraint}"
    
    def test_invalid_constraints(self):
        invalid = [
            "",
            "status ==",
            "== 'active'",
            "REQUIRES",
            "IN ['a', 'b']",
            "status ??? 'active'",
        ]
        for constraint in invalid:
            assert not validate_constraint(constraint), f"Should be invalid: {constraint}"


class TestConstraintEvaluation:
    """Test constraint evaluation against state."""
    
    def test_simple_equality(self):
        state = {"status": "active"}
        assert evaluate_constraint_string("status == 'active'", state)
        assert not evaluate_constraint_string("status == 'inactive'", state)
    
    def test_numeric_comparison(self):
        state = {"confidence": 0.85}
        assert evaluate_constraint_string("confidence >= 0.8", state)
        assert not evaluate_constraint_string("confidence >= 0.9", state)
    
    def test_nested_field(self):
        state = {"execution": {"duration": 3600}}
        assert evaluate_constraint_string("execution.duration <= 7200", state)
    
    def test_in_predicate(self):
        state = {"classification": "CUI"}
        assert evaluate_constraint_string("classification IN ['UNCLASSIFIED', 'CUI']", state)
        assert not evaluate_constraint_string("classification IN ['SECRET', 'TOP_SECRET']", state)
    
    def test_requires_predicate(self):
        state = {"capabilities": ["network_access", "file_read"]}
        assert evaluate_constraint_string("REQUIRES network_access", state)
        assert not evaluate_constraint_string("REQUIRES admin_access", state)
    
    def test_forbids_predicate(self):
        state = {"forbidden_actions": ["delete_data"]}
        # FORBIDS action returns True if action IS forbidden
        assert not evaluate_constraint_string("FORBIDS external_api", state)  # Not in forbidden list
        assert evaluate_constraint_string("FORBIDS delete_data", state)  # Is in forbidden list
        
        # Typical usage: NOT FORBIDS means "action is allowed"
        assert evaluate_constraint_string("NOT FORBIDS external_api", state)  # Allowed
        assert not evaluate_constraint_string("NOT FORBIDS delete_data", state)  # Not allowed
    
    def test_and_expression(self):
        state = {"status": "active", "priority": 7}
        assert evaluate_constraint_string("status == 'active' AND priority > 5", state)
        assert not evaluate_constraint_string("status == 'active' AND priority > 10", state)
    
    def test_or_expression(self):
        state = {"status": "pending"}
        assert evaluate_constraint_string("status == 'active' OR status == 'pending'", state)
        assert not evaluate_constraint_string("status == 'active' OR status == 'completed'", state)
    
    def test_not_expression(self):
        state = {"status": "active"}
        assert evaluate_constraint_string("NOT status == 'disabled'", state)
        assert not evaluate_constraint_string("NOT status == 'active'", state)
    
    def test_complex_expression(self):
        state = {
            "capabilities": ["network_access"],
            "forbidden_actions": [],
        }
        assert evaluate_constraint_string(
            "REQUIRES network_access AND NOT FORBIDS external_api", 
            state
        )
    
    def test_missing_field_raises(self):
        state = {}
        with pytest.raises(KeyError):
            evaluate_constraint_string("status == 'active'", state)
    
    def test_contains_comparator(self):
        state = {"tags": ["urgent", "review"]}
        assert evaluate_constraint_string("tags CONTAINS 'urgent'", state)
        assert not evaluate_constraint_string("tags CONTAINS 'archived'", state)


class TestPaperExamples:
    """Test the specific examples from the MANDATE paper."""
    
    def test_paper_example_duration(self):
        # "execution.duration <= PT4H" (ISO 8601 duration: max 4 hours)
        ast = parse_constraint("execution.duration <= PT4H")
        assert validate_constraint("execution.duration <= PT4H")
    
    def test_paper_example_classification(self):
        # "data.classification IN ['UNCLASSIFIED', 'CUI']"
        ast = parse_constraint("data.classification IN ['UNCLASSIFIED', 'CUI']")
        state = {"data": {"classification": "CUI"}}
        assert evaluate_constraint(ast, state)
    
    def test_paper_example_requires_forbids(self):
        # "REQUIRES network_access AND NOT FORBIDS external_api"
        ast = parse_constraint("REQUIRES network_access AND NOT FORBIDS external_api")
        state = {
            "capabilities": ["network_access", "file_read"],
            "forbidden_actions": []
        }
        assert evaluate_constraint(ast, state)
    
    def test_paper_example_confidence_risk(self):
        # "outcome.confidence >= 0.8 AND risk.score != 'HIGH'"
        ast = parse_constraint("outcome.confidence >= 0.8 AND risk.score != 'HIGH'")
        state = {
            "outcome": {"confidence": 0.85},
            "risk": {"score": "MEDIUM"}
        }
        assert evaluate_constraint(ast, state)
