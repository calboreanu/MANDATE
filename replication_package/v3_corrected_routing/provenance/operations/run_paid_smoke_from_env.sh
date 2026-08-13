#!/usr/bin/env zsh
set -euo pipefail

if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  printf "Temporary Anthropic API key: " >&2
  stty -echo
  IFS= read -r ANTHROPIC_API_KEY
  stty echo
  printf "\n" >&2
  export ANTHROPIC_API_KEY
fi
trap 'unset ANTHROPIC_API_KEY' EXIT

cd /Users/ws01admin/Desktop/mandate-eval-v3-local-exec
. .venv-rerun/bin/activate

export PYTHONPATH="/Users/ws01admin/Desktop/mandate-eval-v3-local-exec/code:/Users/ws01admin/Desktop/MLT-Governance-Stack-v3-local-exec/src"
export MLT_ROOT="/Users/ws01admin/Desktop/MLT-Governance-Stack-v3-local-exec"
export MLT_COMMIT="$(git -C "$MLT_ROOT" rev-parse HEAD)"
export APP_COMMIT="$(git rev-parse HEAD)"
export LOCAL_PREFLIGHT="/Users/ws01admin/Desktop/mandate-eval-v3-local-exec/work/v3_preflight_local/preflight_manifest.json"
export SMOKE_ROOT="/Users/ws01admin/Desktop/mandate-eval-v3-local-exec/work/v3_corrected_routing_smoke_local_$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$SMOKE_ROOT/cond_a" "$SMOKE_ROOT/cond_b" "$SMOKE_ROOT/analysis" "$SMOKE_ROOT/logs"
printf '{"smoke_root":"%s","mlt_commit":"%s","apparatus_commit":"%s","preflight_manifest":"%s"}\n' \
  "$SMOKE_ROOT" "$MLT_COMMIT" "$APP_COMMIT" "$LOCAL_PREFLIGHT" > "$SMOKE_ROOT/smoke_run_context.json"

{
  echo "SMOKE_ROOT=$SMOKE_ROOT"
  echo "MLT_COMMIT=$MLT_COMMIT"
  echo "APP_COMMIT=$APP_COMMIT"
  date -u +%Y-%m-%dT%H:%M:%SZ
} | tee "$SMOKE_ROOT/logs/smoke_start.log"

caffeinate -dimsu python -m apparatus.run run-cond-a \
  TASK-MAIN-FIN-001 \
  --tasks replication_package/v1_main/corpus/main_tasks.jsonl \
  --out "$SMOKE_ROOT/cond_a" \
  --extraction-model claude-sonnet-4-6 \
  --runs-per-task 1 \
  --seed 20260623 \
  --max-workers 1 \
  --domain-profile-mode default \
  --checkpoint-every 1 \
  --cost-ledger "$SMOKE_ROOT/api_cost_ledger.jsonl" \
  --campaign-budget-usd 1.00 \
  --preflight-manifest "$LOCAL_PREFLIGHT" \
  --expected-mlt-commit "$MLT_COMMIT" \
  --expected-apparatus-commit "$APP_COMMIT" \
  --require-clean-worktree 2>&1 | tee "$SMOKE_ROOT/logs/cond_a_paid_smoke.log"
rc=${pipestatus[1]}
if [[ "$rc" -ne 0 ]]; then
  echo "COND_A_SMOKE_FAILED rc=$rc"
  exit "$rc"
fi

caffeinate -dimsu python -m apparatus.run run-cond-b \
  TASK-MAIN-FIN-001 \
  --tasks replication_package/v1_main/corpus/main_tasks.jsonl \
  --out "$SMOKE_ROOT/cond_b" \
  --llm-backend anthropic \
  --llm-model claude-sonnet-4-6 \
  --runs-per-task 1 \
  --seed 20260623 \
  --max-workers 1 \
  --domain-profile-mode auto \
  --checkpoint-every 1 \
  --cost-ledger "$SMOKE_ROOT/api_cost_ledger.jsonl" \
  --campaign-budget-usd 1.00 \
  --preflight-manifest "$LOCAL_PREFLIGHT" \
  --expected-mlt-commit "$MLT_COMMIT" \
  --expected-apparatus-commit "$APP_COMMIT" \
  --require-clean-worktree 2>&1 | tee "$SMOKE_ROOT/logs/cond_b_paid_smoke.log"
rc=${pipestatus[1]}
if [[ "$rc" -ne 0 ]]; then
  echo "COND_B_SMOKE_FAILED rc=$rc"
  exit "$rc"
fi

python -m apparatus.rerun_analysis \
  --smoke \
  --v3-cond-a "$SMOKE_ROOT/cond_a" \
  --v3-cond-b "$SMOKE_ROOT/cond_b" \
  --main-corpus replication_package/v1_main/corpus/main_tasks.jsonl \
  --holdout-corpus replication_package/v1_main/corpus/holdout_tasks.jsonl \
  --cost-ledger "$SMOKE_ROOT/api_cost_ledger.jsonl" \
  --preflight-manifest "$LOCAL_PREFLIGHT" \
  --expected-mlt-commit "$MLT_COMMIT" \
  --expected-apparatus-commit "$APP_COMMIT" \
  --require-clean-worktree \
  --out-json "$SMOKE_ROOT/analysis/smoke_analysis.json" \
  --out-dir "$SMOKE_ROOT/analysis" 2>&1 | tee "$SMOKE_ROOT/logs/smoke_analysis.log"
rc=${pipestatus[1]}
if [[ "$rc" -ne 0 ]]; then
  echo "SMOKE_ANALYSIS_FAILED rc=$rc"
  exit "$rc"
fi

(
  rg -n --hidden --glob '!*.pyc' --glob '!__pycache__/**' --glob '!.venv-rerun/**' \
    'sk-ant-[A-Za-z0-9_-]{20,}|sk-ant-api|api03|ANTHROPIC_API_KEY\s*=|OPENAI_API_KEY\s*=' \
    "$SMOKE_ROOT" > "$SMOKE_ROOT/analysis/secret_scan.log"
) || true

python - <<'PY'
import json, os
from pathlib import Path
root = Path(os.environ["SMOKE_ROOT"])
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
import json, os
from pathlib import Path
root = Path(os.environ["SMOKE_ROOT"])
analysis = json.loads((root / "analysis" / "smoke_analysis.json").read_text(encoding="utf-8"))
print(json.dumps({
    "smoke_root": str(root),
    "ok": analysis.get("ok"),
    "total_records": analysis.get("total_records"),
    "N": analysis.get("primary_denominator_N"),
    "executable_with_blocking_count": analysis.get("executable_with_blocking_count"),
    "settled_total_usd": (analysis.get("cost_accounting") or {}).get("settled_total_usd"),
}, indent=2, sort_keys=True))
PY

unset ANTHROPIC_API_KEY
echo "PAID_SMOKE_PASS"
