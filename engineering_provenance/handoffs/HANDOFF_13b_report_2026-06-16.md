# HANDOFF_13b Report: Phase 8 three-judge grading corrected scope

## Verdict

HALT

## Halt Point

Pre-spend apparatus contract audit, before Task 1 writes `04_ground_truth/ground_truth.json` and before any judge API healthchecks or grading calls.

## Preconditions Checked

- `outputs_freeze_v1_1`: present.
- Anonymized outputs: 9000 JSON records under `08_grading/anonymized_outputs/`.
- Output composition: 8400 main records and 600 hold-out records.
- Scaffold pools: 120 main scaffolds and 30 hold-out scaffolds present; all 150 have `parse_ok=true`.
- Judge API healthchecks: not run. The run halted before any API spend because the current grading apparatus cannot satisfy this handoff's definition of done.

## Total Anonymized Records Graded

0.

## Per-Judge Cost

- Anthropic: `$0.00`
- OpenAI: `$0.00`
- Google: `$0.00`

Total cost: `$0.00`

## Per-Pair Cohen's Kappa

Not computed; no grading calls were made.

Min pairwise kappa: not computed.

## Blocking Findings

1. The current `apparatus.run grade` command does not execute the required 20% double-grading sample.

   Evidence: `apparatus/run.py` `cmd_grade` loads anonymized outputs and ground truth, constructs the three judges, runs `pipe.grade_all(...)`, saves the single-pass scores, and writes `pipe.irr(graded)`. It never calls `GradingPipeline.double_grade(...)`, never samples 20% of outputs, and never writes double-grade artifacts. This fails HANDOFF_13b definition-of-done item 3 and the decision-boundary rule forbidding a skipped 20% double-grading sample.

2. The Task 1 `ground_truth.json` shape in HANDOFF_13b is incompatible with the current grading pipeline.

   Evidence: `apparatus/grading/pipeline.py` sends `json.dumps(gt.get("anchor", {}), ...)` to each judge. The handoff's Task 1 assembler writes task entries with top-level `mission_intent`, `minimum`, `target`, `constraints`, and `suspected_gaps`, but no `anchor` key. Running Task 1 as written would cause the judges to grade against `{}` as the ground truth anchor.

3. HANDOFF_13b's narrative still contains a stale 9036-record scope, but the frozen anonymized tree contains exactly 9000 records.

   This is not a halt condition by itself because the precondition requires `>=9000`, and the current tree matches the corrected `outputs_freeze_v1_1` deposit-ready state. It should be corrected in the next grading handoff/report language to avoid ambiguity.

## Anomalies

- No judge schema-invalid rate, rate-limit behavior, retry behavior, or per-call cost could be measured because the run halted before API calls.
- No files under `08_grading/` were modified by this handoff.
- `04_ground_truth/ground_truth.json` was not generated because the specified assembly shape would be consumed incorrectly by the current grader.

## Per-Domain Breakouts

Not available; no ensemble scores were produced.

## Escalation Queue

1. Issue a corrected HANDOFF_13c or an apparatus patch handoff before Phase 8 grading proceeds.
2. Patch or wrap the ground-truth assembly so each task maps to a dict containing an `anchor` object with the scaffold fields the judges should compare against. Include `category`, `expected_output_type`, and `is_injection_trial` if the grader needs those fields for rubric conditioning.
3. Extend `python3 -m apparatus.run grade` to perform and persist the required 20% double-grading sample, or add a separate explicit command for that sample. The implementation should save double-grade artifacts, include cost accounting, and preserve the kappa halt checks specified in HANDOFF_13b.
4. Re-run small real-call judge healthchecks only after the two contract gaps above are closed.
5. Re-fire Phase 8 grading only after the corrected apparatus can satisfy all HANDOFF_13b definition-of-done items without manual inference.
