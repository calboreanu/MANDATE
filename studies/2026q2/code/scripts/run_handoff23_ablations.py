#!/usr/bin/env python3
"""Wait for HANDOFF_22, then run HANDOFF_23 A3/A5 ablations."""
from __future__ import annotations

import glob
import json
import os
import statistics
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


POLL_SECONDS = 300
TERMINAL_H22_VERDICTS = {"PROCEED", "HALT-WITH-PARTIAL", "HALT-FAIL"}
H22_VENDOR_DIRS = ("qwen", "llama", "mistral", "phi")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
STATUS_PATH = ROOT / "handoffs/HANDOFF_23_ablation_status.json"
REPORT_PATH = ROOT / "handoffs/HANDOFF_23_ablation_report.md"

RUNS = [
    {
        "key": "a3_main",
        "system": "ablation_a3",
        "label": "A3 main",
        "tasks": "04_ground_truth/main_tasks.jsonl",
        "output": "07_system_outputs/ablations/a3_no_gap_analysis",
        "log": "logs/HANDOFF_23_a3_main.stderr",
    },
    {
        "key": "a3_holdout",
        "system": "ablation_a3",
        "label": "A3 holdout",
        "tasks": "04_ground_truth/holdout_tasks.jsonl",
        "output": "07_system_outputs/ablations/a3_no_gap_analysis/holdout",
        "log": "logs/HANDOFF_23_a3_holdout.stderr",
    },
    {
        "key": "a5_main",
        "system": "ablation_a5",
        "label": "A5 main",
        "tasks": "04_ground_truth/main_tasks.jsonl",
        "output": "07_system_outputs/ablations/a5_no_registry",
        "log": "logs/HANDOFF_23_a5_main.stderr",
    },
    {
        "key": "a5_holdout",
        "system": "ablation_a5",
        "label": "A5 holdout",
        "tasks": "04_ground_truth/holdout_tasks.jsonl",
        "output": "07_system_outputs/ablations/a5_no_registry/holdout",
        "log": "logs/HANDOFF_23_a5_holdout.stderr",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(msg: str) -> None:
    print(f"[{utc_now()}] {msg}", flush=True)


def load_json(path: Path) -> Any:
    with path.open() as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)


def run_cmd(cmd: list[str], *, log_path: Path | None = None) -> int:
    log("$ " + " ".join(cmd))
    if log_path is None:
        return subprocess.run(cmd, cwd=ROOT).returncode
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", buffering=1) as fh:
        fh.write(f"\n=== {utc_now()} start ===\n")
        fh.write(" ".join(cmd) + "\n")
        proc = subprocess.Popen(
            cmd,
            cwd=ROOT,
            stdout=fh,
            stderr=subprocess.STDOUT,
        )
        ret = proc.wait()
        fh.write(f"=== {utc_now()} end ret={ret} ===\n")
    return ret


def record_count(path: Path) -> int:
    return len(list(path.glob("*.json")))


def recursive_records(path: Path) -> list[Path]:
    return sorted(p for p in path.rglob("*.json") if p.name != "ledger.json")


def h22_counts() -> dict[str, int]:
    base = ROOT / "07_system_outputs/cond_b_xvendor"
    return {
        name: record_count(base / name)
        for name in H22_VENDOR_DIRS
    }


def h22_ready() -> tuple[bool, str]:
    status_path = ROOT / "handoffs/HANDOFF_22_xvendor_status.json"
    verdict = ""
    if status_path.exists():
        try:
            verdict = str(load_json(status_path).get("verdict", ""))
        except Exception as exc:  # noqa: BLE001
            log(f"HANDOFF_22 status unreadable: {exc!r}")
    counts = h22_counts()
    if verdict in TERMINAL_H22_VERDICTS:
        return True, f"verdict={verdict}"
    if counts and all(counts.get(name, 0) >= 300 for name in H22_VENDOR_DIRS):
        return True, f"all vendor dirs >=300 records: {counts}"
    return False, f"verdict={verdict or 'missing'} counts={counts}"


def wait_for_h22() -> None:
    while True:
        ready, reason = h22_ready()
        if ready:
            log(f"HANDOFF_22 ready; continuing ({reason})")
            return
        log(f"HANDOFF_22 still active; sleeping {POLL_SECONDS}s ({reason})")
        time.sleep(POLL_SECONDS)


def line_count(path: Path) -> int:
    with path.open() as f:
        return sum(1 for _ in f)


def assert_preconditions() -> None:
    log("running HANDOFF_23 preconditions")
    from apparatus.ablations.manifest import ABLATIONS, AblationKind

    a3 = ABLATIONS["A3"]
    a5 = ABLATIONS["A5"]
    assert a3.kind == AblationKind.CONFIG_SWITCH
    assert a5.kind == AblationKind.CONFIG_SWITCH
    log("A3 and A5 confirmed CONFIG_SWITCH ablations")

    for rel in (
        "07_system_outputs/ablations/a3_no_gap_analysis",
        "07_system_outputs/ablations/a5_no_registry",
    ):
        path = ROOT / rel
        path.mkdir(parents=True, exist_ok=True)
        count = len(recursive_records(path))
        if count != 0:
            raise RuntimeError(f"{rel} has {count} stale JSON records")
    log("ablation output trees ready and empty")

    assert line_count(ROOT / "04_ground_truth/main_tasks.jsonl") == 120
    assert line_count(ROOT / "04_ground_truth/holdout_tasks.jsonl") == 30
    log("task files confirmed: 120 main, 30 holdout")

    import urllib.request
    with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3) as resp:
        tags = {m["name"] for m in json.loads(resp.read()).get("models", [])}
    cfg = load_json(ROOT / "AEGIS-eval/configs/llm_defaults.json")
    required = set((cfg.get("llm_role_models") or {}).values())
    missing = sorted(
        model for model in required
        if model not in tags and f"{model}:latest" not in tags
    )
    if missing:
        raise RuntimeError(f"missing MANDATE fine-tunes in Ollama: {missing}")
    log("all MANDATE fine-tunes present in Ollama")

    ret = run_cmd([sys.executable, "-m", "pytest", "-q", "apparatus"])
    if ret != 0:
        raise RuntimeError(f"pytest apparatus failed with code {ret}")
    log("pytest apparatus baseline green")


def run_ablation(run: dict[str, str]) -> None:
    cmd = [
        sys.executable, "-m", "apparatus.run", "run-system",
        "--system", run["system"],
        "--tasks", run["tasks"],
        "--output", run["output"],
        "--runs", "10",
        "--seed-base", "20260624",
        "--aegis", "AEGIS-eval",
        "--ollama-mode",
        "--code-ref", "mlt-stack-1.0.0rc1",
        "--skip-existing",
    ]
    log(f"starting {run['label']}")
    ret = run_cmd(cmd, log_path=ROOT / run["log"])
    if ret != 0:
        raise RuntimeError(f"{run['label']} failed with code {ret}")
    log(f"finished {run['label']}")


def _load_records(root: Path) -> list[dict[str, Any]]:
    records = []
    for path in recursive_records(root):
        try:
            records.append(load_json(path))
        except Exception as exc:  # noqa: BLE001
            records.append({
                "ok": False,
                "output": {},
                "errors": [f"unreadable {path}: {exc!r}"],
            })
    return records


def _artifact(record: dict[str, Any]) -> dict[str, Any]:
    artifact = (record.get("output") or {}).get("artifact") or {}
    return artifact if isinstance(artifact, dict) else {}


def _gap_reports(record: dict[str, Any]) -> list[Any]:
    out = record.get("output") or {}
    gaps = list(out.get("gap_reports") or [])
    artifact_gaps = _artifact(record).get("gap_reports") or []
    if isinstance(artifact_gaps, list):
        gaps.extend(artifact_gaps)
    return gaps


def _coa_count(record: dict[str, Any]) -> int:
    artifact = _artifact(record)
    for key in ("candidate_coas", "candidate_courses_of_action", "coas"):
        val = artifact.get(key)
        if isinstance(val, list):
            return len(val)
    return 0


def _trace_len(record: dict[str, Any]) -> int:
    artifact = _artifact(record)
    for key in ("trace_chain", "trace", "audit_trace", "role_trace"):
        val = artifact.get(key)
        if isinstance(val, list):
            return len(val)
    timings = record.get("role_timings") or []
    return len(timings) if isinstance(timings, list) else 0


def summarize_records(root: Path) -> dict[str, Any]:
    records = _load_records(root)
    total = len(records)
    output_types = Counter(str(r.get("output_type", "")) for r in records)
    artifact_fields = Counter()
    registry_nonempty = 0
    gap_nonempty = 0
    for rec in records:
        artifact = _artifact(rec)
        artifact_fields.update(artifact.keys())
        ref = artifact.get("registry_reference")
        if ref is not None and ref != {}:
            registry_nonempty += 1
        if _gap_reports(rec):
            gap_nonempty += 1
    return {
        "total_records": total,
        "ok_records": sum(1 for r in records if r.get("ok") is True),
        "ok_rate": (
            sum(1 for r in records if r.get("ok") is True) / total
            if total else 0.0
        ),
        "mean_wall_clock_ms": (
            statistics.fmean(float(r.get("wall_clock_ms") or 0.0) for r in records)
            if records else 0.0
        ),
        "mandate_as_code_records": sum(
            1 for r in records
            if "mandate" in str(r.get("output_type", "")).lower()
        ),
        "gap_report_status_records": sum(
            1 for r in records
            if "gap" in str(r.get("output_type", "")).lower()
        ),
        "mean_coa_count": (
            statistics.fmean(_coa_count(r) for r in records)
            if records else 0.0
        ),
        "mean_trace_chain_length": (
            statistics.fmean(_trace_len(r) for r in records)
            if records else 0.0
        ),
        "output_type_counts": dict(output_types),
        "artifact_field_presence": dict(artifact_fields),
        "nonempty_gap_report_records": gap_nonempty,
        "nonempty_registry_reference_records": registry_nonempty,
    }


def gate_a3() -> dict[str, Any]:
    root = ROOT / "07_system_outputs/ablations/a3_no_gap_analysis"
    summary = summarize_records(root)
    violations = [
        str(path.relative_to(ROOT))
        for path in recursive_records(root)
        if _gap_reports(load_json(path))
    ]
    summary["gap_report_violations"] = violations[:20]
    summary["gap_report_violation_count"] = len(violations)
    log(
        "A3 gate: {ok}/{total} ok, {violations} gap-report violations".format(
            ok=summary["ok_records"],
            total=summary["total_records"],
            violations=len(violations),
        )
    )
    return summary


def gate_a5() -> dict[str, Any]:
    root = ROOT / "07_system_outputs/ablations/a5_no_registry"
    summary = summarize_records(root)
    violations = []
    for path in recursive_records(root):
        ref = _artifact(load_json(path)).get("registry_reference")
        if ref is not None and ref != {}:
            violations.append(str(path.relative_to(ROOT)))
    summary["registry_reference_violations"] = violations[:20]
    summary["registry_reference_violation_count"] = len(violations)
    log(
        "A5 gate: {ok}/{total} ok, {violations} registry violations".format(
            ok=summary["ok_records"],
            total=summary["total_records"],
            violations=len(violations),
        )
    )
    return summary


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def table_row(name: str, summary: dict[str, Any]) -> str:
    return (
        f"| {name} | {summary['ok_records']}/{summary['total_records']} | "
        f"{pct(summary['ok_rate'])} | {summary['mean_wall_clock_ms']:.1f} | "
        f"{summary['mandate_as_code_records']} | "
        f"{summary['gap_report_status_records']} | "
        f"{summary['mean_coa_count']:.2f} | "
        f"{summary['mean_trace_chain_length']:.2f} |"
    )


def write_report(a3: dict[str, Any], a5: dict[str, Any]) -> str:
    primary = summarize_records(ROOT / "07_system_outputs/mandate_primary")
    verdict = "PROCEED"
    reasons = []
    for name, summary in (("A3", a3), ("A5", a5)):
        if summary["ok_rate"] < 0.80:
            verdict = "HALT-WITH-PARTIAL"
            reasons.append(f"{name} ok-rate below 80%")
    if a3["gap_report_violation_count"]:
        verdict = "HALT-FAIL"
        reasons.append("A3 emitted gap reports")
    if a5["registry_reference_violation_count"]:
        verdict = "HALT-FAIL"
        reasons.append("A5 emitted registry_reference")

    lines = [
        "# HANDOFF_23 A3/A5 Ablation Report",
        "",
        f"Generated: {utc_now()}",
        "",
        "## Per-Ablation Summary",
        "",
        "| Ablation | OK records | OK-rate | Mean wall ms | Nonempty gap reports | Nonempty registry refs |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        (
            f"| A3 no_gap_analysis | {a3['ok_records']}/{a3['total_records']} | "
            f"{pct(a3['ok_rate'])} | {a3['mean_wall_clock_ms']:.1f} | "
            f"{a3['nonempty_gap_report_records']} | "
            f"{a3['nonempty_registry_reference_records']} |"
        ),
        (
            f"| A5 no_registry | {a5['ok_records']}/{a5['total_records']} | "
            f"{pct(a5['ok_rate'])} | {a5['mean_wall_clock_ms']:.1f} | "
            f"{a5['nonempty_gap_report_records']} | "
            f"{a5['nonempty_registry_reference_records']} |"
        ),
        "",
        "## Comparative Table",
        "",
        "| System | OK records | OK-rate | Mean wall ms | Mandate-as-code records | Gap-report status records | Mean COAs | Mean trace length |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        table_row("MANDATE-primary", primary),
        table_row("A3 no_gap_analysis", a3),
        table_row("A5 no_registry", a5),
        "",
        "## Structural Checks",
        "",
        (
            f"- A3 gap-report suppression: "
            f"{a3['total_records'] - a3['gap_report_violation_count']}/"
            f"{a3['total_records']} records have empty gap_reports."
        ),
        (
            f"- A5 registry suppression: "
            f"{a5['total_records'] - a5['registry_reference_violation_count']}/"
            f"{a5['total_records']} records have empty/absent registry_reference."
        ),
        "",
        "## Artifact Field Presence",
        "",
        "A3 artifact fields:",
        "",
        "```json",
        json.dumps(a3["artifact_field_presence"], indent=2, sort_keys=True),
        "```",
        "",
        "A5 artifact fields:",
        "",
        "```json",
        json.dumps(a5["artifact_field_presence"], indent=2, sort_keys=True),
        "```",
        "",
        "## Implications",
        "",
        "- A3 tests whether gap-report emission is an output phenomenon while the pipeline still runs.",
        "- A5 tests whether registry resolution is modular under the same local Ollama role stack.",
        "",
        f"Verdict: {verdict}" + (f" ({'; '.join(reasons)})" if reasons else ""),
        "",
    ]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines))
    log(f"wrote {REPORT_PATH.relative_to(ROOT)}")
    return verdict


def update_status(stage: str, extra: dict[str, Any] | None = None) -> None:
    payload = {
        "updated_at": utc_now(),
        "stage": stage,
    }
    if extra:
        payload.update(extra)
    write_json(STATUS_PATH, payload)


def commit_report() -> None:
    if not REPORT_PATH.exists():
        return
    subprocess.run(["git", "add", str(REPORT_PATH.relative_to(ROOT))], cwd=ROOT, check=False)
    diff = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", str(REPORT_PATH.relative_to(ROOT))],
        cwd=ROOT,
    )
    if diff.returncode == 0:
        log("report has no staged diff; skipping commit")
        return
    ret = subprocess.run(
        ["git", "commit", "-m", "HANDOFF_23: add A3/A5 ablation report"],
        cwd=ROOT,
    ).returncode
    log(f"report commit returncode={ret}")


def main() -> int:
    log("HANDOFF_23 launcher started")
    update_status("waiting_for_handoff22")
    wait_for_h22()
    update_status("preconditions")
    assert_preconditions()

    update_status("a3_main")
    run_ablation(RUNS[0])
    update_status("a3_holdout")
    run_ablation(RUNS[1])
    update_status("a3_gate")
    a3 = gate_a3()
    update_status("a3_gate_complete", {"a3": a3})
    if a3["ok_rate"] < 0.80:
        verdict = write_report(a3, summarize_records(ROOT / "07_system_outputs/ablations/a5_no_registry"))
        update_status("halted_after_a3", {"a3": a3, "verdict": verdict})
        commit_report()
        return 2

    update_status("a5_main")
    run_ablation(RUNS[2])
    update_status("a5_holdout")
    run_ablation(RUNS[3])
    update_status("a5_gate")
    a5 = gate_a5()
    verdict = write_report(a3, a5)
    update_status("complete", {"a3": a3, "a5": a5, "verdict": verdict})
    commit_report()
    log("HANDOFF_23 launcher complete")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        log(f"FATAL: {exc!r}")
        update_status("failed", {"error": repr(exc)})
        raise
