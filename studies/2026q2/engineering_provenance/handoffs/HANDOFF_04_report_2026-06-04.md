# Handoff 04 Report: B4-B6 Phase 4 calibration

**Codex session:** desktop session
**Eval host:** lattice-ws01
**Date:** 2026-06-04
**Wall clock:** ~15 minutes

## Verdict

PROCEED

## Evidence

- calibration tasks found: 6
- systems run: `baseline_4`, `baseline_5`, `baseline_6`
- runs per task: 1
- seed base: 20260604
- model: `claude-sonnet-4-6`

| baseline | records | ok | schema_valid | input_tokens | output_tokens | cost_usd |
|---|---:|---:|---:|---:|---:|---:|
| baseline_4 | 6 | 6 | 6 | 16,137 | 23,421 | 0.399726 |
| baseline_5 | 6 | 6 | 6 | 10,289 | 12,682 | 0.221097 |
| baseline_6 | 6 | 6 | 6 | 17,733 | 13,283 | 0.252444 |
| total | 18 | 18 | 18 | 44,159 | 49,386 | 0.873267 |

## Verification Command

```text
baseline_4: 6 records, 6 ok, 6 schema_valid
baseline_5: 6 records, 6 ok, 6 schema_valid
baseline_6: 6 records, 6 ok, 6 schema_valid
```

## Output Locations

- `07_system_outputs/baseline_4/`
- `07_system_outputs/baseline_5/`
- `07_system_outputs/baseline_6/`

Each directory contains six RunRecord JSON files plus `ledger.jsonl`.

## Anything the PI must decide before proceeding

- Whether to freeze B4-B6 calibration settings as the Phase 4 baseline configuration for downstream Phase 6 runs.

## Deviations

- None from the handoff success criteria. The apparatus records aggregate token usage/cost per RunRecord in `model_versions` and `api_cost_usd`; per-agent entries in `role_timings` record role name and timing but do not serialize per-agent token counts separately.
