"""Fail-closed execution-state contract for MANDATE pipeline results."""
from __future__ import annotations

from enum import Enum
from functools import lru_cache
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator

from .schema import load_schema


CONTRACT_SCHEMA_VERSION = "mandate-result-envelope.v1"
RESULT_ENVELOPE_SCHEMA_NAME = "mandate-result-envelope.schema.json"


class ExecutionState(str, Enum):
    EXECUTABLE = "EXECUTABLE"
    NON_EXECUTABLE_GAPS = "NON_EXECUTABLE_GAPS"
    NON_EXECUTABLE_VALIDATION = "NON_EXECUTABLE_VALIDATION"
    FAILED = "FAILED"


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value) or "").upper()


def is_blocking_or_insufficient_gap(gap: Mapping[str, Any]) -> bool:
    """Return whether a serialized gap carries a fail-closed signal."""
    if not isinstance(gap, Mapping):
        return False
    if _enum_value(gap.get("severity")) == "BLOCKING" or gap.get("blocking") is True:
        return True
    score = gap.get("readiness_score")
    if isinstance(score, Mapping) and score.get("blocking") is True:
        return True
    readiness = gap.get("readiness_assessment")
    if isinstance(readiness, Mapping):
        if int(readiness.get("blocking_gap_count") or 0) > 0:
            return True
        if _enum_value(readiness.get("recommendation")) == "INSUFFICIENT_FOR_AUTOMATION":
            return True
    return _enum_value(gap.get("execution_state")) in {
        ExecutionState.NON_EXECUTABLE_GAPS.value,
        "INSUFFICIENT_FOR_AUTOMATION",
    }


def has_blocking_or_insufficient_signal(
    gap_reports: Sequence[Mapping[str, Any]] | None,
) -> bool:
    return any(is_blocking_or_insufficient_gap(gap) for gap in list(gap_reports or []))


def derive_execution_state(
    *,
    pipeline_succeeded: bool,
    artifact: Mapping[str, Any] | None,
    gap_reports: Sequence[Mapping[str, Any]] | None,
    schema_valid: bool | None,
    errors: Sequence[Any] | None = None,
) -> ExecutionState:
    """Derive the closed state with deterministic fail-closed precedence."""
    gaps = list(gap_reports or [])
    if artifact is None and not gaps:
        return ExecutionState.FAILED
    if has_blocking_or_insufficient_signal(gaps):
        return ExecutionState.NON_EXECUTABLE_GAPS
    if schema_valid is False:
        return ExecutionState.NON_EXECUTABLE_VALIDATION
    if pipeline_succeeded and artifact is not None and schema_valid is True and not errors:
        return ExecutionState.EXECUTABLE
    if errors:
        return ExecutionState.FAILED
    return ExecutionState.NON_EXECUTABLE_VALIDATION if artifact is not None else ExecutionState.FAILED


def output_representation(
    artifact: Mapping[str, Any] | None,
    gap_reports: Sequence[Mapping[str, Any]] | None,
) -> str:
    if artifact is not None:
        return "MANDATE_AS_CODE"
    if gap_reports:
        return "GAP_REPORT"
    return "NONE"


def build_result_envelope(
    *,
    pipeline_succeeded: bool,
    artifact: Mapping[str, Any] | None,
    gap_reports: Sequence[Mapping[str, Any]] | None,
    schema_valid: bool | None,
    errors: Sequence[Any] | None = None,
) -> dict[str, Any]:
    gaps = list(gap_reports or [])
    state = derive_execution_state(
        pipeline_succeeded=pipeline_succeeded,
        artifact=artifact,
        gap_reports=gaps,
        schema_valid=schema_valid,
        errors=errors,
    )
    return {
        "contract_schema_version": CONTRACT_SCHEMA_VERSION,
        "ok": state is ExecutionState.EXECUTABLE,
        "execution_state": state.value,
        "output_representation": output_representation(artifact, gaps),
        "artifact_present": artifact is not None,
        "schema_valid": schema_valid,
        "gap_report_count": len(gaps),
        "has_blocking_or_insufficient_signal": has_blocking_or_insufficient_signal(gaps),
        "errors_present": bool(errors),
        "missing_result": artifact is None and not gaps,
    }


@lru_cache(maxsize=1)
def _schema_validator() -> Draft202012Validator:
    return Draft202012Validator(load_schema(RESULT_ENVELOPE_SCHEMA_NAME))


def validate_result_envelope(
    envelope: Mapping[str, Any],
    *,
    artifact: Mapping[str, Any] | None,
    gap_reports: Sequence[Mapping[str, Any]] | None,
    schema_valid: bool | None,
    errors: Sequence[Any] | None = None,
) -> list[str]:
    """Apply JSON-Schema checks and reconcile its summary against raw payloads."""
    issues: list[str] = []
    for err in sorted(_schema_validator().iter_errors(dict(envelope)), key=str):
        path = "/".join(str(p) for p in err.absolute_path)
        issues.append(f"{path}: {err.message}" if path else err.message)
    expected = build_result_envelope(
        # Reconstruct the state from raw payload facts, not from the claimed
        # state. A valid artifact with no errors is a completed pipeline result;
        # blocking gaps and schema failure still take fail-closed precedence.
        pipeline_succeeded=artifact is not None and schema_valid is True and not errors,
        artifact=artifact,
        gap_reports=gap_reports,
        schema_valid=schema_valid,
        errors=errors,
    )
    for field in (
        "ok", "execution_state",
        "artifact_present", "schema_valid", "gap_report_count",
        "has_blocking_or_insufficient_signal", "errors_present", "missing_result",
        "output_representation",
    ):
        if envelope.get(field) != expected[field]:
            issues.append(f"{field} mismatch: {envelope.get(field)!r} != {expected[field]!r}")
    if envelope.get("execution_state") == ExecutionState.EXECUTABLE.value and expected[
        "has_blocking_or_insufficient_signal"
    ]:
        issues.append("EXECUTABLE cannot coexist with blocking or insufficient gap signals")
    return issues


__all__ = [
    "CONTRACT_SCHEMA_VERSION", "ExecutionState", "build_result_envelope",
    "derive_execution_state", "has_blocking_or_insufficient_signal",
    "is_blocking_or_insufficient_gap", "validate_result_envelope",
]
