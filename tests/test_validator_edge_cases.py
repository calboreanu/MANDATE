"""Tests for validator edge cases (v0.2.2 fixes)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from mandate.validator import validate_artifact, validate_hashes, validate_constraints
from mandate.hashing import compute_chain_hash_from_strings, compute_anchor_hash


def _create_temp_artifact(obj: dict) -> Path:
    """Helper to create a temporary JSON file."""
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(obj, f)
    f.close()
    return Path(f.name)


class TestEmptyTraceChainHash:
    """P0.1 fix: chain hash must be verified even for empty entries."""
    
    def test_empty_trace_correct_chain_hash(self):
        """Empty trace with correct chain_hash should pass."""
        # sha256(canonical_json([])) = "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
        expected_chain = compute_chain_hash_from_strings([])
        
        anchor = {
            "mission_intent": "Test",
            "minimum": {"test": True},
            "constraints": [],
        }
        anchor["anchor_hash"] = compute_anchor_hash(anchor)
        
        mandate = {
            "mandate_id": "TEST-001",
            "version": "0.64",
            "generated": "2026-02-02T12:00:00Z",
            "anchor": anchor,
            "courses_of_action": [{
                "coa_id": "COA-A",
                "approach": "Test",
                "task_dag": {"nodes": [{"id": "t1", "name": "Test"}], "edges": []},
                "risk_assessment": {"score": "LOW", "confidence_min": "HIGH", "confidence_target": "HIGH", "primary_factor": "Test"},
                "off_nominal_triggers": []
            }],
            "recommendation": {"primary_coa": "COA-A", "fallback_sequence": [], "rationale": "Test"},
            "trace": {
                "chain_hash": expected_chain,
                "entry_count": 0,
                "entries": []
            }
        }
        
        path = _create_temp_artifact(mandate)
        try:
            artifact_type, issues = validate_artifact(str(path))
            assert artifact_type == "mandate-as-code"
            assert issues == [], f"Unexpected issues: {issues}"
        finally:
            path.unlink()
    
    def test_empty_trace_wrong_chain_hash_detected(self):
        """Empty trace with wrong chain_hash should be detected."""
        anchor = {
            "mission_intent": "Test",
            "minimum": {"test": True},
            "constraints": [],
        }
        anchor["anchor_hash"] = compute_anchor_hash(anchor)
        
        mandate = {
            "mandate_id": "TEST-001",
            "version": "0.64",
            "generated": "2026-02-02T12:00:00Z",
            "anchor": anchor,
            "courses_of_action": [{
                "coa_id": "COA-A",
                "approach": "Test",
                "task_dag": {"nodes": [{"id": "t1", "name": "Test"}], "edges": []},
                "risk_assessment": {"score": "LOW", "confidence_min": "HIGH", "confidence_target": "HIGH", "primary_factor": "Test"},
                "off_nominal_triggers": []
            }],
            "recommendation": {"primary_coa": "COA-A", "fallback_sequence": [], "rationale": "Test"},
            "trace": {
                "chain_hash": "0000000000000000000000000000000000000000000000000000000000000000",
                "entry_count": 0,
                "entries": []
            }
        }
        
        path = _create_temp_artifact(mandate)
        try:
            artifact_type, issues = validate_artifact(str(path))
            hash_issues = [i for i in issues if i.kind == "hash" and "chain_hash" in i.path]
            assert len(hash_issues) == 1, f"Expected chain_hash issue, got: {issues}"
        finally:
            path.unlink()


class TestEntryCountValidation:
    """P0.2 fix: entry_count must match actual entry count."""
    
    def test_entry_count_mismatch_detected(self):
        """Mismatched entry_count should be detected."""
        anchor = {
            "mission_intent": "Test",
            "minimum": {"test": True},
            "constraints": [],
        }
        anchor["anchor_hash"] = compute_anchor_hash(anchor)
        
        # Declare 5 entries but provide 0
        mandate = {
            "mandate_id": "TEST-001",
            "version": "0.64",
            "generated": "2026-02-02T12:00:00Z",
            "anchor": anchor,
            "courses_of_action": [{
                "coa_id": "COA-A",
                "approach": "Test",
                "task_dag": {"nodes": [{"id": "t1", "name": "Test"}], "edges": []},
                "risk_assessment": {"score": "LOW", "confidence_min": "HIGH", "confidence_target": "HIGH", "primary_factor": "Test"},
                "off_nominal_triggers": []
            }],
            "recommendation": {"primary_coa": "COA-A", "fallback_sequence": [], "rationale": "Test"},
            "trace": {
                "chain_hash": compute_chain_hash_from_strings([]),
                "entry_count": 5,  # Wrong!
                "entries": []
            }
        }
        
        path = _create_temp_artifact(mandate)
        try:
            artifact_type, issues = validate_artifact(str(path))
            count_issues = [i for i in issues if "entry_count" in i.message]
            assert len(count_issues) == 1, f"Expected entry_count issue, got: {issues}"
            assert "declared 5, actual 0" in count_issues[0].message
        finally:
            path.unlink()


class TestConstraintValidationEdgeCases:
    """Tests for constraint validation edge cases."""
    
    def test_non_string_constraint_detected(self):
        """Non-string constraint values should be detected."""
        anchor = {
            "mission_intent": "Test",
            "minimum": {"test": True},
            "constraints": ["valid == 'yes'", 123, {"invalid": "object"}],  # Mix of valid and invalid
        }
        anchor["anchor_hash"] = compute_anchor_hash(anchor)
        
        issues = validate_constraints(
            {"anchor": anchor},
            "mandate-as-code"
        )
        
        non_string_issues = [i for i in issues if "must be a string" in i.message]
        assert len(non_string_issues) == 2  # 123 and {"invalid": "object"}


class TestContainsTypeSafety:
    """P1.4 fix: CONTAINS should raise EvaluationError for non-iterables."""
    
    def test_contains_on_non_iterable_raises_evaluation_error(self):
        from mandate.constraints import evaluate_constraint_string, EvaluationError
        
        state = {"count": 42}  # Not iterable
        
        with pytest.raises(EvaluationError) as exc_info:
            evaluate_constraint_string("count CONTAINS 4", state)
        
        assert "CONTAINS requires an iterable" in str(exc_info.value)
        assert "int" in str(exc_info.value)


class TestTriggerValidation:
    """v1.0.0: off_nominal_triggers must be validated as constraint predicates."""
    
    def test_valid_triggers_pass(self):
        from mandate.validator import validate_triggers
        
        obj = {
            "courses_of_action": [
                {
                    "coa_id": "COA-A",
                    "off_nominal_triggers": [
                        "time_remaining <= PT1H",
                        "dashboard_unavailable == true"
                    ]
                }
            ]
        }
        
        issues = validate_triggers(obj, "mandate-as-code")
        assert issues == []
    
    def test_invalid_trigger_detected(self):
        from mandate.validator import validate_triggers
        
        obj = {
            "courses_of_action": [
                {
                    "coa_id": "COA-A",
                    "off_nominal_triggers": [
                        "valid == true",
                        "invalid ??? syntax"  # Bad trigger
                    ]
                }
            ]
        }
        
        issues = validate_triggers(obj, "mandate-as-code")
        trigger_issues = [i for i in issues if i.kind == "trigger"]
        assert len(trigger_issues) == 1
        assert "COA-A" in trigger_issues[0].message
    
    def test_non_string_trigger_detected(self):
        from mandate.validator import validate_triggers
        
        obj = {
            "courses_of_action": [
                {
                    "coa_id": "COA-B",
                    "off_nominal_triggers": [
                        "valid == true",
                        123,  # Wrong type
                        {"bad": "object"}  # Wrong type
                    ]
                }
            ]
        }
        
        issues = validate_triggers(obj, "mandate-as-code")
        non_string_issues = [i for i in issues if "must be a string" in i.message]
        assert len(non_string_issues) == 2
