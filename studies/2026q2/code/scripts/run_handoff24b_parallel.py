#!/usr/bin/env python3
"""HANDOFF_24b parallel Phase B supervisor.

This amends the original serial HANDOFF_24 Phase B launcher without stopping
the live baseline_1 child process. It starts baseline_2 on OpenAI quota, starts
v2 grading for already-complete perturbation systems, and continues polling so
newly complete baseline directories are anonymized and graded as soon as they
are ready.
"""
from __future__ import annotations

import collections
import glob
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv/bin/python"
POLL_SECONDS = int(os.environ.get("HANDOFF24B_POLL_SECONDS", "300"))

PERT_OUT = ROOT / "07_system_outputs/perturbations"
RUN_TASKS_PATH = ROOT / "06_perturbations/perturbation_suite_for_runs.jsonl"
PERT_GT_PATH = ROOT / "04_ground_truth/ground_truth_perturbations.json"
SUITE_PATH = ROOT / "06_perturbations/perturbation_suite.jsonl"

GRADE_ROOT = ROOT / "08_grading_v2/perturbations"
ANON_DIR = GRADE_ROOT / "anonymized_outputs"
PERT_MAPPING = GRADE_ROOT / "anonymization_mapping.json"
STATUS_PATH = ROOT / "handoffs/HANDOFF_24_phase_b_status.json"
QUEUE_LOG = ROOT / "handoffs/HANDOFF_24_phase_b_grading_queue.jsonl"
PROBE_STATE = ROOT / "handoffs/HANDOFF_24_phase_b_provider_probe_state.json"
COMPLETE_MARKER = ROOT / "handoffs/HANDOFF_24_phase_b_complete.md"
REPORT_PATH = ROOT / "handoffs/HANDOFF_24_phase_b_report.md"
DEVIATION_PATH = ROOT / "handoffs/HANDOFF_24_phase_b_deviation.md"
SCOPE_LOCK = ROOT / "handoffs/HANDOFF_24c_scope_lock.marker"
DAEMON_LOG = ROOT / "logs/HANDOFF_24b_parallel_supervisor.log"
PROBE_LOG = ROOT / "logs/HANDOFF_24_phase_b_provider_probe.log"

TMUX_SESSION = "handoff24_perturbations"
GEN_TARGET = 3500
GRADE_TARGET_TOTAL = 3500 + 350 + 350 + 4 * 3500
SCOPE_RATIONALE = "multi-agent-shell class representative measured via baseline_4"
PROBE_REQUIRED_CONSECUTIVE_HEALTHY = 2

PHASE_A_TARGETS = {
    "mandate_primary": 3500,
    "cond_a": 350,
    "cond_b": 350,
}
BASELINES = tuple(f"baseline_{i}" for i in range(1, 5))
SCOPED_OUT_BASELINES = ("baseline_5", "baseline_6")
ALL_SYSTEMS = tuple(PHASE_A_TARGETS) + BASELINES


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(message: str) -> None:
    DAEMON_LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{utc_now()}] {message}"
    with DAEMON_LOG.open("a") as fh:
        fh.write(line + "\n")
    print(line, flush=True)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open() as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def append_probe_log(payload: dict[str, Any]) -> None:
    append_jsonl(PROBE_LOG, payload)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open() as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def file_count(path: Path) -> int:
    if not path.exists():
        return 0
    return len([p for p in path.glob("*.json") if p.name != "ledger.json"])


def recursive_record_paths(system: str) -> list[Path]:
    root = PERT_OUT / system
    if not root.exists():
        return []
    return sorted(
        p for p in root.rglob("*.json")
        if p.name != "ledger.json" and not p.name.endswith(".jsonl")
    )


def record_count(system: str) -> int:
    return len(recursive_record_paths(system))


def run_capture(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def tmux_windows() -> set[str]:
    ret = run_capture(["tmux", "list-windows", "-t", TMUX_SESSION, "-F", "#{window_name}"])
    if ret.returncode != 0:
        raise RuntimeError(f"tmux session {TMUX_SESSION!r} not available: {ret.stderr}")
    return set(ret.stdout.splitlines())


def launch_tmux_window(name: str, command: str) -> bool:
    if name in tmux_windows():
        return False
    ret = subprocess.run(
        ["tmux", "new-window", "-t", TMUX_SESSION, "-n", name, command],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if ret.returncode != 0:
        raise RuntimeError(f"tmux new-window {name} failed: {ret.stderr}")
    log(f"launched tmux window {name}: {command}")
    return True


def run_provider_probe(label: str, cmd: list[str]) -> dict[str, Any]:
    t0 = time.time()
    ret = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=900,
    )
    return {
        "label": label,
        "ok": ret.returncode == 0,
        "returncode": ret.returncode,
        "elapsed_seconds": round(time.time() - t0, 1),
        "output_tail": ret.stdout[-1200:],
    }


def provider_probe_gate() -> bool:
    """Require two consecutive healthy Gemini + Opus probe intervals.

    HANDOFF_24c inherits the HANDOFF_20 daemon lesson: after provider 503s or
    connection degradation, do not immediately re-fire a large grade-v2 pass.
    Probe both retry-sensitive judges first, then launch only after sustained
    health across two supervisor intervals.
    """
    state = load_json(PROBE_STATE, {}) or {}
    probes = [
        run_provider_probe(
            "gemini",
            [
                str(PYTHON), "-m", "apparatus.grading.probe_gemini",
                "--probes", "5", "--interval", "5",
            ],
        ),
        run_provider_probe(
            "claude_opus",
            [
                str(PYTHON), "-m", "apparatus.probe_anthropic",
                "--model", "claude-opus-4-6",
                "--probes", "5", "--interval", "5",
            ],
        ),
    ]
    ok = all(p["ok"] for p in probes)
    consecutive = int(state.get("consecutive_healthy_intervals", 0))
    consecutive = consecutive + 1 if ok else 0
    payload = {
        "ts": utc_now(),
        "event": "provider_probe_gate",
        "ok": ok,
        "consecutive_healthy_intervals": consecutive,
        "required_consecutive_healthy_intervals": PROBE_REQUIRED_CONSECUTIVE_HEALTHY,
        "probes": probes,
    }
    append_probe_log(payload)
    write_json(PROBE_STATE, payload)
    if consecutive >= PROBE_REQUIRED_CONSECUTIVE_HEALTHY:
        return True
    log(
        "provider probe gate not yet cleared: "
        f"{consecutive}/{PROBE_REQUIRED_CONSECUTIVE_HEALTHY} healthy intervals"
    )
    return False


def ps_lines() -> list[str]:
    ret = run_capture(["ps", "aux"])
    return ret.stdout.splitlines()


def process_running(*needles: str) -> bool:
    for line in ps_lines():
        if all(needle in line for needle in needles):
            return True
    return False


def baseline_running(system: str) -> bool:
    return process_running("apparatus.run", "run-system", f"--system {system}")


def grader_running() -> bool:
    return process_running("apparatus.run", "grade-v2", "08_grading_v2/perturbations")


def original_phase_b_launcher_running() -> bool:
    return process_running("scripts/run_handoff24_perturbations.py", "phase-b")


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


def check_preconditions() -> None:
    if not (ROOT / "09_analysis/HANDOFF_24_structural_invariance_phase_a.md").exists():
        raise RuntimeError("Phase A structural invariance table missing")
    if file_count(ROOT / "08_grading_v2/by_record") != 12000:
        raise RuntimeError("Stage 4 by_record count is not 12000")
    env = load_dotenv()
    missing = [k for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY") if not env.get(k)]
    if missing:
        raise RuntimeError("missing API keys: " + ", ".join(missing))
    if not (PERT_OUT / "baseline_1").exists():
        raise RuntimeError("baseline_1 output directory missing")
    if not RUN_TASKS_PATH.exists():
        raise RuntimeError(f"run tasks missing: {RUN_TASKS_PATH}")
    if not PERT_GT_PATH.exists():
        raise RuntimeError(f"perturbation ground truth missing: {PERT_GT_PATH}")


def launch_baseline(system: str) -> bool:
    if system in SCOPED_OUT_BASELINES and SCOPE_LOCK.exists():
        log(f"HANDOFF_24c scope lock active; refusing to launch {system}")
        return False
    if record_count(system) >= GEN_TARGET or baseline_running(system):
        return False
    name = f"b{system.split('_')[1]}"
    log_path = f"logs/HANDOFF_24_{system}_perturbations.stderr"
    cmd = (
        f"cd '{ROOT}' && "
        f".venv/bin/python -m apparatus.run run-system "
        f"--system {system} "
        f"--tasks {rel(RUN_TASKS_PATH)} "
        f"--output 07_system_outputs/perturbations/{system} "
        f"--runs 10 "
        f"--seed-base 20260624 "
        f"--skip-existing "
        f"2>&1 | tee -a {log_path}"
    )
    return launch_tmux_window(name, cmd)


def maybe_launch_generation() -> None:
    launch_baseline("baseline_2")

    # The original HANDOFF_24 Phase B launcher is already driving baseline_1
    # and will continue baseline_3..baseline_4 serially. While it is alive,
    # this supervisor only adds the independent B2 lane to avoid duplicate
    # schedulers racing on later baseline output directories.
    if original_phase_b_launcher_running():
        return

    if record_count("baseline_1") < GEN_TARGET or baseline_running("baseline_1"):
        return
    # Scope amendment 2026-07-06 per HANDOFF_24c:
    # baselines 5 and 6 (CrewAI shell, LangGraph shell) are pattern-shell
    # variants of baseline 4 (AutoGen shell) sharing the same LLM and
    # architectural class. Perturbation results for baseline_4 are
    # representative of the multi-agent-shell class per PROTOCOL_LOCK
    # §2.2 shell classification.
    for system in ("baseline_3", "baseline_4"):
        if record_count(system) >= GEN_TARGET:
            continue
        if any(baseline_running(other) for other in ("baseline_3", "baseline_4")):
            return
        launch_baseline(system)
        return


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


def ready_systems() -> list[str]:
    ready = []
    for system, target in PHASE_A_TARGETS.items():
        if record_count(system) >= target:
            ready.append(system)
    for system in BASELINES:
        if record_count(system) >= GEN_TARGET:
            ready.append(system)
    return ready


def anonymize_ready_systems(systems: list[str]) -> int:
    ANON_DIR.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, Any] = {}
    outputs: list[dict[str, Any]] = []
    used: set[str] = set()
    for system in systems:
        for path in recursive_record_paths(system):
            rec = load_json(path)
            anon_id = stable_anon_id(rec)
            if anon_id in used:
                raise RuntimeError(f"anon_id collision: {anon_id}")
            used.add(anon_id)
            mapping[anon_id] = {
                "system_id": rec.get("system_id", ""),
                "system_label": rec.get("system_label", ""),
                "run_id": rec.get("run_id", ""),
                "run_number": rec.get("run_number"),
                "task_id": rec.get("task_id", ""),
            }
            outputs.append({
                "anon_id": anon_id,
                "task_id": rec.get("task_id", ""),
                "output_type": rec.get("output_type", ""),
                "output": scrub_identity(rec.get("output")),
                "ok": rec.get("ok", False),
            })
    for old in ANON_DIR.glob("*.json"):
        old.unlink()
    outputs.sort(key=lambda row: row["anon_id"])
    for row in outputs:
        (ANON_DIR / f"{row['anon_id']}.json").write_text(
            json.dumps(row, indent=2, default=str, ensure_ascii=False) + "\n"
        )
    write_json(PERT_MAPPING, mapping)
    log(f"anonymized {len(outputs)} ready perturbation records from {systems}")
    return len(outputs)


def graded_counts_by_system() -> dict[str, int]:
    mapping = load_json(PERT_MAPPING, {})
    counts: dict[str, int] = collections.Counter()
    by_record = GRADE_ROOT / "by_record"
    if not by_record.exists():
        return {system: 0 for system in ALL_SYSTEMS + SCOPED_OUT_BASELINES}
    for path in by_record.glob("*.json"):
        anon_id = path.stem
        ident = mapping.get(anon_id, {})
        system = ident.get("system_id")
        if system:
            counts[system] += 1
    return {system: counts.get(system, 0) for system in ALL_SYSTEMS + SCOPED_OUT_BASELINES}


def launch_grader_if_ready() -> None:
    if grader_running():
        return
    systems = ready_systems()
    if not systems:
        return
    graded = graded_counts_by_system()
    targets = {**PHASE_A_TARGETS, **{b: GEN_TARGET for b in BASELINES}}
    needs_grade = [s for s in systems if graded.get(s, 0) < targets[s]]
    if not needs_grade:
        return
    if not provider_probe_gate():
        return
    n_anon = anonymize_ready_systems(systems)
    max_workers = 3 if record_count("baseline_2") < GEN_TARGET else 5
    event = {
        "ts": utc_now(),
        "event": "launch_grade_v2",
        "ready_systems": systems,
        "needs_grade": needs_grade,
        "n_anonymized": n_anon,
        "max_workers": max_workers,
    }
    append_jsonl(QUEUE_LOG, event)
    name = f"grade_{int(time.time())}"
    cmd = (
        f"cd '{ROOT}' && "
        f".venv/bin/python -m apparatus.run grade-v2 "
        f"--anonymized {rel(ANON_DIR)} "
        f"--ground-truth {rel(PERT_GT_PATH)} "
        f"--judges-config 08_grading/judges_config.json "
        f"--rubric v2 "
        f"--out {rel(GRADE_ROOT)} "
        f"--full-coverage "
        f"--double-grade-pct 0.20 "
        f"--double-grade-seed 20260624 "
        f"--max-workers {max_workers} "
        f"--skip-existing "
        f"2>&1 | tee -a logs/HANDOFF_24_grade_perturbations.stderr"
    )
    launch_tmux_window(name, cmd)


def ok_rate(system: str) -> float:
    paths = recursive_record_paths(system)
    if not paths:
        return 0.0
    ok = 0
    for path in paths:
        try:
            rec = load_json(path)
        except Exception:
            continue
        ok += 1 if rec.get("ok") is True else 0
    return ok / len(paths)


def generation_status() -> dict[str, dict[str, Any]]:
    data: dict[str, dict[str, Any]] = {}
    for system in BASELINES:
        n = record_count(system)
        state = "complete" if n >= GEN_TARGET else "running" if baseline_running(system) else "pending"
        data[system] = {"n_records": n, "target": GEN_TARGET, "state": state}
    for system in SCOPED_OUT_BASELINES:
        data[system] = {
            "n_records": record_count(system),
            "target": GEN_TARGET,
            "state": "scoped_out",
            "scope_amendment": "HANDOFF_24c",
            "rationale": SCOPE_RATIONALE,
        }
    return data


def grading_status() -> dict[str, dict[str, Any]]:
    graded = graded_counts_by_system()
    data: dict[str, dict[str, Any]] = {}
    for system, target in PHASE_A_TARGETS.items():
        key = f"{system}_perturbations"
        n = graded.get(system, 0)
        data[key] = {
            "n_graded": n,
            "target": target,
            "state": "complete" if n >= target else "running" if grader_running() else "pending",
        }
    for system in BASELINES:
        key = f"{system}_perturbations"
        n = graded.get(system, 0)
        target = GEN_TARGET
        if record_count(system) < target:
            state = "waiting_for_generation"
        else:
            state = "complete" if n >= target else "running" if grader_running() else "pending"
        data[key] = {"n_graded": n, "target": target, "state": state}
    for system in SCOPED_OUT_BASELINES:
        data[f"{system}_perturbations"] = {
            "n_graded": graded.get(system, 0),
            "target": GEN_TARGET,
            "state": "scoped_out",
            "scope_amendment": "HANDOFF_24c",
            "rationale": SCOPE_RATIONALE,
        }
    return data


def write_status() -> None:
    status = {
        "current_state": "parallel_gen_and_grade",
        "scope_amendment": "HANDOFF_24c",
        "scoped_grade_target": GRADE_TARGET_TOTAL,
        "generation": generation_status(),
        "grading": grading_status(),
        "rate_limit_policy": {
            "grader_max_workers_while_baseline_2_generating": 3,
            "grader_max_workers_after_baseline_2_complete": 5,
        },
        "updated_at": utc_now(),
    }
    write_json(STATUS_PATH, status)


def completion_ready() -> bool:
    if any(record_count(system) < GEN_TARGET for system in BASELINES):
        return False
    by_record = file_count(GRADE_ROOT / "by_record")
    incomplete = file_count(GRADE_ROOT / "incomplete_grades")
    if by_record < GRADE_TARGET_TOTAL or incomplete:
        return False
    return all(ok_rate(system) >= 0.70 for system in ALL_SYSTEMS)


def write_completion() -> None:
    by_record = file_count(GRADE_ROOT / "by_record")
    incomplete = file_count(GRADE_ROOT / "incomplete_grades")
    lines = [
        "# HANDOFF_24 Phase B Complete",
        "",
        f"Completed at: {utc_now()}",
        "",
        "- Scope amendment: HANDOFF_24c excludes baseline_5 and baseline_6.",
        f"- Scoped grade target: {GRADE_TARGET_TOTAL}",
        f"- Perturbation grade checkpoints: {by_record}",
        f"- Incomplete grades: {incomplete}",
        "",
        "| System | Records | OK-rate |",
        "|---|---:|---:|",
    ]
    for system in ALL_SYSTEMS:
        n = record_count(system)
        lines.append(f"| {system} | {n} | {ok_rate(system):.1%} |")
    for system in SCOPED_OUT_BASELINES:
        lines.append(f"| {system} | {record_count(system)} | scoped_out |")
    COMPLETE_MARKER.write_text("\n".join(lines) + "\n")
    REPORT_PATH.write_text("\n".join(lines) + "\n")
    DEVIATION_PATH.write_text("""# Phase B Scope Amendment — HANDOFF_24c (2026-07-06)

**Change:** Perturbation baseline generation scoped to baselines 1-4 only.
**Excluded:** baseline_5 (CrewAI shell) and baseline_6 (LangGraph shell).

**Rationale:**
Baselines 4, 5, 6 are implementation-pattern shells per PROTOCOL_LOCK §2.2
(explicit shell classification: not real AutoGen / CrewAI / LangGraph
installs; pattern implementations sharing the same LLM and architectural
class). Audit 5 (2026-07-01, `AUDIT10_5_literature_comparability.md`)
confirms the shell classification empirically. Baseline_4 (AutoGen shell)
is treated as the class representative for multi-agent-shell perturbation
behavior.

**Cost / time saved:**
- ~5.8 days wall clock
- ~$4,200 API spend (2 × ~$700 gen + 7,000 × ~$0.15 × 5 grading calls)

**Empirical coverage under this amendment:**
Baseline archetypes covered by the scoped set:
- single-prompt Anthropic best-in-class (baseline_1)
- single-prompt OpenAI (baseline_2)
- agentic reasoning (baseline_3 ReAct)
- multi-agent orchestration pattern (baseline_4 AutoGen shell — class representative)

**Deposit citation:**
Supplement should reference this deviation as row D-12 in the Deviation
Table (§9). Both `HANDOFF_24_phase_b_deviation.md` and HANDOFF_24c are
on-disk provenance for the amendment.
""")
    status = load_json(STATUS_PATH, {})
    status["current_state"] = "complete"
    status["completed_at"] = utc_now()
    write_json(STATUS_PATH, status)


def main() -> int:
    check_preconditions()
    log("HANDOFF_24b parallel supervisor starting")
    while True:
        maybe_launch_generation()
        launch_grader_if_ready()
        write_status()
        if completion_ready():
            write_completion()
            log("HANDOFF_24b Phase B complete")
            return 0
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
