"""
Run records for the MANDATE evaluation harness (Workstream B1).

A RunRecord is the unit of captured evidence for one execution of one system
on one task. Every system under comparison (MANDATE-primary, baselines B1-B6,
the five alternative backends, the seven ablations, and the human expert)
emits RunRecords through the same harness, so that anonymization, three-judge
grading, and the statistical analysis all operate on a single schema.

This module has no third-party dependencies and no dependency on AEGIS.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

HARNESS_VERSION = "0.1.0"

# Output-type vocabulary (PROTOCOL_LOCK Section 4, PROMPTS Section 4).
OUTPUT_MANDATE_AS_CODE = "MANDATE_AS_CODE"
OUTPUT_GAP_REPORT = "GAP_REPORT"
# Baseline schemas are namespaced as "BASELINE_SCHEMA:<name>".


def utc_now_iso() -> str:
    """Current UTC time as an ISO-8601 string, second precision."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class RoleTiming:
    """One stage of a system's execution.

    For MANDATE this is one of the six roles. For single-stage systems it is
    one synthetic entry. The llm_used / llm_fallback fields are the silent-
    fallback detector the execution plan flags as critical: a MANDATE-primary
    run with llm_fallback set on any fine-tuned role is not a clean
    observation of MANDATE-primary.
    """
    role_name: str
    status: str = "success"            # success | failed | skipped
    duration_ms: float = 0.0
    llm_used: bool = False
    llm_fallback: bool = False
    llm_fallback_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "role_name": self.role_name,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 4),
            "llm_used": self.llm_used,
            "llm_fallback": self.llm_fallback,
            "llm_fallback_reason": self.llm_fallback_reason,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RoleTiming":
        return cls(
            role_name=d.get("role_name", ""),
            status=d.get("status", "success"),
            duration_ms=float(d.get("duration_ms", 0.0)),
            llm_used=bool(d.get("llm_used", False)),
            llm_fallback=bool(d.get("llm_fallback", False)),
            llm_fallback_reason=d.get("llm_fallback_reason", ""),
        )


@dataclass
class RunRecord:
    """Captured evidence for one (system, task, run) execution."""

    # --- identity ---
    run_id: str
    task_id: str
    system_id: str
    system_label: str
    run_number: int
    seed: Optional[int] = None

    # --- timing ---
    started_at: str = ""
    wall_clock_ms: float = 0.0
    role_timings: list = field(default_factory=list)        # list[RoleTiming]

    # --- cost / compute (PROTOCOL_LOCK Section 6.5) ---
    api_cost_usd: Optional[float] = None
    local_compute_ms: Optional[float] = None

    # --- provenance / pinning (PROTOCOL_LOCK Section 10) ---
    model_versions: dict = field(default_factory=dict)
    decoding_params: dict = field(default_factory=dict)
    code_ref: str = ""                                      # AEGIS git tag/commit
    harness_version: str = HARNESS_VERSION

    # --- output ---
    output_type: str = ""
    output: Any = None

    # --- status ---
    ok: bool = False
    errors: list = field(default_factory=list)              # list[str]

    @property
    def any_llm_fallback(self) -> bool:
        """True if any role silently fell back to the deterministic path."""
        return any(getattr(rt, "llm_fallback", False) for rt in self.role_timings)

    @property
    def fallback_roles(self) -> list:
        return [rt.role_name for rt in self.role_timings
                if getattr(rt, "llm_fallback", False)]

    @property
    def llm_roles_used(self) -> list:
        return [rt.role_name for rt in self.role_timings
                if getattr(rt, "llm_used", False)]

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "system_id": self.system_id,
            "system_label": self.system_label,
            "run_number": self.run_number,
            "seed": self.seed,
            "started_at": self.started_at,
            "wall_clock_ms": round(self.wall_clock_ms, 4),
            "role_timings": [rt.to_dict() for rt in self.role_timings],
            "api_cost_usd": self.api_cost_usd,
            "local_compute_ms": (round(self.local_compute_ms, 4)
                                 if self.local_compute_ms is not None else None),
            "model_versions": self.model_versions,
            "decoding_params": self.decoding_params,
            "code_ref": self.code_ref,
            "harness_version": self.harness_version,
            "output_type": self.output_type,
            "output": self.output,
            "ok": self.ok,
            "errors": self.errors,
            # derived fields, included for downstream convenience and audit:
            "any_llm_fallback": self.any_llm_fallback,
            "fallback_roles": self.fallback_roles,
            "llm_roles_used": self.llm_roles_used,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RunRecord":
        return cls(
            run_id=d["run_id"], task_id=d["task_id"],
            system_id=d["system_id"], system_label=d.get("system_label", ""),
            run_number=int(d.get("run_number", 1)), seed=d.get("seed"),
            started_at=d.get("started_at", ""),
            wall_clock_ms=float(d.get("wall_clock_ms", 0.0)),
            role_timings=[RoleTiming.from_dict(x)
                          for x in d.get("role_timings", [])],
            api_cost_usd=d.get("api_cost_usd"),
            local_compute_ms=d.get("local_compute_ms"),
            model_versions=d.get("model_versions", {}),
            decoding_params=d.get("decoding_params", {}),
            code_ref=d.get("code_ref", ""),
            harness_version=d.get("harness_version", ""),
            output_type=d.get("output_type", ""),
            output=d.get("output"),
            ok=bool(d.get("ok", False)),
            errors=list(d.get("errors", [])),
        )

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def save(self, path: str) -> None:
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)
        with open(path, "w") as f:
            f.write(self.to_json())
