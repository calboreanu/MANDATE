#!/usr/bin/env zsh
set -euo pipefail

cleanup() {
  unset ANTHROPIC_API_KEY
  stty echo 2>/dev/null || true
}
trap cleanup EXIT

export EVAL_ROOT="/Users/ws01admin/Desktop/mandate-eval-v3-local-exec"
export MLT_ROOT="/Users/ws01admin/Desktop/MLT-Governance-Stack-v3-local-exec"
export V3_ROOT="$EVAL_ROOT/replication_package/v3_corrected_routing_20260806T231117Z"
export FULL_CAMPAIGN_CAP="299.250033"
export EXPECTED_MLT_COMMIT="c0b58fb38b3c72ab6ece72f7576425892234976c"
export EXPECTED_APP_COMMIT="74c62b02856254656905269d2bff9851dbfb1800"

cd "$EVAL_ROOT"
. .venv-rerun/bin/activate

export PYTHONPATH="$EVAL_ROOT/code:$MLT_ROOT/src"
export ACTUAL_MLT_COMMIT="$(git -C "$MLT_ROOT" rev-parse HEAD)"
export ACTUAL_APP_COMMIT="$(git rev-parse HEAD)"
export MLT_COMMIT="$EXPECTED_MLT_COMMIT"
export APP_COMMIT="$EXPECTED_APP_COMMIT"
export LOCAL_PREFLIGHT="$EVAL_ROOT/work/v3_preflight_local/preflight_manifest.json"
export LOCAL_PREFLIGHT_SHA256="$(shasum -a 256 "$LOCAL_PREFLIGHT" | awk '{print $1}')"

if [[ ! -d "$V3_ROOT" ]]; then
  echo "Missing existing campaign root: $V3_ROOT" >&2
  exit 2
fi

if [[ "$ACTUAL_MLT_COMMIT" != "$EXPECTED_MLT_COMMIT" ]]; then
  echo "MLT commit drift: actual=$ACTUAL_MLT_COMMIT expected=$EXPECTED_MLT_COMMIT" >&2
  exit 2
fi

if [[ "$ACTUAL_APP_COMMIT" != "$EXPECTED_APP_COMMIT" ]]; then
  echo "Apparatus commit drift: actual=$ACTUAL_APP_COMMIT expected=$EXPECTED_APP_COMMIT" >&2
  exit 2
fi

mkdir -p "$V3_ROOT/logs" "$V3_ROOT/analysis" "$V3_ROOT/provenance"

{
  echo "RESUME_V3_ROOT=$V3_ROOT"
  echo "MLT_COMMIT=$MLT_COMMIT"
  echo "APP_COMMIT=$APP_COMMIT"
  echo "ACTUAL_MLT_COMMIT=$ACTUAL_MLT_COMMIT"
  echo "ACTUAL_APP_COMMIT=$ACTUAL_APP_COMMIT"
  echo "LOCAL_PREFLIGHT=$LOCAL_PREFLIGHT"
  echo "LOCAL_PREFLIGHT_SHA256=$LOCAL_PREFLIGHT_SHA256"
  echo "FULL_CAMPAIGN_CAP=$FULL_CAMPAIGN_CAP"
  date -u +%Y-%m-%dT%H:%M:%SZ
} | tee "$V3_ROOT/logs/resume_start_$(date -u +%Y%m%dT%H%M%SZ).log"

python - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ["V3_ROOT"])
rows = []
ledger = root / "api_cost_ledger.jsonl"
if ledger.exists():
    rows = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
reservations = [r for r in rows if r.get("row_type") == "reservation"]
settlements = [r for r in rows if r.get("row_type") == "settlement"]
settled_ids = {r.get("reservation_id") for r in settlements}
active = [r for r in reservations if r.get("reservation_id") not in settled_ids]
counts = {
    name: len(list((root / name).glob("*.json")))
    for name in ("cond_a_main", "cond_a_holdout", "cond_b_main", "cond_b_holdout")
}
print(json.dumps({
    "resume_root": str(root),
    "existing_counts": counts,
    "active_reservations_before_resume": len(active),
    "active_reservations": active[-5:],
}, indent=2, sort_keys=True))
PY

require_api_key_for_paid_execution() {
  if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
    printf "Temporary Anthropic API key: " >&2
    stty -echo
    IFS= read -r ANTHROPIC_API_KEY
    stty echo
    printf "\n" >&2
    export ANTHROPIC_API_KEY
  fi

  if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
    echo "ANTHROPIC_API_KEY was empty; refusing paid execution." >&2
    exit 2
  fi
}

validate_anthropic_key_for_paid_execution() {
  local log_path="$V3_ROOT/logs/key_auth_probe_$(date -u +%Y%m%dT%H%M%SZ).log"
  python - <<'PY' 2>&1 | tee "$log_path"
import os
import re
import sys

from anthropic import Anthropic

key = os.environ.get("ANTHROPIC_API_KEY") or ""
if not key:
    print("ANTHROPIC_API_KEY_AUTH_PROBE_FAILED: missing key", file=sys.stderr)
    raise SystemExit(2)

redact = re.compile(r"sk-ant-[A-Za-z0-9_-]+|sk-ant-api[A-Za-z0-9_-]+")
try:
    Anthropic(api_key=key).models.list(limit=1)
except Exception as exc:  # noqa: BLE001 - shell gate must turn any auth/network failure into a stop.
    message = redact.sub("<redacted-key>", str(exc))
    lower = message.lower()
    if "invalid x-api-key" in lower or "authentication" in lower or "401" in lower:
        print(
            f"ANTHROPIC_API_KEY_AUTH_PROBE_FAILED: invalid key ({exc.__class__.__name__}: {message})",
            file=sys.stderr,
        )
    else:
        print(
            f"ANTHROPIC_API_KEY_AUTH_PROBE_FAILED: {exc.__class__.__name__}: {message}",
            file=sys.stderr,
        )
    raise SystemExit(2)

print("ANTHROPIC_API_KEY_AUTH_PROBE_PASS")
PY
  local rc=${pipestatus[1]}
  if [[ "$rc" -ne 0 ]]; then
    echo "ANTHROPIC_API_KEY_AUTH_PROBE_FAILED rc=$rc"
    exit "$rc"
  fi
}

repair_stale_shard_ledgers() {
  local log_path="$V3_ROOT/logs/shard_ledger_checkpoint_repair_$(date -u +%Y%m%dT%H%M%SZ).log"
  python - <<'PY' 2>&1 | tee "$log_path"
import hashlib
import json
import os
import shutil
import time
from collections import Counter
from pathlib import Path

root = Path(os.environ["V3_ROOT"])
timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
repair_dir = root / "provenance" / "repairs" / f"{timestamp}_auto_shard_ledger_checkpoint_repair"


def sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: Path) -> tuple[list[dict], list[dict]]:
    rows = []
    errors = []
    if not path.exists():
        return rows, errors
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            errors.append({
                "line_number": line_number,
                "error": str(exc),
            })
    return rows, errors


repairs = []
for dirname in ("cond_a_main", "cond_a_holdout", "cond_b_main", "cond_b_holdout"):
    shard = root / dirname
    if not shard.exists():
        continue
    ledger_path = shard / "ledger.jsonl"
    active_records = []
    for fp in sorted(shard.glob("*.json")):
        if fp.name.startswith(".") or ".tmp." in fp.name:
            continue
        active_records.append(json.loads(fp.read_text(encoding="utf-8")))

    active_run_ids = [str(rec.get("run_id") or "") for rec in active_records]
    active_run_id_set = set(active_run_ids)
    if len(active_run_ids) != len(active_run_id_set):
        raise SystemExit(f"{dirname}: duplicate active checkpoint run_id detected")

    ledger_rows, parse_errors = read_jsonl(ledger_path)
    ledger_run_ids = [str(row.get("run_id") or "") for row in ledger_rows]
    extra_run_ids = sorted(set(ledger_run_ids) - active_run_id_set)
    duplicate_run_ids = sorted(
        run_id for run_id, count in Counter(ledger_run_ids).items()
        if run_id and count > 1
    )

    if not ledger_path.exists() or not (parse_errors or extra_run_ids or duplicate_run_ids):
        continue

    repair_dir.mkdir(parents=True, exist_ok=True)
    backup_path = repair_dir / f"{dirname}.ledger.stale_pre_repair.jsonl"
    shutil.copy2(ledger_path, backup_path)
    with ledger_path.open("w", encoding="utf-8") as fh:
        for rec in active_records:
            fh.write(json.dumps(rec, default=str, sort_keys=True) + "\n")

    repairs.append({
        "shard": dirname,
        "ledger_path": str(ledger_path),
        "backup_path": str(backup_path),
        "backup_sha256": sha256(backup_path),
        "after_sha256": sha256(ledger_path),
        "active_checkpoint_count": len(active_records),
        "ledger_row_count_before": len(ledger_rows),
        "ledger_row_count_after": len(active_records),
        "parse_error_count": len(parse_errors),
        "parse_errors_sample": parse_errors[:5],
        "extra_run_id_count_vs_active_checkpoints": len(extra_run_ids),
        "extra_run_ids_sample": extra_run_ids[:20],
        "duplicate_run_ids": duplicate_run_ids[:20],
    })

report = {
    "ok": True,
    "repair": "auto_shard_ledger_checkpoint_repair",
    "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "root": str(root),
    "repair_count": len(repairs),
    "repairs": repairs,
}
if repairs:
    audit_path = repair_dir / "repair_audit.json"
    audit_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    report["audit_path"] = str(audit_path)
print(json.dumps(report, indent=2, sort_keys=True))
PY
  local rc=${pipestatus[1]}
  if [[ "$rc" -ne 0 ]]; then
    echo "SHARD_LEDGER_CHECKPOINT_REPAIR_FAILED rc=$rc"
    exit "$rc"
  fi
}

pre_resume_checkpoint_gate() {
  local log_path="$V3_ROOT/logs/pre_resume_checkpoint_gate_$(date -u +%Y%m%dT%H%M%SZ).log"
  python - <<'PY' 2>&1 | tee "$log_path"
import json
import os
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from apparatus.rerun_analysis import (
    _load_result_envelope_schema,
    load_corpus_rows,
    load_json,
    load_jsonl,
    validate_record,
)

root = Path(os.environ["V3_ROOT"])
preflight_path = Path(os.environ["LOCAL_PREFLIGHT"])
ledger_path = root / "api_cost_ledger.jsonl"
expected_mlt_commit = os.environ["MLT_COMMIT"]
expected_apparatus_commit = os.environ["APP_COMMIT"]
cap = Decimal(os.environ["FULL_CAMPAIGN_CAP"])

issues = []
if not ledger_path.exists():
    issues.append(f"missing cost ledger: {ledger_path}")

preflight = load_json(preflight_path)
schema = _load_result_envelope_schema(preflight)
corpus_rows = load_corpus_rows([
    Path("replication_package/v1_main/corpus/main_tasks.jsonl"),
    Path("replication_package/v1_main/corpus/holdout_tasks.jsonl"),
])

shards = [
    ("cond_a_main", "cond_a", Path("replication_package/v1_main/corpus/main_tasks.jsonl")),
    ("cond_a_holdout", "cond_a", Path("replication_package/v1_main/corpus/holdout_tasks.jsonl")),
    ("cond_b_main", "cond_b", Path("replication_package/v1_main/corpus/main_tasks.jsonl")),
    ("cond_b_holdout", "cond_b", Path("replication_package/v1_main/corpus/holdout_tasks.jsonl")),
]

shard_reports = {}
for dirname, condition, corpus_path in shards:
    shard = root / dirname
    expected_rows = load_jsonl(corpus_path)
    expected_task_ids = [str(row.get("task_id") or "") for row in expected_rows]
    expected_task_id_set = set(expected_task_ids)
    expected_max_records = len(expected_task_ids) * 10
    records = []
    hidden_or_tmp = [
        str(fp)
        for fp in sorted(shard.iterdir())
        if fp.is_file() and (fp.name.startswith(".") or ".tmp." in fp.name)
    ] if shard.exists() else []
    for fp in sorted(shard.glob("*.json")):
        records.append(json.loads(fp.read_text(encoding="utf-8")))

    if hidden_or_tmp:
        issues.append(f"{dirname}: incomplete/hidden checkpoint files present: {hidden_or_tmp[:5]}")
    if len(records) > expected_max_records:
        issues.append(f"{dirname}: found {len(records)} records, expected at most {expected_max_records}")

    active_run_ids = {str(rec.get("run_id") or "") for rec in records}
    shard_ledger = shard / "ledger.jsonl"
    if shard_ledger.exists():
        shard_ledger_run_ids = []
        for line_number, line in enumerate(shard_ledger.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                shard_ledger_run_ids.append(str(json.loads(line).get("run_id") or ""))
            except json.JSONDecodeError as exc:
                issues.append(f"{dirname}/ledger.jsonl parse failure at line {line_number}: {exc}")
        extra_shard_ledger_run_ids = sorted(set(shard_ledger_run_ids) - active_run_ids)
        duplicate_shard_ledger_run_ids = sorted(
            run_id for run_id, count in Counter(shard_ledger_run_ids).items()
            if run_id and count > 1
        )
        if extra_shard_ledger_run_ids:
            issues.append(
                f"{dirname}/ledger.jsonl has {len(extra_shard_ledger_run_ids)} "
                "run_id(s) without active checkpoint JSON"
            )
        if duplicate_shard_ledger_run_ids:
            issues.append(
                f"{dirname}/ledger.jsonl has duplicate run_id(s): "
                f"{duplicate_shard_ledger_run_ids[:10]}"
            )

    seen_keys = set()
    seen_run_ids = set()
    runs_by_task = defaultdict(set)
    states = Counter()
    duplicate_role_records = []
    retry_status_counts = Counter()
    for rec in records:
        run_id = str(rec.get("run_id") or "")
        task_id = str(rec.get("task_id") or "")
        run_number = rec.get("run_number")
        seed = rec.get("seed")
        states[str(rec.get("execution_state") or "")] += 1

        if run_id in seen_run_ids:
            issues.append(f"{dirname}: duplicate run_id {run_id}")
        seen_run_ids.add(run_id)

        key = (task_id, run_number, seed)
        if key in seen_keys:
            issues.append(f"{dirname}: duplicate task/run/seed {key}")
        seen_keys.add(key)

        if task_id not in expected_task_id_set:
            issues.append(f"{run_id}: task id not in {dirname} corpus")
        if run_number not in range(1, 11):
            issues.append(f"{run_id}: run_number outside 1..10")
        else:
            runs_by_task[task_id].add(int(run_number))
            expected_seed = 20260623 + int(run_number)
            if seed != expected_seed:
                issues.append(f"{run_id}: seed {seed} != {expected_seed}")

        if rec.get("execution_state") == "FAILED":
            issues.append(f"{run_id}: final execution_state FAILED")

        output = rec.get("output") if isinstance(rec.get("output"), dict) else {}
        if condition == "cond_a":
            raw = output.get("mission_input_metadata", {}).get("raw_provider_response", {})
            status = str((raw.get("retry") or {}).get("final_status") or "")
            retry_status_counts[status] += 1
            if status.lower() == "failed":
                issues.append(f"{run_id}: provider retry final_status failed")
        else:
            role_counts = Counter()
            for response in output.get("provider_responses") or []:
                if not isinstance(response, dict):
                    continue
                role = response.get("role") or "UNKNOWN_ROLE"
                role_counts[role] += 1
                raw = response.get("raw_response") if isinstance(response.get("raw_response"), dict) else {}
                status = str((raw.get("retry") or {}).get("final_status") or "")
                retry_status_counts[status] += 1
                if status.lower() == "failed":
                    issues.append(f"{run_id}: {role} provider retry final_status failed")
            dup = {role: count for role, count in role_counts.items() if count > 1}
            if dup:
                duplicate_role_records.append({"run_id": run_id, "roles": dup})

        issues.extend(validate_record(
            rec,
            condition=condition,
            expected_mlt_commit=expected_mlt_commit,
            expected_apparatus_commit=expected_apparatus_commit,
            require_clean_worktree=True,
            preflight_manifest=preflight,
            corpus_rows=corpus_rows,
            result_envelope_schema=schema,
        ))

    partial_tasks = {
        task_id: sorted(runs)
        for task_id, runs in sorted(runs_by_task.items())
        if runs != set(range(1, 11))
    }
    complete_tasks = sum(1 for runs in runs_by_task.values() if runs == set(range(1, 11)))
    shard_reports[dirname] = {
        "records": len(records),
        "expected_max_records": expected_max_records,
        "complete_10_run_tasks": complete_tasks,
        "partial_tasks": dict(list(partial_tasks.items())[:20]),
        "state_counts": dict(states),
        "retry_status_counts": dict(retry_status_counts),
        "duplicate_role_record_count": len(duplicate_role_records),
        "duplicate_role_records_sample": duplicate_role_records[:10],
    }

ledger_rows = []
if ledger_path.exists():
    for line_number, line in enumerate(ledger_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            ledger_rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            issues.append(f"ledger JSON parse failure at line {line_number}: {exc}")

reservations = [row for row in ledger_rows if row.get("row_type") == "reservation"]
settlements = [row for row in ledger_rows if row.get("row_type") == "settlement"]
settled_ids = {row.get("reservation_id") for row in settlements}
active = [row for row in reservations if row.get("reservation_id") not in settled_ids]
last_by_reservation = {}
for row in ledger_rows:
    rid = row.get("reservation_id")
    if rid:
        last_by_reservation[rid] = row
if len(active) > 1:
    issues.append(f"more than one active reservation before resume: {len(active)}")

settled_total = sum(Decimal(str(row.get("actual_cost_usd") or "0")) for row in settlements)
active_reserved = sum(Decimal(str(row.get("reserved_cost_usd") or "0")) for row in active)
remaining_capacity = cap - settled_total - active_reserved
if remaining_capacity <= 0:
    issues.append(f"no remaining budget capacity: {remaining_capacity}")

report = {
    "ok": not issues,
    "resume_root": str(root),
    "shards": shard_reports,
    "ledger": {
        "rows": len(ledger_rows),
        "reservations": len(reservations),
        "settlements": len(settlements),
        "active_reservation_count": len(active),
        "active_reservations": active,
        "latest_rows_for_active": [last_by_reservation.get(row.get("reservation_id")) for row in active],
        "settled_total_usd": str(settled_total),
        "active_reserved_usd": str(active_reserved),
        "remaining_capacity_after_active_usd": str(remaining_capacity),
    },
    "issue_count": len(issues),
    "issues": issues[:50],
}
(root / "analysis" / "pre_resume_checkpoint_gate.json").write_text(
    json.dumps(report, indent=2, sort_keys=True),
    encoding="utf-8",
)
print(json.dumps(report, indent=2, sort_keys=True))
raise SystemExit(0 if not issues else 1)
PY
  local rc=${pipestatus[1]}
  if [[ "$rc" -ne 0 ]]; then
    echo "PRE_RESUME_CHECKPOINT_GATE_FAILED rc=$rc"
    exit "$rc"
  fi
}

paid_work_remaining() {
  python - <<'PY'
import json
import os
from collections import Counter
from pathlib import Path

root = Path(os.environ["V3_ROOT"])
pairs = [
    (root / "cond_b_main", Path("replication_package/v1_main/corpus/main_tasks.jsonl")),
    (root / "cond_b_holdout", Path("replication_package/v1_main/corpus/holdout_tasks.jsonl")),
]
for shard, corpus_path in pairs:
    records_by_task = Counter()
    for fp in sorted(shard.glob("*.json")):
        if fp.name.startswith(".") or ".tmp." in fp.name:
            continue
        rec = json.loads(fp.read_text(encoding="utf-8"))
        records_by_task[str(rec.get("task_id") or "")] += 1
    for line in corpus_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        task_id = str(json.loads(line).get("task_id") or "")
        if records_by_task.get(task_id, 0) < 10:
            raise SystemExit(0)
raise SystemExit(1)
PY
}

remaining_task_ids() {
  local shard_dir="$1"
  local corpus_path="$2"
  SHARD_DIR="$shard_dir" CORPUS_PATH="$corpus_path" python - <<'PY'
import json
import os
from collections import Counter
from pathlib import Path

shard = Path(os.environ["SHARD_DIR"])
corpus_path = Path(os.environ["CORPUS_PATH"])
records_by_task = Counter()
for fp in sorted(shard.glob("*.json")):
    if fp.name.startswith(".") or ".tmp." in fp.name:
        continue
    rec = json.loads(fp.read_text(encoding="utf-8"))
    records_by_task[str(rec.get("task_id") or "")] += 1

for line in corpus_path.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    task_id = str(json.loads(line).get("task_id") or "")
    if records_by_task.get(task_id, 0) < 10:
        print(task_id)
PY
}

check_shard() {
  local shard_path="$1"
  local condition="$2"
  local corpus_path="$3"
  local label="$4"
  local log_path="$V3_ROOT/logs/${label}_shard_check.log"

  SHARD_PATH="$shard_path" \
  SHARD_CONDITION="$condition" \
  SHARD_CORPUS="$corpus_path" \
  SHARD_LABEL="$label" \
  python - <<'PY' 2>&1 | tee "$log_path"
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

from apparatus.rerun_analysis import (
    _cost_accounting_report,
    _load_result_envelope_schema,
    _validate_cost_ledger,
    load_corpus_rows,
    load_json,
    load_jsonl,
    validate_record,
)

root = Path(os.environ["V3_ROOT"])
shard = Path(os.environ["SHARD_PATH"])
condition = os.environ["SHARD_CONDITION"]
corpus_path = Path(os.environ["SHARD_CORPUS"])
label = os.environ["SHARD_LABEL"]
ledger_path = root / "api_cost_ledger.jsonl"
preflight_path = Path(os.environ["LOCAL_PREFLIGHT"])
expected_mlt_commit = os.environ["MLT_COMMIT"]
expected_apparatus_commit = os.environ["APP_COMMIT"]
cap = float(os.environ["FULL_CAMPAIGN_CAP"])

preflight = load_json(preflight_path)
corpus_rows = load_corpus_rows([
    Path("replication_package/v1_main/corpus/main_tasks.jsonl"),
    Path("replication_package/v1_main/corpus/holdout_tasks.jsonl"),
])
expected_rows = load_jsonl(corpus_path)
expected_task_ids = {str(row.get("task_id")) for row in expected_rows}
expected_count = len(expected_task_ids) * 10
schema = _load_result_envelope_schema(preflight)

issues = []
records = []
for fp in sorted(shard.glob("*.json")):
    if fp.name.startswith(".") or ".tmp." in fp.name:
        issues.append(f"incomplete or hidden checkpoint present: {fp}")
        continue
    records.append(json.loads(fp.read_text(encoding="utf-8")))

if len(records) != expected_count:
    issues.append(f"{label}: expected {expected_count} records, found {len(records)}")

seen_keys = set()
seen_run_ids = set()
runs_by_task = defaultdict(set)
state_counts = Counter()
retry_status_counts = Counter()
for rec in records:
    run_id = str(rec.get("run_id") or "")
    task_id = str(rec.get("task_id") or "")
    run_number = rec.get("run_number")
    seed = rec.get("seed")
    state = str(rec.get("execution_state") or "")
    state_counts[state] += 1

    if run_id in seen_run_ids:
        issues.append(f"{label}: duplicate run_id {run_id}")
    seen_run_ids.add(run_id)

    key = (task_id, run_number, seed)
    if key in seen_keys:
        issues.append(f"{label}: duplicate task/run/seed {key}")
    seen_keys.add(key)

    if task_id not in expected_task_ids:
        issues.append(f"{run_id}: task id not in shard corpus")
    if run_number not in range(1, 11):
        issues.append(f"{run_id}: run_number outside 1..10")
    else:
        runs_by_task[task_id].add(int(run_number))
        expected_seed = 20260623 + int(run_number)
        if seed != expected_seed:
            issues.append(f"{run_id}: seed {seed} != {expected_seed}")

    if state == "FAILED":
        issues.append(f"{run_id}: final execution_state FAILED")

    output = rec.get("output") if isinstance(rec.get("output"), dict) else {}
    if condition == "cond_a":
        raw = (
            output.get("mission_input_metadata", {})
            .get("raw_provider_response", {})
        )
        status = str((raw.get("retry") or {}).get("final_status") or "")
        retry_status_counts[status] += 1
        if status.lower() == "failed":
            issues.append(f"{run_id}: provider retry final_status failed")
    else:
        for response in output.get("provider_responses") or []:
            if not isinstance(response, dict):
                continue
            raw = response.get("raw_response") if isinstance(response.get("raw_response"), dict) else {}
            status = str((raw.get("retry") or {}).get("final_status") or "")
            retry_status_counts[status] += 1
            if status.lower() == "failed":
                role = response.get("role") or "UNKNOWN_ROLE"
                issues.append(f"{run_id}: {role} provider retry final_status failed")

    issues.extend(validate_record(
        rec,
        condition=condition,
        expected_mlt_commit=expected_mlt_commit,
        expected_apparatus_commit=expected_apparatus_commit,
        require_clean_worktree=True,
        preflight_manifest=preflight,
        corpus_rows=corpus_rows,
        result_envelope_schema=schema,
    ))

missing_task_runs = {
    task_id: sorted(set(range(1, 11)) - runs)
    for task_id, runs in runs_by_task.items()
    if runs != set(range(1, 11))
}
for task_id in sorted(expected_task_ids - set(runs_by_task)):
    missing_task_runs[task_id] = list(range(1, 11))
if missing_task_runs:
    shown = dict(list(sorted(missing_task_runs.items()))[:10])
    issues.append(f"{label}: missing task runs {shown}")

issues.extend(_validate_cost_ledger(records, ledger_path))
cost_report = _cost_accounting_report(records, ledger_path)
ledger_rows = load_jsonl(ledger_path)
reservations = [row for row in ledger_rows if row.get("row_type") == "reservation"]
settlements = [row for row in ledger_rows if row.get("row_type") == "settlement"]
settled_ids = {row.get("reservation_id") for row in settlements}
active_reservations = [
    row for row in reservations
    if row.get("reservation_id") not in settled_ids
]
active_reserved = round(sum(float(row.get("reserved_cost_usd") or 0.0) for row in active_reservations), 6)
settled_total = round(sum(float(row.get("actual_cost_usd") or 0.0) for row in settlements), 6)
remaining_capacity = round(cap - settled_total - active_reserved, 6)

report = {
    "label": label,
    "ok": not issues,
    "condition": condition,
    "records": len(records),
    "expected_records": expected_count,
    "state_counts": dict(state_counts),
    "retry_status_counts": dict(retry_status_counts),
    "cost_accounting": cost_report,
    "ledger_totals": {
        "settled_total_usd": settled_total,
        "active_reservation_count": len(active_reservations),
        "active_reserved_usd": active_reserved,
        "remaining_reservable_capacity_usd": remaining_capacity,
    },
    "issue_count": len(issues),
    "issues": issues[:50],
}
out = root / "analysis" / f"{label}_shard_check.json"
out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(report, indent=2, sort_keys=True))
raise SystemExit(0 if not issues else 1)
PY
  local rc=${pipestatus[1]}
  if [[ "$rc" -ne 0 ]]; then
    echo "SHARD_CHECK_FAILED label=$label rc=$rc"
    exit "$rc"
  fi
}

run_cond_b_main() {
  local -a task_ids
  local remaining
  remaining="$(remaining_task_ids "$V3_ROOT/cond_b_main" "replication_package/v1_main/corpus/main_tasks.jsonl")"
  if [[ -z "$remaining" ]]; then
    task_ids=()
  else
    task_ids=("${(@f)remaining}")
  fi

  if [[ "${#task_ids[@]}" -eq 0 ]]; then
    echo "COND_B_MAIN_ALREADY_COMPLETE"
    return 0
  fi

  printf 'COND_B_MAIN_RESUME_TASK_IDS=%s\n' "${task_ids[*]}"
  caffeinate -dimsu python -m apparatus.run run-cond-b "${task_ids[@]}" \
    --tasks replication_package/v1_main/corpus/main_tasks.jsonl \
    --out "$V3_ROOT/cond_b_main" \
    --llm-backend anthropic \
    --llm-model claude-sonnet-4-6 \
    --runs-per-task 10 \
    --seed 20260623 \
    --max-workers 1 \
    --domain-profile-mode auto \
    --checkpoint-every 1 \
    --skip-existing \
    --cost-ledger "$V3_ROOT/api_cost_ledger.jsonl" \
    --campaign-budget-usd "$FULL_CAMPAIGN_CAP" \
    --preflight-manifest "$LOCAL_PREFLIGHT" \
    --expected-mlt-commit "$MLT_COMMIT" \
    --expected-apparatus-commit "$APP_COMMIT" \
    --require-clean-worktree 2>&1 | tee "$V3_ROOT/logs/cond_b_main_resume_$(date -u +%Y%m%dT%H%M%SZ).log"
  local rc=${pipestatus[1]}
  if [[ "$rc" -ne 0 ]]; then
    echo "COND_B_MAIN_RESUME_FAILED rc=$rc"
    exit "$rc"
  fi
}

run_cond_b_holdout() {
  local -a task_ids
  local remaining
  remaining="$(remaining_task_ids "$V3_ROOT/cond_b_holdout" "replication_package/v1_main/corpus/holdout_tasks.jsonl")"
  if [[ -z "$remaining" ]]; then
    task_ids=()
  else
    task_ids=("${(@f)remaining}")
  fi

  if [[ "${#task_ids[@]}" -eq 0 ]]; then
    echo "COND_B_HOLDOUT_ALREADY_COMPLETE"
    return 0
  fi

  printf 'COND_B_HOLDOUT_RESUME_TASK_IDS=%s\n' "${task_ids[*]}"
  caffeinate -dimsu python -m apparatus.run run-cond-b "${task_ids[@]}" \
    --tasks replication_package/v1_main/corpus/holdout_tasks.jsonl \
    --out "$V3_ROOT/cond_b_holdout" \
    --llm-backend anthropic \
    --llm-model claude-sonnet-4-6 \
    --runs-per-task 10 \
    --seed 20260623 \
    --max-workers 1 \
    --domain-profile-mode auto \
    --checkpoint-every 1 \
    --skip-existing \
    --cost-ledger "$V3_ROOT/api_cost_ledger.jsonl" \
    --campaign-budget-usd "$FULL_CAMPAIGN_CAP" \
    --preflight-manifest "$LOCAL_PREFLIGHT" \
    --expected-mlt-commit "$MLT_COMMIT" \
    --expected-apparatus-commit "$APP_COMMIT" \
    --require-clean-worktree 2>&1 | tee "$V3_ROOT/logs/cond_b_holdout_resume_$(date -u +%Y%m%dT%H%M%SZ).log"
  local rc=${pipestatus[1]}
  if [[ "$rc" -ne 0 ]]; then
    echo "COND_B_HOLDOUT_RESUME_FAILED rc=$rc"
    exit "$rc"
  fi
}

repair_stale_shard_ledgers
pre_resume_checkpoint_gate
if [[ "${RESUME_PREFLIGHT_ONLY:-0}" == "1" ]]; then
  echo "RESUME_PREFLIGHT_ONLY_PASS"
  exit 0
fi

if paid_work_remaining; then
  require_api_key_for_paid_execution
  validate_anthropic_key_for_paid_execution
else
  echo "NO_PAID_WORK_REMAINING"
fi

run_cond_b_main
check_shard "$V3_ROOT/cond_b_main" "cond_b" "replication_package/v1_main/corpus/main_tasks.jsonl" "cond_b_main"

run_cond_b_holdout
check_shard "$V3_ROOT/cond_b_holdout" "cond_b" "replication_package/v1_main/corpus/holdout_tasks.jsonl" "cond_b_holdout"

python -m apparatus.consolidate_rerun \
  --cond-a-shards "$V3_ROOT/cond_a_main" "$V3_ROOT/cond_a_holdout" \
  --cond-b-shards "$V3_ROOT/cond_b_main" "$V3_ROOT/cond_b_holdout" \
  --out-root "$V3_ROOT" \
  --preflight-manifest "$LOCAL_PREFLIGHT" \
  --main-corpus replication_package/v1_main/corpus/main_tasks.jsonl \
  --holdout-corpus replication_package/v1_main/corpus/holdout_tasks.jsonl \
  --expected-mlt-commit "$MLT_COMMIT" \
  --expected-apparatus-commit "$APP_COMMIT" \
  --require-clean-worktree 2>&1 | tee "$V3_ROOT/logs/consolidate_rerun.log"
rc=${pipestatus[1]}
if [[ "$rc" -ne 0 ]]; then
  echo "CONSOLIDATE_FAILED rc=$rc"
  exit "$rc"
fi

python -m apparatus.rerun_analysis \
  --v3-cond-a "$V3_ROOT/cond_a_rerun.jsonl" \
  --v3-cond-b "$V3_ROOT/cond_b_rerun.jsonl" \
  --v1-cond-a-main replication_package/v1_main/system_outputs/cond_a_main.jsonl \
  --v1-cond-a-holdout replication_package/v1_main/system_outputs/cond_a_holdout.jsonl \
  --v1-cond-b-main replication_package/v1_main/system_outputs/cond_b_main.jsonl \
  --v1-cond-b-holdout replication_package/v1_main/system_outputs/cond_b_holdout.jsonl \
  --main-corpus replication_package/v1_main/corpus/main_tasks.jsonl \
  --holdout-corpus replication_package/v1_main/corpus/holdout_tasks.jsonl \
  --cost-ledger "$V3_ROOT/api_cost_ledger.jsonl" \
  --preflight-manifest "$LOCAL_PREFLIGHT" \
  --expected-mlt-commit "$MLT_COMMIT" \
  --expected-apparatus-commit "$APP_COMMIT" \
  --require-clean-worktree \
  --out-json "$V3_ROOT/analysis/final_analysis.json" \
  --out-dir "$V3_ROOT/analysis" 2>&1 | tee "$V3_ROOT/logs/final_analysis.log"
rc=${pipestatus[1]}
if [[ "$rc" -ne 0 ]]; then
  echo "FINAL_ANALYSIS_FAILED rc=$rc"
  exit "$rc"
fi

python - <<'PY'
import os
import re
from pathlib import Path

root = Path(os.environ["V3_ROOT"])
patterns = [
    ("anthropic_key", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}|sk-ant-api|api03")),
    ("api_key_assignment", re.compile(r"(ANTHROPIC_API_KEY|OPENAI_API_KEY)\s*=")),
]
hits = []
for path in sorted(root.rglob("*")):
    if not path.is_file():
        continue
    parts = set(path.parts)
    if "__pycache__" in parts or path.suffix == ".pyc":
        continue
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        continue
    for line_number, line in enumerate(text.splitlines(), start=1):
        matched = [name for name, pattern in patterns if pattern.search(line)]
        if matched:
            hits.append(f"{path}:{line_number}:{','.join(matched)}:<redacted>")
(root / "analysis" / "secret_scan.log").write_text(
    "\n".join(hits) + ("\n" if hits else ""),
    encoding="utf-8",
)
PY

python - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ["V3_ROOT"])
log = root / "analysis" / "secret_scan.log"
text = log.read_text(encoding="utf-8") if log.exists() else ""
report = {
    "ok": text.strip() == "",
    "hit_count": 0 if text.strip() == "" else len(text.splitlines()),
    "log": str(log),
}
(root / "analysis" / "secret_scan_report.json").write_text(
    json.dumps(report, indent=2, sort_keys=True),
    encoding="utf-8",
)
print(json.dumps(report, sort_keys=True))
raise SystemExit(0 if report["ok"] else 1)
PY

python - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ["V3_ROOT"])
analysis = json.loads((root / "analysis" / "final_analysis.json").read_text(encoding="utf-8"))
cost = analysis.get("cost_accounting") or {}
by_condition = analysis.get("by_condition") or {}
summary = {
    "v3_root": str(root),
    "ok": analysis.get("ok"),
    "cond_a_total": (by_condition.get("cond_a") or {}).get("records"),
    "cond_b_total": (by_condition.get("cond_b") or {}).get("records"),
    "primary_denominator_N": analysis.get("primary_denominator_N"),
    "executable_with_blocking_count": analysis.get("executable_with_blocking_count"),
    "settled_total_usd": cost.get("settled_total_usd"),
    "cost_mode": cost.get("mode"),
    "file_hash_inventory": str(root / "provenance" / "file_hashes.sha256"),
}
(root / "analysis" / "full_campaign_summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True),
    encoding="utf-8",
)
print(json.dumps(summary, indent=2, sort_keys=True))
PY

HASH_INVENTORY="$V3_ROOT/provenance/file_hashes.sha256"
HASH_INVENTORY_TMP="$HASH_INVENTORY.tmp.$$"
find "$V3_ROOT" -type f \
  ! -path "$HASH_INVENTORY" \
  ! -path "$HASH_INVENTORY_TMP" \
  -print0 \
  | sort -z \
  | xargs -0 shasum -a 256 > "$HASH_INVENTORY_TMP"
mv "$HASH_INVENTORY_TMP" "$HASH_INVENTORY"
shasum -a 256 -c "$HASH_INVENTORY"

echo "FULL_CAMPAIGN_PASS"
