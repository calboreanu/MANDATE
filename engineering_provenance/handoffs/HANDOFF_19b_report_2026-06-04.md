# Handoff 19b Report: Materialize selections + cut freeze tags

**Codex session:** desktop session
**Eval host:** lattice-ws01
**Date:** 2026-06-04
**Wall clock:** <1 minute

## Verdict

PROCEED

## Evidence

- Materialized pilot task count: 6
- Materialized main task count: 120
- Materialized holdout task count: 30
- Selection entries that failed to resolve: 0
- Materialization commit: `05fc0aa87baed57d2c1a5ad62f14f02028eaaf3e`
- `corpus_freeze_v1` annotated tag hash: `de4417dfaef4d6748d164bc31764b8d3180f5836`
- `corpus_freeze_v1` peeled commit: `05fc0aa87baed57d2c1a5ad62f14f02028eaaf3e`
- `baseline_freeze_v1` annotated tag hash: `0fb2eff9be3b3f5f911db38532c9b1010f8b2d39`
- `baseline_freeze_v1` peeled commit: `05fc0aa87baed57d2c1a5ad62f14f02028eaaf3e`
- `gt_freeze_v1`: not cut by this handoff

## Output Locations

- `04_ground_truth/pilot_tasks.jsonl`
- `04_ground_truth/main_tasks.jsonl`
- `04_ground_truth/holdout_tasks.jsonl`

## Anything the PI must decide before proceeding

- None for Handoff 19b. `corpus_freeze_v1` and `baseline_freeze_v1` are now present and both point at the materialization commit.

## Deviations from this handoff

- None.
