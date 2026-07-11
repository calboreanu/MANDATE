# Handoff 24 Report: Resume 11b-i with --skip-existing

**Codex session:** desktop session
**Eval host:** lattice-ws01
**Date:** 2026-06-08
**Wall clock:** ~30 minutes

## Verdict

HALT

## Stop Point

Handoff 24 passed all preconditions, verified the new `--skip-existing` apparatus support, and began Task 1. The watchdog halted during Task 1 after detecting one new record with `wall_clock_ms < 60_000`.

The triggering record was:

```text
07_system_outputs/mandate_primary/mandate_primary__TASK-MAIN-FIN-015__r07.json
task_id: TASK-MAIN-FIN-015
wall_clock_ms: 42910.3458
ok: False
any_llm_fallback: False
fallback_roles: []
errors: ['Procedure: Unhandled exception: index file does not exist: /Users/ws01admin/Desktop/MANDATE Evaluation/mandate_eval_2026Q2/AEGIS-eval/rag/embeddings/enterprise-attack.jsonl']
```

This was not an all-role fallback contamination event. The root cause was an infrastructure/path remap during the run: the project path changed from:

```text
/Users/ws01admin/Desktop/MANDATE Evaluation/mandate_eval_2026Q2
```

to:

```text
/Users/ws01admin/Desktop/Desktop - lattice-ws01/MANDATE Evaluation/mandate_eval_2026Q2
```

The missing index exists at the new path:

```text
/Users/ws01admin/Desktop/Desktop - lattice-ws01/MANDATE Evaluation/mandate_eval_2026Q2/AEGIS-eval/rag/embeddings/enterprise-attack.jsonl
```

The in-flight run still held the old absolute AEGIS path, so Procedure failed quickly when it tried to open the RAG index.

## Preconditions

All HANDOFF_24 preconditions passed:

```text
--skip-existing flag present
2 passed in 0.01s
all six mandate-* models loaded
healthcheck response: ''
healthcheck completed in 3s
checkpoint: 132/132 ok, 0 contamination
no contention processes detected
AEGIS-eval still at v1 baseline
```

The apparatus resume patch was committed before this handoff run:

```text
a813481 Patch apparatus resume support for --skip-existing
```

## Skip-Existing Verification

Target startup skip count: 132.

Observed startup skip count: 132.

The run-system console stream did not flush its `SKIP (existing)` lines before the halt, but the side-channel state confirmed the skip behavior:

```text
JSON records before first new run: 132
ledger lines after skip phase: 264
checkpoint JSON files rewritten: 0
```

That is exactly the 132 existing records loaded through `--skip-existing`, with no checkpoint output files re-executed or overwritten.

## Resume Progress

```text
records skipped at startup: 132
records attempted after skip phase: 15
records retained from this attempt: 0
target remaining records: 1068
total records now after cleanup: 132
```

The 15 attempted new records were quarantined outside the repository at:

```text
/tmp/handoff24_quarantine_20260608/
```

The project output directory and ledger were restored to the last committed 132-record checkpoint:

```text
records: 132
ok: 132
fast_under_60s: 0
bad_fast_allrole: 0
ledger_lines: 132
```

No contaminated or partial Phase 6 output records were committed.

## Watchdog

Watchdog trigger count: 1.

The trigger was the `TASK-MAIN-FIN-015 r07` record above. The watchdog killed `run-system` immediately and no checkpoint commit was made.

## Ollama / Contention

Ollama was started once for this handoff and passed the real generation healthcheck. No TRACE Phase 8, `run-system`, or competing `apparatus.run` process was active at precondition time.

Ollama did not disappear; the halt was caused by the project path remap invalidating the old absolute AEGIS path inside the in-flight process.

## Action Queue

- Do not rerun from the old root path. The old path no longer exists.
- Re-issue the resume from the current root:

```text
/Users/ws01admin/Desktop/Desktop - lattice-ws01/MANDATE Evaluation/mandate_eval_2026Q2
```

- Alternatively, restore a stable symlink at the old canonical path before rerunning:

```text
/Users/ws01admin/Desktop/MANDATE Evaluation/mandate_eval_2026Q2
```

- Keep `--skip-existing`; the apparatus resume patch worked and skipped exactly 132 records.
- Keep the watchdog unchanged; it caught the path-remap failure before the contaminated record could be committed.

## Deviations from this handoff

- Codex used side-channel ledger/output counts to verify the 132 skipped records because the Python console stream was buffered and did not flush the `SKIP (existing)` lines before the halt.
- Codex quarantined the 15 attempted new records outside the repository and restored the output directory to the last committed 132-record checkpoint to preserve the Phase 6 data boundary.
- No `AEGIS-eval/` or `04_ground_truth/` files were modified.
