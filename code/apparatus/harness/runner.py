"""
Run orchestration for the MANDATE evaluation harness (Workstream B1).

run_matrix executes one system over a task set with replication, captures a
RunRecord per execution, appends each to the ledger, and writes a per-run
output JSON into the system's output directory. Unexpected exceptions are
caught here as a backstop and recorded as failed runs, so a single crashing
task never aborts a batch.
"""
from __future__ import annotations

import json
import os
import time
import traceback
from dataclasses import dataclass
from typing import Callable, Optional

from .records import RunRecord, utc_now_iso
from .ledger import RunLedger
from .system import System


@dataclass
class Task:
    """One evaluation task. The harness only ever passes request_text to a
    system; domain and category are metadata for stratification and analysis."""
    task_id: str
    request_text: str
    domain: str = ""
    category: str = ""
    source_path: str = ""

    @classmethod
    def from_json_file(cls, path: str) -> "Task":
        with open(path) as f:
            d = json.load(f)
        if "task_id" not in d or "request_text" not in d:
            raise ValueError(
                f"{path}: task JSON must contain 'task_id' and 'request_text'")
        return cls(
            task_id=d["task_id"], request_text=d["request_text"],
            domain=d.get("domain", ""), category=d.get("category", ""),
            source_path=path,
        )


def load_tasks(directory: str) -> list:
    """Load every *.json task file in a directory, sorted by filename."""
    tasks = []
    for name in sorted(os.listdir(directory)):
        if name.endswith(".json"):
            tasks.append(Task.from_json_file(os.path.join(directory, name)))
    return tasks


def run_matrix(system: System, tasks: list, *, n_runs: int,
               ledger: RunLedger, output_dir: str,
               seed_base: int = 1000, verbose: bool = True,
               skip_existing: bool = False,
               on_record: Optional[Callable[[RunRecord], None]] = None) -> list:
    """Run `system` over `tasks`, `n_runs` times each.

    Returns the list of RunRecords. Each record is appended to `ledger` and
    saved as `<output_dir>/<run_id>.json`.

    If `skip_existing` is True, a (task, run_number) tuple whose output file
    `<output_dir>/<run_id>.json` already exists is loaded from disk and
    re-appended to the ledger but NOT re-executed. This is the resume mode
    for long-running multi-day Phase 6 work; without it, a re-fired
    `run-system` would re-execute and overwrite every previously-completed
    record (see HANDOFF_23 2026-06-08 halt).
    """
    os.makedirs(output_dir, exist_ok=True)
    records = []
    n_skipped = 0
    for task in tasks:
        for run_number in range(1, n_runs + 1):
            run_id = f"{system.system_id}__{task.task_id}__r{run_number:02d}"
            seed = seed_base + run_number
            out_path = os.path.join(output_dir, run_id + ".json")

            if skip_existing and os.path.exists(out_path):
                try:
                    import json as _json
                    with open(out_path) as _fh:
                        rec = RunRecord.from_dict(_json.load(_fh))
                    ledger.append(rec)
                    records.append(rec)
                    n_skipped += 1
                    if on_record is not None:
                        on_record(rec)
                    if verbose:
                        print(f"  {run_id}: SKIP (existing)")
                    continue
                except Exception as e:
                    # If the file is corrupt, fall through to re-run rather
                    # than failing the whole resume.
                    if verbose:
                        print(f"  {run_id}: existing file unreadable "
                              f"({e!r}); re-running")

            t0 = time.time()
            try:
                rec = system.run(task.request_text, run_id=run_id,
                                 task_id=task.task_id, run_number=run_number,
                                 seed=seed)
            except Exception as e:                       # backstop only
                rec = RunRecord(
                    run_id=run_id, task_id=task.task_id,
                    system_id=system.system_id,
                    system_label=system.system_label,
                    run_number=run_number, seed=seed,
                    started_at=utc_now_iso(),
                    wall_clock_ms=(time.time() - t0) * 1000.0,
                    ok=False,
                    errors=[f"unhandled exception in system.run: {e!r}",
                            traceback.format_exc()],
                )
            ledger.append(rec)
            rec.save(out_path)
            records.append(rec)
            if on_record is not None:
                on_record(rec)
            if verbose:
                flag = " [LLM-FALLBACK]" if rec.any_llm_fallback else ""
                print(f"  {run_id}: ok={rec.ok} "
                      f"{rec.wall_clock_ms:.1f}ms{flag}")
    if verbose and skip_existing and n_skipped:
        print(f"  (skipped {n_skipped} existing records; "
              f"executed {len(records) - n_skipped} new)")
    return records
