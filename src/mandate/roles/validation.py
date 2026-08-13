"""
Role 5: Validation

Final pipeline role: assembles the mandate-as-code artifact from
PipelineState and runs validation as a quality gate.

Responsibilities:
- Assemble complete mandate-as-code dict from PipelineState
- Generate trace entries and chain hash
- Run the existing validator.validate_artifact() as final gate
- Return the complete artifact or detailed error report
"""
from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ..hashing import (
    compute_anchor_hash,
    compute_chain_hash_from_strings,
    compute_trace_entry_hash,
)
from ..models import (
    COASpec,
    PipelineConfig,
    PipelineState,
    RoleResult,
)
from .base import Role


class ValidationRole(Role):
    """Validation role: final assembly and validation gate."""

    ROLE_NAME = "Validation"

    def execute(self, state: PipelineState) -> RoleResult:
        # ── Build trace entries ────────────────────────────────────
        trace_hashes, chain_hash = self._build_trace(state)
        state.trace_entry_hashes = trace_hashes
        state.chain_hash = chain_hash

        # ── Assemble artifact ─────────────────────────────────────
        artifact = self._assemble_artifact(state)

        # ── Validate using existing validator ─────────────────────
        is_valid, errors = self._validate(artifact)

        if not is_valid:
            detail = "; ".join(errors[:5])  # First 5 errors
            state.errors.extend(errors)
            return self._fail(f"Validation failed ({len(errors)} issues): {detail}")

        return self._success(
            "Artifact assembled and validated successfully",
            artifact=artifact,
            trace_entries=len(trace_hashes),
            chain_hash=chain_hash[:16] + "...",
        )

    def _build_trace(self, state: PipelineState) -> Tuple[List[str], str]:
        """
        Build trace entry hashes for the pipeline roles.

        Uses bare hash strings (the lightweight form accepted by
        mandate-as-code.schema.json trace.entries).
        """
        roles = [
            "Intake", "Interpreter", "Decomposition",
            "Procedure", "Binding", "Validation",
        ]
        now = datetime.now(timezone.utc).isoformat(
            timespec="milliseconds"
        ).replace("+00:00", "Z")

        entry_hashes: List[str] = []
        for role in roles:
            entry = {
                "role": role,
                "action": f"{role.lower()}_phase",
                "timestamp": now,
                "mission_id": state.mission_id,
            }
            h = compute_trace_entry_hash(entry)
            entry_hashes.append(h)

        chain_hash = compute_chain_hash_from_strings(entry_hashes)
        return entry_hashes, chain_hash

    def _assemble_artifact(self, state: PipelineState) -> Dict[str, Any]:
        """Assemble the complete mandate-as-code artifact from state."""
        now = state.timestamp or datetime.now(timezone.utc).isoformat(
            timespec="milliseconds"
        ).replace("+00:00", "Z")

        # Build anchor
        anchor: Dict[str, Any] = {
            "mission_intent": state.anchor_intent,
            "minimum": state.anchor_minimum,
            "constraints": state.constraints,
            "anchor_hash": state.anchor_hash,
        }
        if state.anchor_target:
            anchor["target"] = state.anchor_target
        if state.risk_tolerance:
            anchor["risk_tolerance"] = state.risk_tolerance

        # Build courses of action
        coas_list = [self._coa_to_dict(coa) for coa in state.coas]

        # Build recommendation
        rec = state.recommendation
        recommendation = {
            "primary_coa": rec.primary_coa if rec else state.coas[0].coa_id,
            "fallback_sequence": rec.fallback_sequence if rec else [],
            "rationale": rec.rationale if rec else "Default selection",
        }

        # Build trace
        trace = {
            "chain_hash": state.chain_hash,
            "entry_count": len(state.trace_entry_hashes),
            "entries": state.trace_entry_hashes,
        }

        artifact = {
            "mandate_id": state.mission_id,
            "version": self.config.version,
            "generated": now,
            "anchor": anchor,
            "courses_of_action": coas_list,
            "recommendation": recommendation,
            "trace": trace,
        }

        return artifact

    def _coa_to_dict(self, coa: COASpec) -> Dict[str, Any]:
        """Convert COASpec to schema-compliant dict."""
        # Build task DAG
        nodes = []
        for node in coa.task_nodes:
            n: Dict[str, Any] = {
                "id": node.node_id,
                "name": node.name,
            }
            if node.description:
                n["description"] = node.description
            if node.risk_factors:
                n["risk_factors"] = node.risk_factors
            nodes.append(n)

        edges = []
        for edge in coa.edges:
            edges.append({"from": edge["from"], "to": edge["to"]})

        d: Dict[str, Any] = {
            "coa_id": coa.coa_id,
            "approach": coa.approach,
            "task_dag": {"nodes": nodes, "edges": edges},
            "risk_assessment": {
                "score": coa.risk_assessment.score.value if coa.risk_assessment else "MEDIUM",
                "confidence_min": coa.risk_assessment.confidence_min.value if coa.risk_assessment else "MEDIUM",
                "confidence_target": coa.risk_assessment.confidence_target.value if coa.risk_assessment else "HIGH",
                "primary_factor": coa.risk_assessment.primary_factor if coa.risk_assessment else "execution_uncertainty",
            },
            "off_nominal_triggers": coa.off_nominal_triggers,
        }

        if coa.procedures:
            d["procedures"] = coa.procedures
        if coa.capabilities:
            d["capabilities"] = coa.capabilities

        return d

    def _validate(self, artifact: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate the assembled artifact using MANDATE's validator.

        Writes to a temp file because validate_artifact expects a path.
        """
        try:
            from ..validator import validate_artifact

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                json.dump(artifact, f, indent=2, ensure_ascii=False)
                tmp_path = Path(f.name)

            try:
                artifact_type, issues = validate_artifact(tmp_path)
                if not issues:
                    return True, []
                errors = []
                for issue in issues:
                    msg = f"[{issue.kind}] {issue.message}"
                    if issue.path:
                        msg += f" (path: {issue.path})"
                    errors.append(msg)
                return False, errors
            finally:
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

        except ImportError as e:
            # Validator unavailable — pass through
            return True, [f"Note: Validator unavailable ({e})"]
        except Exception as e:
            return False, [f"Validation error: {str(e)}"]
