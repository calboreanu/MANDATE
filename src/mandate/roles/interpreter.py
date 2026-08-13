"""
Role 1: Interpreter

Extracts the anchor structure from the mission input:
- mission_intent
- minimum (minimum viable outcome)
- target (ideal outcome)
- constraints (validated EBNF strings)
- risk_tolerance

Computes anchor_hash using mandate.hashing.compute_anchor_hash().
"""
from __future__ import annotations

from typing import Any, Dict

from ..constraints import parse_constraint, ForbidsPredicate
from ..hashing import compute_anchor_hash
from ..models import GapSpec, GapType, PipelineState, RoleResult
from .base import Role


class InterpreterRole(Role):
    """Interpreter role: anchor extraction and constraint parsing."""

    ROLE_NAME = "Interpreter"

    def execute(self, state: PipelineState) -> RoleResult:
        mi = state.mission_input
        if mi is None:
            return self._fail("No MissionInput in state")

        # ── Build anchor intent ───────────────────────────────────
        state.anchor_intent = mi.intent

        # ── Build minimum outcome (detect gap if missing) ─────────
        if mi.minimum_outcome:
            state.anchor_minimum = {"description": mi.minimum_outcome}
        else:
            # Derive a reasonable minimum from the intent
            state.anchor_minimum = {
                "description": f"Minimally satisfy: {mi.intent[:120]}"
            }
            state.gaps.append(GapSpec(
                gap_type=GapType.UNDEFINED_MINIMUM,
                detected_by=self.ROLE_NAME,
                pipeline_stage=2,
                field_or_task="minimum_outcome",
                reason="Mission input does not specify an explicit minimum outcome. "
                       "A default was derived from mission intent.",
                action_required="Define an explicit minimum_outcome field with "
                                "quantifiable acceptance criteria.",
                responsible_party="Mission Author",
                complexity="LOW",
                completion_percentage=30,
                blocking=False,
                partial_spec_available=True,
            ))

        # ── Build target outcome (detect gap if missing) ──────────
        if mi.target_outcome:
            state.anchor_target = {"description": mi.target_outcome}
        else:
            state.anchor_target = {
                "description": f"Fully achieve: {mi.intent[:120]}"
            }
            state.gaps.append(GapSpec(
                gap_type=GapType.UNDEFINED_TARGET,
                detected_by=self.ROLE_NAME,
                pipeline_stage=2,
                field_or_task="target_outcome",
                reason="Mission input does not specify an explicit target outcome. "
                       "A default was derived from mission intent.",
                action_required="Define an explicit target_outcome field describing "
                                "the ideal outcome with measurable criteria.",
                responsible_party="Mission Author",
                complexity="LOW",
                completion_percentage=30,
                blocking=False,
                partial_spec_available=True,
            ))

        # ── Constraints ───────────────────────────────────────────
        state.constraints = list(mi.constraints)

        # ── Determine risk tolerance (detect gap if unassessable) ─
        state.risk_tolerance = self._derive_risk_tolerance(mi.risk_tolerance, mi.constraints)

        if state.risk_tolerance is None:
            state.gaps.append(GapSpec(
                gap_type=GapType.UNASSESSABLE_RISK,
                detected_by=self.ROLE_NAME,
                pipeline_stage=2,
                field_or_task="risk_tolerance",
                reason="Cannot determine risk tolerance. No explicit risk_tolerance "
                       "was provided and no FORBIDS constraints exist to infer one.",
                action_required="Provide an explicit risk_tolerance field (LOW, MEDIUM, "
                                "or HIGH) or add FORBIDS constraints to establish boundaries.",
                responsible_party="Mission Author",
                complexity="LOW",
                completion_percentage=0,
                blocking=False,
                partial_spec_available=False,
            ))

        # ── Compute anchor_hash ───────────────────────────────────
        anchor_dict = self._build_anchor_dict(state)
        state.anchor_hash = compute_anchor_hash(anchor_dict)

        gap_count = len(state.gaps)
        msg = f"Anchor extracted: hash={state.anchor_hash[:16]}..."
        if gap_count:
            msg += f" ({gap_count} gap(s) detected)"

        return self._success(
            msg,
            anchor_hash=state.anchor_hash,
            constraint_count=len(state.constraints),
            gaps_detected=gap_count,
        )

    def _build_anchor_dict(self, state: PipelineState) -> Dict[str, Any]:
        """Build the anchor dict (without anchor_hash) for hashing."""
        d: Dict[str, Any] = {
            "mission_intent": state.anchor_intent,
            "minimum": state.anchor_minimum,
            "constraints": state.constraints,
        }
        if state.anchor_target:
            d["target"] = state.anchor_target
        if state.risk_tolerance:
            d["risk_tolerance"] = state.risk_tolerance
        return d

    def _derive_risk_tolerance(
        self,
        explicit: str | None,
        constraints: list[str],
    ) -> Dict[str, Any] | None:
        """
        Derive risk_tolerance from explicit setting or constraint analysis.

        Heuristic: If FORBIDS constraints exist, assume stricter tolerance.
        """
        if explicit:
            level = explicit.upper()
            if level in ("LOW", "MEDIUM", "HIGH"):
                escalate = "MEDIUM" if level == "LOW" else "HIGH"
                return {
                    "max_autonomous_score": level,
                    "escalate_above": escalate,
                }

        # Analyze constraints for severity signals
        forbids_count = 0
        for c in constraints:
            try:
                ast = parse_constraint(c)
                if isinstance(ast, ForbidsPredicate):
                    forbids_count += 1
            except Exception:
                pass

        if forbids_count >= 2:
            return {
                "max_autonomous_score": "LOW",
                "escalate_above": "MEDIUM",
            }
        elif forbids_count == 1:
            return {
                "max_autonomous_score": "MEDIUM",
                "escalate_above": "HIGH",
            }

        # No explicit tolerance, no strong signals
        return None
