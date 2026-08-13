#!/usr/bin/env python3
"""Run HANDOFF_22 local Cond-B cross-vendor jobs sequentially."""
from __future__ import annotations

import json
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VENDORS = [
    ("qwen", "qwen2.5:32b"),
    ("llama", "llama3.2:3b"),
    ("mistral", "mistral:7b"),
    ("phi", "phi3:14b"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    with path.open() as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)


def record_files(out_dir: Path) -> list[Path]:
    return sorted(out_dir.glob("cond_b__*.json"))


def _coa_count(record: dict[str, Any]) -> int:
    artifact = ((record.get("output") or {}).get("artifact") or {})
    for key in ("candidate_coas", "candidate_courses_of_action", "coas"):
        value = artifact.get(key)
        if isinstance(value, list):
            return len(value)
    return 0


def _gap_count(record: dict[str, Any]) -> int:
    return len(((record.get("output") or {}).get("gap_reports") or []))


def _fallback_used(record: dict[str, Any]) -> bool:
    return any(bool(row.get("llm_fallback")) for row in record.get("role_timings") or [])


def _trace_complete(record: dict[str, Any]) -> bool:
    output = record.get("output") or {}
    artifact = output.get("artifact")
    gap_reports = output.get("gap_reports") or []
    return bool(record.get("role_timings")) and bool(artifact or gap_reports)


def vendor_metrics(out_dir: Path) -> dict[str, Any]:
    files = record_files(out_dir)
    records = []
    for path in files:
        try:
            records.append(load_json(path))
        except Exception as exc:  # noqa: BLE001
            records.append({"ok": False, "errors": [f"unreadable {path.name}: {exc!r}"]})

    total = len(records)
    ok = sum(1 for rec in records if rec.get("ok") is True)
    wall = [float(rec.get("wall_clock_ms") or 0.0) for rec in records]
    trace_complete = sum(1 for rec in records if _trace_complete(rec))
    metrics = {
        "total_records": total,
        "ok_records": ok,
        "ok_rate": (ok / total) if total else 0.0,
        "mean_wall_clock_ms": statistics.fmean(wall) if wall else 0.0,
        "fallback_rate": (
            sum(1 for rec in records if _fallback_used(rec)) / total
            if total else 0.0
        ),
        "mean_coa_count": (
            statistics.fmean(_coa_count(rec) for rec in records)
            if records else 0.0
        ),
        "mean_gap_report_count": (
            statistics.fmean(_gap_count(rec) for rec in records)
            if records else 0.0
        ),
        "trace_completeness_rate": (trace_complete / total) if total else 0.0,
    }
    return metrics


def write_report(report_path: Path, status: dict[str, Any]) -> None:
    lines = [
        "# HANDOFF_22 cross-vendor Cond-B status",
        "",
        f"Updated: {status['updated_at']}",
        "",
        "Selection:",
        (
            f"- {status['selection']['n_task_ids_total']} task IDs x "
            f"{status['selection']['runs_per_task']} runs = "
            f"{status['selection']['n_records_total']} records"
        ),
        f"- Rule: {status['selection']['selection_rule']}",
        "",
        "| Vendor | Model | State | Records | OK-rate | Mean ms | Fallback | Trace completeness | Mean COAs | Mean gaps |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for vendor, model in VENDORS:
        row = status["vendors"].get(vendor, {})
        metrics = row.get("metrics") or {}
        total = metrics.get("total_records", 0)
        ok = metrics.get("ok_records", 0)
        lines.append(
            "| {vendor} | `{model}` | {state} | {ok}/{total} | {ok_rate:.1%} | "
            "{mean_ms:.1f} | {fallback:.1%} | {trace:.1%} | {coas:.2f} | {gaps:.2f} |".format(
                vendor=vendor,
                model=model,
                state=row.get("state", "pending"),
                ok=ok,
                total=total,
                ok_rate=float(metrics.get("ok_rate", 0.0)),
                mean_ms=float(metrics.get("mean_wall_clock_ms", 0.0)),
                fallback=float(metrics.get("fallback_rate", 0.0)),
                trace=float(metrics.get("trace_completeness_rate", 0.0)),
                coas=float(metrics.get("mean_coa_count", 0.0)),
                gaps=float(metrics.get("mean_gap_report_count", 0.0)),
            )
        )
    lines.extend(["", f"Verdict: {status.get('verdict', 'RUNNING')}", ""])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines))


def update_status(
    *,
    status_path: Path,
    report_path: Path,
    status: dict[str, Any],
) -> None:
    status["updated_at"] = utc_now()
    gate_passing = []
    failed = []
    for vendor, _model in VENDORS:
        row = status["vendors"].get(vendor, {})
        metrics = row.get("metrics") or {}
        if row.get("state") == "completed":
            if metrics.get("ok_rate", 0.0) >= 0.80:
                gate_passing.append(metrics)
            else:
                failed.append(vendor)
    if all(status["vendors"].get(v, {}).get("state") == "completed" for v, _ in VENDORS):
        if any(m.get("trace_completeness_rate", 0.0) < 0.95 for m in gate_passing):
            status["verdict"] = "HALT-FAIL"
        elif failed:
            status["verdict"] = "HALT-WITH-PARTIAL"
        elif all(m.get("trace_completeness_rate", 0.0) >= 0.99 for m in gate_passing):
            status["verdict"] = "PROCEED"
        else:
            status["verdict"] = "HALT-WITH-PARTIAL"
    else:
        status["verdict"] = "RUNNING"
    write_json(status_path, status)
    write_report(report_path, status)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    selection_path = root / "07_system_outputs/cond_b/_handoff_22_task_selection.json"
    status_path = root / "handoffs/HANDOFF_22_xvendor_status.json"
    report_path = root / "handoffs/HANDOFF_22_xvendor_report.md"
    selection = load_json(selection_path)
    task_ids = list(selection["task_ids"])
    runs_per_task = int(selection.get("runs_per_task", 1))
    expected_records = len(task_ids) * runs_per_task

    status = {
        "started_at": utc_now(),
        "updated_at": utc_now(),
        "selection": selection,
        "expected_records_per_vendor": expected_records,
        "vendors": {},
        "verdict": "RUNNING",
    }
    if status_path.exists():
        previous = load_json(status_path)
        status["started_at"] = previous.get("started_at", status["started_at"])
        status["vendors"] = previous.get("vendors", {})

    update_status(status_path=status_path, report_path=report_path, status=status)

    for vendor, model in VENDORS:
        out_dir = root / "07_system_outputs/cond_b_xvendor" / vendor
        out_dir.mkdir(parents=True, exist_ok=True)
        log_path = root / "logs" / f"HANDOFF_22_{vendor}.stderr"
        existing = len(record_files(out_dir))
        row = status["vendors"].setdefault(vendor, {
            "model": model,
            "output_dir": str(out_dir.relative_to(root)),
            "log_path": str(log_path.relative_to(root)),
            "state": "pending",
        })
        if existing >= expected_records and row.get("state") == "completed":
            row["metrics"] = vendor_metrics(out_dir)
            update_status(status_path=status_path, report_path=report_path, status=status)
            continue

        row.update({
            "model": model,
            "state": "running",
            "started_at": utc_now(),
            "output_dir": str(out_dir.relative_to(root)),
            "log_path": str(log_path.relative_to(root)),
        })
        update_status(status_path=status_path, report_path=report_path, status=status)

        cmd = [
            sys.executable, "-m", "apparatus.run", "run-cond-b",
            *task_ids,
            "--out", str(out_dir.relative_to(root)),
            "--llm-backend", "ollama",
            "--llm-model", model,
            "--runs-per-task", str(runs_per_task),
            "--domain-profile-mode", "auto",
            "--max-workers", "1",
            "--skip-existing",
        ]
        with log_path.open("a", buffering=1) as log:
            log.write(f"\n=== {utc_now()} starting {vendor} ({model}) ===\n")
            log.write(" ".join(cmd) + "\n")
            proc = subprocess.Popen(
                cmd,
                cwd=str(root),
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            ret = proc.wait()
            log.write(f"=== {utc_now()} finished {vendor} ret={ret} ===\n")

        row["finished_at"] = utc_now()
        row["returncode"] = ret
        row["metrics"] = vendor_metrics(out_dir)
        row["state"] = "completed" if ret == 0 else "failed"
        if row["metrics"]["ok_rate"] < 0.50:
            row["state"] = "halted"
        update_status(status_path=status_path, report_path=report_path, status=status)
        time.sleep(2)

    update_status(status_path=status_path, report_path=report_path, status=status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
