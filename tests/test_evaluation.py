"""Tests for mandate.evaluation — Evaluation Harness."""
import json
import pytest
from pathlib import Path

from mandate.evaluation import (
    CheckResult,
    CaseResult,
    EvaluationCase,
    EvaluationHarness,
    EvaluationReport,
    ExpectedOutcome,
)
from mandate.metrics import PipelineMetrics, RoleMetric


REPO_ROOT = Path(__file__).parent.parent


# ── ExpectedOutcome ─────────────────────────────────────────────────

class TestExpectedOutcome:
    def test_from_dict_defaults(self):
        eo = ExpectedOutcome.from_dict({})
        assert eo.pipeline_ok is True
        assert eo.min_coas is None
        assert eo.gaps_expected is False

    def test_from_dict_full(self):
        eo = ExpectedOutcome.from_dict({
            "pipeline_ok": True,
            "min_coas": 2,
            "max_coas": 3,
            "required_tool_classes_in_coas": ["RECON"],
            "recommendation_has_primary": True,
            "artifact_has_anchor_hash": True,
            "constraints_count": 4,
        })
        assert eo.min_coas == 2
        assert eo.max_coas == 3
        assert eo.constraints_count == 4

    def test_from_dict_failure_case(self):
        eo = ExpectedOutcome.from_dict({
            "pipeline_ok": False,
            "expected_error_role": "Intake",
        })
        assert eo.pipeline_ok is False
        assert eo.expected_error_role == "Intake"


# ── CheckResult / CaseResult ───────────────────────────────────────

class TestCheckResult:
    def test_pass(self):
        cr = CheckResult("test_check", True, "ok")
        assert cr.passed is True

    def test_fail(self):
        cr = CheckResult("test_check", False, "expected 2, got 1")
        assert cr.passed is False


class TestCaseResult:
    def test_checks_counts(self):
        result = CaseResult(
            case_id="E-001",
            name="Test",
            passed=False,
            checks=[
                CheckResult("a", True),
                CheckResult("b", False),
                CheckResult("c", True),
            ],
        )
        assert result.checks_passed == 2
        assert result.checks_failed == 1

    def test_to_dict(self):
        result = CaseResult(
            case_id="E-001",
            name="Test",
            passed=True,
            checks=[CheckResult("a", True, "ok")],
            duration_ms=5.5,
        )
        d = result.to_dict()
        assert d["case_id"] == "E-001"
        assert d["passed"] is True
        assert d["duration_ms"] == 5.5
        assert len(d["checks"]) == 1


# ── EvaluationReport ───────────────────────────────────────────────

class TestEvaluationReport:
    def test_empty_report(self):
        report = EvaluationReport()
        assert report.total_cases == 0
        assert report.pass_rate == 0.0

    def test_pass_rate(self):
        report = EvaluationReport(
            case_results=[
                CaseResult("A", "a", True),
                CaseResult("B", "b", True),
                CaseResult("C", "c", False),
            ],
        )
        assert report.total_cases == 3
        assert report.cases_passed == 2
        assert report.cases_failed == 1
        assert abs(report.pass_rate - 2 / 3) < 0.01

    def test_summary_includes_failures(self):
        report = EvaluationReport(
            case_results=[
                CaseResult("F1", "fail", False, error="boom"),
            ],
        )
        s = report.summary()
        assert "failed_cases" in s
        assert len(s["failed_cases"]) == 1

    def test_to_dict(self):
        report = EvaluationReport(
            corpus_version="2.0.0",
            case_results=[CaseResult("A", "a", True)],
            total_duration_ms=10.0,
        )
        d = report.to_dict()
        assert d["corpus_version"] == "2.0.0"
        assert len(d["case_results"]) == 1


# ── EvaluationCase ──────────────────────────────────────────────────

class TestEvaluationCase:
    def test_from_dict(self):
        d = {
            "case_id": "E-001",
            "name": "Test Case",
            "mission_file": "../../examples/normal_mission.json",
            "domain": "pentest",
            "expected": {"pipeline_ok": True, "min_coas": 2},
            "tags": ["pentest", "standard"],
        }
        case = EvaluationCase.from_dict(d, REPO_ROOT / "benchmarks" / "corpus")
        assert case.case_id == "E-001"
        assert case.tags == ["pentest", "standard"]
        assert case.expected.min_coas == 2


# ── EvaluationHarness ──────────────────────────────────────────────

class TestEvaluationHarness:
    def test_from_manifest(self):
        manifest = REPO_ROOT / "benchmarks" / "corpus" / "manifest.json"
        if not manifest.exists():
            pytest.skip("Corpus manifest not found")
        harness = EvaluationHarness.from_manifest(manifest)
        assert len(harness.cases) >= 5
        assert harness.corpus_version == "2.0.0"

    def test_run_normal_mission(self):
        """Run the standard pentest case and verify it passes."""
        manifest = REPO_ROOT / "benchmarks" / "corpus" / "manifest.json"
        if not manifest.exists():
            pytest.skip("Corpus manifest not found")
        harness = EvaluationHarness.from_manifest(manifest)
        report = harness.run_all(tags=["standard"])
        # The standard pentest case should pass
        assert report.total_cases >= 1
        for cr in report.case_results:
            if "Standard Pentest" in cr.name:
                assert cr.passed, f"Standard pentest failed: {[c for c in cr.checks if not c.passed]}"

    def test_run_all_corpus(self):
        """Run the full corpus and check we get results for each case."""
        manifest = REPO_ROOT / "benchmarks" / "corpus" / "manifest.json"
        if not manifest.exists():
            pytest.skip("Corpus manifest not found")
        harness = EvaluationHarness.from_manifest(manifest)
        report = harness.run_all()
        assert report.total_cases == len(harness.cases)
        assert report.total_duration_ms > 0
        assert report.benchmark_stats is not None
        # run_count may be less than total_cases if some cases fail before
        # the pipeline runs (e.g., invalid input), so no metrics to record
        assert report.benchmark_stats.run_count >= report.total_cases - 1

    def test_tag_filtering(self):
        manifest = REPO_ROOT / "benchmarks" / "corpus" / "manifest.json"
        if not manifest.exists():
            pytest.skip("Corpus manifest not found")
        harness = EvaluationHarness.from_manifest(manifest)
        report = harness.run_all(tags=["negative"])
        # Should only run cases tagged "negative"
        for cr in report.case_results:
            assert cr.case_id == "EVAL-008"

    def test_repetitions(self):
        manifest = REPO_ROOT / "benchmarks" / "corpus" / "manifest.json"
        if not manifest.exists():
            pytest.skip("Corpus manifest not found")
        harness = EvaluationHarness.from_manifest(manifest)
        report = harness.run_all(tags=["standard"], repetitions=3)
        # Should have 3x results for the standard tag
        standard_count = sum(1 for c in harness.cases if "standard" in c.tags)
        assert report.total_cases == standard_count * 3

    def test_metrics_collected(self):
        """Verify metrics are collected during evaluation."""
        manifest = REPO_ROOT / "benchmarks" / "corpus" / "manifest.json"
        if not manifest.exists():
            pytest.skip("Corpus manifest not found")
        harness = EvaluationHarness.from_manifest(manifest)
        report = harness.run_all(tags=["standard"])
        for cr in report.case_results:
            if cr.passed and cr.metrics:
                assert cr.metrics.total_duration_ms > 0
                assert len(cr.metrics.role_metrics) > 0

    def test_invalid_input_case(self):
        """Verify the invalid input case correctly identifies failure."""
        manifest = REPO_ROOT / "benchmarks" / "corpus" / "manifest.json"
        if not manifest.exists():
            pytest.skip("Corpus manifest not found")
        harness = EvaluationHarness.from_manifest(manifest)
        report = harness.run_all(tags=["negative"])
        for cr in report.case_results:
            if "Invalid" in cr.name:
                assert cr.passed, f"Invalid input case should pass (expected failure): {cr.error}"

    def test_underspecified_detects_gaps(self):
        """Verify underspecified mission reports gaps."""
        manifest = REPO_ROOT / "benchmarks" / "corpus" / "manifest.json"
        if not manifest.exists():
            pytest.skip("Corpus manifest not found")
        harness = EvaluationHarness.from_manifest(manifest)
        report = harness.run_all(tags=["gap-detection"])
        for cr in report.case_results:
            if "Underspecified" in cr.name:
                # Check that gaps_detected check passed
                gap_checks = [c for c in cr.checks if c.check_name == "gaps_detected"]
                assert len(gap_checks) > 0
                assert gap_checks[0].passed


# ── Pipeline Metrics Integration ────────────────────────────────────

class TestPipelineMetricsIntegration:
    """Verify that Pipeline.run() returns metrics."""

    def test_pipeline_returns_metrics(self):
        from mandate.models import MissionInput, PipelineConfig
        from mandate.pipeline import Pipeline

        mi = MissionInput(
            mission_id="METRICS-TEST-001",
            intent="Test pipeline metrics collection",
            scope=["10.0.0.0/24"],
        )
        pipe = Pipeline(PipelineConfig())
        result = pipe.run(mi, collect_metrics=True)
        assert result.metrics is not None
        assert result.metrics.total_duration_ms > 0
        assert len(result.metrics.role_metrics) == 6

    def test_pipeline_metrics_opt_out(self):
        from mandate.models import MissionInput, PipelineConfig
        from mandate.pipeline import Pipeline

        mi = MissionInput(
            mission_id="METRICS-TEST-002",
            intent="Test metrics opt-out",
            scope=["10.0.0.0/24"],
        )
        pipe = Pipeline(PipelineConfig())
        result = pipe.run(mi, collect_metrics=False)
        assert result.metrics is None

    def test_pipeline_result_summary_includes_duration(self):
        from mandate.models import MissionInput, PipelineConfig
        from mandate.pipeline import Pipeline

        mi = MissionInput(
            mission_id="METRICS-TEST-003",
            intent="Test summary includes duration",
            scope=["10.0.0.0/24"],
        )
        pipe = Pipeline(PipelineConfig())
        result = pipe.run(mi)
        s = result.summary()
        assert "total_duration_ms" in s
        assert s["total_duration_ms"] > 0

    def test_failed_pipeline_has_metrics(self):
        """Even failed pipelines should have metrics."""
        from mandate.models import MissionInput, PipelineConfig
        from mandate.pipeline import Pipeline

        mi = MissionInput(mission_id="", intent="")
        pipe = Pipeline(PipelineConfig(strict=True))
        result = pipe.run(mi)
        # Pipeline may fail but should still have partial metrics
        assert result.metrics is not None
