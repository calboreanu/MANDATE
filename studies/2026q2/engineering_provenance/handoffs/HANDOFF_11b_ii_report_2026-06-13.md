# HANDOFF_11b-ii Report: Phase 6 baselines + hold-out + anonymize + freeze

## Verdict

PROCEED

## Summary

HANDOFF_11b-ii completed the API-backed Phase 6 baseline matrix, the MANDATE-primary plus B1 hold-out leg, the Phase 8 anonymized output set, and the `outputs_freeze_v1` tag.

Final Phase 6 output set:

- Main matrix: 8,400 RunRecords (MANDATE-primary + B1-B6, 120 tasks x 10 runs).
- Hold-out: 600 RunRecords (MANDATE-primary + B1, 30 tasks x 10 runs).
- Total: 9,000 RunRecords, 8,979 `ok=True`.
- Total API cost recorded in RunRecords: $339.03, below the $600 halt threshold.

Known not-ok records:

- MANDATE-primary main: 20 records, all Intake content-tripwire failures on `TASK-MAIN-SEC-038` and `TASK-MAIN-SEC-040` (10 runs each), accepted as Phase 6 data from 11b-i.
- Baseline 3 main: 1 record, `baseline_3__TASK-MAIN-FIN-037__r08`, Anthropic 529 `overloaded_error`.
- Hold-out: 0 not-ok records.

## Preconditions

- Freeze tetrad present before execution: `corpus_freeze_v1`, `baseline_freeze_v1`, `gt_freeze_v1`, `perturbation_freeze_v1`.
- Main and hold-out task files present: `04_ground_truth/main_tasks.jsonl` (120), `04_ground_truth/holdout_tasks.jsonl` (30).
- `AEGIS-eval/` remained the v1 tree.
- `outputs_freeze_v1` was absent before Task 4.
- API keys were sourced from the Desktop API keys file for commands that needed provider authentication. Secrets were not written to the repo.

Precondition deviation carried from PI go-ahead: HANDOFF_11b-i landed 1,180 ok MANDATE-primary main records rather than the handoff text's 1,190 floor, due to the already-characterized Intake content-tripwire on SEC-038/SEC-040. The PI explicitly authorized proceeding with 11b-ii after reviewing those findings.

## Task 1: Baselines B1-B6 Main

| System | Records | ok | ok rate | schema_valid | fallback | API cost | Sum wall clock |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_1 | 1,200 | 1,200 | 100.0% | 0 | 0 | $39.46 | 12.51 h |
| baseline_2 | 1,200 | 1,200 | 100.0% | 0 | 0 | $6.84 | 1.20 h |
| baseline_3 | 1,200 | 1,199 | 99.9% | 0 | 0 | $93.15 | 28.01 h |
| baseline_4 | 1,200 | 1,200 | 100.0% | 0 | 0 | $87.77 | 20.84 h |
| baseline_5 | 1,200 | 1,200 | 100.0% | 0 | 0 | $52.30 | 16.28 h |
| baseline_6 | 1,200 | 1,200 | 100.0% | 0 | 0 | $48.93 | 13.20 h |

Task 1 total: 7,200 records, 7,199 ok. The single B3 529 overload is below the handoff escalation threshold of more than 12 not-ok records for an entire baseline.

Checkpoint commits:

- `e883be7` baseline_1 main complete.
- `9cad659` baseline_2 main complete.
- `35cf656` baseline_3 main complete (1 transient overload).
- `685df2f` baseline_4 main complete.
- `05503b8` baseline_5 main complete.
- `b2cc0d3` baseline_6 main complete.

## Task 2: Hold-Out

| System | Records | ok | ok rate | schema_valid | fallback | API cost | Sum wall clock |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| mandate_primary | 300 | 300 | 100.0% | 0 | 300 | $0.00 | 0.18 h |
| baseline_1 | 300 | 300 | 100.0% | 0 | 0 | $10.58 | 3.35 h |

MANDATE-primary hold-out produced `any_llm_fallback=True` on all 300 records. The handoff explicitly says this is Phase 6 data, not a halt condition.

Checkpoint commits:

- `8a7df5a` MANDATE-primary hold-out complete.
- `45e98e7` baseline_1 hold-out complete.

## Task 3: Anonymization

Anonymization integrity:

- Anonymized output files: 9,000 under `08_grading/anonymized_outputs/`.
- Mapping entries: 9,000 in `07_system_outputs/anonymization_mapping.json`.
- Mapping file is gitignored.
- Anonymized task groups: 8,400 main, 600 hold-out.
- Top-level identity fields stripped from every anonymized record (`system_id`, `system_label`, `run_id`, `model_versions`, `decoding_params`, `code_ref`, `role_timings` absent).
- Sample obvious identity string search over anonymized outputs for `mandate_primary`, `MANDATE-primary`, `baseline_[1-6]`, and `B[1-6] ` returned no matches.

Execution deviation for Task 3:

The literal `python3 -m apparatus.run anonymize --in 07_system_outputs ...` path was not used as-is because the on-disk input tree contained 9,078 RunRecord JSONs, not the 9,000 Phase 6 records requested by the handoff. The extra records were 42 pilot-smoke records and 36 calibration records. In addition, the current CLI wrapper writes a single JSON file for `--out` while the handoff requires a directory of anonymized outputs, and its final print references `result.anon_outputs` although the dataclass field is `outputs`.

To preserve the handoff's data contract without modifying apparatus source, Task 3 used the existing `apparatus.anonymize.Anonymizer(seed=20260605)` API on the exact filtered Phase 6 set (`TASK-MAIN-*` and `TASK-HOLDOUT-*` only), verified `verify_mapping(result)`, wrote one blinded JSON per anonymized output under `08_grading/anonymized_outputs/`, and wrote the gitignored mapping to `07_system_outputs/anonymization_mapping.json`.

## Task 4: Freeze

`outputs_freeze_v1` was cut after committing the anonymized outputs.

- Tag object: `54068a02dd9e609b903313b92dcab3f2dfe4dabd`
- Tag target commit: `8ac78211859f6761481e68b39147e74fa692cbf9`
- Target commit message: `Handoff 11b-ii: Phase 6 baselines + hold-out + anonymize + outputs_freeze_v1`

## Final 9000-Record Summary

| System | Main records | Hold-out records | Total records | ok | schema_valid | fallback | API cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| mandate_primary | 1,200 | 300 | 1,500 | 1,480 | 0 | 533 | $0.00 |
| baseline_1 | 1,200 | 300 | 1,500 | 1,500 | 0 | 0 | $50.04 |
| baseline_2 | 1,200 | 0 | 1,200 | 1,200 | 0 | 0 | $6.84 |
| baseline_3 | 1,200 | 0 | 1,200 | 1,199 | 0 | 0 | $93.15 |
| baseline_4 | 1,200 | 0 | 1,200 | 1,200 | 0 | 0 | $87.77 |
| baseline_5 | 1,200 | 0 | 1,200 | 1,200 | 0 | 0 | $52.30 |
| baseline_6 | 1,200 | 0 | 1,200 | 1,200 | 0 | 0 | $48.93 |
| Total | 8,400 | 600 | 9,000 | 8,979 | 0 | 533 | $339.03 |

## Escalations

None.

Observed issues below halt thresholds or explicitly non-halting under the handoff:

- One B3 transient Anthropic 529 overload.
- 300 MANDATE-primary hold-out fallback records.
- 20 MANDATE-primary main Intake content-tripwire failures inherited from 11b-i.
- `schema_valid` observed as false/absent across the output matrix; the handoff states `schema_valid=False` is Phase 6 O4 data, not a halt condition.

