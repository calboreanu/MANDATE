# Handoff 11b-i Report: Phase 6 MANDATE-primary Main

**Codex session:** desktop session
**Eval host:** lattice-ws01
**Date:** 2026-06-05
**Wall clock:** ~several hours including checkpointing, Ollama restart attempts, and cleanup

## Verdict

HALT

## Run State

Handoff 11b-i did not reach the 1200-record definition of done.

Clean committed output state:

```text
07_system_outputs/mandate_primary/
records: 132
ok: 132
bad_fast_allrole: 0
```

Checkpoint commits:

```text
8b5944c  Handoff 11b-i checkpoint: MANDATE-primary main 100 records
1fa2e4b  Handoff 11b-i checkpoint: MANDATE-primary main 132 records after interruption
```

The clean committed records cover the beginning of the financial-reporting portion of the main corpus, through:

```text
last clean file: 07_system_outputs/mandate_primary/mandate_primary__TASK-MAIN-FIN-014__r02.json
```

## Precondition Results

All five handoff preconditions passed before Task 1 started:

- Freeze tetrad present.
- HANDOFF_11a MANDATE-primary pilot smoke records present.
- `04_ground_truth/main_tasks.jsonl` present with 120 lines.
- `AEGIS-eval/` verified at `mandate-eval-primary-2026q2-v1`; `binding.py` present with no v2 patch marker.
- `llm_rag_index` on production MITRE ATT&CK: `rag/embeddings/enterprise-attack.jsonl`.
- Initial Ollama model check passed for all six `mandate-*` role models.

## Task 1 Outcome

Task 1 started with the handoff command:

```text
python3 -m apparatus.run run-system --system mandate_primary --aegis ./AEGIS-eval --ollama-mode --code-ref mandate-eval-primary-2026q2-v1 --tasks 04_ground_truth/main_tasks.jsonl --runs 10 --output 07_system_outputs/mandate_primary --seed-base 20260605
```

The initial official CLI run produced 132 clean records before the runner process exited unexpectedly. All 132 records were `ok=True`; none were apparatus failures.

When resuming, Ollama was no longer serving:

```text
curl: (7) Failed to connect to localhost port 11434
```

Bad resume attempts produced fast all-role fallback records with role fallback reasons of the form:

```text
Ollama backend failed after N attempt(s): Ollama connection error: [Errno 61] Connection refused
```

Those uncommitted invalid fallback-only records were removed, and `ledger.jsonl` was restored to the last clean committed checkpoint. Final verification found zero fast all-role-fallback records in the output directory.

## Partial Demo-finding Observations

These observations are **partial only** and should not be treated as the Handoff 11b-i result:

```text
records: 132
ok: 132
fallback_runs: 4
fallback_roles: {'Binding': 4}
COA count distribution: {1: 132}
Interpreter modes: {'deterministic_prefix': 75, 'clean_distillation': 57}
Validator gap-flagged: 18
average wall clock: 117.8s
max wall clock: 229.7s
```

All 132 clean records are financial-domain records because the task file is ordered and the run stopped early.

## Escalation / Action Queue

- Stabilize Ollama before resuming Handoff 11b-i. The server disappeared during the long run, and subsequent generation attempts returned connection refused.
- Confirm the eval host is quiescent for Metal/Ollama work before resuming. During diagnosis, an unrelated long-running process was visible:

```text
/Users/ws01admin/Desktop/TRACE Evaluation/workstream_b/run_harness/phase8_exclusive_metal_driver.py
```

- After Ollama stability is confirmed, resume from the 132-record checkpoint. Do not use any outputs from the removed fast all-role-fallback attempts.

## Deviations from this handoff

- Incremental checkpoint commits were made at 100 records and 132 records, as allowed by the handoff.
- After the initial runner interruption, I attempted a skip-existing resume to avoid recomputing already committed records. That attempt revealed the Ollama connection-refused failure mode and produced invalid fast all-role-fallback records. These records were not committed and were removed.
- No v1 `AEGIS-eval/` source files, `04_ground_truth/` artifacts, or seed values were modified.
