"""
MANDATE 1+6 Pipeline Orchestrator

Chains the six roles (Intake → Interpreter → Decomposition → Procedure →
Binding → Validation) into a sequential pipeline that transforms a
MissionInput into a validated mandate-as-code artifact.

Usage:
    from mandate.pipeline import Pipeline
    from mandate.models import MissionInput, PipelineConfig

    mi = MissionInput(mission_id="M-001", intent="...")
    pipe = Pipeline(PipelineConfig())
    result = pipe.run(mi)

    if result.ok:
        artifact = result.artifact
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .gap_report import build_gap_reports, save_gap_reports
from .execution_contract import (
    CONTRACT_SCHEMA_VERSION,
    build_result_envelope,
    validate_result_envelope,
)
from .hashing import compute_trace_entry_hash
from .metrics import MetricsCollector, PipelineMetrics
from .models import (
    GapSpec,
    MissionInput,
    PipelineConfig,
    PipelineState,
    RoleResult,
    RoleStatus,
)
from .roles import (
    IntakeRole,
    InterpreterRole,
    DecompositionRole,
    ProcedureRole,
    BindingRole,
    ValidationRole,
)
from .roles.base import Role


@dataclass
class PipelineResult:
    """Final output of the pipeline."""
    ok: bool
    artifact: Optional[Dict[str, Any]] = None
    gap_reports: List[Dict[str, Any]] = field(default_factory=list)
    role_results: List[RoleResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metrics: Optional[PipelineMetrics] = None
    schema_valid: Optional[bool] = None
    execution_state: str = ""
    contract_schema_version: str = CONTRACT_SCHEMA_VERSION
    result_envelope: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.result_envelope = build_result_envelope(
            pipeline_succeeded=self.ok,
            artifact=self.artifact,
            gap_reports=self.gap_reports,
            schema_valid=self.schema_valid,
            errors=self.errors,
        )
        self.ok = bool(self.result_envelope["ok"])
        self.execution_state = str(self.result_envelope["execution_state"])
        self.contract_schema_version = str(self.result_envelope["contract_schema_version"])
        issues = validate_result_envelope(
            self.result_envelope,
            artifact=self.artifact,
            gap_reports=self.gap_reports,
            schema_valid=self.schema_valid,
            errors=self.errors,
        )
        if issues:
            raise ValueError("invalid MANDATE result envelope: " + "; ".join(issues))

    @property
    def has_gaps(self) -> bool:
        """True if any specification gaps were detected."""
        return len(self.gap_reports) > 0

    def summary(self) -> Dict[str, Any]:
        """Return a summary dict for logging/display."""
        s: Dict[str, Any] = {
            "ok": self.ok,
            "roles_executed": len(self.role_results),
            "roles_passed": sum(1 for r in self.role_results if r.ok),
            "gaps": len(self.gap_reports),
            "execution_state": self.execution_state,
            "errors": self.errors[:5],
            "mandate_id": self.artifact.get("mandate_id") if self.artifact else None,
        }
        if self.metrics:
            s["total_duration_ms"] = round(self.metrics.total_duration_ms, 3)
        return s


class Pipeline:
    """
    MANDATE 1+6 pipeline orchestrator.

    Runs six roles in sequence, building up PipelineState.
    If any role fails and config.strict is True, the pipeline
    stops and returns the error.
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self._roles: List[Role] = [
            IntakeRole(self.config),
            InterpreterRole(self.config),
            DecompositionRole(self.config),
            ProcedureRole(self.config),
            BindingRole(self.config),
            ValidationRole(self.config),
        ]

    def run(self, mission_input: MissionInput,
            collect_metrics: bool = True) -> PipelineResult:
        """
        Execute the full pipeline.

        Args:
            mission_input: The mission specification to process
            collect_metrics: Whether to collect timing metrics (default True)

        Returns:
            PipelineResult with the artifact (if successful) and role results
        """
        collector: Optional[MetricsCollector] = None
        if collect_metrics:
            collector = MetricsCollector()
            collector.start_pipeline()

        state = PipelineState(mission_input=mission_input)
        results: List[RoleResult] = []
        errors: List[str] = []

        for role in self._roles:
            if self.config.verbose:
                print(f"[PIPELINE] Running {role.ROLE_NAME}...", file=sys.stderr)

            if collector:
                collector.start_role(role.ROLE_NAME)

            try:
                result = role.execute(state)
            except Exception as e:
                result = RoleResult(
                    role_name=role.ROLE_NAME,
                    status=RoleStatus.FAILED,
                    message=f"Unhandled exception: {e}",
                )

            if collector:
                collector.end_role(
                    role.ROLE_NAME,
                    success=result.ok,
                    error_message=result.message if not result.ok else "",
                )

            # Generate trace entry for this role
            trace_entry = role._make_trace_entry(state, f"{role.ROLE_NAME.lower()}_phase")
            result.trace_entry_hash = compute_trace_entry_hash(trace_entry)

            results.append(result)

            if self.config.verbose:
                status = "OK" if result.ok else "FAIL"
                print(
                    f"[PIPELINE]   {role.ROLE_NAME}: {status} — {result.message}",
                    file=sys.stderr,
                )

            if not result.ok:
                errors.append(f"{role.ROLE_NAME}: {result.message}")
                if self.config.strict:
                    if collector:
                        collector.end_pipeline()
                    metrics = None
                    if collector:
                        domain_id = ""
                        if self.config.domain_profile:
                            domain_id = self.config.domain_profile.domain_id
                        metrics = collector.finalize(
                            mission_id=state.mission_id or mission_input.mission_id,
                            domain_profile=domain_id,
                            pipeline_ok=False,
                        )
                    return PipelineResult(
                        ok=False,
                        role_results=results,
                        errors=errors + state.errors,
                        metrics=metrics,
                        schema_valid=None,
                    )

        # Extract artifact from the Validation role's output
        artifact = None
        validation_result = results[-1] if results else None
        if validation_result and validation_result.ok:
            artifact = validation_result.artifacts.get("artifact")

        all_ok = all(r.ok for r in results) and artifact is not None

        # Build gap reports if any gaps were detected
        gap_reports: List[Dict[str, Any]] = []
        # Gap evidence is part of the result contract, not an optional logging
        # side channel. Omitting it would make fail-closed routing impossible.
        if state.gaps:
            gap_reports = build_gap_reports(state.gaps, state.mission_id)
            if self.config.verbose:
                print(
                    f"[PIPELINE] {len(gap_reports)} gap report(s) generated",
                    file=sys.stderr,
                )

        schema_valid: Optional[bool] = None
        if artifact is not None:
            import tempfile
            from .validator import validate_artifact

            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
                json.dump(artifact, tmp, ensure_ascii=False)
                tmp_path = Path(tmp.name)
            try:
                _artifact_type, issues = validate_artifact(tmp_path)
                schema_valid = not issues
            finally:
                tmp_path.unlink(missing_ok=True)

        # Finalize metrics
        metrics = None
        if collector:
            collector.end_pipeline()
            domain_id = ""
            if self.config.domain_profile:
                domain_id = self.config.domain_profile.domain_id
            metrics = collector.finalize(
                mission_id=state.mission_id or mission_input.mission_id,
                domain_profile=domain_id,
                pipeline_ok=all_ok,
            )

        return PipelineResult(
            ok=all_ok,
            artifact=artifact,
            gap_reports=gap_reports,
            role_results=results,
            errors=errors + state.errors,
            metrics=metrics,
            schema_valid=schema_valid,
        )

    def run_and_save(
        self,
        mission_input: MissionInput,
        output_path: Path,
    ) -> PipelineResult:
        """
        Run the pipeline and save the artifact to a file.

        Saves gap reports whenever the pipeline detects them.

        Args:
            mission_input: The mission specification
            output_path: Where to write the mandate-as-code JSON

        Returns:
            PipelineResult (same as run())
        """
        result = self.run(mission_input)

        if result.artifact:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result.artifact, f, indent=2, ensure_ascii=False)

            if self.config.verbose:
                print(f"[PIPELINE] Artifact saved to {output_path}", file=sys.stderr)

        # Save gap reports alongside the mandate
        if result.gap_reports:
            gap_dir = output_path.parent / "gaps"
            paths = save_gap_reports(result.gap_reports, gap_dir)
            if self.config.verbose:
                for p in paths:
                    print(f"[PIPELINE] Gap report saved to {p}", file=sys.stderr)

        return result
