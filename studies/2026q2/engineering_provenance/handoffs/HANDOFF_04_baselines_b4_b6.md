# Codex Handoff 04: B4-B6 Multi-Agent Baseline Calibration (Phase 4)

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-03
**Estimated wall clock:** 30 to 60 minutes per baseline (Phase 4 budgets 3 days each for full calibration; this handoff does the apparatus-side smoke).
**Blocked on:** `corpus_freeze_v1`, the six calibration tasks under `02_calibration/`, Cal's model decision (Decisions memo Section 4, default `claude-sonnet-4-6`).

## Mission

Calibrate B4 (PlannerReviewer / AutoGen shape), B5 (SequentialCrew / CrewAI shape), B6 (GraphRevision / LangGraph shape) on the six calibration tasks. Calibration confirms each baseline runs end to end against a live key, produces baseline-schema outputs that validate, and records the per-agent token usage and cost.

**Definition of done.** 18 `RunRecord` JSON files (3 baselines x 6 tasks x 1 run) under `07_system_outputs/baseline_4|5|6/`, every record `ok=True`, every output `schema_valid=True`, plus one handoff report.

## Tasks

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

for B in baseline_4 baseline_5 baseline_6; do
  python3 -m apparatus.run run-system \
    --system $B \
    --tasks 02_calibration/tasks \
    --runs 1 \
    --output 07_system_outputs/$B \
    --seed-base 20260604
done

python3 -c "
import json, glob
for b in ('baseline_4','baseline_5','baseline_6'):
    files = sorted(glob.glob(f'07_system_outputs/{b}/*.json'))
    rows = [json.load(open(p)) for p in files]
    ok = sum(1 for r in rows if r['ok'])
    sv = sum(1 for r in rows if (r.get('output') or {}).get('schema_valid'))
    print('%s: %d records, %d ok, %d schema_valid' % (b, len(rows), ok, sv))
"
```

## Report

`handoffs/HANDOFF_04_report_<YYYY-MM-DD>.md` with per-baseline counts, schema-validity rates, Anthropic cost, and PROCEED or HALT verdict. Commit with `Handoff 04: B4-B6 Phase 4 calibration (apparatus-shell, claude-sonnet-4-6)`.
