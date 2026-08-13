# HANDOFF_26 Report: Hold-Out Contamination Correction

## Verdict

HALT

## Halt Point

Task 0 / preconditions. HANDOFF_26 did not proceed to quarantine, regeneration, re-anonymization, or tagging because Ollama was not reachable on `localhost:11434`.

Command result:

```text
curl: (7) Failed to connect to localhost port 11434 after 0 ms: Couldn't connect to server
HALT: Ollama not reachable
```

## Preconditions

- Ollama reachable and six `mandate-*` models loaded: FAILED.
- Real-call `mandate-intake` healthcheck: NOT RUN because Ollama was unreachable.
- Existing 300 MP hold-out contamination confirmed: PASS.
- MP main clean / not contaminated: not rechecked after the Ollama halt command, but not modified in this session.
- `AEGIS-eval` v1 baseline check: NOT RUN after precondition halt.
- `outputs_freeze_v1` present and `outputs_freeze_v1_1` absent: confirmed separately after the halt.

Path note: the handoff body uses the old canonical project path, but that path is absent on this eval host. Commands were executed from the actual project root:

```text
/Users/ws01admin/Desktop/Desktop - lattice-ws01/MANDATE Evaluation/mandate_eval_2026Q2
```

## Quarantine Path

N/A. Task 1 was not started. No files were moved to quarantine.

## Current MP Hold-Out State

- Existing MP hold-out records: 300.
- Contamination signature count (`all role_timings[].llm_fallback == True`): 300.
- Canonical hold-out directory remains populated with the contaminated records.

## Watchdog Trigger Count

N/A. The regeneration run did not start, so the checkpoint watchdog was not run against new records.

## Re-Anonymization

N/A. Task 4 was not started.

Current anonymized output count remains 9,000 from `outputs_freeze_v1`; those anonymized outputs still correspond to the contaminated MP hold-out records and must be regenerated after a clean MP hold-out re-run.

## Freeze Tags

- `outputs_freeze_v1` tag object: `54068a02dd9e609b903313b92dcab3f2dfe4dabd`
- `outputs_freeze_v1` target commit: `8ac78211859f6761481e68b39147e74fa692cbf9`
- `outputs_freeze_v1_1`: absent

`outputs_freeze_v1` was not moved or deleted.

## Escalation Queue

1. Start or restart Ollama on the eval host.
2. Verify `curl -sS http://localhost:11434/api/tags` responds.
3. Verify all six models are listed: `mandate-intake`, `mandate-interpreter`, `mandate-decomp`, `mandate-procedure`, `mandate-binding`, `mandate-validation`.
4. Re-run HANDOFF_26 from the beginning after the PI checklist is complete.

## Session Changes

Before running HANDOFF_26, the existing `00_preregistration/DEVIATIONS.md` contamination note was committed as requested:

- `b1373dfb` — `Document HANDOFF_11b-ii MP hold-out contamination`

No Phase 6 output files, anonymized outputs, AEGIS files, or ground-truth files were modified in this session.

