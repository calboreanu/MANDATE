#!/usr/bin/env zsh
set -euo pipefail

cleanup() {
  unset ANTHROPIC_API_KEY
  stty echo 2>/dev/null || true
}
trap cleanup EXIT

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

export EVAL_ROOT="/Users/ws01admin/Desktop/mandate-eval-v3-local-exec"
export MLT_ROOT="/Users/ws01admin/Desktop/MLT-Governance-Stack-v3-local-exec"
cd "$EVAL_ROOT"
. .venv-rerun/bin/activate

export PYTHONPATH="$EVAL_ROOT/code:$MLT_ROOT/src"
export MLT_COMMIT="$(git -C "$MLT_ROOT" rev-parse HEAD)"
export APP_COMMIT="$(git rev-parse HEAD)"
export LOCAL_PREFLIGHT="$EVAL_ROOT/work/v3_preflight_local/preflight_manifest.json"
export LOCAL_PREFLIGHT_SHA256="$(shasum -a 256 "$LOCAL_PREFLIGHT" | awk '{print $1}')"
export FULL_CAMPAIGN_CAP="299.250033"
export PRIOR_RECORDED_SMOKE_PROBE_USD="0.123435"
export FAILED_SMOKE_USD="0.517674"
export REPLACEMENT_SMOKE_USD="0.108858"
export PRE_CAMPAIGN_SPEND_USD="0.749967"
export V3_ROOT="$EVAL_ROOT/replication_package/v3_corrected_routing_$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p \
  "$V3_ROOT/cond_a_main" \
  "$V3_ROOT/cond_a_holdout" \
  "$V3_ROOT/cond_b_main" \
  "$V3_ROOT/cond_b_holdout" \
  "$V3_ROOT/logs" \
  "$V3_ROOT/analysis" \
  "$V3_ROOT/provenance"

python - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ["V3_ROOT"])
manifest = {
    "campaign_root": str(root),
    "created_utc": os.popen("date -u +%Y-%m-%dT%H:%M:%SZ").read().strip(),
    "mlt_commit": os.environ["MLT_COMMIT"],
    "apparatus_commit": os.environ["APP_COMMIT"],
    "preflight_manifest": os.environ["LOCAL_PREFLIGHT"],
    "preflight_manifest_sha256": os.environ["LOCAL_PREFLIGHT_SHA256"],
    "authorization_usd": {
        "total_authorized": 300.000000,
        "prior_recorded_smoke_probe": float(os.environ["PRIOR_RECORDED_SMOKE_PROBE_USD"]),
        "failed_invalid_key_smoke_conservative": {
            "root": "work/v3_corrected_routing_smoke_local_20260806T225847Z",
            "usd": float(os.environ["FAILED_SMOKE_USD"]),
            "basis": "conservative_settled_bound",
        },
        "replacement_paid_smoke_exact": {
            "root": "work/v3_corrected_routing_smoke_local_20260806T225913Z",
            "usd": float(os.environ["REPLACEMENT_SMOKE_USD"]),
            "basis": "exact_authoritative_response",
        },
        "pre_campaign_spend_total": float(os.environ["PRE_CAMPAIGN_SPEND_USD"]),
        "full_campaign_cap": float(os.environ["FULL_CAMPAIGN_CAP"]),
    },
    "run_parameters": {
        "model": "claude-sonnet-4-6",
        "seed_base": 20260623,
        "runs_per_task": 10,
        "recorded_seeds": list(range(20260624, 20260634)),
        "max_workers": 1,
        "shared_cost_ledger": str(root / "api_cost_ledger.jsonl"),
    },
}
(root / "provenance" / "campaign_budget_manifest.json").write_text(
    json.dumps(manifest, indent=2, sort_keys=True),
    encoding="utf-8",
)
print(json.dumps({
    "campaign_root": str(root),
    "full_campaign_cap": manifest["authorization_usd"]["full_campaign_cap"],
    "pre_campaign_spend_total": manifest["authorization_usd"]["pre_campaign_spend_total"],
}, indent=2, sort_keys=True))
PY

{
  echo "V3_ROOT=$V3_ROOT"
  echo "MLT_COMMIT=$MLT_COMMIT"
  echo "APP_COMMIT=$APP_COMMIT"
  echo "LOCAL_PREFLIGHT=$LOCAL_PREFLIGHT"
  echo "LOCAL_PREFLIGHT_SHA256=$LOCAL_PREFLIGHT_SHA256"
  echo "FULL_CAMPAIGN_CAP=$FULL_CAMPAIGN_CAP"
  date -u +%Y-%m-%dT%H:%M:%SZ
} | tee "$V3_ROOT/logs/full_campaign_start.log"

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
seeds_by_task = defaultdict(set)
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
        seeds_by_task[task_id].add(seed)

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

ledger_issues = _validate_cost_ledger(records, ledger_path)
issues.extend(ledger_issues)
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

run_cond_a_main() {
  caffeinate -dimsu python -m apparatus.run run-cond-a --all \
    --tasks replication_package/v1_main/corpus/main_tasks.jsonl \
    --out "$V3_ROOT/cond_a_main" \
    --extraction-model claude-sonnet-4-6 \
    --runs-per-task 10 \
    --seed 20260623 \
    --max-workers 1 \
    --domain-profile-mode default \
    --checkpoint-every 1 \
    --skip-existing \
    --cost-ledger "$V3_ROOT/api_cost_ledger.jsonl" \
    --campaign-budget-usd "$FULL_CAMPAIGN_CAP" \
    --preflight-manifest "$LOCAL_PREFLIGHT" \
    --expected-mlt-commit "$MLT_COMMIT" \
    --expected-apparatus-commit "$APP_COMMIT" \
    --require-clean-worktree 2>&1 | tee "$V3_ROOT/logs/cond_a_main.log"
  local rc=${pipestatus[1]}
  if [[ "$rc" -ne 0 ]]; then
    echo "COND_A_MAIN_FAILED rc=$rc"
    exit "$rc"
  fi
}

run_cond_a_holdout() {
  caffeinate -dimsu python -m apparatus.run run-cond-a --all \
    --tasks replication_package/v1_main/corpus/holdout_tasks.jsonl \
    --out "$V3_ROOT/cond_a_holdout" \
    --extraction-model claude-sonnet-4-6 \
    --runs-per-task 10 \
    --seed 20260623 \
    --max-workers 1 \
    --domain-profile-mode default \
    --checkpoint-every 1 \
    --skip-existing \
    --cost-ledger "$V3_ROOT/api_cost_ledger.jsonl" \
    --campaign-budget-usd "$FULL_CAMPAIGN_CAP" \
    --preflight-manifest "$LOCAL_PREFLIGHT" \
    --expected-mlt-commit "$MLT_COMMIT" \
    --expected-apparatus-commit "$APP_COMMIT" \
    --require-clean-worktree 2>&1 | tee "$V3_ROOT/logs/cond_a_holdout.log"
  local rc=${pipestatus[1]}
  if [[ "$rc" -ne 0 ]]; then
    echo "COND_A_HOLDOUT_FAILED rc=$rc"
    exit "$rc"
  fi
}

run_cond_b_main() {
  caffeinate -dimsu python -m apparatus.run run-cond-b --all \
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
    --require-clean-worktree 2>&1 | tee "$V3_ROOT/logs/cond_b_main.log"
  local rc=${pipestatus[1]}
  if [[ "$rc" -ne 0 ]]; then
    echo "COND_B_MAIN_FAILED rc=$rc"
    exit "$rc"
  fi
}

run_cond_b_holdout() {
  caffeinate -dimsu python -m apparatus.run run-cond-b --all \
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
    --require-clean-worktree 2>&1 | tee "$V3_ROOT/logs/cond_b_holdout.log"
  local rc=${pipestatus[1]}
  if [[ "$rc" -ne 0 ]]; then
    echo "COND_B_HOLDOUT_FAILED rc=$rc"
    exit "$rc"
  fi
}

run_cond_a_main
check_shard "$V3_ROOT/cond_a_main" "cond_a" "replication_package/v1_main/corpus/main_tasks.jsonl" "cond_a_main"

run_cond_a_holdout
check_shard "$V3_ROOT/cond_a_holdout" "cond_a" "replication_package/v1_main/corpus/holdout_tasks.jsonl" "cond_a_holdout"

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

(
  rg -n --hidden --glob '!*.pyc' --glob '!__pycache__/**' --glob '!.venv-rerun/**' \
    'sk-ant-[A-Za-z0-9_-]{20,}|sk-ant-api|api03|ANTHROPIC_API_KEY\s*=|OPENAI_API_KEY\s*=' \
    "$V3_ROOT" > "$V3_ROOT/analysis/secret_scan.log"
) || true

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

find "$V3_ROOT" -type f -print0 | sort -z | xargs -0 shasum -a 256 > "$V3_ROOT/provenance/file_hashes.sha256"

python - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ["V3_ROOT"])
analysis = json.loads((root / "analysis" / "final_analysis.json").read_text(encoding="utf-8"))
cost = analysis.get("cost_accounting") or {}
summary = {
    "v3_root": str(root),
    "ok": analysis.get("ok"),
    "cond_a_total": analysis.get("cond_a_total"),
    "cond_b_total": analysis.get("cond_b_total"),
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

echo "FULL_CAMPAIGN_PASS"
