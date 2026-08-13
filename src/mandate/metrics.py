"""
MANDATE Pipeline Metrics Collection

Provides timing and performance metrics for pipeline role execution,
supporting the evaluation harness and benchmark suite.

Usage:
    from mandate.metrics import MetricsCollector, PipelineMetrics

    collector = MetricsCollector()
    collector.start_role("Intake")
    # ... role executes ...
    collector.end_role("Intake", success=True)
    metrics = collector.finalize()

    print(metrics.total_duration_ms)
    print(metrics.summary())
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RoleMetric:
    """Timing and status metric for a single role execution."""
    role_name: str
    start_time_ns: int = 0           # monotonic nanoseconds
    end_time_ns: int = 0             # monotonic nanoseconds
    success: bool = False
    error_message: str = ""

    @property
    def duration_ns(self) -> int:
        """Duration in nanoseconds."""
        return self.end_time_ns - self.start_time_ns

    @property
    def duration_ms(self) -> float:
        """Duration in milliseconds."""
        return self.duration_ns / 1_000_000

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_name": self.role_name,
            "duration_ms": round(self.duration_ms, 3),
            "success": self.success,
            "error_message": self.error_message,
        }


@dataclass
class PipelineMetrics:
    """Aggregated metrics for a full pipeline run."""
    role_metrics: List[RoleMetric] = field(default_factory=list)
    pipeline_start_ns: int = 0
    pipeline_end_ns: int = 0
    mission_id: str = ""
    domain_profile: str = ""         # domain_id if used
    pipeline_ok: bool = False

    @property
    def total_duration_ns(self) -> int:
        return self.pipeline_end_ns - self.pipeline_start_ns

    @property
    def total_duration_ms(self) -> float:
        return self.total_duration_ns / 1_000_000

    @property
    def roles_passed(self) -> int:
        return sum(1 for m in self.role_metrics if m.success)

    @property
    def roles_failed(self) -> int:
        return sum(1 for m in self.role_metrics if not m.success)

    @property
    def slowest_role(self) -> Optional[RoleMetric]:
        if not self.role_metrics:
            return None
        return max(self.role_metrics, key=lambda m: m.duration_ns)

    @property
    def fastest_role(self) -> Optional[RoleMetric]:
        if not self.role_metrics:
            return None
        return min(self.role_metrics, key=lambda m: m.duration_ns)

    def role_duration_pct(self) -> Dict[str, float]:
        """Return each role's share of total pipeline time as a percentage."""
        total = self.total_duration_ns
        if total == 0:
            return {m.role_name: 0.0 for m in self.role_metrics}
        return {
            m.role_name: round((m.duration_ns / total) * 100, 2)
            for m in self.role_metrics
        }

    def summary(self) -> Dict[str, Any]:
        """Return a serializable summary dict."""
        slowest = self.slowest_role
        return {
            "mission_id": self.mission_id,
            "domain_profile": self.domain_profile,
            "pipeline_ok": self.pipeline_ok,
            "total_duration_ms": round(self.total_duration_ms, 3),
            "roles_executed": len(self.role_metrics),
            "roles_passed": self.roles_passed,
            "roles_failed": self.roles_failed,
            "slowest_role": slowest.role_name if slowest else None,
            "slowest_role_ms": round(slowest.duration_ms, 3) if slowest else None,
            "role_timings": [m.to_dict() for m in self.role_metrics],
            "role_duration_pct": self.role_duration_pct(),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Full serialization for storage/comparison."""
        return self.summary()


class MetricsCollector:
    """
    Collects pipeline execution metrics.

    Used by the Pipeline orchestrator to time each role and by the
    evaluation harness to compare performance across runs.
    """

    def __init__(self) -> None:
        self._role_metrics: Dict[str, RoleMetric] = {}
        self._pipeline_start_ns: int = 0
        self._pipeline_end_ns: int = 0

    def start_pipeline(self) -> None:
        """Mark pipeline start time."""
        self._pipeline_start_ns = time.monotonic_ns()

    def end_pipeline(self) -> None:
        """Mark pipeline end time."""
        self._pipeline_end_ns = time.monotonic_ns()

    def start_role(self, role_name: str) -> None:
        """Mark the start of a role execution."""
        self._role_metrics[role_name] = RoleMetric(
            role_name=role_name,
            start_time_ns=time.monotonic_ns(),
        )

    def end_role(self, role_name: str, success: bool = True,
                 error_message: str = "") -> None:
        """Mark the end of a role execution."""
        metric = self._role_metrics.get(role_name)
        if metric is None:
            # Role wasn't started — create a zero-duration entry
            metric = RoleMetric(role_name=role_name)
            self._role_metrics[role_name] = metric
        metric.end_time_ns = time.monotonic_ns()
        metric.success = success
        metric.error_message = error_message

    def finalize(self, mission_id: str = "", domain_profile: str = "",
                 pipeline_ok: bool = False) -> PipelineMetrics:
        """
        Build the final PipelineMetrics from collected data.

        Should be called after end_pipeline().
        """
        return PipelineMetrics(
            role_metrics=list(self._role_metrics.values()),
            pipeline_start_ns=self._pipeline_start_ns,
            pipeline_end_ns=self._pipeline_end_ns,
            mission_id=mission_id,
            domain_profile=domain_profile,
            pipeline_ok=pipeline_ok,
        )

    def reset(self) -> None:
        """Clear all collected metrics."""
        self._role_metrics.clear()
        self._pipeline_start_ns = 0
        self._pipeline_end_ns = 0


@dataclass
class BenchmarkStats:
    """
    Aggregate statistics across multiple pipeline runs.

    Used by the benchmark suite to report on corpus-level performance.
    """
    run_count: int = 0
    total_pass: int = 0
    total_fail: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float("inf")
    max_duration_ms: float = 0.0
    per_role_totals: Dict[str, float] = field(default_factory=dict)
    per_role_counts: Dict[str, int] = field(default_factory=dict)

    def record(self, metrics: PipelineMetrics) -> None:
        """Record a single pipeline run's metrics."""
        self.run_count += 1
        if metrics.pipeline_ok:
            self.total_pass += 1
        else:
            self.total_fail += 1

        dur = metrics.total_duration_ms
        self.total_duration_ms += dur
        if dur < self.min_duration_ms:
            self.min_duration_ms = dur
        if dur > self.max_duration_ms:
            self.max_duration_ms = dur

        for rm in metrics.role_metrics:
            name = rm.role_name
            self.per_role_totals[name] = self.per_role_totals.get(name, 0.0) + rm.duration_ms
            self.per_role_counts[name] = self.per_role_counts.get(name, 0) + 1

    @property
    def avg_duration_ms(self) -> float:
        if self.run_count == 0:
            return 0.0
        return self.total_duration_ms / self.run_count

    @property
    def pass_rate(self) -> float:
        if self.run_count == 0:
            return 0.0
        return self.total_pass / self.run_count

    def per_role_avg_ms(self) -> Dict[str, float]:
        """Average duration per role across all runs."""
        return {
            name: round(self.per_role_totals[name] / self.per_role_counts[name], 3)
            for name in sorted(self.per_role_totals)
        }

    def summary(self) -> Dict[str, Any]:
        return {
            "run_count": self.run_count,
            "pass_rate": round(self.pass_rate, 4),
            "avg_duration_ms": round(self.avg_duration_ms, 3),
            "min_duration_ms": round(self.min_duration_ms, 3) if self.min_duration_ms != float("inf") else None,
            "max_duration_ms": round(self.max_duration_ms, 3),
            "per_role_avg_ms": self.per_role_avg_ms(),
        }
