"""Tests for mandate.metrics — Pipeline Metrics Collection."""
import time
import pytest

from mandate.metrics import (
    BenchmarkStats,
    MetricsCollector,
    PipelineMetrics,
    RoleMetric,
)


# ── RoleMetric ──────────────────────────────────────────────────────

class TestRoleMetric:
    def test_basic_creation(self):
        rm = RoleMetric(role_name="Intake", start_time_ns=1000, end_time_ns=2000)
        assert rm.role_name == "Intake"
        assert rm.duration_ns == 1000
        assert rm.duration_ms == 0.001

    def test_defaults(self):
        rm = RoleMetric(role_name="X")
        assert rm.success is False
        assert rm.error_message == ""
        assert rm.duration_ns == 0

    def test_to_dict(self):
        rm = RoleMetric(
            role_name="Intake",
            start_time_ns=0,
            end_time_ns=5_000_000,  # 5ms
            success=True,
        )
        d = rm.to_dict()
        assert d["role_name"] == "Intake"
        assert d["duration_ms"] == 5.0
        assert d["success"] is True


# ── PipelineMetrics ─────────────────────────────────────────────────

class TestPipelineMetrics:
    def _make_metrics(self):
        return PipelineMetrics(
            role_metrics=[
                RoleMetric("Intake", 0, 1_000_000, True),           # 1ms
                RoleMetric("Interpreter", 1_000_000, 3_000_000, True),  # 2ms
                RoleMetric("Decomposition", 3_000_000, 8_000_000, True),  # 5ms
                RoleMetric("Procedure", 8_000_000, 10_000_000, True),  # 2ms
                RoleMetric("Binding", 10_000_000, 11_000_000, True),   # 1ms
                RoleMetric("Validation", 11_000_000, 12_000_000, True),  # 1ms
            ],
            pipeline_start_ns=0,
            pipeline_end_ns=12_000_000,  # 12ms total
            mission_id="M-001",
            domain_profile="pentest",
            pipeline_ok=True,
        )

    def test_total_duration(self):
        pm = self._make_metrics()
        assert pm.total_duration_ms == 12.0

    def test_roles_passed(self):
        pm = self._make_metrics()
        assert pm.roles_passed == 6
        assert pm.roles_failed == 0

    def test_slowest_role(self):
        pm = self._make_metrics()
        assert pm.slowest_role.role_name == "Decomposition"

    def test_fastest_role(self):
        pm = self._make_metrics()
        # Intake, Binding, and Validation all 1ms — any is valid
        assert pm.fastest_role.duration_ms == 1.0

    def test_role_duration_pct(self):
        pm = self._make_metrics()
        pcts = pm.role_duration_pct()
        assert "Decomposition" in pcts
        # Decomposition is 5/12 ≈ 41.67%
        assert abs(pcts["Decomposition"] - 41.67) < 0.1

    def test_summary(self):
        pm = self._make_metrics()
        s = pm.summary()
        assert s["mission_id"] == "M-001"
        assert s["pipeline_ok"] is True
        assert s["roles_executed"] == 6
        assert s["slowest_role"] == "Decomposition"
        assert len(s["role_timings"]) == 6

    def test_empty_metrics(self):
        pm = PipelineMetrics()
        assert pm.total_duration_ms == 0.0
        assert pm.slowest_role is None
        assert pm.fastest_role is None
        assert pm.roles_passed == 0

    def test_mixed_pass_fail(self):
        pm = PipelineMetrics(
            role_metrics=[
                RoleMetric("Intake", 0, 1_000_000, True),
                RoleMetric("Interpreter", 1_000_000, 2_000_000, False, "failed"),
            ],
            pipeline_ok=False,
        )
        assert pm.roles_passed == 1
        assert pm.roles_failed == 1


# ── MetricsCollector ────────────────────────────────────────────────

class TestMetricsCollector:
    def test_full_collection(self):
        mc = MetricsCollector()
        mc.start_pipeline()
        mc.start_role("Intake")
        mc.end_role("Intake", success=True)
        mc.start_role("Interpreter")
        mc.end_role("Interpreter", success=True)
        mc.end_pipeline()

        metrics = mc.finalize(mission_id="M-001", pipeline_ok=True)
        assert len(metrics.role_metrics) == 2
        assert metrics.pipeline_ok is True
        assert metrics.mission_id == "M-001"
        assert metrics.total_duration_ms > 0

    def test_end_role_without_start(self):
        mc = MetricsCollector()
        mc.end_role("UnknownRole", success=False, error_message="not started")
        metrics = mc.finalize()
        assert len(metrics.role_metrics) == 1
        assert metrics.role_metrics[0].success is False

    def test_reset(self):
        mc = MetricsCollector()
        mc.start_pipeline()
        mc.start_role("X")
        mc.end_role("X")
        mc.reset()
        metrics = mc.finalize()
        assert len(metrics.role_metrics) == 0

    def test_real_timing(self):
        """Verify that timing actually captures real wall clock."""
        mc = MetricsCollector()
        mc.start_pipeline()
        mc.start_role("SlowRole")
        time.sleep(0.01)  # 10ms
        mc.end_role("SlowRole", success=True)
        mc.end_pipeline()
        metrics = mc.finalize()
        assert metrics.role_metrics[0].duration_ms >= 5  # at least 5ms (conservative)


# ── BenchmarkStats ──────────────────────────────────────────────────

class TestBenchmarkStats:
    def test_empty(self):
        bs = BenchmarkStats()
        assert bs.run_count == 0
        assert bs.avg_duration_ms == 0.0
        assert bs.pass_rate == 0.0

    def test_record_runs(self):
        bs = BenchmarkStats()

        pm1 = PipelineMetrics(
            role_metrics=[RoleMetric("Intake", 0, 2_000_000, True)],
            pipeline_start_ns=0,
            pipeline_end_ns=2_000_000,
            pipeline_ok=True,
        )
        pm2 = PipelineMetrics(
            role_metrics=[RoleMetric("Intake", 0, 4_000_000, True)],
            pipeline_start_ns=0,
            pipeline_end_ns=4_000_000,
            pipeline_ok=True,
        )
        pm3 = PipelineMetrics(
            role_metrics=[RoleMetric("Intake", 0, 1_000_000, False)],
            pipeline_start_ns=0,
            pipeline_end_ns=1_000_000,
            pipeline_ok=False,
        )

        bs.record(pm1)
        bs.record(pm2)
        bs.record(pm3)

        assert bs.run_count == 3
        assert bs.total_pass == 2
        assert bs.total_fail == 1
        assert abs(bs.pass_rate - 2 / 3) < 0.01
        assert bs.min_duration_ms == 1.0
        assert bs.max_duration_ms == 4.0
        assert abs(bs.avg_duration_ms - 7 / 3) < 0.01

    def test_per_role_avg(self):
        bs = BenchmarkStats()
        pm = PipelineMetrics(
            role_metrics=[
                RoleMetric("A", 0, 2_000_000, True),
                RoleMetric("B", 0, 4_000_000, True),
            ],
            pipeline_start_ns=0,
            pipeline_end_ns=6_000_000,
            pipeline_ok=True,
        )
        bs.record(pm)
        bs.record(pm)

        avg = bs.per_role_avg_ms()
        assert avg["A"] == 2.0
        assert avg["B"] == 4.0

    def test_summary(self):
        bs = BenchmarkStats()
        pm = PipelineMetrics(
            role_metrics=[],
            pipeline_start_ns=0,
            pipeline_end_ns=1_000_000,
            pipeline_ok=True,
        )
        bs.record(pm)
        s = bs.summary()
        assert s["run_count"] == 1
        assert s["pass_rate"] == 1.0
