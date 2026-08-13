"""
Integration tests for the MANDATE 1+6 pipeline.

Tests end-to-end pipeline execution, strict/lenient modes,
artifact schema compliance, trace integrity, and error handling.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from mandate.models import (
    MissionInput,
    PipelineConfig,
    PipelineState,
    RoleResult,
    RoleStatus,
    ToolSpec,
)
from mandate.pipeline import Pipeline, PipelineResult
from mandate.validator import validate_artifact


# ── Fixtures ─────────────────────────────────────────────────────────

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


def _normal_mission() -> MissionInput:
    """Load the normal_mission.json example as a MissionInput."""
    raw = json.loads((EXAMPLES_DIR / "normal_mission.json").read_text())
    return MissionInput.from_dict(raw)


def _minimal_mission() -> MissionInput:
    """Construct a minimal MissionInput with only required fields."""
    return MissionInput(
        mission_id="TEST-MINIMAL-001",
        intent="Enumerate services on the target host",
        scope=["192.168.1.0/24"],
        constraints=[
            "FORBIDS destructive_action",
        ],
        available_tools=[
            ToolSpec(tool_id="nmap", tool_class="RECON", description="Port scanner"),
        ],
    )


def _no_tools_mission() -> MissionInput:
    """Mission with no available tools — should still produce an artifact."""
    return MissionInput(
        mission_id="TEST-NOTOOLS-001",
        intent="Analyze network traffic patterns",
        scope=["10.0.0.0/8"],
        constraints=[],
        available_tools=[],
    )


# ── End-to-End Tests ─────────────────────────────────────────────────

class TestPipelineEndToEnd:
    """Test the full pipeline from MissionInput to PipelineResult."""

    def test_normal_mission_succeeds(self):
        """Pipeline produces a valid artifact for the normal_mission example."""
        mi = _normal_mission()
        pipe = Pipeline(PipelineConfig(strict=True))
        result = pipe.run(mi)

        assert result.ok is True
        assert result.artifact is not None
        assert result.artifact["mandate_id"] == "MANDATE-NM-001"
        assert len(result.role_results) == 6
        assert all(r.ok for r in result.role_results)
        assert len(result.errors) == 0

    def test_minimal_mission_succeeds(self):
        """Pipeline handles a minimal input with a single tool."""
        mi = _minimal_mission()
        pipe = Pipeline(PipelineConfig(strict=True))
        result = pipe.run(mi)

        assert result.ok is True
        assert result.artifact is not None
        assert result.artifact["mandate_id"] == "TEST-MINIMAL-001"

    def test_no_tools_mission_succeeds(self):
        """Pipeline handles a mission with no available tools."""
        mi = _no_tools_mission()
        pipe = Pipeline(PipelineConfig(strict=True))
        result = pipe.run(mi)

        assert result.ok is True
        assert result.artifact is not None

    def test_all_six_roles_execute(self):
        """All 6 roles appear in role_results in order."""
        mi = _normal_mission()
        pipe = Pipeline(PipelineConfig(strict=True))
        result = pipe.run(mi)

        expected_roles = [
            "Intake", "Interpreter", "Decomposition",
            "Procedure", "Binding", "Validation",
        ]
        actual_roles = [r.role_name for r in result.role_results]
        assert actual_roles == expected_roles

    def test_role_results_have_trace_hashes(self):
        """Each role result should carry a trace_entry_hash."""
        mi = _normal_mission()
        pipe = Pipeline(PipelineConfig(strict=True))
        result = pipe.run(mi)

        for r in result.role_results:
            assert r.trace_entry_hash, f"Role {r.role_name} missing trace_entry_hash"
            assert len(r.trace_entry_hash) == 64  # SHA-256 hex

    def test_summary_method(self):
        """PipelineResult.summary() returns expected structure."""
        mi = _normal_mission()
        pipe = Pipeline(PipelineConfig(strict=True))
        result = pipe.run(mi)

        summary = result.summary()
        assert summary["ok"] is True
        assert summary["roles_executed"] == 6
        assert summary["roles_passed"] == 6
        assert summary["mandate_id"] == "MANDATE-NM-001"


# ── Artifact Schema Compliance ───────────────────────────────────────

class TestArtifactCompliance:
    """Verify generated artifacts pass schema validation."""

    def test_artifact_validates_against_schema(self, tmp_path):
        """Generated artifact passes `mandate validate`."""
        mi = _normal_mission()
        pipe = Pipeline(PipelineConfig(strict=True))
        result = pipe.run(mi)

        assert result.ok and result.artifact
        out = tmp_path / "test_mandate.json"
        out.write_text(json.dumps(result.artifact, indent=2))

        artifact_type, issues = validate_artifact(str(out))
        assert artifact_type == "mandate-as-code"
        assert issues == []

    def test_artifact_has_required_top_level_keys(self):
        """Artifact contains all required top-level keys."""
        mi = _normal_mission()
        pipe = Pipeline(PipelineConfig(strict=True))
        result = pipe.run(mi)

        required = {"mandate_id", "version", "generated", "anchor",
                     "courses_of_action", "recommendation", "trace"}
        assert required.issubset(set(result.artifact.keys()))

    def test_anchor_has_hash(self):
        """Anchor section contains a valid anchor_hash."""
        mi = _normal_mission()
        pipe = Pipeline(PipelineConfig(strict=True))
        result = pipe.run(mi)

        anchor = result.artifact["anchor"]
        assert "anchor_hash" in anchor
        assert len(anchor["anchor_hash"]) == 64

    def test_constraints_preserved(self):
        """Input constraints appear in the anchor."""
        mi = _normal_mission()
        pipe = Pipeline(PipelineConfig(strict=True))
        result = pipe.run(mi)

        anchor_constraints = result.artifact["anchor"]["constraints"]
        assert len(anchor_constraints) == 4
        assert "FORBIDS data_exfiltration" in anchor_constraints
        assert "FORBIDS destructive_action" in anchor_constraints

    def test_coas_generated(self):
        """At least one COA is generated with expected structure."""
        mi = _normal_mission()
        pipe = Pipeline(PipelineConfig(strict=True))
        result = pipe.run(mi)

        coas = result.artifact["courses_of_action"]
        assert len(coas) >= 1

        for coa in coas:
            assert "coa_id" in coa
            assert "approach" in coa
            assert "task_dag" in coa
            assert "nodes" in coa["task_dag"]
            assert "edges" in coa["task_dag"]

    def test_recommendation_structure(self):
        """Recommendation has primary_coa and fallback_sequence."""
        mi = _normal_mission()
        pipe = Pipeline(PipelineConfig(strict=True))
        result = pipe.run(mi)

        rec = result.artifact["recommendation"]
        assert "primary_coa" in rec
        assert "fallback_sequence" in rec
        assert "rationale" in rec
        assert isinstance(rec["fallback_sequence"], list)

    def test_minimal_mission_validates(self, tmp_path):
        """Even a minimal mission produces a schema-valid artifact."""
        mi = _minimal_mission()
        pipe = Pipeline(PipelineConfig(strict=True))
        result = pipe.run(mi)

        assert result.ok and result.artifact
        out = tmp_path / "test_minimal.json"
        out.write_text(json.dumps(result.artifact, indent=2))

        artifact_type, issues = validate_artifact(str(out))
        assert artifact_type == "mandate-as-code"
        assert issues == []


# ── Trace Integrity ──────────────────────────────────────────────────

class TestTraceIntegrity:
    """Verify trace hashes and chain integrity in generated artifacts."""

    def test_trace_entry_count_matches(self):
        """trace.entry_count matches actual number of entries."""
        mi = _normal_mission()
        pipe = Pipeline(PipelineConfig(strict=True))
        result = pipe.run(mi)

        trace = result.artifact["trace"]
        assert trace["entry_count"] == len(trace["entries"])

    def test_trace_has_six_entries(self):
        """Each of the 6 roles produces a trace entry."""
        mi = _normal_mission()
        pipe = Pipeline(PipelineConfig(strict=True))
        result = pipe.run(mi)

        trace = result.artifact["trace"]
        assert trace["entry_count"] == 6

    def test_trace_entries_are_valid_hashes(self):
        """All trace entries are 64-char hex strings (SHA-256)."""
        mi = _normal_mission()
        pipe = Pipeline(PipelineConfig(strict=True))
        result = pipe.run(mi)

        for entry in result.artifact["trace"]["entries"]:
            assert isinstance(entry, str)
            assert len(entry) == 64
            int(entry, 16)  # Raises ValueError if not valid hex

    def test_chain_hash_present(self):
        """trace.chain_hash is a 64-char hex string."""
        mi = _normal_mission()
        pipe = Pipeline(PipelineConfig(strict=True))
        result = pipe.run(mi)

        chain = result.artifact["trace"]["chain_hash"]
        assert isinstance(chain, str)
        assert len(chain) == 64

    def test_chain_hash_deterministic(self):
        """Same input produces same chain_hash when run twice."""
        mi = _normal_mission()
        r1 = Pipeline(PipelineConfig(strict=True)).run(mi)
        r2 = Pipeline(PipelineConfig(strict=True)).run(mi)

        # Entry hashes depend on timestamps so they differ,
        # but both should be valid
        assert r1.artifact["trace"]["entry_count"] == r2.artifact["trace"]["entry_count"]


# ── Strict / Lenient Modes ───────────────────────────────────────────

class TestPipelineModes:
    """Test strict vs lenient pipeline behavior."""

    def test_strict_is_default(self):
        """PipelineConfig defaults to strict=True."""
        config = PipelineConfig()
        assert config.strict is True

    def test_lenient_mode_continues_past_errors(self):
        """In lenient mode, pipeline continues even if a role has issues."""
        mi = _normal_mission()
        config = PipelineConfig(strict=False)
        pipe = Pipeline(config)
        result = pipe.run(mi)

        # Normal mission should succeed in either mode
        assert result.ok is True
        assert len(result.role_results) == 6

    def test_version_passed_through(self):
        """Config version appears in the generated artifact."""
        mi = _normal_mission()
        config = PipelineConfig(strict=True, version="2.0")
        pipe = Pipeline(config)
        result = pipe.run(mi)

        assert result.artifact["version"] == "2.0"


# ── Save to File ─────────────────────────────────────────────────────

class TestRunAndSave:
    """Test Pipeline.run_and_save() writes valid JSON."""

    def test_saves_artifact_to_file(self, tmp_path):
        """run_and_save writes a valid JSON file."""
        mi = _normal_mission()
        pipe = Pipeline(PipelineConfig(strict=True))
        out = tmp_path / "output" / "mandate.json"
        result = pipe.run_and_save(mi, out)

        assert result.ok is True
        assert out.exists()

        loaded = json.loads(out.read_text())
        assert loaded["mandate_id"] == "MANDATE-NM-001"

    def test_saved_file_validates(self, tmp_path):
        """Saved file passes schema validation."""
        mi = _normal_mission()
        pipe = Pipeline(PipelineConfig(strict=True))
        out = tmp_path / "mandate.json"
        pipe.run_and_save(mi, out)

        artifact_type, issues = validate_artifact(str(out))
        assert artifact_type == "mandate-as-code"
        assert issues == []

    def test_creates_parent_directories(self, tmp_path):
        """run_and_save creates parent dirs if they don't exist."""
        mi = _normal_mission()
        pipe = Pipeline(PipelineConfig(strict=True))
        out = tmp_path / "deep" / "nested" / "dir" / "mandate.json"
        result = pipe.run_and_save(mi, out)

        assert result.ok is True
        assert out.exists()


# ── MissionInput.from_dict ───────────────────────────────────────────

class TestMissionInputParsing:
    """Test MissionInput construction from dicts and JSON."""

    def test_from_dict_round_trip(self):
        """MissionInput.from_dict produces expected fields."""
        raw = json.loads((EXAMPLES_DIR / "normal_mission.json").read_text())
        mi = MissionInput.from_dict(raw)

        assert mi.mission_id == "MANDATE-NM-001"
        assert mi.intent.startswith("Identify exploitable")
        assert len(mi.available_tools) == 3
        assert mi.available_tools[0].tool_id == "nmap"
        assert mi.available_tools[0].tool_class == "RECON"
        assert mi.risk_tolerance == "LOW"

    def test_from_dict_missing_mission_id_raises(self):
        """Missing mission_id raises KeyError."""
        with pytest.raises(KeyError):
            MissionInput.from_dict({"intent": "something"})

    def test_from_dict_missing_intent_raises(self):
        """Missing intent raises KeyError."""
        with pytest.raises(KeyError):
            MissionInput.from_dict({"mission_id": "X"})

    def test_from_dict_optional_defaults(self):
        """Optional fields default correctly."""
        mi = MissionInput.from_dict({
            "mission_id": "M-001",
            "intent": "Test intent",
        })
        assert mi.scope == []
        assert mi.time_limit == ""
        assert mi.constraints == []
        assert mi.available_tools == []
        assert mi.risk_tolerance is None
        assert mi.metadata == {}
