"""
Tests for MANDATE gap report generation.

Covers:
- Gap detection in Interpreter and Decomposition roles
- Gap report artifact generation and schema compliance
- Fail-closed gap-evidence behavior
- CLI --emit-gaps flag
- Underspecified mission example
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mandate.gap_report import (
    build_gap_reports,
    gap_spec_to_artifact,
    validate_gap_reports,
)
from mandate.models import (
    GapSpec,
    GapType,
    MissionInput,
    PipelineConfig,
    ToolSpec,
)
from mandate.pipeline import Pipeline
from mandate.validator import validate_artifact
from mandate.cli import main as cli_main


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


# ── Fixtures ─────────────────────────────────────────────────────────

def _fully_specified_mission() -> MissionInput:
    """Mission with all fields provided — should produce zero gaps."""
    return MissionInput(
        mission_id="TEST-FULL-001",
        intent="Enumerate services on target host",
        scope=["192.168.1.0/24"],
        constraints=["FORBIDS destructive_action"],
        minimum_outcome="Identify all open ports and running services",
        target_outcome="Complete service enumeration with version detection",
        available_tools=[
            ToolSpec(tool_id="nmap", tool_class="RECON", description="Port scanner"),
        ],
        risk_tolerance="LOW",
    )


def _underspecified_mission() -> MissionInput:
    """Mission missing many fields — should produce multiple gaps."""
    return MissionInput(
        mission_id="TEST-UNDER-001",
        intent="Assess security posture",
        constraints=["FORBIDS destructive_action"],
    )


def _no_recon_mission() -> MissionInput:
    """Mission with tools but no RECON class — specific gap."""
    return MissionInput(
        mission_id="TEST-NORECON-001",
        intent="Exploit confirmed vulnerabilities",
        scope=["10.0.0.0/8"],
        minimum_outcome="Achieve access via one vulnerability",
        target_outcome="Full exploitation with post-access enumeration",
        available_tools=[
            ToolSpec(tool_id="metasploit", tool_class="EXPLOIT", description="Exploit framework"),
        ],
        risk_tolerance="HIGH",
    )


def _no_risk_tolerance_mission() -> MissionInput:
    """Mission with no risk_tolerance and no FORBIDS — triggers UNASSESSABLE_RISK."""
    return MissionInput(
        mission_id="TEST-NORISK-001",
        intent="Perform general network assessment",
        scope=["10.0.0.0/8"],
        minimum_outcome="Baseline network map",
        target_outcome="Complete network assessment",
        constraints=[],  # No FORBIDS => can't infer risk tolerance
        available_tools=[
            ToolSpec(tool_id="nmap", tool_class="RECON"),
        ],
    )


# ── Gap Detection: Fully Specified ───────────────────────────────────

class TestFullySpecifiedNoGaps:
    """A fully specified mission should produce zero gaps."""

    def test_no_gaps_with_emit(self):
        mi = _fully_specified_mission()
        config = PipelineConfig(emit_gaps=True)
        result = Pipeline(config).run(mi)

        assert result.ok is True
        assert result.has_gaps is False
        assert len(result.gap_reports) == 0

    def test_normal_mission_example_no_gaps(self):
        raw = json.loads((EXAMPLES_DIR / "normal_mission.json").read_text())
        mi = MissionInput.from_dict(raw)
        config = PipelineConfig(emit_gaps=True)
        result = Pipeline(config).run(mi)

        assert result.ok is True
        assert result.has_gaps is False


# ── Gap Detection: Underspecified ────────────────────────────────────

class TestUnderspecifiedGaps:
    """An underspecified mission should produce multiple gaps."""

    def test_detects_undefined_minimum(self):
        mi = _underspecified_mission()
        config = PipelineConfig(emit_gaps=True)
        result = Pipeline(config).run(mi)

        types = [g["gap_type"] for g in result.gap_reports]
        assert "UNDEFINED_MINIMUM" in types

    def test_detects_undefined_target(self):
        mi = _underspecified_mission()
        config = PipelineConfig(emit_gaps=True)
        result = Pipeline(config).run(mi)

        types = [g["gap_type"] for g in result.gap_reports]
        assert "UNDEFINED_TARGET" in types

    def test_detects_missing_capability(self):
        mi = _underspecified_mission()
        config = PipelineConfig(emit_gaps=True)
        result = Pipeline(config).run(mi)

        types = [g["gap_type"] for g in result.gap_reports]
        assert "MISSING_CAPABILITY" in types

    def test_detects_unknown_pattern_no_scope(self):
        mi = _underspecified_mission()
        config = PipelineConfig(emit_gaps=True)
        result = Pipeline(config).run(mi)

        types = [g["gap_type"] for g in result.gap_reports]
        assert "UNKNOWN_PATTERN" in types

    def test_four_gaps_total(self):
        mi = _underspecified_mission()
        config = PipelineConfig(emit_gaps=True)
        result = Pipeline(config).run(mi)

        # UNDEFINED_MINIMUM, UNDEFINED_TARGET, MISSING_CAPABILITY, UNKNOWN_PATTERN
        assert len(result.gap_reports) == 4

    def test_blocking_gaps_route_non_executable(self):
        """A partial artifact may exist, but a blocking signal fails closed."""
        mi = _underspecified_mission()
        config = PipelineConfig(emit_gaps=True)
        result = Pipeline(config).run(mi)

        assert result.ok is False
        assert result.execution_state == "NON_EXECUTABLE_GAPS"
        assert result.artifact is not None


# ── Gap Detection: Specific Scenarios ────────────────────────────────

class TestSpecificGapScenarios:

    def test_missing_recon_tools(self):
        """No RECON-class tools triggers MISSING_CAPABILITY gap."""
        mi = _no_recon_mission()
        config = PipelineConfig(emit_gaps=True)
        result = Pipeline(config).run(mi)

        recon_gaps = [
            g for g in result.gap_reports
            if g["gap_type"] == "MISSING_CAPABILITY"
            and "RECON" in g["location"]["field_or_task"]
        ]
        assert len(recon_gaps) == 1

    def test_unassessable_risk(self):
        """No risk_tolerance + no FORBIDS triggers UNASSESSABLE_RISK."""
        mi = _no_risk_tolerance_mission()
        config = PipelineConfig(emit_gaps=True)
        result = Pipeline(config).run(mi)

        types = [g["gap_type"] for g in result.gap_reports]
        assert "UNASSESSABLE_RISK" in types

    def test_blocking_gap_for_no_scope(self):
        """Missing scope produces a blocking gap."""
        mi = _underspecified_mission()
        config = PipelineConfig(emit_gaps=True)
        result = Pipeline(config).run(mi)

        scope_gaps = [
            g for g in result.gap_reports
            if g["gap_type"] == "UNKNOWN_PATTERN"
        ]
        assert len(scope_gaps) == 1
        assert scope_gaps[0]["readiness_score"]["blocking"] is True


# ── Gap Report Schema Compliance ─────────────────────────────────────

class TestGapReportSchemaCompliance:
    """All generated gap reports must validate against gap-report.schema.json."""

    def test_all_gap_reports_validate(self, tmp_path):
        mi = _underspecified_mission()
        config = PipelineConfig(emit_gaps=True)
        result = Pipeline(config).run(mi)

        for i, gap in enumerate(result.gap_reports):
            path = tmp_path / f"gap_{i}.json"
            path.write_text(json.dumps(gap, indent=2))

            artifact_type, issues = validate_artifact(str(path))
            assert artifact_type == "gap-report", f"Gap {i}: expected gap-report, got {artifact_type}"
            assert issues == [], f"Gap {i} validation failed: {issues}"

    def test_gap_report_has_required_fields(self):
        mi = _underspecified_mission()
        config = PipelineConfig(emit_gaps=True)
        result = Pipeline(config).run(mi)

        required = {
            "gap_id", "gap_type", "detected_by", "pipeline_stage",
            "location", "reason", "remediation", "severity", "readiness_score",
            "readiness_assessment",
            "trace_to_gap"
        }
        for gap in result.gap_reports:
            assert required.issubset(set(gap.keys()))

    def test_gap_ids_are_unique(self):
        mi = _underspecified_mission()
        config = PipelineConfig(emit_gaps=True)
        result = Pipeline(config).run(mi)

        ids = [g["gap_id"] for g in result.gap_reports]
        assert len(ids) == len(set(ids))

    def test_trace_to_gap_is_valid_hash(self):
        mi = _underspecified_mission()
        config = PipelineConfig(emit_gaps=True)
        result = Pipeline(config).run(mi)

        for gap in result.gap_reports:
            h = gap["trace_to_gap"]
            assert isinstance(h, str)
            assert len(h) == 64
            int(h, 16)  # Valid hex

    def test_detected_by_matches_role_enum(self):
        mi = _underspecified_mission()
        config = PipelineConfig(emit_gaps=True)
        result = Pipeline(config).run(mi)

        valid_roles = {"Intake", "Interpreter", "Decomposition",
                       "Procedure", "Binding", "Validation"}
        for gap in result.gap_reports:
            assert gap["detected_by"] in valid_roles


# ── Gap Evidence Is Contractual ──────────────────────────────────────

class TestGapEvidenceContract:
    """Gap payloads are retained even when the legacy flag is false."""

    def test_gap_reports_present_by_default(self):
        mi = _underspecified_mission()
        config = PipelineConfig()  # emit_gaps defaults to False
        result = Pipeline(config).run(mi)

        assert result.has_gaps is True
        assert len(result.gap_reports) == 4

    def test_pipeline_without_legacy_flag_fails_closed(self):
        mi = _underspecified_mission()
        config = PipelineConfig()
        result = Pipeline(config).run(mi)

        assert result.ok is False
        assert result.execution_state == "NON_EXECUTABLE_GAPS"


# ── gap_report Module Direct Tests ───────────────────────────────────

class TestGapReportModule:

    def test_gap_spec_to_artifact(self):
        gap = GapSpec(
            gap_type=GapType.MISSING_CAPABILITY,
            detected_by="Decomposition",
            pipeline_stage=3,
            field_or_task="available_tools",
            reason="No tools provided",
            action_required="Add tools",
        )
        artifact = gap_spec_to_artifact(gap, "TEST-001", sequence=1)

        assert artifact["gap_id"] == "GAP-TEST-001-001"
        assert artifact["gap_type"] == "MISSING_CAPABILITY"
        assert artifact["detected_by"] == "Decomposition"
        assert artifact["pipeline_stage"] == 3
        assert artifact["location"]["field_or_task"] == "available_tools"
        assert len(artifact["trace_to_gap"]) == 64

    def test_build_gap_reports_sequencing(self):
        gaps = [
            GapSpec(
                gap_type=GapType.UNDEFINED_MINIMUM,
                detected_by="Interpreter",
                pipeline_stage=2,
                field_or_task="minimum_outcome",
                reason="Missing minimum",
                action_required="Define minimum",
            ),
            GapSpec(
                gap_type=GapType.MISSING_CAPABILITY,
                detected_by="Decomposition",
                pipeline_stage=3,
                field_or_task="available_tools",
                reason="No tools",
                action_required="Add tools",
            ),
        ]
        reports = build_gap_reports(gaps, "TEST-SEQ-001")

        assert len(reports) == 2
        assert reports[0]["gap_id"] == "GAP-TEST-SEQ-001-001"
        assert reports[1]["gap_id"] == "GAP-TEST-SEQ-001-002"

    def test_validate_gap_reports_all_valid(self):
        gaps = [
            GapSpec(
                gap_type=GapType.UNDEFINED_TARGET,
                detected_by="Interpreter",
                pipeline_stage=2,
                field_or_task="target_outcome",
                reason="Missing target",
                action_required="Define target",
            ),
        ]
        reports = build_gap_reports(gaps, "TEST-VAL-001")
        results = validate_gap_reports(reports)

        assert len(results) == 1
        gap_id, is_valid, errors = results[0]
        assert is_valid is True
        assert errors == []


# ── Pipeline run_and_save with Gaps ──────────────────────────────────

class TestRunAndSaveWithGaps:

    def test_saves_gap_reports_to_gaps_dir(self, tmp_path):
        mi = _underspecified_mission()
        config = PipelineConfig(emit_gaps=True)
        out = tmp_path / "mandate.json"
        result = Pipeline(config).run_and_save(mi, out)

        assert result.ok is False
        assert result.execution_state == "NON_EXECUTABLE_GAPS"
        gap_dir = tmp_path / "gaps"
        assert gap_dir.exists()

        gap_files = list(gap_dir.glob("*.json"))
        assert len(gap_files) == 4

    def test_saved_gap_reports_validate(self, tmp_path):
        mi = _underspecified_mission()
        config = PipelineConfig(emit_gaps=True)
        out = tmp_path / "mandate.json"
        Pipeline(config).run_and_save(mi, out)

        gap_dir = tmp_path / "gaps"
        for gap_file in gap_dir.glob("*.json"):
            artifact_type, issues = validate_artifact(str(gap_file))
            assert artifact_type == "gap-report"
            assert issues == []

    def test_no_gaps_dir_when_no_gaps(self, tmp_path):
        mi = _fully_specified_mission()
        config = PipelineConfig(emit_gaps=True)
        out = tmp_path / "mandate.json"
        Pipeline(config).run_and_save(mi, out)

        gap_dir = tmp_path / "gaps"
        assert not gap_dir.exists()


# ── PipelineResult.summary ───────────────────────────────────────────

class TestPipelineResultSummary:

    def test_summary_includes_gap_count(self):
        mi = _underspecified_mission()
        config = PipelineConfig(emit_gaps=True)
        result = Pipeline(config).run(mi)

        summary = result.summary()
        assert "gaps" in summary
        assert summary["gaps"] == 4

    def test_summary_zero_gaps_for_full_spec(self):
        mi = _fully_specified_mission()
        config = PipelineConfig(emit_gaps=True)
        result = Pipeline(config).run(mi)

        summary = result.summary()
        assert summary["gaps"] == 0


# ── CLI --emit-gaps ──────────────────────────────────────────────────

def _run_cli(argv: list[str]) -> int:
    try:
        cli_main(argv)
        return 0
    except SystemExit as e:
        return e.code


class TestCLIEmitGaps:

    def test_emit_gaps_flag_accepted(self, capsys):
        rc = _run_cli([
            "pipeline",
            str(EXAMPLES_DIR / "underspecified_mission.json"),
            "--emit-gaps",
        ])
        assert rc == 3
        captured = capsys.readouterr()
        assert "Gaps detected:" in captured.out

    def test_emit_gaps_shows_gap_types(self, capsys):
        rc = _run_cli([
            "pipeline",
            str(EXAMPLES_DIR / "underspecified_mission.json"),
            "--emit-gaps",
        ])
        assert rc == 3
        captured = capsys.readouterr()
        assert "UNDEFINED_MINIMUM" in captured.out
        assert "MISSING_CAPABILITY" in captured.out

    def test_emit_gaps_with_output(self, tmp_path, capsys):
        out = tmp_path / "mandate.json"
        rc = _run_cli([
            "pipeline",
            str(EXAMPLES_DIR / "underspecified_mission.json"),
            "--emit-gaps",
            "-o", str(out),
        ])
        assert rc == 3

        # Gap files should be saved
        gap_dir = tmp_path / "gaps"
        assert gap_dir.exists()
        gap_files = list(gap_dir.glob("*.json"))
        assert len(gap_files) == 4

    def test_no_gaps_without_flag(self, capsys):
        rc = _run_cli([
            "pipeline",
            str(EXAMPLES_DIR / "underspecified_mission.json"),
        ])
        assert rc == 3
        captured = capsys.readouterr()
        assert "Gaps detected:" in captured.out

    def test_normal_mission_no_gaps_with_flag(self, capsys):
        rc = _run_cli([
            "pipeline",
            str(EXAMPLES_DIR / "normal_mission.json"),
            "--emit-gaps",
        ])
        assert rc == 0
        captured = capsys.readouterr()
        assert "Gaps detected:" not in captured.out


# ── Underspecified Mission Example ───────────────────────────────────

class TestUnderspecifiedExample:

    def test_example_loads(self):
        path = EXAMPLES_DIR / "underspecified_mission.json"
        raw = json.loads(path.read_text())
        mi = MissionInput.from_dict(raw)
        assert mi.mission_id == "MANDATE-UNDERSPEC-001"

    def test_example_produces_valid_mandate(self, tmp_path):
        raw = json.loads((EXAMPLES_DIR / "underspecified_mission.json").read_text())
        mi = MissionInput.from_dict(raw)
        config = PipelineConfig(emit_gaps=True)
        result = Pipeline(config).run(mi)

        assert result.ok is False
        assert result.execution_state == "NON_EXECUTABLE_GAPS"
        out = tmp_path / "mandate.json"
        out.write_text(json.dumps(result.artifact, indent=2))
        artifact_type, issues = validate_artifact(str(out))
        assert artifact_type == "mandate-as-code"
        assert issues == []

    def test_example_produces_four_gaps(self):
        raw = json.loads((EXAMPLES_DIR / "underspecified_mission.json").read_text())
        mi = MissionInput.from_dict(raw)
        config = PipelineConfig(emit_gaps=True)
        result = Pipeline(config).run(mi)

        assert len(result.gap_reports) == 4
        types = sorted([g["gap_type"] for g in result.gap_reports])
        expected = sorted([
            "MISSING_CAPABILITY",
            "UNDEFINED_MINIMUM",
            "UNDEFINED_TARGET",
            "UNKNOWN_PATTERN",
        ])
        assert types == expected
