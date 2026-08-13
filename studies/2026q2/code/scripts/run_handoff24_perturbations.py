#!/usr/bin/env python3
"""Two-phase HANDOFF_24 perturbation launcher.

Phase A waits for HANDOFF_23 to land, then runs the local/Ollama-side
perturbation jobs. Phase B waits for Stage 4 grading to finish, then runs
API-backed baselines and perturbation grading.
"""
from __future__ import annotations

import argparse
import collections
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv/bin/python"
POLL_SECONDS = int(os.environ.get("HANDOFF24_POLL_SECONDS", "300"))

SUITE_PATH = ROOT / "06_perturbations/perturbation_suite.jsonl"
RUN_TASKS_PATH = ROOT / "06_perturbations/perturbation_suite_for_runs.jsonl"
PERT_GT_PATH = ROOT / "04_ground_truth/ground_truth_perturbations.json"

PHASE_A_STATUS = ROOT / "handoffs/HANDOFF_24_phase_a_status.json"
PHASE_B_STATUS = ROOT / "handoffs/HANDOFF_24_phase_b_status.json"
STRUCTURAL_PHASE_A = ROOT / "09_analysis/HANDOFF_24_structural_invariance_phase_a.md"
STRUCTURAL_FINAL = ROOT / "09_analysis/HANDOFF_24_structural_invariance_final.md"
REPORT_PATH = ROOT / "handoffs/HANDOFF_24_o5_perturbation_report.md"
SCOPE_LOCK = ROOT / "handoffs/HANDOFF_24c_scope_lock.marker"

PERT_OUT = ROOT / "07_system_outputs/perturbations"
ANON_DIR = ROOT / "08_grading_v2/perturbations_anonymized_outputs"
PERT_MAPPING = ROOT / "08_grading_v2/anonymization_mapping_perturbations.json"
PERT_GRADE_DIR = ROOT / "08_grading_v2/perturbations"

PHASE_A_SYSTEMS = ("mandate_primary", "cond_a", "cond_b")
BASELINE_SYSTEMS = tuple(f"baseline_{i}" for i in range(1, 5))
SCOPED_OUT_BASELINE_SYSTEMS = ("baseline_5", "baseline_6")
ALL_SYSTEMS = PHASE_A_SYSTEMS + BASELINE_SYSTEMS


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(message: str) -> None:
    print(f"[{utc_now()}] {message}", flush=True)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def load_json(path: Path) -> Any:
    with path.open() as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)


def append_status(path: Path, **updates: Any) -> dict[str, Any]:
    status: dict[str, Any] = {}
    if path.exists():
        try:
            status = load_json(path)
        except Exception:
            status = {}
    status.update(updates)
    status["updated_at"] = utc_now()
    write_json(path, status)
    return status


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open() as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_dotenv() -> dict[str, str]:
    env = dict(os.environ)
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            key, val = s.split("=", 1)
            env.setdefault(key.strip(), val.strip().strip('"').strip("'"))
    return env


def run_cmd(cmd: list[str], log_path: Path) -> None:
    log("$ " + " ".join(cmd))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    env = load_dotenv()
    with log_path.open("a", buffering=1) as fh:
        fh.write(f"\n=== {utc_now()} start ===\n")
        fh.write(" ".join(cmd) + "\n")
        proc = subprocess.Popen(
            cmd,
            cwd=ROOT,
            env=env,
            stdout=fh,
            stderr=subprocess.STDOUT,
        )
        ret = proc.wait()
        fh.write(f"=== {utc_now()} end ret={ret} ===\n")
    if ret != 0:
        raise RuntimeError(f"command failed with code {ret}: {' '.join(cmd)}")


def file_count(pattern: str) -> int:
    return len(glob.glob(str(ROOT / pattern)))


def recursive_record_paths(system: str) -> list[Path]:
    root = PERT_OUT / system
    if not root.exists():
        return []
    return sorted(
        p for p in root.rglob("*.json")
        if p.name != "ledger.json" and not p.name.endswith(".jsonl")
    )


def stage4_report_path() -> Path | None:
    exact = ROOT / "handoffs/HANDOFF_20_stage4_report.md"
    if exact.exists():
        return exact
    candidates = sorted((ROOT / "handoffs").glob("HANDOFF_20_stage4_report*.md"))
    return candidates[-1] if candidates else None


def check_api_keys(required: tuple[str, ...]) -> None:
    env = load_dotenv()
    missing = [key for key in required if not env.get(key)]
    if missing:
        raise RuntimeError("missing API key(s): " + ", ".join(missing))


def prepare_perturbation_inputs() -> None:
    rows = load_jsonl(SUITE_PATH)
    if len(rows) != 350:
        raise RuntimeError(f"perturbation suite has {len(rows)} rows, expected 350")
    required = {"perturbation_id", "base_task_id", "request_text", "perturbation_type"}
    bad = [r for r in rows if not required.issubset(r)]
    if bad:
        raise RuntimeError(f"{len(bad)} perturbation rows missing required keys")

    by_type = collections.Counter(r["perturbation_type"] for r in rows)
    if sorted(by_type.values()) != [50] * 7:
        raise RuntimeError(f"expected 7 perturbation types x 50, got {dict(by_type)}")

    tasks = []
    for row in rows:
        tasks.append({
            "task_id": row["perturbation_id"],
            "request_text": row["request_text"],
            "domain": row.get("domain", ""),
            "category": row.get("perturbation_type", ""),
            "base_task_id": row.get("base_task_id", ""),
            "perturbation_type": row.get("perturbation_type", ""),
            "sub_type": row.get("sub_type", ""),
        })
    RUN_TASKS_PATH.write_text(
        "".join(json.dumps(t, ensure_ascii=False) + "\n" for t in tasks)
    )

    base_gt = load_json(ROOT / "04_ground_truth/ground_truth.json")
    pert_gt: dict[str, Any] = {}
    missing = []
    for row in rows:
        base_id = row["base_task_id"]
        if base_id not in base_gt:
            missing.append(base_id)
            continue
        gt = dict(base_gt[base_id])
        gt["base_task_id"] = base_id
        gt["perturbation_id"] = row["perturbation_id"]
        gt["perturbation_type"] = row["perturbation_type"]
        gt["sub_type"] = row.get("sub_type", "")
        gt["category"] = gt.get("category") or row["perturbation_type"]
        gt["is_injection_trial"] = row["perturbation_type"] == "prompt_injection"
        pert_gt[row["perturbation_id"]] = gt
    if missing:
        raise RuntimeError(f"missing ground truth for base task(s): {sorted(set(missing))}")
    write_json(PERT_GT_PATH, pert_gt)
    log(
        "prepared derived perturbation inputs: "
        f"{rel(RUN_TASKS_PATH)}, {rel(PERT_GT_PATH)}"
    )


def assert_common_preconditions() -> None:
    prepare_perturbation_inputs()
    ret = subprocess.run(
        ["git", "tag", "--list", "perturbation_freeze_v1"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if ret.returncode != 0 or "perturbation_freeze_v1" not in ret.stdout.split():
        raise RuntimeError("perturbation_freeze_v1 tag missing")
    ret = subprocess.run(
        ["git", "show", "perturbation_freeze_v1:06_perturbations/perturbation_suite.jsonl"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if ret.returncode != 0 or len([ln for ln in ret.stdout.splitlines() if ln.strip()]) != 350:
        raise RuntimeError("perturbation_freeze_v1 suite is not 350 rows")


def summarize_system(system: str) -> dict[str, Any]:
    paths = recursive_record_paths(system)
    suite = suite_by_id()
    by_type: dict[str, dict[str, int]] = collections.defaultdict(lambda: {"total": 0, "ok": 0, "p2": 0})
    total = ok = p2 = 0
    for path in paths:
        rec = load_json(path)
        ptype = suite.get(rec.get("task_id", ""), {}).get("perturbation_type", "unknown")
        by_type[ptype]["total"] += 1
        total += 1
        if rec.get("ok") is True:
            by_type[ptype]["ok"] += 1
            ok += 1
        if trace_complete(rec):
            by_type[ptype]["p2"] += 1
            p2 += 1
    return {
        "total_records": total,
        "ok_records": ok,
        "ok_rate": ok / total if total else 0.0,
        "p2_records": p2,
        "p2_rate": p2 / total if total else 0.0,
        "by_type": by_type,
    }


def suite_by_id() -> dict[str, dict[str, Any]]:
    return {r["perturbation_id"]: r for r in load_jsonl(SUITE_PATH)}


def trace_complete(rec: dict[str, Any]) -> bool:
    output = rec.get("output") or {}
    artifact = output.get("artifact") if isinstance(output, dict) else {}
    if not isinstance(artifact, dict):
        artifact = {}
    for key in ("trace", "trace_chain", "audit_trace", "role_trace"):
        val = artifact.get(key)
        if isinstance(val, list) and len(val) >= 6:
            return True
    timings = rec.get("role_timings") or []
    return isinstance(timings, list) and len(timings) >= 6


def write_structural_table(path: Path, systems: tuple[str, ...] = ALL_SYSTEMS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# HANDOFF_24 Structural Invariance Check",
        "",
        f"Updated: {utc_now()}",
        "",
        "| System | Perturbation type | ok-rate | P2 trace-complete |",
        "|---|---|---:|---:|",
    ]
    for system in systems:
        summary = summarize_system(system)
        by_type = summary["by_type"]
        for ptype in sorted(by_type):
            row = by_type[ptype]
            total = row["total"]
            lines.append(
                f"| {system} | {ptype} | {row['ok']}/{total} "
                f"({100 * row['ok'] / total:.1f}%) | {row['p2']}/{total} "
                f"({100 * row['p2'] / total:.1f}%) |"
            )
    lines.append("")
    path.write_text("\n".join(lines))
    log(f"wrote structural invariance table: {rel(path)}")


def enforce_ok_floor(system: str, *, halt: bool = False) -> None:
    summary = summarize_system(system)
    rate = summary["ok_rate"]
    log(f"{system} ok-rate {summary['ok_records']}/{summary['total_records']} ({rate:.1%})")
    if summary["total_records"] and rate < 0.70:
        msg = f"{system} perturbation ok-rate below 70% halt threshold"
        log("HALT: " + msg)
        if halt:
            raise RuntimeError(msg)


def wait_for_handoff23() -> None:
    gate = ROOT / "handoffs/HANDOFF_23_ablation_report.md"
    while not gate.exists():
        append_status(
            PHASE_A_STATUS,
            stage="waiting_for_handoff23",
            gate=str(gate.relative_to(ROOT)),
        )
        log(f"Phase A waiting: {rel(gate)} missing; sleeping {POLL_SECONDS}s")
        time.sleep(POLL_SECONDS)
    log(f"Phase A gate satisfied: {rel(gate)} exists")


def wait_for_stage4() -> None:
    while True:
        n = file_count("08_grading_v2/by_record/*.json")
        report = stage4_report_path()
        if n >= 12000 and report is not None:
            log(f"Phase B gate satisfied: by_record={n}, report={rel(report)}")
            return
        append_status(
            PHASE_B_STATUS,
            stage="waiting_for_stage4",
            by_record_count=n,
            stage4_report=str(report.relative_to(ROOT)) if report else "",
        )
        log(
            "Phase B waiting: "
            f"08_grading_v2/by_record has {n}/12000 files, "
            f"report={'present' if report else 'missing'}; sleeping {POLL_SECONDS}s"
        )
        time.sleep(POLL_SECONDS)


def phase_a() -> None:
    append_status(PHASE_A_STATUS, stage="started", started_at=utc_now())
    wait_for_handoff23()
    assert_common_preconditions()
    check_api_keys(("ANTHROPIC_API_KEY",))

    (PERT_OUT / "mandate_primary").mkdir(parents=True, exist_ok=True)
    run_cmd([
        str(PYTHON), "-m", "apparatus.run", "run-system",
        "--system", "mandate_primary",
        "--tasks", rel(RUN_TASKS_PATH),
        "--output", "07_system_outputs/perturbations/mandate_primary",
        "--runs", "10",
        "--seed-base", "20260624",
        "--aegis", "AEGIS-eval",
        "--ollama-mode",
        "--code-ref", "mandate-eval-primary-2026q2-v1",
        "--skip-existing",
    ], ROOT / "logs/HANDOFF_24_mandate_primary_perturbations.stderr")
    enforce_ok_floor("mandate_primary", halt=True)

    (PERT_OUT / "cond_a").mkdir(parents=True, exist_ok=True)
    run_cmd([
        str(PYTHON), "-m", "apparatus.run", "run-cond-a",
        "--all",
        "--tasks", rel(RUN_TASKS_PATH),
        "--out", "07_system_outputs/perturbations/cond_a",
        "--runs-per-task", "1",
        "--seed", "20260624",
        "--max-workers", "1",
        "--skip-existing",
    ], ROOT / "logs/HANDOFF_24_cond_a_perturbations.stderr")
    enforce_ok_floor("cond_a", halt=True)

    (PERT_OUT / "cond_b").mkdir(parents=True, exist_ok=True)
    run_cmd([
        str(PYTHON), "-m", "apparatus.run", "run-cond-b",
        "--all",
        "--tasks", rel(RUN_TASKS_PATH),
        "--out", "07_system_outputs/perturbations/cond_b",
        "--llm-backend", "anthropic",
        "--llm-model", "claude-sonnet-4-6",
        "--domain-profile-mode", "auto",
        "--runs-per-task", "1",
        "--max-workers", "1",
        "--seed", "20260624",
        "--skip-existing",
    ], ROOT / "logs/HANDOFF_24_cond_b_perturbations.stderr")
    enforce_ok_floor("cond_b", halt=True)

    write_structural_table(STRUCTURAL_PHASE_A, PHASE_A_SYSTEMS)
    append_status(PHASE_A_STATUS, stage="completed", completed_at=utc_now())
    log("Phase A completed")


def phase_b() -> None:
    append_status(PHASE_B_STATUS, stage="started", started_at=utc_now())
    wait_for_stage4()
    assert_common_preconditions()
    check_api_keys(("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY"))

    # Scope amendment 2026-07-06 per HANDOFF_24c:
    # baselines 5 and 6 (CrewAI shell, LangGraph shell) are pattern-shell
    # variants of baseline 4 (AutoGen shell) sharing the same LLM and
    # architectural class. Perturbation results for baseline_4 are
    # representative of the multi-agent-shell class per PROTOCOL_LOCK
    # §2.2 shell classification. If the old live parent reaches b5 after
    # b4 finishes, apparatus.run's scope-lock guard refuses that launch.
    for system in BASELINE_SYSTEMS:
        out_dir = PERT_OUT / system
        out_dir.mkdir(parents=True, exist_ok=True)
        b = system.split("_", 1)[1]
        run_cmd([
            str(PYTHON), "-m", "apparatus.run", "run-system",
            "--system", system,
            "--tasks", rel(RUN_TASKS_PATH),
            "--output", rel(out_dir),
            "--runs", "10",
            "--seed-base", "20260624",
            "--skip-existing",
        ], ROOT / f"logs/HANDOFF_24_baseline_{b}_perturbations.stderr")
        enforce_ok_floor(system, halt=False)

    write_structural_table(STRUCTURAL_FINAL, ALL_SYSTEMS)
    anonymize_perturbation_records()
    run_cmd([
        str(PYTHON), "-m", "apparatus.run", "grade-v2",
        "--anonymized", rel(ANON_DIR),
        "--ground-truth", rel(PERT_GT_PATH),
        "--judges-config", "08_grading/judges_config.json",
        "--rubric", "v2",
        "--out", rel(PERT_GRADE_DIR),
        "--full-coverage",
        "--double-grade-pct", "0.20",
        "--double-grade-seed", "20260625",
        "--skip-existing",
        "--max-workers", "5",
    ], ROOT / "logs/HANDOFF_24_grade_v2_perturbations.stderr")
    write_report()
    append_status(PHASE_B_STATUS, stage="completed", completed_at=utc_now())
    log("Phase B completed")


def stable_anon_id(record: dict[str, Any]) -> str:
    key = f"{record.get('system_id','')}|{record.get('run_id','')}"
    return "OUT-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:8].upper()


def scrub_identity(obj: Any) -> Any:
    tokens = [
        "mandate_primary", "MANDATE-primary", "baseline_1", "baseline_2",
        "baseline_3", "baseline_4", "baseline_5", "baseline_6",
        "cond_a", "cond_b",
    ]
    if isinstance(obj, str):
        out = obj
        for token in tokens:
            out = out.replace(token, "[redacted]")
        return out
    if isinstance(obj, list):
        return [scrub_identity(x) for x in obj]
    if isinstance(obj, dict):
        return {k: scrub_identity(v) for k, v in obj.items()}
    return obj


def anonymize_perturbation_records() -> None:
    suite = suite_by_id()
    ANON_DIR.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, Any] = {}
    outputs = []
    used: set[str] = set()
    for system in ALL_SYSTEMS:
        for path in recursive_record_paths(system):
            rec = load_json(path)
            anon_id = stable_anon_id(rec)
            if anon_id in used:
                raise RuntimeError(f"anon_id collision: {anon_id}")
            used.add(anon_id)
            meta = suite.get(rec.get("task_id", ""), {})
            mapping[anon_id] = {
                "system_id": rec.get("system_id", ""),
                "system_label": rec.get("system_label", ""),
                "run_id": rec.get("run_id", ""),
                "run_number": rec.get("run_number"),
                "task_id": rec.get("task_id", ""),
                "base_task_id": meta.get("base_task_id", ""),
                "perturbation_type": meta.get("perturbation_type", ""),
                "sub_type": meta.get("sub_type", ""),
            }
            outputs.append({
                "anon_id": anon_id,
                "task_id": rec.get("task_id", ""),
                "output_type": rec.get("output_type", ""),
                "output": scrub_identity(rec.get("output")),
                "ok": rec.get("ok", False),
            })
    outputs.sort(key=lambda row: row["anon_id"])
    for old in ANON_DIR.glob("*.json"):
        old.unlink()
    for row in outputs:
        (ANON_DIR / f"{row['anon_id']}.json").write_text(
            json.dumps(row, indent=2, default=str, ensure_ascii=False) + "\n"
        )
    write_json(PERT_MAPPING, mapping)
    log(f"anonymized {len(outputs)} perturbation records -> {rel(ANON_DIR)}")


def load_grading_irr() -> dict[str, Any]:
    path = PERT_GRADE_DIR / "irr.json"
    return load_json(path) if path.exists() else {}


def report_samples() -> list[str]:
    suite = suite_by_id()
    baseline_by_task: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    mandate_by_type: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for system in BASELINE_SYSTEMS:
        for path in recursive_record_paths(system):
            rec = load_json(path)
            baseline_by_task[rec.get("task_id", "")].append(rec)
    for path in recursive_record_paths("mandate_primary"):
        rec = load_json(path)
        ptype = suite.get(rec.get("task_id", ""), {}).get("perturbation_type", "unknown")
        mandate_by_type[ptype].append(rec)

    preferred = ["prompt_injection", "missing_required_field", "contradictory_constraints"]
    lines: list[str] = []
    for ptype in preferred:
        chosen = None
        for rec in mandate_by_type.get(ptype, []):
            if rec.get("ok") is True and any(
                b.get("ok") is not True for b in baseline_by_task.get(rec.get("task_id", ""), [])
            ):
                chosen = rec
                break
        if chosen is None and mandate_by_type.get(ptype):
            chosen = mandate_by_type[ptype][0]
        if chosen is None:
            continue
        meta = suite.get(chosen.get("task_id", ""), {})
        request = str(meta.get("request_text", "")).replace("\n", " ")[:500]
        output = json.dumps(chosen.get("output"), default=str, ensure_ascii=False)[:500]
        lines.extend([
            f"### {ptype}",
            "",
            f"- Perturbation: `{chosen.get('task_id')}` from `{meta.get('base_task_id', '')}`",
            f"- MANDATE run: `{chosen.get('run_id')}`, ok={chosen.get('ok')}",
            f"- Request excerpt: {request}",
            f"- Output excerpt: {output}",
            "",
        ])
    return lines


def write_report() -> None:
    irr = load_grading_irr()
    grade_count = file_count("08_grading_v2/perturbations/by_record/*.json")
    dg_count = file_count("08_grading_v2/perturbations/double_grade/pass1/by_record/*.json")
    lines = [
        "# HANDOFF_24 O5 perturbation report",
        "",
        f"Updated: {utc_now()}",
        "",
        "## Per-system O5 score",
        "",
        "| System | Records | OK-rate | P2 trace-complete |",
        "|---|---:|---:|---:|",
    ]
    verdict_ok = True
    for system in ALL_SYSTEMS:
        s = summarize_system(system)
        if s["total_records"] == 0 or s["ok_rate"] < 0.70:
            verdict_ok = False
        lines.append(
            f"| {system} | {s['total_records']} | "
            f"{s['ok_records']}/{s['total_records']} ({100 * s['ok_rate']:.1f}%) | "
            f"{s['p2_records']}/{s['total_records']} ({100 * s['p2_rate']:.1f}%) |"
        )
    lines.extend([
        "",
        "## Per-type structural invariance",
        "",
        STRUCTURAL_FINAL.read_text() if STRUCTURAL_FINAL.exists() else "_Structural table missing._",
        "",
        "## Governance-critical samples",
        "",
    ])
    lines.extend(report_samples() or ["_No samples available._", ""])
    min_kappa = irr.get("min_pairwise_kappa")
    halt = irr.get("halt")
    if min_kappa is None or float(min_kappa) < 0.40 or halt:
        verdict_ok = False
    lines.extend([
        "## Kappa stability",
        "",
        f"- Perturbation grade checkpoints: {grade_count}",
        f"- Double-grade pass1 checkpoints: {dg_count}",
        f"- min_pairwise_kappa: {min_kappa}",
        f"- halt: {halt}",
        "",
        "## Verdict",
        "",
        "PROCEED" if verdict_ok else "HALT",
        "",
    ])
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines))
    log(f"wrote HANDOFF_24 report: {rel(REPORT_PATH)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["phase-a", "phase-b"])
    args = parser.parse_args()
    try:
        if args.phase == "phase-a":
            phase_a()
        else:
            phase_b()
        return 0
    except Exception as exc:
        status_path = PHASE_A_STATUS if args.phase == "phase-a" else PHASE_B_STATUS
        append_status(status_path, stage="failed", error=repr(exc))
        log(f"FAILED {args.phase}: {exc!r}")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
