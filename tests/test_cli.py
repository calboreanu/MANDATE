"""
Tests for the MANDATE CLI commands.

Covers: validate, pipeline, hash-anchor, hash-trace,
        check-constraint, validate-constraints.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from mandate.cli import build_parser, main

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
NORMAL_MISSION = EXAMPLES_DIR / "normal_mission.json"
QUARTERLY_MANDATE = EXAMPLES_DIR / "quarterly_report_mandate.json"
QUARTERLY_GAP = EXAMPLES_DIR / "quarterly_report_gap.json"


# ── Helper ───────────────────────────────────────────────────────────

def run_cli(argv: list[str]) -> int:
    """Run CLI and return exit code (swallowing SystemExit)."""
    try:
        main(argv)
        return 0  # Should not reach here; main always raises SystemExit
    except SystemExit as e:
        return e.code


# ── mandate validate ─────────────────────────────────────────────────

class TestCLIValidate:
    """Tests for `mandate validate`."""

    def test_validate_mandate_artifact(self):
        """Validating the quarterly report mandate succeeds."""
        rc = run_cli(["validate", str(QUARTERLY_MANDATE)])
        assert rc == 0

    def test_validate_gap_artifact(self):
        """Validating the quarterly report gap report succeeds."""
        rc = run_cli(["validate", str(QUARTERLY_GAP)])
        assert rc == 0

    def test_validate_invalid_file(self, tmp_path):
        """Validating garbage JSON returns exit code 2."""
        bad = tmp_path / "bad.json"
        bad.write_text('{"not": "a mandate"}')
        rc = run_cli(["validate", str(bad)])
        assert rc == 2


# ── mandate pipeline ─────────────────────────────────────────────────

class TestCLIPipeline:
    """Tests for `mandate pipeline`."""

    def test_pipeline_stdout(self, capsys):
        """Pipeline with no -o prints JSON to stdout."""
        rc = run_cli(["pipeline", str(NORMAL_MISSION)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "Pipeline SUCCESS" in captured.out
        assert '"mandate_id"' in captured.out

    def test_pipeline_output_file(self, tmp_path):
        """Pipeline with -o writes a valid artifact."""
        out = tmp_path / "mandate_out.json"
        rc = run_cli(["pipeline", str(NORMAL_MISSION), "-o", str(out)])
        assert rc == 0
        assert out.exists()

        artifact = json.loads(out.read_text())
        assert artifact["mandate_id"] == "MANDATE-NM-001"

    def test_pipeline_output_validates(self, tmp_path):
        """Pipeline output passes `mandate validate`."""
        out = tmp_path / "mandate_out.json"
        run_cli(["pipeline", str(NORMAL_MISSION), "-o", str(out)])
        rc = run_cli(["validate", str(out)])
        assert rc == 0

    def test_pipeline_missing_file(self):
        """Pipeline with nonexistent file returns exit code 2."""
        rc = run_cli(["pipeline", "/nonexistent/path.json"])
        assert rc == 2

    def test_pipeline_invalid_json(self, tmp_path):
        """Pipeline with malformed JSON returns exit code 2."""
        bad = tmp_path / "bad.json"
        bad.write_text("not json at all")
        rc = run_cli(["pipeline", str(bad)])
        assert rc == 2

    def test_pipeline_missing_required_fields(self, tmp_path):
        """Pipeline with JSON missing mission_id returns exit code 2."""
        bad = tmp_path / "incomplete.json"
        bad.write_text('{"intent": "only intent"}')
        rc = run_cli(["pipeline", str(bad)])
        assert rc == 2

    def test_pipeline_lenient_flag(self, tmp_path):
        """Pipeline with --lenient flag runs without error."""
        out = tmp_path / "lenient.json"
        rc = run_cli(["pipeline", str(NORMAL_MISSION), "--lenient", "-o", str(out)])
        assert rc == 0

    def test_pipeline_version_flag(self, capsys):
        """Pipeline with --version flag sets artifact version."""
        rc = run_cli(["pipeline", str(NORMAL_MISSION), "--version", "3.0"])
        assert rc == 0
        captured = capsys.readouterr()
        # The JSON output should contain version "3.0"
        assert '"version": "3.0"' in captured.out


# ── mandate hash-anchor ──────────────────────────────────────────────

class TestCLIHashAnchor:
    """Tests for `mandate hash-anchor`."""

    def test_hash_anchor(self, capsys):
        """hash-anchor prints a 64-char hex hash."""
        rc = run_cli(["hash-anchor", str(QUARTERLY_MANDATE)])
        assert rc == 0
        captured = capsys.readouterr()
        h = captured.out.strip()
        assert len(h) == 64
        int(h, 16)  # valid hex

    def test_hash_anchor_no_anchor(self, tmp_path):
        """hash-anchor on JSON without anchor returns error."""
        bad = tmp_path / "no_anchor.json"
        bad.write_text('{"foo": "bar"}')
        rc = run_cli(["hash-anchor", str(bad)])
        assert rc == 2


# ── mandate hash-trace ───────────────────────────────────────────────

class TestCLIHashTrace:
    """Tests for `mandate hash-trace`."""

    def test_hash_trace_entry(self, capsys):
        """hash-trace prints a 64-char hex hash for a trace entry."""
        trace_dir = EXAMPLES_DIR / "trace_entries"
        entries = list(trace_dir.glob("*.json"))
        assert len(entries) > 0, "No trace entry examples found"

        rc = run_cli(["hash-trace", str(entries[0])])
        assert rc == 0
        captured = capsys.readouterr()
        h = captured.out.strip()
        assert len(h) == 64


# ── mandate check-constraint ─────────────────────────────────────────

class TestCLICheckConstraint:
    """Tests for `mandate check-constraint`."""

    def test_valid_constraint(self, capsys):
        """Valid constraint prints success marker."""
        rc = run_cli(["check-constraint", "FORBIDS destructive_action"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "Valid" in captured.out

    def test_invalid_constraint(self, capsys):
        """Invalid constraint returns exit code 2."""
        rc = run_cli(["check-constraint", "NOT VALID !!@#$"])
        assert rc == 2

    def test_complex_constraint(self, capsys):
        """Complex constraint with AND/OR parses correctly."""
        rc = run_cli([
            "check-constraint",
            "target.scope IN ['10.0.0.0/8'] AND execution.duration <= PT4H",
        ])
        assert rc == 0


# ── mandate validate-constraints ─────────────────────────────────────

class TestCLIValidateConstraints:
    """Tests for `mandate validate-constraints`."""

    def test_validate_constraints_in_mandate(self, capsys):
        """Validates all constraints in the quarterly report mandate."""
        rc = run_cli(["validate-constraints", str(QUARTERLY_MANDATE)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "valid" in captured.out.lower()

    def test_validate_constraints_no_constraints(self, tmp_path, capsys):
        """Artifact with no constraints prints informational message."""
        empty = tmp_path / "empty.json"
        empty.write_text('{"anchor": {}}')
        rc = run_cli(["validate-constraints", str(empty)])
        assert rc == 0


# ── Parser Structure ─────────────────────────────────────────────────

class TestParserStructure:
    """Verify CLI parser has expected subcommands."""

    def test_subcommands_exist(self):
        """Parser has all expected subcommands."""
        parser = build_parser()
        # Build the subcommand choices from the parser
        subparsers_actions = [
            action for action in parser._actions
            if isinstance(action, type(parser._subparsers._group_actions[0]))
        ]
        assert len(subparsers_actions) == 1
        choices = subparsers_actions[0].choices
        expected = {"validate", "hash-anchor", "hash-trace",
                    "check-constraint", "validate-constraints", "pipeline",
                    "translate", "benchmark", "registry"}
        assert expected == set(choices.keys())
