"""
Abstract base class for MANDATE pipeline roles.

Each role in the 1+6 pipeline:
1. Receives the current PipelineState
2. Performs its processing
3. Returns a RoleResult indicating success/failure
4. Mutates PipelineState with its outputs

The pipeline orchestrator calls roles in sequence and generates
trace entries for each role execution.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict

from ..models import PipelineState, RoleResult, RoleStatus, PipelineConfig
from ..hashing import compute_trace_entry_hash


class Role(ABC):
    """Abstract base for pipeline roles."""

    # Subclasses set this to their role name (must match trace-entry schema enum)
    ROLE_NAME: str = ""

    def __init__(self, config: PipelineConfig):
        self.config = config

    @abstractmethod
    def execute(self, state: PipelineState) -> RoleResult:
        """
        Execute this role's processing.

        Args:
            state: The shared pipeline state (read inputs, write outputs)

        Returns:
            RoleResult with status and optional artifacts
        """
        ...

    def _make_trace_entry(self, state: PipelineState, decision_type: str) -> Dict[str, Any]:
        """
        Build a trace entry dict for this role execution.

        Returns a dict suitable for hashing with compute_trace_entry_hash().
        """
        return {
            "role": self.ROLE_NAME,
            "decision_type": decision_type,
            "timestamp": datetime.now(timezone.utc).isoformat(
                timespec="milliseconds"
            ).replace("+00:00", "Z"),
            "mission_id": state.mission_id,
        }

    def _success(self, message: str = "", **artifacts: Any) -> RoleResult:
        return RoleResult(
            role_name=self.ROLE_NAME,
            status=RoleStatus.SUCCESS,
            message=message,
            artifacts=artifacts,
        )

    def _fail(self, message: str) -> RoleResult:
        return RoleResult(
            role_name=self.ROLE_NAME,
            status=RoleStatus.FAILED,
            message=message,
        )
