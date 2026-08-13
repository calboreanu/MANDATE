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
from collections import defaultdict
from typing import Any, Callable, Optional

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


def _budget_attempt_id(attempt: dict[str, Any]) -> str:
    return str(
        attempt.get("budget_reservation_id")
        or attempt.get("reservation_id")
        or ""
    )


def _budget_attempt_total(attempts: list[dict[str, Any]]) -> float:
    return round(sum(float(a.get("cost_usd") or 0.0) for a in attempts), 6)


def _budget_cost_accounting(attempts: list[dict[str, Any]]) -> str:
    if all(
        str(a.get("cost_basis") or "").startswith("authoritative")
        or str(a.get("cost_basis") or "") == "undispatched_zero"
        for a in attempts
    ):
        return "exact"
    return "conservative_upper_bound"


def _normalize_budget_attempt(
    attempt: dict[str, Any],
    *,
    role: str = "",
) -> dict[str, Any]:
    row = dict(attempt)
    rid = _budget_attempt_id(row)
    if rid:
        row["budget_reservation_id"] = rid
        row.setdefault("reservation_id", rid)
    if role and not row.get("role"):
        row["role"] = role
    if row.get("cost_usd") is not None:
        cost = round(float(row.get("cost_usd") or 0.0), 6)
        row["cost_usd"] = cost
        row.setdefault("debit_usd", cost)
    elif row.get("debit_usd") is not None:
        cost = round(float(row.get("debit_usd") or 0.0), 6)
        row["cost_usd"] = cost
        row["debit_usd"] = cost
    return row


def _merge_budget_attempts(
    existing: list[dict[str, Any]],
    ledger_attempts: list[dict[str, Any]],
    *,
    role: str = "",
) -> list[dict[str, Any]]:
    order: list[str] = []
    by_id: dict[str, dict[str, Any]] = {}
    extras: list[dict[str, Any]] = []
    for attempt in existing or []:
        if not isinstance(attempt, dict):
            continue
        row = _normalize_budget_attempt(attempt, role=role)
        rid = _budget_attempt_id(row)
        if not rid:
            if not ledger_attempts:
                extras.append(row)
            continue
        if rid not in by_id:
            order.append(rid)
        by_id[rid] = row
    for attempt in ledger_attempts or []:
        if not isinstance(attempt, dict):
            continue
        row = _normalize_budget_attempt(attempt, role=role)
        rid = _budget_attempt_id(row)
        if not rid:
            continue
        if rid not in by_id:
            order.append(rid)
            by_id[rid] = row
        else:
            merged = dict(by_id[rid])
            merged.update(row)
            by_id[rid] = merged
    return extras + [by_id[rid] for rid in order]


def _apply_budget_raw(
    raw: dict[str, Any],
    attempts: list[dict[str, Any]],
    *,
    preserve_response_cost: bool = True,
) -> None:
    if not attempts:
        return
    if preserve_response_cost and raw.get("response_cost_usd") is None:
        raw["response_cost_usd"] = raw.get("cost_usd")
    raw["budget_attempts"] = list(attempts)
    raw["budget_total_cost_usd"] = _budget_attempt_total(attempts)
    raw["budget_cost_accounting"] = _budget_cost_accounting(attempts)
    raw["budget_reservation_id"] = _budget_attempt_id(attempts[-1])


def _enrich_record_cost_evidence(record: RunRecord, cost_ledger) -> bool:
    if cost_ledger is None or not hasattr(cost_ledger, "settlement_attempts_for_run"):
        return False
    settlement_attempts = cost_ledger.settlement_attempts_for_run(record.run_id)
    if not settlement_attempts:
        return False

    before = json.dumps(record.to_dict(), sort_keys=True, default=str)
    ledger_total = _budget_attempt_total(settlement_attempts)
    output = record.output if isinstance(record.output, dict) else {}
    condition = record.system_id

    if condition == "cond_a":
        meta = output.get("mission_input_metadata")
        if isinstance(meta, dict):
            raw = meta.get("raw_provider_response")
            if not isinstance(raw, dict):
                raw = {}
                meta["raw_provider_response"] = raw
            attempts = _merge_budget_attempts(
                list(raw.get("budget_attempts") or []),
                settlement_attempts,
                role="PreExtractor",
            )
            _apply_budget_raw(raw, attempts)
            raw["cost_usd"] = _budget_attempt_total(attempts)
            meta["extraction_cost_usd"] = raw["cost_usd"]
    elif condition == "cond_b":
        attempts_by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for attempt in settlement_attempts:
            attempts_by_role[str(attempt.get("role") or "UNKNOWN_ROLE")].append(attempt)
        attached: set[str] = set()
        responses = output.get("provider_responses")
        if isinstance(responses, list):
            claimed_roles: set[str] = set()
            for response in responses:
                if not isinstance(response, dict):
                    continue
                role = str(response.get("role") or "UNKNOWN_ROLE")
                raw = response.get("raw_response")
                if not isinstance(raw, dict):
                    raw = {}
                    response["raw_response"] = raw
                role_attempts = (
                    attempts_by_role.get(role, [])
                    if role not in claimed_roles
                    else []
                )
                if not role_attempts and not raw.get("budget_attempts"):
                    continue
                attempts = _merge_budget_attempts(
                    list(raw.get("budget_attempts") or []),
                    role_attempts,
                    role=role,
                )
                _apply_budget_raw(raw, attempts)
                if attempts:
                    if response.get("response_cost_usd") is None:
                        response["response_cost_usd"] = (
                            raw.get("response_cost_usd")
                            if raw.get("response_cost_usd") is not None
                            else raw.get("cost_usd")
                        )
                    response["cost_usd"] = _budget_attempt_total(attempts)
                    attached.update(
                        _budget_attempt_id(attempt)
                        for attempt in attempts
                        if _budget_attempt_id(attempt)
                    )
                claimed_roles.add(role)
            output["provider_response_count"] = len([
                response for response in responses if isinstance(response, dict)
            ])
        unassigned = [
            attempt
            for attempt in settlement_attempts
            if _budget_attempt_id(attempt) not in attached
        ]
        if unassigned:
            output["recovered_budget_attempts"] = _merge_budget_attempts(
                list(output.get("recovered_budget_attempts") or []),
                unassigned,
            )
        else:
            output.pop("recovered_budget_attempts", None)

    record.api_cost_usd = ledger_total
    return json.dumps(record.to_dict(), sort_keys=True, default=str) != before


def run_matrix(system: System, tasks: list, *, n_runs: int,
               ledger: RunLedger, output_dir: str,
               seed_base: int = 1000, verbose: bool = True,
               skip_existing: bool = False,
               on_record: Optional[Callable[[RunRecord], None]] = None,
               cost_ledger=None) -> list:
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
    if cost_ledger is not None:
        cost_ledger.reconcile_stale_attempts()
    for task in tasks:
        for run_number in range(1, n_runs + 1):
            run_id = f"{system.system_id}__{task.task_id}__r{run_number:02d}"
            seed = seed_base + run_number
            out_path = os.path.join(output_dir, run_id + ".json")

            if skip_existing and os.path.exists(out_path):
                rec = None
                try:
                    import json as _json
                    with open(out_path) as _fh:
                        rec = RunRecord.from_dict(_json.load(_fh))
                except Exception as e:
                    # If the file is corrupt, fall through to re-run rather
                    # than failing the whole resume.
                    if verbose:
                        print(f"  {run_id}: existing file unreadable "
                              f"({e!r}); re-running")
                if rec is not None:
                    if cost_ledger is not None:
                        if _enrich_record_cost_evidence(rec, cost_ledger):
                            rec.save(out_path)
                        cost_ledger.ensure_record_summary(rec)
                    if not ledger.has_run_id(rec.run_id):
                        ledger.append(rec)
                    records.append(rec)
                    n_skipped += 1
                    if on_record is not None:
                        on_record(rec)
                    if verbose:
                        print(f"  {run_id}: SKIP (existing)")
                    continue

            t0 = time.time()
            if cost_ledger is not None:
                cost_ledger.assert_can_schedule()
            try:
                rec = system.run(task.request_text, run_id=run_id,
                                 task_id=task.task_id, run_number=run_number,
                                 seed=seed)
            except Exception as e:                       # backstop only
                api_cost_usd = None
                if cost_ledger is not None:
                    settled = cost_ledger.run_settlement_total(run_id)
                    api_cost_usd = settled if settled > 0 else None
                rec = RunRecord(
                    run_id=run_id, task_id=task.task_id,
                    system_id=system.system_id,
                    system_label=system.system_label,
                    run_number=run_number, seed=seed,
                    started_at=utc_now_iso(),
                    wall_clock_ms=(time.time() - t0) * 1000.0,
                    api_cost_usd=api_cost_usd,
                    ok=False,
                    errors=[f"unhandled exception in system.run: {e!r}",
                            traceback.format_exc()],
                )
            if cost_ledger is not None:
                _enrich_record_cost_evidence(rec, cost_ledger)
            rec.save(out_path)
            ledger.append(rec)
            if cost_ledger is not None and not cost_ledger.has_record_summary(rec.run_id):
                cost_ledger.append_record_summary(rec)
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
