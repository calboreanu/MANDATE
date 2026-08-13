"""
ReferenceSystem: a dependency-free, deterministic system.

It is NOT a study comparator. It exists so the harness can be exercised and
tested end to end without AEGIS, Ollama, or any API, and as a trivial sanity
floor when checking the run matrix and the ledger.
"""
from __future__ import annotations

import time
from typing import Optional

from ..harness.records import RoleTiming
from ..harness.system import System


class ReferenceSystem(System):
    system_id = "reference"
    system_label = "Reference (harness self-test)"
    output_type = "BASELINE_SCHEMA:reference"

    def run(self, request_text: str, *, run_id: str, task_id: str,
            run_number: int, seed: Optional[int] = None):
        t0 = time.time()
        rec = self._new_record(run_id=run_id, task_id=task_id,
                               run_number=run_number, seed=seed)
        words = request_text.split()
        rec.output = {
            "echo_chars": len(request_text),
            "word_count": len(words),
            "note": "reference system, not a study comparator",
        }
        elapsed = (time.time() - t0) * 1000.0
        rec.role_timings = [RoleTiming(role_name="reference", status="success",
                                       duration_ms=elapsed)]
        rec.wall_clock_ms = elapsed
        rec.local_compute_ms = elapsed
        rec.api_cost_usd = 0.0
        rec.model_versions = {"mode": "deterministic-reference"}
        rec.ok = True
        return rec
