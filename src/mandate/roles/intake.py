"""
Role 0: Intake

Parses and validates the raw MissionInput, populating the initial
PipelineState fields that downstream roles depend on.

Responsibilities:
- Validate required fields (mission_id, intent)
- Set mission_id and timestamp on PipelineState
- Store the MissionInput for downstream access
- Validate constraint syntax (early fail for malformed constraints)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..constraints import validate_constraint, ConstraintError
from ..models import (
    MissionInput,
    PipelineConfig,
    PipelineState,
    RoleResult,
)
from .base import Role


class IntakeRole(Role):
    """Intake role: input parsing and validation."""

    ROLE_NAME = "Intake"

    def execute(self, state: PipelineState) -> RoleResult:
        mi = state.mission_input
        if mi is None:
            return self._fail("No MissionInput provided in PipelineState")

        # ── Validate required fields ──────────────────────────────
        if not mi.mission_id:
            mi.mission_id = f"MANDATE-{uuid.uuid4().hex[:8].upper()}"

        if not mi.intent:
            return self._fail("MissionInput.intent is required")

        # ── Early constraint syntax validation ────────────────────
        invalid_constraints = []
        for i, c in enumerate(mi.constraints):
            if not validate_constraint(c):
                invalid_constraints.append(f"[{i}] {c}")

        if invalid_constraints:
            detail = "; ".join(invalid_constraints)
            return self._fail(f"Invalid constraint syntax: {detail}")

        # ── Populate state ────────────────────────────────────────
        state.mission_id = mi.mission_id
        state.timestamp = datetime.now(timezone.utc).isoformat(
            timespec="milliseconds"
        ).replace("+00:00", "Z")

        return self._success(
            f"Intake complete: mission_id={state.mission_id}",
            mission_id=state.mission_id,
            constraint_count=len(mi.constraints),
            scope_count=len(mi.scope),
        )
