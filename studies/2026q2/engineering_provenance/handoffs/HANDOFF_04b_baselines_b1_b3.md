# Codex Handoff 04b: B1-B3 Single-Agent Baseline Calibration (Phase 4)

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-04
**Estimated wall clock:** 20 to 40 minutes total (six tasks × three baselines × one run).
**Blocked on:** `ANTHROPIC_API_KEY` set (long-standing), `OPENAI_API_KEY` set (added 2026-06-04, was the blocker for B2). Six calibration tasks under `02_calibration/tasks/` (already present per HANDOFF_04 PROCEED).

## Mission

Calibrate the three single-agent baselines on the same six calibration tasks HANDOFF_04 used:

- B1: single-prompt Claude Sonnet 4.6, no RAG, no role decomposition (the protocol's `baseline_1`).
- B2: single-prompt GPT, default model per the Decisions memo Section 4 (the protocol's `baseline_2`).
- B3: ReAct loop on Claude (the protocol's `baseline_3`).

Calibration confirms each baseline runs end to end against a live key, produces baseline-schema outputs that validate, and records per-call token usage and cost. Mirrors HANDOFF_04's shape exactly; only the system names change.

**Definition of done.** 18 RunRecord JSON files (3 baselines × 6 tasks × 1 run) under `07_system_outputs/baseline_{1,2,3}/`, every record `ok=True`, every output `schema_valid=True`, plus one handoff report.

## Preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

python3 -c "
import os
from pathlib import Path
for line in Path('.env').read_text().splitlines():
    if '=' in line:
        k, v = line.split('=', 1); os.environ[k] = v
assert os.environ.get('ANTHROPIC_API_KEY','').startswith('sk-ant'), 'Anthropic key missing'
assert os.environ.get('OPENAI_API_KEY','').startswith('sk-'), 'OpenAI key missing'
print('both keys set')
"

ls 02_calibration/tasks/ | head -10
```

**Success criteria.** Both keys set; six calibration task files present.

**On HALT.** If `OPENAI_API_KEY` is empty, do NOT skip B2 silently. Stop and report. B2 calibration is a precondition for the B2 row in Phase 6's main run.

## Tasks

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

for B in baseline_1 baseline_2 baseline_3; do
  python3 -m apparatus.run run-system \
    --system $B \
    --tasks 02_calibration/tasks \
    --runs 1 \
    --output 07_system_outputs/$B \
    --seed-base 20260604
done

python3 -c "
import json, glob
for b in ('baseline_1','baseline_2','baseline_3'):
    files = sorted(glob.glob(f'07_system_outputs/{b}/*.json'))
    rows = [json.load(open(p)) for p in files]
    ok = sum(1 for r in rows if r['ok'])
    sv = sum(1 for r in rows if (r.get('output') or {}).get('schema_valid'))
    cost = sum((r.get('api_cost_usd') or 0) for r in rows)
    in_tok = sum((r.get('tokens_input') or 0) for r in rows)
    out_tok = sum((r.get('tokens_output') or 0) for r in rows)
    print('%s: %d records, %d ok, %d schema_valid, %d in / %d out tokens, \$%.4f'
          % (b, len(rows), ok, sv, in_tok, out_tok, cost))
"
```

## Decision boundary

You may decide:
- A single retry on a transient API rate-limit error per task per baseline.
- Adding a `--seed-base` override only if a re-run is needed; default 20260604.

You must escalate:
- Any baseline emitting `ok=False` or `schema_valid=False` on more than one of the six tasks.
- A persistent OpenAI auth failure on B2 that does not clear on one retry (the key was newly added; first-call auth issues are reportable but should clear on retry).
- Total Anthropic + OpenAI cost above $10 for the calibration — that signals a misconfigured model size or runaway tokens.

You may not:
- Modify the six calibration task files.
- Change the seed.
- Reuse the prior HANDOFF_04 outputs at `07_system_outputs/baseline_{4,5,6}/`.

## Report

`handoffs/HANDOFF_04b_report_<YYYY-MM-DD>.md` with per-baseline counts, schema-validity rates, total Anthropic cost, total OpenAI cost, B2 first-call auth check result, PROCEED or HALT verdict. Commit with `Handoff 04b: B1-B3 Phase 4 calibration (apparatus-shell)`.
