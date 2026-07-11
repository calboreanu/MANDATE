# HANDOFF 19c Stage 2c Report - 2026-06-23

## Verdict

PROCEED

## Patch Landing Confirmation

Retry hardening landed in commit `2d51f13d`:

- Added shared retry/backoff helper: `apparatus/llm_retry.py`.
- Refactored `apparatus/grading/judge.py` to delegate retry classification and calls to the shared helper.
- Wired retry/backoff into Cond-A extraction in `apparatus/preprocess/extract_mission_input.py`.
- Wired retry/backoff into Cond-B by wrapping the canonical MLT adapter with `RetryingLLMClient` underneath the existing HANDOFF_19b constraint-gap wrapper in `apparatus/systems/mandate_canonical.py`.
- Added Anthropic pre-flight probe utility: `apparatus/probe_anthropic.py`.

## Test Results

- Focused retry / grading / extractor / canonical-system suites: `59 passed in 1.98s`.
- Full apparatus suite: `297 passed, 1 skipped in 3.80s`.

## Anthropic Probe Result

Attempt 1 failed, correctly blocking pilot launch:

- Probe result: `1/3` succeeded.
- Failures: 2 Anthropic `529 overloaded_error`.
- Note: the first shell branch initially logged `PROBE_PASS` because `tee` masked the probe exit status; this was corrected in `logs/HANDOFF_19c_probe_attempts.log`, and subsequent attempts used `set -o pipefail`.

Attempt 2 passed:

- Probe result: `3/3` succeeded.
- Decision: `SAFE TO RE-FIRE Stage 2b`.

## Cond-A Pilot Table

| Task ID | ok | Valid constraints | Failed grammar | COAs | First COA approach | Schema valid |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| TASK-MAIN-FIN-001 | true | 7 | 0 | 1 | Aggressive multi-vector approach with parallel execution | true |
| TASK-MAIN-FIN-018 | true | 7 | 0 | 1 | Aggressive multi-vector approach with parallel execution | true |
| TASK-MAIN-INT-003 | true | 13 | 0 | 2 | Conservative reconnaissance and scanning without exploitation | true |
| TASK-MAIN-INT-034 | true | 6 | 0 | 2 | Conservative reconnaissance and scanning without exploitation | true |
| TASK-MAIN-SEC-014 | true | 10 | 0 | 2 | Conservative reconnaissance and scanning without exploitation | true |

Cond-A criteria:

- 5/5 records `ok=True`.
- 5/5 records have at least 3 canonical-grammar-valid constraints.
- 5/5 records have `constraints_failed_grammar = 0`.
- 5/5 records have at least 1 COA.
- 5/5 records have first COA approach text other than `Minimal manual assessment approach`.
- 5/5 records have trace entry count 6 and chain hash present.
- 5/5 artifacts validate against canonical `mandate-as-code.schema.json`.

## Cond-B Pilot Table

| Task ID | ok | Valid constraints | Extraction gaps | COAs | Schema valid |
| --- | ---: | ---: | ---: | ---: | ---: |
| TASK-MAIN-FIN-001 | true | 11 | 0 | 1 | true |
| TASK-MAIN-FIN-018 | true | 9 | 0 | 1 | true |
| TASK-MAIN-INT-003 | true | 16 | 0 | 1 | true |
| TASK-MAIN-INT-034 | true | 13 | 0 | 1 | true |
| TASK-MAIN-SEC-014 | true | 15 | 0 | 1 | true |

Cond-B criteria:

- 5/5 records `ok=True`.
- Total `extraction_failed_constraints` across 5 records: 0, below the `<25` threshold.
- 5/5 records have at least 1 COA.
- 5/5 records have trace entry count 6 and chain hash present.
- 5/5 artifacts validate against canonical `mandate-as-code.schema.json`.
- `output.gap_reports` is populated for each record with canonical `SPECIFICATION_GAP` reports from Decomposition and Validation.

## Anomalies / Unexpected Findings

Cond-B did not emit live `EXTRACTION_GAP` entries because the EBNF-aware prompt and retry-hardened run produced only canonical-valid constraints in all five records. The HANDOFF_19b wrapper therefore was not exercised by live invalid constraints in this pilot. This is not treated as a failure because the revised success threshold is total extraction failures `<25`, and the wrapper behavior is covered by regression tests for mixed-valid, all-valid, and all-invalid constraint outputs.

The Cond-A pilot was interrupted once after two successful checkpoints because of operator correction around a zsh glob/pipefail handling issue. It was resumed with `--skip-existing`; the two existing records were skipped and the remaining three completed. The active Cond-A and Cond-B ledgers were normalized to the five current RunRecord JSON files.

## Retry-Layer Observations

The new probe utility prevented relaunch during the first degraded window. The Stage 2c pilots ran after a clean `3/3` probe pass. No unrecovered provider errors surfaced in the final Cond-A or Cond-B artifacts.

## Stage 3 Status

Stage 2c satisfies the revised criteria. Stage 3 full Cond-A and Cond-B runs are unblocked, per HANDOFF_19 §3 unchanged.
