# HANDOFF_26 Report Attempt 02: Hold-Out Contamination Correction

## Verdict

PROCEED

## Summary

HANDOFF_26 attempt 02 completed the correction of the contaminated MANDATE-primary hold-out leg.

- Quarantined the 300 contaminated MP hold-out records from HANDOFF_11b-ii.
- Regenerated 300 fresh MP hold-out records against reachable Ollama.
- Confirmed zero all-role-fallback contamination in the regenerated records.
- Re-anonymized the exact 9,000-record Phase 6 set with seed `20260613`.
- Cut `outputs_freeze_v1_1` at the corrected-output commit.
- Preserved `outputs_freeze_v1` unchanged as the historical contaminated freeze.

Path note: the handoff body uses the old canonical project path, but this eval host's active project root is:

```text
/Users/ws01admin/Desktop/Desktop - lattice-ws01/MANDATE Evaluation/mandate_eval_2026Q2
```

## Preconditions

- Ollama `/api/tags` reachable after restart.
- All six `mandate-*` models present: `mandate-intake`, `mandate-interpreter`, `mandate-decomp`, `mandate-procedure`, `mandate-binding`, `mandate-validation`.
- Real `mandate-intake` healthcheck completed in under 60s.
- 300/300 existing MP hold-out records confirmed contaminated before quarantine.
- 1200/1200 MP main records confirmed not contaminated.
- `AEGIS-eval` confirmed at v1 baseline, with no v2 Binding-refusal marker.
- `outputs_freeze_v1` present; `outputs_freeze_v1_1` absent before tagging.
- AC power detected. A `caffeinate` guard was refreshed during the run; `pmset` could not be applied without root.

## Quarantine

Quarantine path:

```text
/tmp/handoff_26_contaminated_quarantine_20260615-124056
```

Quarantined files:

- 300 contaminated MP hold-out JSON records.
- 1 prior hold-out `ledger.jsonl`.
- Total: 301 files.

The canonical `07_system_outputs/mandate_primary/holdout/` directory was emptied before regeneration.

## Regenerated MP Hold-Out

Command scope:

- System: `mandate_primary`
- AEGIS source: `./AEGIS-eval`
- Mode: `--ollama-mode`
- Code ref: `mandate-eval-primary-2026q2-v1`
- Tasks: `04_ground_truth/holdout_tasks.jsonl`
- Runs: 10
- Seed base: `20260605`

Final validation:

| Metric | Value |
| --- | ---: |
| New MP hold-out records | 300 |
| `ok=True` | 300 |
| `any_llm_fallback=True` | 21 |
| All-role fallback contamination | 0 |
| Fast records under 60s | 0 |
| Wall clock median | 106,494.6 ms |
| Wall clock min | 94,417.0 ms |
| Wall clock max | 133,282.6 ms |

Watchdog checkpoints:

- 50 records: contamination 0, fast-legit 0.
- 100 records: contamination 0, fast-legit 0.
- 150 records: contamination 0, fast-legit 0.
- 200 records: contamination 0, fast-legit 0.
- 250 records: contamination 0, fast-legit 0.
- 300 records final: contamination 0, fast-legit 0.

Watchdog trigger count: 0.

## Hold-Out Behavior Breakdown

Domain: `software_engineering_specification`.

| Measure | Count | Rate |
| --- | ---: | ---: |
| Intake failures | 0 / 300 | 0.0% |
| Binding fallback/refusal-like parse failures | 21 / 300 | 7.0% |
| Validator gap-flagged records | 0 / 300 | 0.0% |
| Interpreter deterministic-prefix/echo mode | 300 / 300 | 100.0% |
| Interpreter clean-distillation mode | 0 / 300 | 0.0% |
| Single-COA outputs | 300 / 300 | 100.0% |

COA count distribution:

```text
{1: 300}
```

Binding fallback reason:

```text
LLM response parsing failed after 3 attempt(s): schema validation failed: 'decision_summary' is a required property
```

Binding fallback by task:

| Task | Count |
| --- | ---: |
| TASK-HOLDOUT-SES-004 | 2 |
| TASK-HOLDOUT-SES-005 | 3 |
| TASK-HOLDOUT-SES-006 | 1 |
| TASK-HOLDOUT-SES-008 | 2 |
| TASK-HOLDOUT-SES-010 | 2 |
| TASK-HOLDOUT-SES-018 | 1 |
| TASK-HOLDOUT-SES-020 | 1 |
| TASK-HOLDOUT-SES-026 | 7 |
| TASK-HOLDOUT-SES-029 | 1 |
| TASK-HOLDOUT-SES-030 | 1 |

## Re-Anonymization

The literal `apparatus.run anonymize --in 07_system_outputs` path was not used because the output tree contains prior pilot/calibration RunRecords in addition to the Phase 6 main and hold-out set, and the current CLI wrapper writes a single JSON output path rather than the directory shape required by the handoff. As in HANDOFF_11b-ii, re-anonymization used `apparatus.anonymize.Anonymizer(seed=20260613)` over the exact filtered Phase 6 set (`TASK-MAIN-*` and `TASK-HOLDOUT-*` only).

Integrity checks:

- Re-anonymized output files: 9,000.
- Mapping entries: 9,000.
- Task groups: 8,400 main, 600 hold-out.
- Top-level identity fields absent from every anonymized record.
- Search for obvious system identity strings in anonymized outputs returned no matches.
- Mapping file: `07_system_outputs/anonymization_mapping.json` (gitignored).

## Freeze Tags

Original historical tag:

- `outputs_freeze_v1` tag object: `54068a02dd9e609b903313b92dcab3f2dfe4dabd`
- `outputs_freeze_v1` target commit: `8ac78211859f6761481e68b39147e74fa692cbf9`

Corrected tag:

- `outputs_freeze_v1_1` tag object: `a1202cf0e3b8a57cbc641c63258d27e0fdd4a7ff`
- `outputs_freeze_v1_1` target commit: `5f4de5472c794259bfe3ba54f615707c6fcb5617`

Confirmation: `outputs_freeze_v1` was not moved or deleted.

## Commits

- `b1373dfb` — `Document HANDOFF_11b-ii MP hold-out contamination`
- `0cf4d2e8` — `Handoff 26: HALT on Ollama precondition`
- `5f4de547` — `Handoff 26 attempt 02: regenerate 300 MP hold-out + re-anonymize + outputs_freeze_v1_1 after Ollama restart`

## Escalations

None.

The corrected Phase 6 deposit-ready output freeze is `outputs_freeze_v1_1`.

