# Handoff 25 Report: Resume 11b-i with Refined Watchdog

**Codex session:** desktop session
**Eval host:** lattice-ws01
**Date:** 2026-06-10
**Wall clock:** ~2.1 hours for the resume command after restore

## Verdict

PROCEED

## Summary

Handoff 25 completed successfully. The two quarantined `TASK-MAIN-SEC-038` records were restored as legitimate Intake failures, the `run-system --skip-existing` resume skipped 1134 existing records, executed 66 new records, and reached the 1200-record MANDATE-primary main target.

The refined watchdog found no Ollama-crash contamination:

```text
records: 1200
contamination (all-roles-fb, fast):   0
fast legitimate (single-role fail):   20
unreadable JSON:                       0
```

## Preconditions

Preconditions passed before this resume:

```text
--skip-existing flag present
7 harness tests passed
Ollama reachable
mandate-intake healthcheck completed
checkpoint: 1132/1132 ok
quarantine has 2 SEC-038 records ready to restore
AEGIS-eval still at v1
```

The project was run from the physical Desktop path:

```text
/Users/ws01admin/Desktop/Desktop - lattice-ws01/MANDATE Evaluation/mandate_eval_2026Q2
```

## Restored Records

Records restored from quarantine: 2.

Both restored records were verified as Intake-LLM failures, not all-role fallback contamination:

```text
mandate_primary__TASK-MAIN-SEC-038__r01.json
  wall_clock_ms: 10959
  intake.llm_used: True
  all_roles_fb: False
  ok: False

mandate_primary__TASK-MAIN-SEC-038__r02.json
  wall_clock_ms: 8301
  intake.llm_used: True
  all_roles_fb: False
  ok: False
```

After restore: 1134 records.

## Resume Execution

Observed resume result:

```text
skipped 1134 existing records
executed 66 new records
wrote 1200 RunRecords to 07_system_outputs/mandate_primary
```

Records executed this resume: 66.

Total records at end: 1200.

## Watchdog

Refined-rule trigger count: 0.

The refined watchdog halted only on the Ollama-crash signature: `wall_clock_ms < 60_000` and all roles `llm_used=False`. No records matched that signature. The 20 fast records all had at least one role use the LLM and are retained as Phase 6 data.

Fast legitimate records by task:

```text
TASK-MAIN-SEC-038: 10
TASK-MAIN-SEC-040: 10
```

## Final Summary

```text
records: 1200 (target 1200)
ok: 1180/1200

Intake-failure records by task_id:
  TASK-MAIN-SEC-038: 10 runs failed in Intake
  TASK-MAIN-SEC-040: 10 runs failed in Intake
```

Per-domain summary:

```text
=== financial_reporting (400 records) ===
  ok rate:                400/400  (100.0%)
  Intake failures:        0/400  (0.0%)
  any_llm_fallback:       18/400  (4.5%)
  Binding refusal:        8/400  (2.0%)
  COA count distribution: {1: 400}
  Interpreter modes:      clean=258, det_prefix=142
  Validator gap-flagged:  77/400  (19.2%)

=== intelligence_collection_tasking (400 records) ===
  ok rate:                400/400  (100.0%)
  Intake failures:        0/400  (0.0%)
  any_llm_fallback:       161/400  (40.2%)
  Binding refusal:        161/400  (40.2%)
  COA count distribution: {1: 400}
  Interpreter modes:      clean=224, det_prefix=176
  Validator gap-flagged:  56/400  (14.0%)

=== security_operations_reporting (400 records) ===
  ok rate:                380/400  (95.0%)
  Intake failures:        20/400  (5.0%)
  any_llm_fallback:       54/400  (13.5%)
  Binding refusal:        54/400  (13.5%)
  COA count distribution: {1: 380, 0: 20}
  Interpreter modes:      clean=310, det_prefix=90
  Validator gap-flagged:  77/400  (19.2%)
```

## Deviations / Notes

- The shell command for Task 1 was adjusted to export `QUAR` before the first Python snippet, preserving the handoff's intent.
- The Task 4 Intake-failure classifier was adjusted for v1 RunRecord shape: failed role timings use `status="failed"` rather than `status="fail"`. The affected records were classified as Intake failures based on `ok=False`, `task_id` in `{TASK-MAIN-SEC-038, TASK-MAIN-SEC-040}`, and role timing with `role_name="Intake"`, `llm_used=True`, `llm_fallback=False`.
- No `AEGIS-eval/` or `04_ground_truth/` files were modified.
- Pre-existing unrelated worktree changes, including `rag/embeddings/*`, were not staged.

## Next Target

After this PROCEED, the next queued handoff is HANDOFF_11b-ii: baselines + hold-out + anonymize + `outputs_freeze_v1`.
