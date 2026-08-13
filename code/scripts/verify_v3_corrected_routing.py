#!/usr/bin/env python3
"""Read-only Tier-1 verification of the V3 corrected-routing deposit."""

from __future__ import annotations

import gzip
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


EXPECTED = {
    "archive_sha256": "9193189e58b99e8e7655448fbebfc3da5021bca69dc4d43330f051a8040ba0ef",
    "cond_a_gzip_sha256": "05ba1e25a4d67fd2dbfba23a6081797a5e13dd614bdf641ad1a152dbb9daebb0",
    "cond_b_gzip_sha256": "059b22351e24c2c3cb18fdf0ffe43fdbdbc15f9a6ecfe1ecd6c40b89146e3bcd",
    "ledger_gzip_sha256": "a5654fda3eb76b250dcfd9ecabf42e09a705cb56bbb86c7c89b752d35ea1f467",
    "main_corpus_sha256": "a6fb48501ebd58088452a0e68a329f0bf7b1df6b623e9abb940f7a8094b65dbb",
    "holdout_corpus_sha256": "d92b7e3b68f15e3abfe54a2cff7c81a1b7f0959b03a7a7597c8e52501504f9ae",
    "cond_a_main_v1_sha256": "28627274c0001f8dd9cd84ea62b8bc67c28a09171afbfa9f8c64cb8329d8eca2",
    "cond_a_holdout_v1_sha256": "0ff5b5b6b048af91c15ab496f1d01647de0fcdeaacf9726c9f0620aedf86198f",
    "cond_b_main_v1_sha256": "7dcca59490fa4de24e4e0138d16398fc9b5c795b7f0aa6822efa668ba5f13c72",
    "cond_b_holdout_v1_sha256": "bd81ac0bfe78dc3db2e9d4d95da5881ab739f3bfa321a17f232309b805285b26",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def enum_value(value: Any) -> str:
    return str(value or "").upper()


def is_blocking(gap: dict[str, Any]) -> bool:
    if enum_value(gap.get("severity")) == "BLOCKING" or gap.get("blocking") is True:
        return True
    readiness_score = gap.get("readiness_score")
    if isinstance(readiness_score, dict) and readiness_score.get("blocking") is True:
        return True
    readiness = gap.get("readiness_assessment")
    if isinstance(readiness, dict):
        if int(readiness.get("blocking_gap_count") or 0) > 0:
            return True
        if enum_value(readiness.get("recommendation")) == "INSUFFICIENT_FOR_AUTOMATION":
            return True
    return enum_value(gap.get("execution_state")) in {
        "NON_EXECUTABLE_GAPS",
        "INSUFFICIENT_FOR_AUTOMATION",
    }


def check(condition: bool, message: str, issues: list[str]) -> None:
    if not condition:
        issues.append(message)


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    v1 = repo / "replication_package" / "v1_main"
    v3 = repo / "replication_package" / "v3_corrected_routing"
    issues: list[str] = []

    hash_targets = {
        v3 / "outputs/cond_a_rerun.jsonl.gz": EXPECTED["cond_a_gzip_sha256"],
        v3 / "outputs/cond_b_rerun.jsonl.gz": EXPECTED["cond_b_gzip_sha256"],
        v3 / "outputs/api_cost_ledger.jsonl.gz": EXPECTED["ledger_gzip_sha256"],
        v1 / "corpus/main_tasks.jsonl": EXPECTED["main_corpus_sha256"],
        v1 / "corpus/holdout_tasks.jsonl": EXPECTED["holdout_corpus_sha256"],
        v1 / "system_outputs/cond_a_main.jsonl": EXPECTED["cond_a_main_v1_sha256"],
        v1 / "system_outputs/cond_a_holdout.jsonl": EXPECTED["cond_a_holdout_v1_sha256"],
        v1 / "system_outputs/cond_b_main.jsonl": EXPECTED["cond_b_main_v1_sha256"],
        v1 / "system_outputs/cond_b_holdout.jsonl": EXPECTED["cond_b_holdout_v1_sha256"],
    }
    for path, expected in hash_targets.items():
        check(path.is_file(), f"missing file: {path.relative_to(repo)}", issues)
        if path.is_file():
            check(sha256_file(path) == expected, f"hash mismatch: {path.relative_to(repo)}", issues)

    records: dict[str, list[dict[str, Any]]] = {}
    identities: dict[str, set[tuple[str, int, int]]] = {}
    states = Counter()
    fallback = Counter()
    blocking = 0
    executable_with_blocking = 0
    trace_entries = 0
    response_objects = 0
    evidence_attempts = 0
    record_cost_total = 0.0

    for condition in ("cond_a", "cond_b"):
        path = v3 / "outputs" / f"{condition}_rerun.jsonl.gz"
        rows = list(load_jsonl(path)) if path.is_file() else []
        records[condition] = rows
        identities[condition] = set()
        check(len(rows) == 1500, f"{condition}: expected 1500 records, got {len(rows)}", issues)
        per_task_runs: dict[str, set[int]] = defaultdict(set)
        for record in rows:
            task_id = str(record.get("task_id"))
            run_number = int(record.get("run_number") or 0)
            seed = int(record.get("seed") or 0)
            identities[condition].add((task_id, run_number, seed))
            per_task_runs[task_id].add(run_number)
            check(seed == 20260623 + run_number, f"{record.get('run_id')}: seed mismatch", issues)
            check(record.get("system_id") == condition, f"{record.get('run_id')}: system mismatch", issues)
            output = record.get("output") if isinstance(record.get("output"), dict) else {}
            envelope = output.get("result_envelope") if isinstance(output.get("result_envelope"), dict) else {}
            gaps = [gap for gap in output.get("gap_reports", []) if isinstance(gap, dict)]
            record_blocks = any(is_blocking(gap) for gap in gaps)
            state = str(record.get("execution_state") or "")
            states[state] += 1
            if record_blocks:
                blocking += 1
                if state == "EXECUTABLE":
                    executable_with_blocking += 1
                check(state == "NON_EXECUTABLE_GAPS", f"{record.get('run_id')}: blocking route", issues)
            check(envelope.get("has_blocking_or_insufficient_signal") is record_blocks,
                  f"{record.get('run_id')}: envelope blocker mismatch", issues)
            check(bool(record.get("ok")) == (state == "EXECUTABLE"),
                  f"{record.get('run_id')}: ok/state mismatch", issues)
            if record.get("any_llm_fallback"):
                fallback[condition] += 1
                check(state == "NON_EXECUTABLE_GAPS", f"{record.get('run_id')}: fallback route", issues)
            artifact = output.get("artifact") if isinstance(output.get("artifact"), dict) else {}
            trace = artifact.get("trace") if isinstance(artifact.get("trace"), dict) else {}
            trace_entries += len(trace.get("entries") or [])
            record_cost_total += float(record.get("api_cost_usd") or 0.0)
            if condition == "cond_a":
                raw = ((output.get("mission_input_metadata") or {}).get("raw_provider_response") or {})
                evidence_attempts += len(raw.get("budget_attempts") or [])
                response_objects += 1
            else:
                responses = output.get("provider_responses") or []
                response_objects += len(responses)
                for response in responses:
                    raw = response.get("raw_response") if isinstance(response, dict) else {}
                    evidence_attempts += len((raw or {}).get("budget_attempts") or [])
        for task_id, run_numbers in per_task_runs.items():
            check(run_numbers == set(range(1, 11)), f"{condition}/{task_id}: run matrix", issues)
        check(len(per_task_runs) == 150, f"{condition}: expected 150 tasks", issues)

    check(identities.get("cond_a") == identities.get("cond_b"), "Cond-A/Cond-B identity mismatch", issues)
    check(blocking == 2999, f"expected blocking N=2999, got {blocking}", issues)
    check(executable_with_blocking == 0, "executable-with-blocking is nonzero", issues)
    check(states == {"NON_EXECUTABLE_GAPS": 2999, "EXECUTABLE": 1}, f"state counts: {states}", issues)
    check(fallback == {"cond_b": 157}, f"fallback counts: {fallback}", issues)
    check(trace_entries == 18000, f"trace entry count: {trace_entries}", issues)
    check(response_objects == 10503, f"response object count: {response_objects}", issues)
    check(evidence_attempts == 10513, f"attempt-evidence count: {evidence_attempts}", issues)
    check(round(record_cost_total, 6) == 191.388447,
          f"record cost total: {round(record_cost_total, 6)}", issues)

    v1_identities: dict[str, set[tuple[str, int, int]]] = defaultdict(set)
    v1_blocking = Counter()
    v1_ok = Counter()
    for condition in ("cond_a", "cond_b"):
        for split in ("main", "holdout"):
            path = v1 / "system_outputs" / f"{condition}_{split}.jsonl"
            for record in load_jsonl(path) if path.is_file() else []:
                identity = (str(record.get("task_id")), int(record.get("run_number") or 0), int(record.get("seed") or 0))
                v1_identities[condition].add(identity)
                v1_ok[condition] += int(record.get("ok") is True)
                gaps = (record.get("output") or {}).get("gap_reports") or []
                v1_blocking[condition] += int(any(is_blocking(gap) for gap in gaps if isinstance(gap, dict)))
        check(v1_identities[condition] == identities.get(condition), f"{condition}: V1/V3 identity mismatch", issues)
    check(v1_ok == {"cond_a": 1500, "cond_b": 1500}, f"V1 ok counts: {v1_ok}", issues)
    check(v1_blocking == {"cond_a": 1500, "cond_b": 1500}, f"V1 blocker counts: {v1_blocking}", issues)

    ledger_path = v3 / "outputs/api_cost_ledger.jsonl.gz"
    row_types = Counter()
    attempt_states = Counter()
    settlement_total = 0.0
    conservative = 0
    if ledger_path.is_file():
        for row in load_jsonl(ledger_path):
            row_type = str(row.get("row_type"))
            row_types[row_type] += 1
            if row_type == "attempt_state":
                attempt_states[str(row.get("attempt_state"))] += 1
            elif row_type == "settlement":
                settlement_total += float(row.get("actual_cost_usd") or 0.0)
                conservative += int("conservative" in str(row.get("cost_basis") or ""))
    check(row_types == {"attempt_state": 21023, "reservation": 10513,
                        "settlement": 10513, "record_summary": 3000},
          f"ledger row counts: {row_types}", issues)
    check(attempt_states == {"dispatch_started": 10513, "response_received": 10510},
          f"attempt states: {attempt_states}", issues)
    check(round(settlement_total, 6) == 191.388447,
          f"settlement total: {round(settlement_total, 6)}", issues)
    check(conservative == 3, f"conservative settlements: {conservative}", issues)

    archive_parts = sorted((v3 / "archive").glob("*.zip.part-*"))
    archive_digest = hashlib.sha256()
    for part in archive_parts:
        with part.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                archive_digest.update(chunk)
    check(len(archive_parts) == 3, f"archive part count: {len(archive_parts)}", issues)
    check(archive_digest.hexdigest() == EXPECTED["archive_sha256"], "reconstructed archive hash mismatch", issues)

    report = {
        "ok": not issues,
        "issues": issues,
        "records": sum(len(rows) for rows in records.values()),
        "primary_denominator_N": blocking,
        "executable_with_blocking": executable_with_blocking,
        "states": dict(states),
        "fallbacks": dict(fallback),
        "trace_entries": trace_entries,
        "provider_response_objects": response_objects,
        "attempt_evidence": evidence_attempts,
        "ledger_row_types": dict(row_types),
        "settled_cost_usd": round(settlement_total, 6),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())

