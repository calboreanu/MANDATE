"""
The System interface for the MANDATE evaluation harness (Workstream B1).

Every system under comparison implements System. The interface enforces
PROTOCOL_LOCK Section 11 (baseline fairness):

  * every system receives the SAME raw request_text string and nothing else;
  * no system receives extra context, structure, or hints;
  * every system returns a RunRecord on the single shared schema.
"""
from __future__ import annotations

import abc
from typing import Optional

from .records import RunRecord, utc_now_iso


class System(abc.ABC):
    """Abstract base for every evaluated system."""

    # Subclasses set these.
    system_id: str = ""        # stable machine id, e.g. "mandate_primary"
    system_label: str = ""     # human label, e.g. "MANDATE-primary"
    output_type: str = ""      # default output type for this system

    @abc.abstractmethod
    def run(self, request_text: str, *, run_id: str, task_id: str,
            run_number: int, seed: Optional[int] = None) -> RunRecord:
        """Execute the system on one task and return a populated RunRecord.

        Implementations should not raise for ordinary system failure; they
        should return a RunRecord with ok=False and errors populated. The
        runner catches unexpected exceptions as a backstop.
        """
        raise NotImplementedError

    def describe(self) -> dict:
        """Provenance for the pre-registration pinning section
        (PROTOCOL_LOCK Section 10). Subclasses extend this."""
        return {
            "system_id": self.system_id,
            "system_label": self.system_label,
            "output_type": self.output_type,
        }

    def _new_record(self, *, run_id: str, task_id: str, run_number: int,
                    seed: Optional[int]) -> RunRecord:
        """Helper: a blank RunRecord stamped with identity and start time."""
        return RunRecord(
            run_id=run_id, task_id=task_id,
            system_id=self.system_id, system_label=self.system_label,
            run_number=run_number, seed=seed,
            started_at=utc_now_iso(), output_type=self.output_type,
        )
