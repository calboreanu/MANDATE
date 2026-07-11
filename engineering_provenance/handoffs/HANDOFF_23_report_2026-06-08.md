# Handoff 23 Report: Stabilize Ollama and Resume 11b-i

**Codex session:** desktop session
**Eval host:** lattice-ws01
**Date:** 2026-06-08
**Wall clock:** ~15 minutes

## Verdict

HALT

## Stop Point

Handoff 23 passed all seven preconditions after Ollama was restarted, then stopped during Task 1 because the official resume command re-ran existing checkpoint records instead of advancing from record 133.

Observed precondition results:

```text
Ollama API responsive
mandate-* missing: none
Running Ollama healthcheck (real generation call against mandate-intake)...
  healthcheck duration: 2s
  response[:80]: ''
no contention processes detected
checkpoint state: 132/132 clean
no fast-fallback or all-role-fallback contamination detected
AEGIS-eval still at v1 baseline
```

After Task 1 started, the side-channel watchdog saw that total record count stayed at 132 while these already-committed checkpoint files were rewritten:

```text
07_system_outputs/mandate_primary/mandate_primary__TASK-MAIN-FIN-001__r01.json
07_system_outputs/mandate_primary/mandate_primary__TASK-MAIN-FIN-001__r02.json
07_system_outputs/mandate_primary/mandate_primary__TASK-MAIN-FIN-001__r03.json
07_system_outputs/mandate_primary/ledger.jsonl
```

The three overwritten records were real slow Ollama runs, not fast-fallback contaminants, but re-running checkpoint records is outside the handoff boundary. The run was stopped immediately. The four modified files were restored from the committed checkpoint before this report was written.

## Checkpoint State

The existing HANDOFF_11b-i checkpoint is restored and clean:

```text
records: 132
ok: 132
any_llm_fallback: 4
binding_fallback: 4
fast_under_60s: 0
bad_fast_allrole: 0
```

No new records were retained from this handoff.

## Resume Progress

```text
records completed in this resume: 0 retained
target remaining records: 1068
total records now: 132
```

## Watchdog

Watchdog trigger count for fast-fallback contamination: zero.

The watchdog did catch a different stop condition: the resume command rewrote existing run IDs before producing record 133. Because the handoff says not to re-run the 132-record checkpoint, Codex halted rather than allowing the command to continue.

## Ollama / Contention

Ollama was restarted and verified healthy:

```text
curl /api/tags: OK
six mandate-* models present: yes
mandate-intake healthcheck: 2s
```

No `run-system`, `apparatus.run`, or TRACE Phase 8 contention process was active before Task 1 started. The halt was not caused by Ollama health, missing models, or fast fallback.

## Action Queue

- Do not rerun Handoff 23 unchanged. Its Task 1 assumption is false for the current harness.
- The current `apparatus.run run-system` CLI has no `--resume` or `--skip-existing` flag.
- `apparatus/harness/runner.py::run_matrix` iterates every task/run and saves `<run_id>.json` unconditionally; `RunLedger` is append-only but does not act as a resume cursor.
- Issue a corrected resume handoff that runs only the missing `(task_id, run_idx)` tuples, or first add a harness-level skip-existing/resume mode under explicit PI authorization.
- Keep the 132-record checkpoint as the valid baseline for the next resume attempt.

## Deviations from this handoff

- Codex restored the three overwritten checkpoint JSON files and `ledger.jsonl` from the committed checkpoint after stopping Task 1. This preserved the handoff boundary that existing checkpoint records must not be mutated.
- No `AEGIS-eval/` or `04_ground_truth/` files were modified.
