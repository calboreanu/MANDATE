from __future__ import annotations

from mandate.validator import validate_artifact


def test_validate_example_mandate():
    artifact_type, issues = validate_artifact("examples/quarterly_report_mandate.json")
    assert artifact_type == "mandate-as-code"
    assert issues == []


def test_validate_example_gap():
    artifact_type, issues = validate_artifact("examples/quarterly_report_gap.json")
    assert artifact_type == "gap-report"
    assert issues == []
