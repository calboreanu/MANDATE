"""
Append-only run ledger for the MANDATE evaluation harness (Workstream B1).

The ledger is a JSONL file: one RunRecord per line. It is the canonical
index of every system execution in the study. Per-run output JSON files are
written separately into the 07_system_outputs tree by the runner.

The ledger is append-only on purpose. Once a run is recorded it is not
rewritten; corrections are handled by re-running and by the deviation log,
never by editing history. This mirrors the freeze discipline in PROTOCOL_LOCK.
"""
from __future__ import annotations

import json
import os
import uuid
import time
from contextlib import contextmanager

import fcntl

from .records import RunRecord


class RunLedger:
    def __init__(self, path: str):
        self.path = path
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)
        if not os.path.exists(path):
            open(path, "a").close()

    def append(self, record: RunRecord) -> None:
        if self.has_run_id(record.run_id):
            raise ValueError(f"duplicate run_id refused by ledger: {record.run_id}")
        with open(self.path, "a") as f:
            f.write(json.dumps(record.to_dict(), default=str) + "\n")

    def has_run_id(self, run_id: str) -> bool:
        if not os.path.exists(self.path):
            return False
        with open(self.path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    if json.loads(line).get("run_id") == run_id:
                        return True
                except Exception:
                    continue
        return False

    def __iter__(self):
        with open(self.path) as f:
            for line in f:
                line = line.strip()
                if line:
                    yield RunRecord.from_dict(json.loads(line))

    def count(self) -> int:
        return sum(1 for _ in self)

    @staticmethod
    def load(path: str) -> list:
        return list(RunLedger(path))


class CampaignBudgetExceeded(RuntimeError):
    pass


class CampaignCostLedger:
    """Shared JSONL reservation ledger for cumulative API cost cutoffs."""

    def __init__(self, path: str, budget_usd: float):
        if budget_usd <= 0:
            raise ValueError("--campaign-budget-usd must be > 0")
        self.path = path
        self.budget_usd = float(budget_usd)
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)
        if not os.path.exists(path):
            open(path, "a").close()

    @contextmanager
    def _locked_file(self):
        with open(self.path, "a+", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.seek(0)
                yield f
            finally:
                f.flush()
                os.fsync(f.fileno())
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _parse_entries(f) -> list[dict]:
        rows: list[dict] = []
        f.seek(0)
        for line in f:
            s = line.strip()
            if not s:
                continue
            rows.append(json.loads(s))
        return rows

    def entries(self) -> list[dict]:
        with open(self.path, encoding="utf-8") as f:
            return self._parse_entries(f)

    @staticmethod
    def _settled_total(rows: list[dict]) -> float:
        settled = sum(
            float(row.get("actual_cost_usd") or 0.0)
            for row in rows
            if row.get("row_type") == "settlement"
        )
        settled_run_ids = {
            row.get("run_id")
            for row in rows
            if row.get("row_type") == "settlement"
        }
        legacy_or_unreserved = sum(
            float(row.get("api_cost_usd") or 0.0)
            for row in rows
            if row.get("row_type") in {"record_summary", None}
            and row.get("run_id") not in settled_run_ids
        )
        return round(settled + legacy_or_unreserved, 6)

    @staticmethod
    def _active_reserved_total(rows: list[dict]) -> float:
        settled = {
            row.get("reservation_id")
            for row in rows
            if row.get("row_type") == "settlement"
        }
        return round(
            sum(
                float(row.get("reserved_cost_usd") or 0.0)
                for row in rows
                if row.get("row_type") == "reservation"
                and row.get("reservation_id") not in settled
            ),
            6,
        )

    @staticmethod
    def _run_settlement_total(rows: list[dict], run_id: str) -> float:
        return round(
            sum(
                float(row.get("actual_cost_usd") or 0.0)
                for row in rows
                if row.get("row_type") == "settlement"
                and row.get("run_id") == run_id
            ),
            6,
        )

    @staticmethod
    def _reservation_bound(rows: list[dict], reservation_id: str) -> float:
        for row in rows:
            if (
                row.get("row_type") == "reservation"
                and row.get("reservation_id") == reservation_id
            ):
                return round(float(row.get("reserved_cost_usd") or 0.0), 6)
        raise ValueError(f"unknown reservation_id: {reservation_id}")

    @staticmethod
    def _has_run_settlements(rows: list[dict], run_id: str) -> bool:
        return any(
            row.get("row_type") == "settlement" and row.get("run_id") == run_id
            for row in rows
        )

    @staticmethod
    def _latest_attempt_state(rows: list[dict], reservation_id: str) -> dict:
        latest: dict | None = None
        for row in rows:
            if row.get("reservation_id") != reservation_id:
                continue
            if row.get("row_type") == "reservation":
                latest = row
            elif row.get("row_type") in {"attempt_state", "settlement"}:
                latest = row
        return latest or {}

    @staticmethod
    def _reservation_for(rows: list[dict], reservation_id: str) -> dict | None:
        return next(
            (
                row for row in rows
                if row.get("row_type") == "reservation"
                and row.get("reservation_id") == reservation_id
            ),
            None,
        )

    def total(self) -> float:
        return self._settled_total(self.entries())

    def reserved_total(self) -> float:
        rows = self.entries()
        return round(self._settled_total(rows) + self._active_reserved_total(rows), 6)

    def has_run_id(self, run_id: str) -> bool:
        return any(row.get("run_id") == run_id for row in self.entries())

    def has_record_summary(self, run_id: str) -> bool:
        return any(
            row.get("row_type") in {"record_summary", None}
            and row.get("run_id") == run_id
            for row in self.entries()
        )

    def run_settlement_total(self, run_id: str) -> float:
        return self._run_settlement_total(self.entries(), run_id)

    def settlements_for_run(self, run_id: str) -> list[dict]:
        return [
            dict(row)
            for row in self.entries()
            if row.get("row_type") == "settlement"
            and row.get("run_id") == run_id
        ]

    def settlement_attempts_for_run(self, run_id: str) -> list[dict]:
        attempts: list[dict] = []
        for row in self.settlements_for_run(run_id):
            reservation_id = str(row.get("reservation_id") or "")
            cost = round(float(row.get("actual_cost_usd") or 0.0), 6)
            attempts.append({
                "budget_reservation_id": reservation_id,
                "reservation_id": reservation_id,
                "role": str(row.get("role") or ""),
                "status": str(row.get("status") or ""),
                "cost_usd": cost,
                "debit_usd": cost,
                "cost_basis": str(row.get("cost_basis") or ""),
                "input_tokens": int(row.get("input_tokens") or 0),
                "output_tokens": int(row.get("output_tokens") or 0),
                "recovered": bool(row.get("recovery")),
                "model": row.get("model"),
            })
        return attempts

    def reservation_bound(self, reservation_id: str) -> float:
        return self._reservation_bound(self.entries(), reservation_id)

    def assert_can_schedule(self) -> None:
        rows = self.entries()
        committed = self._settled_total(rows)
        reserved = self._active_reserved_total(rows)
        if committed + reserved >= self.budget_usd:
            raise CampaignBudgetExceeded(
                "campaign budget exhausted: "
                f"settled ${committed:.6f} + active reservations ${reserved:.6f} "
                f">= cap ${self.budget_usd:.6f}"
            )

    def reserve_call(
        self,
        *,
        run_id: str,
        system_id: str,
        task_id: str,
        run_number: int,
        role: str,
        model: str,
        reserved_cost_usd: float,
        metadata: dict | None = None,
    ) -> str:
        if reserved_cost_usd < 0:
            raise ValueError("reserved_cost_usd must be >= 0")
        reservation_id = uuid.uuid4().hex
        with self._locked_file() as f:
            rows = self._parse_entries(f)
            committed = self._settled_total(rows)
            active = self._active_reserved_total(rows)
            requested = round(float(reserved_cost_usd), 6)
            if committed + active + requested > self.budget_usd:
                raise CampaignBudgetExceeded(
                    "campaign budget reservation refused: "
                    f"settled ${committed:.6f} + active ${active:.6f} + "
                    f"requested ${requested:.6f} > cap ${self.budget_usd:.6f}"
                )
            row = {
                "row_type": "reservation",
                "attempt_state": "reserved",
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "reservation_id": reservation_id,
                "run_id": run_id,
                "system_id": system_id,
                "task_id": task_id,
                "run_number": run_number,
                "role": role,
                "model": model,
                "reserved_cost_usd": requested,
                "settled_before_usd": committed,
                "active_reserved_before_usd": active,
                "budget_usd": round(self.budget_usd, 6),
                "metadata": dict(metadata or {}),
            }
            f.seek(0, os.SEEK_END)
            f.write(json.dumps(row, default=str, sort_keys=True) + "\n")
        return reservation_id

    def mark_dispatch_started(self, reservation_id: str) -> None:
        self._append_attempt_state(reservation_id, "dispatch_started")

    def mark_response_received(
        self,
        reservation_id: str,
        *,
        actual_cost_usd: float | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        metadata: dict | None = None,
    ) -> None:
        extra = {
            "input_tokens": int(input_tokens or 0),
            "output_tokens": int(output_tokens or 0),
            "metadata": dict(metadata or {}),
        }
        if actual_cost_usd is not None:
            extra["actual_cost_usd"] = round(float(actual_cost_usd), 6)
        self._append_attempt_state(reservation_id, "response_received", extra=extra)

    def _append_attempt_state(
        self,
        reservation_id: str,
        attempt_state: str,
        *,
        extra: dict | None = None,
    ) -> None:
        with self._locked_file() as f:
            rows = self._parse_entries(f)
            reservation = self._reservation_for(rows, reservation_id)
            if reservation is None:
                raise ValueError(f"unknown reservation_id: {reservation_id}")
            if any(
                row.get("row_type") == "settlement"
                and row.get("reservation_id") == reservation_id
                for row in rows
            ):
                raise ValueError(f"reservation already settled: {reservation_id}")
            row = {
                "row_type": "attempt_state",
                "attempt_state": attempt_state,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "reservation_id": reservation_id,
                "run_id": reservation.get("run_id"),
                "system_id": reservation.get("system_id"),
                "task_id": reservation.get("task_id"),
                "run_number": reservation.get("run_number"),
                "role": reservation.get("role"),
                "model": reservation.get("model"),
            }
            row.update(dict(extra or {}))
            f.seek(0, os.SEEK_END)
            f.write(json.dumps(row, default=str, sort_keys=True) + "\n")

    def settle_call(
        self,
        reservation_id: str,
        *,
        actual_cost_usd: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
        status: str = "success",
        error: str = "",
        cost_basis: str = "authoritative",
        recovery: bool = False,
    ) -> None:
        with self._locked_file() as f:
            rows = self._parse_entries(f)
            if any(
                row.get("row_type") == "settlement"
                and row.get("reservation_id") == reservation_id
                for row in rows
            ):
                raise ValueError(f"duplicate cost settlement refused: {reservation_id}")
            reservation = next(
                (
                    row for row in rows
                    if row.get("row_type") == "reservation"
                    and row.get("reservation_id") == reservation_id
                ),
                None,
            )
            if reservation is None:
                raise ValueError(f"unknown reservation_id: {reservation_id}")
            actual = round(float(actual_cost_usd or 0.0), 6)
            committed_before = self._settled_total(rows)
            row = {
                "row_type": "settlement",
                "attempt_state": "settled",
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "reservation_id": reservation_id,
                "run_id": reservation.get("run_id"),
                "system_id": reservation.get("system_id"),
                "task_id": reservation.get("task_id"),
                "run_number": reservation.get("run_number"),
                "role": reservation.get("role"),
                "model": reservation.get("model"),
                "status": status,
                "reserved_cost_usd": reservation.get("reserved_cost_usd", 0.0),
                "actual_cost_usd": actual,
                "cost_basis": cost_basis,
                "input_tokens": int(input_tokens or 0),
                "output_tokens": int(output_tokens or 0),
                "settled_before_usd": committed_before,
                "settled_after_usd": round(committed_before + actual, 6),
                "budget_usd": round(self.budget_usd, 6),
                "recovery": bool(recovery),
            }
            if error:
                row["error"] = str(error)[:500]
            if row["settled_after_usd"] > self.budget_usd:
                raise CampaignBudgetExceeded(
                    "campaign budget exceeded during settlement: "
                    f"${row['settled_after_usd']:.6f} > cap ${self.budget_usd:.6f}"
                )
            f.seek(0, os.SEEK_END)
            f.write(json.dumps(row, default=str, sort_keys=True) + "\n")

    def reconcile_stale_attempts(self) -> dict:
        """Settle active reservations after a crash using fail-closed rules.

        Reserved-but-undispatched attempts are reconciled to zero. Once dispatch
        started, missing response usage is cost-uncertain, so the conservative
        reservation bound is debited. A recorded response state with usage/cost
        is settled to that authoritative value.
        """
        reconciled: list[dict] = []
        with self._locked_file() as f:
            rows = self._parse_entries(f)
            settled = {
                row.get("reservation_id")
                for row in rows
                if row.get("row_type") == "settlement"
            }
            reservations = [
                row for row in rows
                if row.get("row_type") == "reservation"
                and row.get("reservation_id") not in settled
            ]
            for reservation in reservations:
                reservation_id = reservation.get("reservation_id")
                latest = self._latest_attempt_state(rows, reservation_id)
                state = latest.get("attempt_state") or "reserved"
                reserved = round(float(reservation.get("reserved_cost_usd") or 0.0), 6)
                input_tokens = int(latest.get("input_tokens") or 0)
                output_tokens = int(latest.get("output_tokens") or 0)
                if state == "reserved":
                    actual = 0.0
                    status = "reconciled_undispatched_zero"
                    cost_basis = "undispatched_zero"
                elif state == "dispatch_started":
                    actual = reserved
                    status = "reconciled_dispatch_uncertain_reserved_bound"
                    cost_basis = "reserved_bound_conservative"
                elif state == "response_received":
                    if latest.get("actual_cost_usd") is not None:
                        actual = round(float(latest.get("actual_cost_usd") or 0.0), 6)
                        status = "reconciled_response_received"
                        cost_basis = "authoritative_response"
                    else:
                        actual = reserved
                        status = "reconciled_response_uncertain_reserved_bound"
                        cost_basis = "reserved_bound_conservative"
                else:
                    raise ValueError(
                        f"cannot safely reconcile reservation {reservation_id}: "
                        f"unknown state {state!r}"
                    )
                committed_before = self._settled_total(rows)
                settlement = {
                    "row_type": "settlement",
                    "attempt_state": "settled",
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "reservation_id": reservation_id,
                    "run_id": reservation.get("run_id"),
                    "system_id": reservation.get("system_id"),
                    "task_id": reservation.get("task_id"),
                    "run_number": reservation.get("run_number"),
                    "role": reservation.get("role"),
                    "model": reservation.get("model"),
                    "status": status,
                    "reserved_cost_usd": reserved,
                    "actual_cost_usd": actual,
                    "cost_basis": cost_basis,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "settled_before_usd": committed_before,
                    "settled_after_usd": round(committed_before + actual, 6),
                    "budget_usd": round(self.budget_usd, 6),
                    "recovery": True,
                }
                if settlement["settled_after_usd"] > self.budget_usd:
                    raise CampaignBudgetExceeded(
                        "campaign budget exceeded during stale-attempt recovery: "
                        f"${settlement['settled_after_usd']:.6f} > cap ${self.budget_usd:.6f}"
                    )
                f.seek(0, os.SEEK_END)
                f.write(json.dumps(settlement, default=str, sort_keys=True) + "\n")
                rows.append(settlement)
                reconciled.append({
                    "reservation_id": reservation_id,
                    "run_id": reservation.get("run_id"),
                    "state": state,
                    "status": status,
                    "actual_cost_usd": actual,
                    "cost_basis": cost_basis,
                })
        return {"reconciled": reconciled, "count": len(reconciled)}

    def append_record_summary(
        self,
        record: RunRecord,
        *,
        require_settlement: bool = False,
    ) -> None:
        cost = float(record.api_cost_usd or 0.0)
        with self._locked_file() as f:
            rows = self._parse_entries(f)
            if any(
                row.get("row_type") in {"record_summary", None}
                and row.get("run_id") == record.run_id
                for row in rows
            ):
                raise ValueError(f"duplicate cost record refused: {record.run_id}")
            has_settlements = self._has_run_settlements(rows, record.run_id)
            if require_settlement and not has_settlements:
                raise ValueError(
                    f"{record.run_id}: existing checkpoint absent from cost ledger"
                )
            settled_for_run = self._run_settlement_total(rows, record.run_id)
            if has_settlements and abs(settled_for_run - round(cost, 6)) > 0.000001:
                raise ValueError(
                    f"RunRecord cost mismatch for {record.run_id}: "
                    f"record ${cost:.6f} != settlements ${settled_for_run:.6f}"
                )
            total_before = self._settled_total(rows)
            total_after = total_before if has_settlements else round(total_before + cost, 6)
            if total_after > self.budget_usd:
                raise CampaignBudgetExceeded(
                    f"campaign budget exceeded: ${total_after:.6f} > cap ${self.budget_usd:.6f}"
                )
            row = {
                "row_type": "record_summary",
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "run_id": record.run_id,
                "system_id": record.system_id,
                "task_id": record.task_id,
                "run_number": record.run_number,
                "api_cost_usd": round(cost, 6),
                "settlement_cost_usd": settled_for_run if has_settlements else None,
                "total_before_usd": round(total_before, 6),
                "total_after_usd": round(total_after, 6),
                "budget_usd": round(self.budget_usd, 6),
            }
            f.seek(0, os.SEEK_END)
            f.write(json.dumps(row, default=str, sort_keys=True) + "\n")

    def ensure_record_summary(self, record: RunRecord) -> None:
        if self.has_record_summary(record.run_id):
            return
        self.append_record_summary(record, require_settlement=True)

    def append(self, record: RunRecord) -> None:
        self.append_record_summary(record)
