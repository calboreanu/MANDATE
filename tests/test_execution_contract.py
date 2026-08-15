from __future__ import annotations

from jsonschema import Draft202012Validator

from mandate.execution_contract import (
    ExecutionState,
    build_result_envelope,
    derive_execution_state,
    validate_result_envelope,
)
from mandate.models import MissionInput, PipelineConfig
from mandate.pipeline import Pipeline
from mandate.schema import load_schema


ARTIFACT = {"mandate_id": "M-1"}


def _gap(**overrides):
    gap = {
        "readiness_score": {"blocking": False},
        "readiness_assessment": {
            "blocking_gap_count": 0,
            "recommendation": "PROCEED_WITH_CAVEATS",
        },
    }
    gap.update(overrides)
    return gap


def test_blocking_nested_readiness_routes_non_executable():
    state = derive_execution_state(
        pipeline_succeeded=True,
        artifact=ARTIFACT,
        gap_reports=[_gap(readiness_score={"blocking": True})],
        schema_valid=True,
    )
    assert state is ExecutionState.NON_EXECUTABLE_GAPS


def test_insufficient_recommendation_routes_non_executable():
    state = derive_execution_state(
        pipeline_succeeded=True,
        artifact=ARTIFACT,
        gap_reports=[_gap(readiness_assessment={
            "blocking_gap_count": 0,
            "recommendation": "INSUFFICIENT_FOR_AUTOMATION",
        })],
        schema_valid=True,
    )
    assert state is ExecutionState.NON_EXECUTABLE_GAPS


def test_clean_success_routes_executable():
    envelope = build_result_envelope(
        pipeline_succeeded=True,
        artifact=ARTIFACT,
        gap_reports=[],
        schema_valid=True,
    )
    assert envelope["execution_state"] == "EXECUTABLE"
    assert envelope["ok"] is True


def test_schema_rejects_executable_with_true_signal_summary():
    envelope = build_result_envelope(
        pipeline_succeeded=True,
        artifact=ARTIFACT,
        gap_reports=[],
        schema_valid=True,
    )
    envelope["has_blocking_or_insufficient_signal"] = True
    errors = list(
        Draft202012Validator(load_schema("mandate-result-envelope.schema.json")).iter_errors(envelope)
    )
    assert errors


def test_semantic_validator_reconciles_summary_against_raw_gaps():
    envelope = build_result_envelope(
        pipeline_succeeded=True,
        artifact=ARTIFACT,
        gap_reports=[],
        schema_valid=True,
    )
    issues = validate_result_envelope(
        envelope,
        artifact=ARTIFACT,
        gap_reports=[_gap(readiness_score={"blocking": True})],
        schema_valid=True,
    )
    assert any("mismatch" in issue or "cannot coexist" in issue for issue in issues)


def test_semantic_validator_rejects_wrong_non_executable_state():
    gaps = [_gap(readiness_score={"blocking": True})]
    envelope = build_result_envelope(
        pipeline_succeeded=True, artifact=ARTIFACT, gap_reports=gaps,
        schema_valid=True,
    )
    envelope["execution_state"] = "FAILED"
    issues = validate_result_envelope(
        envelope, artifact=ARTIFACT, gap_reports=gaps, schema_valid=True,
    )
    assert any("execution_state mismatch" in issue for issue in issues)


def test_semantic_validator_rejects_wrong_ok_summary():
    envelope = build_result_envelope(
        pipeline_succeeded=True, artifact=ARTIFACT, gap_reports=[],
        schema_valid=True,
    )
    envelope["ok"] = False
    issues = validate_result_envelope(
        envelope, artifact=ARTIFACT, gap_reports=[], schema_valid=True,
    )
    assert any("ok mismatch" in issue for issue in issues)


def test_semantic_validator_rejects_validation_state_for_clean_valid_artifact():
    envelope = build_result_envelope(
        pipeline_succeeded=True, artifact=ARTIFACT, gap_reports=[],
        schema_valid=True,
    )
    envelope["execution_state"] = "NON_EXECUTABLE_VALIDATION"
    envelope["ok"] = False
    issues = validate_result_envelope(
        envelope, artifact=ARTIFACT, gap_reports=[], schema_valid=True,
    )
    assert any("execution_state mismatch" in issue for issue in issues)


def test_semantic_validator_rejects_failed_state_for_blocking_gap():
    gaps = [_gap(readiness_score={"blocking": True})]
    envelope = build_result_envelope(
        pipeline_succeeded=True, artifact=ARTIFACT, gap_reports=gaps,
        schema_valid=True,
    )
    envelope["execution_state"] = "FAILED"
    issues = validate_result_envelope(
        envelope, artifact=ARTIFACT, gap_reports=gaps, schema_valid=True,
    )
    assert any("execution_state mismatch" in issue for issue in issues)


def test_underspecified_pipeline_fails_closed():
    mission = MissionInput(
        mission_id="TEST-CONTRACT-001",
        intent="Assess security posture",
        constraints=["FORBIDS destructive_action"],
    )
    result = Pipeline(PipelineConfig(emit_gaps=True)).run(mission)
    assert result.artifact is not None
    assert result.execution_state == "NON_EXECUTABLE_GAPS"
    assert result.ok is False
    assert result.result_envelope["has_blocking_or_insufficient_signal"] is True
