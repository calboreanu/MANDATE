#!/usr/bin/env python3
"""
Auto-resume HANDOFF_20 Stage 4 v2 grading after sustained Gemini recovery.

The daemon probes Gemini every 15 minutes, requires two consecutive 5/5
health windows, then resumes grade-v2 with --skip-existing. If the grader
halts or stalls, it returns to the probe loop.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
PYTHON = PROJECT / ".venv/bin/python"

BY_RECORD = PROJECT / "08_grading_v2/by_record"
INCOMPLETE = PROJECT / "08_grading_v2/incomplete_grades"
INCOMPLETE_HISTORY = PROJECT / "08_grading_v2/incomplete_history"
DOUBLE_GRADE = PROJECT / "08_grading_v2/double_grade"

LOGS = PROJECT / "logs"
HANDOFFS = PROJECT / "handoffs"
PROBE_LOG = LOGS / "HANDOFF_20_gemini_probe.log"
DAEMON_LOG = LOGS / "HANDOFF_20_stage4_resume_daemon.log"
GRADE_STDOUT = LOGS / "HANDOFF_20_stage4_grade_v2.stdout"
GRADE_STDERR = LOGS / "HANDOFF_20_stage4_grade_v2.stderr"

STATUS_JSON = HANDOFFS / "HANDOFF_20_stage4_resume_status.json"
COMPLETE_MD = HANDOFFS / "HANDOFF_20_stage4_complete.md"

PROBE_INTERVAL_SECONDS = 15 * 60
STALL_SECONDS = 10 * 60
TARGET_RECORDS = 12_000


GRADE_CMD = [
    str(PYTHON),
    "-m",
    "apparatus.run",
    "grade-v2",
    "--anonymized",
    "08_grading_v2/anonymized_outputs",
    "--ground-truth",
    "04_ground_truth/ground_truth.json",
    "--judges-config",
    "08_grading/judges_config.json",
    "--rubric",
    "v2",
    "--out",
    "08_grading_v2",
    "--full-coverage",
    "--double-grade-pct",
    "0.20",
    "--double-grade-seed",
    "20260624",
    "--skip-existing",
    "--max-workers",
    "5",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def compact_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def append(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(text)
        if not text.endswith("\n"):
            fh.write("\n")


def log(msg: str) -> None:
    line = f"{utc_now()} {msg}"
    append(DAEMON_LOG, line)
    print(line, flush=True)


def count_json(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for _ in path.glob("*.json"))


def count_double_grade_json() -> int:
    if not DOUBLE_GRADE.exists():
        return 0
    return sum(1 for _ in DOUBLE_GRADE.rglob("*.json"))


def counts() -> dict[str, int]:
    return {
        "by_record": count_json(BY_RECORD),
        "incomplete_grades": count_json(INCOMPLETE),
        "double_grade_json": count_double_grade_json(),
    }


def load_status() -> dict:
    if not STATUS_JSON.exists():
        return {"transitions": []}
    try:
        data = json.loads(STATUS_JSON.read_text())
    except json.JSONDecodeError:
        return {"transitions": []}
    if "transitions" not in data or not isinstance(data["transitions"], list):
        data["transitions"] = []
    return data


def transition(state: str, details: dict | None = None) -> None:
    details = details or {}
    data = load_status()
    entry = {
        "ts": utc_now(),
        "state": state,
        "details": {
            **details,
            "counts": counts(),
        },
    }
    data["updated_at"] = entry["ts"]
    data["current_state"] = state
    data["transitions"].append(entry)
    tmp = STATUS_JSON.with_suffix(".json.tmp")
    STATUS_JSON.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    tmp.replace(STATUS_JSON)
    log(f"state={state} details={json.dumps(entry['details'], sort_keys=True)}")


def parse_probe_result(text: str) -> tuple[int, int]:
    match = re.search(r"Result:\s*(\d+)/(\d+)\s+probes succeeded", text)
    if not match:
        return 0, 5
    return int(match.group(1)), int(match.group(2))


def run_probe() -> tuple[int, int, int]:
    cmd = [
        str(PYTHON),
        "-m",
        "apparatus.grading.probe_gemini",
        "--probes",
        "5",
    ]
    start = utc_now()
    proc = subprocess.run(
        cmd,
        cwd=PROJECT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = proc.stdout or ""
    n_success, n_total = parse_probe_result(output)
    append(
        PROBE_LOG,
        "\n".join(
            [
                f"{start} n_success={n_success} n_total={n_total} exit_code={proc.returncode}",
                output.rstrip(),
                "-" * 72,
            ]
        )
        + "\n",
    )
    log(f"probe n_success={n_success} n_total={n_total} exit_code={proc.returncode}")
    return n_success, n_total, proc.returncode


def archive_incompletes(reason: str) -> int:
    if not INCOMPLETE.exists():
        return 0
    files = sorted(INCOMPLETE.glob("*.json"))
    if not files:
        return 0
    dest = INCOMPLETE_HISTORY / f"{compact_ts()}_{reason}"
    dest.mkdir(parents=True, exist_ok=True)
    for src in files:
        shutil.move(str(src), dest / src.name)
    log(f"archived {len(files)} incomplete grade files to {dest.relative_to(PROJECT)}")
    return len(files)


def progress_metric() -> tuple[str, int]:
    main_count = count_json(BY_RECORD)
    if main_count < TARGET_RECORDS:
        return "by_record", main_count
    return "double_grade_json", count_double_grade_json()


def terminate_process(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=30)


def run_grade_resume() -> bool:
    archived = archive_incompletes("before_resume")
    before = counts()
    transition(
        "resumed",
        {
            "archived_incomplete_before_resume": archived,
            "command": " ".join(GRADE_CMD),
            "counts_before": before,
        },
    )

    GRADE_STDOUT.parent.mkdir(parents=True, exist_ok=True)
    with GRADE_STDOUT.open("a") as out_fh, GRADE_STDERR.open("a") as err_fh:
        append(GRADE_STDOUT, f"\n===== HANDOFF_20 resume start {utc_now()} =====\n")
        append(GRADE_STDERR, f"\n===== HANDOFF_20 resume start {utc_now()} =====\n")
        proc = subprocess.Popen(
            GRADE_CMD,
            cwd=PROJECT,
            stdout=out_fh,
            stderr=err_fh,
            text=True,
        )

        metric_name, metric_value = progress_metric()
        last_metric_name = metric_name
        last_metric_value = metric_value
        last_progress = time.time()

        while proc.poll() is None:
            time.sleep(60)
            metric_name, metric_value = progress_metric()
            if (
                metric_name != last_metric_name
                or metric_value > last_metric_value
            ):
                last_metric_name = metric_name
                last_metric_value = metric_value
                last_progress = time.time()
                log(f"progress {metric_name}={metric_value}")

            if time.time() - last_progress > STALL_SECONDS:
                reason = (
                    f"no new checkpoints for >{STALL_SECONDS // 60} min "
                    f"(metric={metric_name}, value={metric_value})"
                )
                log(reason)
                terminate_process(proc)
                transition(
                    "halted_again",
                    {
                        "reason": "no_new_checkpoints_gt_10min",
                        "exit_code": proc.returncode,
                        "progress_metric": metric_name,
                        "progress_value": metric_value,
                    },
                )
                return False

        rc = proc.returncode

    current = counts()
    if rc == 0 and current["by_record"] >= TARGET_RECORDS and current["incomplete_grades"] == 0:
        transition("complete", {"exit_code": rc})
        write_complete_markdown()
        return True

    transition("halted_again", {"reason": "grade_v2_exit", "exit_code": rc})
    return False


def write_complete_markdown() -> None:
    current = counts()
    COMPLETE_MD.write_text(
        "\n".join(
            [
                "# HANDOFF 20 Stage 4 Complete",
                "",
                f"Completed at: {utc_now()}",
                "",
                "Final checkpoint counts:",
                f"- `08_grading_v2/by_record/`: {current['by_record']}",
                f"- `08_grading_v2/incomplete_grades/`: {current['incomplete_grades']}",
                f"- `08_grading_v2/double_grade/` JSON files: {current['double_grade_json']}",
                "",
                "The auto-resume daemon required sustained Gemini health, resumed",
                "`grade-v2 --skip-existing`, and exited after the completion",
                "condition was satisfied.",
                "",
            ]
        )
    )


def already_complete() -> bool:
    current = counts()
    return current["by_record"] >= TARGET_RECORDS and current["incomplete_grades"] == 0


def main() -> int:
    LOGS.mkdir(parents=True, exist_ok=True)
    HANDOFFS.mkdir(parents=True, exist_ok=True)
    BY_RECORD.mkdir(parents=True, exist_ok=True)
    INCOMPLETE.mkdir(parents=True, exist_ok=True)

    log("HANDOFF_20 auto-resume daemon starting")
    if already_complete():
        transition("complete", {"reason": "already_complete_on_start"})
        write_complete_markdown()
        return 0

    transition("waiting", {"reason": "daemon_started"})
    consecutive_good = 0

    while True:
        n_success, n_total, rc = run_probe()
        if rc == 0 and n_success == n_total == 5:
            consecutive_good += 1
        else:
            consecutive_good = 0

        data = load_status()
        data["latest_probe"] = {
            "ts": utc_now(),
            "n_success": n_success,
            "n_total": n_total,
            "exit_code": rc,
            "consecutive_healthy_intervals": consecutive_good,
        }
        tmp = STATUS_JSON.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        tmp.replace(STATUS_JSON)

        if consecutive_good >= 2:
            transition(
                "gate_cleared",
                {"consecutive_healthy_intervals": consecutive_good},
            )
            if run_grade_resume():
                return 0
            consecutive_good = 0
            transition("waiting", {"reason": "grade_halted_again"})

        time.sleep(PROBE_INTERVAL_SECONDS)


if __name__ == "__main__":
    sys.exit(main())
