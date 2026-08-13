# HANDOFF 19b Stage 2b Report - 2026-06-23

## Verdict

HALT

## Stage 1 Status

Stage 1 plumbing remains preserved from commit `37477ae8`:

- `apparatus/systems/mandate_canonical.py`
- `apparatus/preprocess/extract_mission_input.py`
- `apparatus/grading/rubric_v2.py`
- `apparatus/run.py` CLI dispatch for `run-cond-a`, `run-cond-b`, and `grade-v2`

The current HEAD before this report was `fabec023`, the prior Stage 2 HALT report. That matches the handoff's allowed warning: Stage 1 is not HEAD because the Stage 2 attempt-1 report commit landed after it.

## Preconditions

- Project venv executable present: yes, using `.venv/bin/python` directly.
- Canonical MLT tests: `418 passed, 8 skipped, 3 xfailed in 1.48s`.
- Previous Stage 2 attempt-1 Cond-A and Cond-B artifacts preserved under:
  - `07_system_outputs/cond_a/_stage2_attempt1/`
  - `07_system_outputs/cond_b/_stage2_attempt1/`
- API keys present in `.env`: Anthropic, OpenAI, and Google all set.

## Patches Landed

Extractor EBNF teaching:

- Updated `apparatus/preprocess/extract_mission_input.py` to teach the canonical MANDATE constraint grammar explicitly: `FORBIDS`, `REQUIRES`, `IN`, and comparison predicates.
- Added post-response canonical validation for every emitted constraint.
- Invalid emitted constraints are no longer silently dropped; they are preserved in `MissionInput.metadata["extraction_failed_constraints"]` with `reason="invalid_grammar"`.
- Added `constraints_extracted` and `constraints_failed_grammar` metadata.

Cond-B constraint-gap wrapper:

- Added `ConstraintGapRoutingAdapter` in `apparatus/systems/mandate_canonical.py`.
- The wrapper intercepts only MissionInput-shaped LLM Intake responses, removes invalid constraint strings before canonical Intake validation, and records each invalid string.
- `run_cond_b` converts those invalid strings into canonical `GapSpec` reports with `gap_type=UNKNOWN_PATTERN`, `gap_source=EXTRACTION_GAP`, `detected_by=Intake`, `pipeline_stage=1`.
- RunRecord output keeps the existing apparatus shape: canonical artifact under `output.artifact`, gap reports under `output.gap_reports`.

Tests added:

- Extractor validates constraints against canonical grammar.
- Extractor routes invalid constraints to metadata.
- Cond-B wrapper routes mixed valid/invalid constraints to extraction gaps.
- Cond-B wrapper passes through all-valid constraints without extraction gaps.
- Cond-B wrapper completes on all-invalid constraints and emits five extraction gaps.

Verification:

- Focused suites: `18 passed in 0.59s`.
- Full apparatus suite: `283 passed, 1 skipped in 3.97s`.

## Cond-A Revised Pilot

Cond-A did not reach a substantive Stage 2b pilot result because Anthropic failed before extraction completed.

Attempt handling:

- First Stage 2b Cond-A run produced five provider failures and was quarantined under `07_system_outputs/cond_a/_stage2_attempt2_api_transient/`.
- One retry was taken after a 60-second backoff.
- The retry again failed before extraction on all five records.

Retry evidence in `07_system_outputs/cond_a/`:

| Task ID | ok | Failure class | Artifact produced | Role timings |
| --- | --- | --- | --- | --- |
| TASK-MAIN-FIN-001 | false | Anthropic 529 `overloaded_error` | no | none |
| TASK-MAIN-FIN-018 | false | Anthropic 500 `api_error` | no | none |
| TASK-MAIN-INT-003 | false | Anthropic 529 `overloaded_error` | no | none |
| TASK-MAIN-INT-034 | false | Anthropic 529 `overloaded_error` | no | none |
| TASK-MAIN-SEC-014 | false | Anthropic 529 `overloaded_error` | no | none |

Cond-A revised criteria were therefore not evaluable:

- `ok=True` in all 5 records: not met, due provider outage before extraction.
- Constraint count, failed-grammar rate, COA differentiation, trace chain, and canonical schema validation: not evaluable because no artifacts were produced.

## Cond-B Revised Pilot

Cond-B was not run after Cond-A failed twice at the provider layer. This avoids burning additional API calls when the shared Anthropic dependency is demonstrably unhealthy.

Cond-B wrapper behavior is covered by unit tests, but no live Cond-B Stage 2b pilot evidence was collected in this attempt.

## Anomalies / Unexpected Findings

- The apparatus patches and tests completed successfully.
- The blocker was external provider availability: repeated Anthropic `529 overloaded_error` plus one `500 api_error` during extractor calls.
- No evidence was collected for or against the revised Stage 2 success criteria.

## Escalation / Action Queue

1. Retry HANDOFF_19b Stage 2b after Anthropic overload clears.
2. Preserve the existing failed-at-provider artifacts as audit evidence:
   - `07_system_outputs/cond_a/_stage2_attempt2_api_transient/`
   - `07_system_outputs/cond_a/`
3. On retry, quarantine the current failed `07_system_outputs/cond_a/*.json` and `ledger.jsonl` into a new attempt directory before re-running Cond-A.
4. No wrapper redesign is indicated by this halt. The current code path passed focused and full apparatus tests.

## Stage 3 Status

Stage 3 remains blocked. Do not start the full Cond-A/Cond-B 1500-record runs until Stage 2b produces live five-task pilot artifacts that satisfy the revised criteria.
