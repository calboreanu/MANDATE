# HANDOFF_13f Report: Judge retry+backoff relaunch

## Verdict

HALT

## Summary

The HANDOFF_13f retry/backoff patch was committed and verified. The revised D-08 sampled grading run was relaunched, but halted early under the handoff's provider-dominance escalation trigger: all incomplete records were attributed to `judge_3_gemini_pro` after retry exhaustion on Gemini `503 UNAVAILABLE` high-demand errors.

The patch behaved correctly: complete three-judge records were written to `08_grading/by_record/`, while records with an exhausted judge error were written to `08_grading/incomplete_grades/` and not treated as successful checkpoints. No partial-failure ensemble was silently persisted as complete.

After the HANDOFF_13f throughput gate was recalibrated, the run was resumed to completion on 2026-06-22. The final grading sample is complete and clean (`700/700` main records, `0` incomplete records, `140/140` double-grade checkpoints). The final verdict remains HALT because PROTOCOL_LOCK Section 8 is binding: final minimum pairwise kappa is `0.296355119519109`, below the `0.40` threshold.

## Patch Confirmation

- Patch commit: `1b3679ce`
- `Judge._call_with_retry()` present: yes
- Retryability smoke test: 503/high-demand retryable, 401 non-retryable
- Default retry schedule: `(5.0, 15.0, 45.0)`
- `pipeline.grade_all()` incomplete-grades branch present: yes
- `MockLLMClient` exception raising present: yes
- Regression tests: `27 passed`

## Preconditions

- CLI flags present: `--skip-existing`, `--max-workers`
- D-08 judge config active: `claude-sonnet-4-6`
- Sample manifest: `700` records
- `by_record/` clean before launch: `0`
- `incomplete_grades/` clean before launch: `0`
- Attempt 05 quarantine preserved: yes
- Stale grading process before launch: none
- API keys present: yes

## Run Log

- Sample staging: `700` symlinks in `08_grading/sample_anonymized_outputs/`
- Grading start: `2026-06-18T18:35:55Z`
- Manual stop: `2026-06-18T18:43:50Z`
- Stdout log: `08_grading/logs/HANDOFF_13f_grade_20260618_143555.stdout`
- Stderr log: `logs/HANDOFF_13f_grade_20260618_143555.stderr`

## Checkpoint State

- `08_grading/by_record/*.json`: `1`
- `08_grading/incomplete_grades/*.json`: `3`
- Incomplete attribution: `judge_3_gemini_pro = 3`
- Error class: Gemini `503 UNAVAILABLE`, high-demand window

The incomplete records are intentionally left in `08_grading/incomplete_grades/` for inspection and natural re-grade. They do not count as successful checkpoints. On a future retry, `--skip-existing` will preserve the one successful record and re-grade records that only have incomplete entries.

## Partial Cost And Tokens

These are partial-run figures from the four records touched before halt.

| Judge | Scores | Parse OK | Errors | Input Tokens | Output Tokens | Cost USD |
|---|---:|---:|---:|---:|---:|---:|
| `judge_1_gpt4o` | 4 | 4 | 0 | 29,987 | 1,788 | 0.092847 |
| `judge_2_claude_opus` | 4 | 4 | 0 | 34,575 | 3,461 | 0.155640 |
| `judge_3_gemini_pro` | 4 | 1 | 3 | 3,766 | 418 | 0.006797 |

Partial total: `$0.255284`.

## Kappa

Not computed. The sampled grading run did not complete, and `08_grading/irr.json` was not produced.

## D-08 Status

- Sampled grading plan: staged but not completed
- Sonnet substitution: active
- 10% double-grade: not reached
- Section 5.4 fill data: not produced

## Escalation Queue

1. Treat Gemini as in a sustained high-demand window for this run. Pause and retry later, or use an alternate Gemini model/tier only after PI sign-off.
2. Re-run HANDOFF_13f from the precondition block when provider conditions improve.
3. On retry, keep `08_grading/by_record/OUT-00450D0F.json` as the one valid checkpoint unless the PI wants a fully fresh grading attempt.
4. If Gemini 503s recur immediately, do not continue; halt again before the sample accumulates many incomplete entries.

## Deviations

The run was manually interrupted after the provider-dominance escalation trigger was observed. This avoided further API spend and avoided accumulating a large `incomplete_grades/` set during an active Gemini high-demand window.

## Retry Attempt After User Request

The user requested another try after the initial 13f HALT. The run was resumed from the existing checkpoint state with `--skip-existing`:

- Start: `2026-06-18T19:21:42Z`
- Stop: `2026-06-18T19:53:39Z`
- Successful `by_record/` checkpoints at the 30-minute gate: `64`
- Final successful `by_record/` checkpoints after interrupt settled: `65`
- `incomplete_grades/` after stale cleanup: `0`
- New Gemini 503 incompletes during retry: `0`
- Halt reason: throughput below HANDOFF_13f threshold (`<100` successful checkpoints after 30 minutes)

The retry demonstrated that provider correctness improved: the three stale Gemini incompletes from the earlier run were successfully re-graded and removed from `incomplete_grades/`. The remaining blocker is wall-clock throughput, not incomplete-state contamination.

Partial cumulative cost across the 65 successful checkpoints:

| Judge | Scores | Parse OK | Errors | Input Tokens | Output Tokens | Cost USD |
|---|---:|---:|---:|---:|---:|---:|
| `judge_1_gpt4o` | 65 | 65 | 0 | 446,182 | 27,600 | 1.391458 |
| `judge_2_claude_opus` | 65 | 65 | 0 | 517,455 | 52,786 | 2.344155 |
| `judge_3_gemini_pro` | 65 | 65 | 0 | 482,641 | 27,292 | 0.739763 |

Partial total: `$4.475376`.

Resume state for next attempt:

- Keep `08_grading/by_record/` as-is; `--skip-existing` will preserve 65 valid checkpoints.
- `08_grading/incomplete_grades/` is empty.
- Re-stage `08_grading/sample_anonymized_outputs/` before the next run.
- If the PI accepts slower throughput, continuing from 65/700 is safe; otherwise revise the throughput gate before re-firing.

## Final Resume And Completion

The handoff was resumed again on 2026-06-22 after the throughput threshold was corrected from `<100 records at 30 minutes` to `<30 records at 30 minutes`.

- Resume3 start: `2026-06-22T17:12:16Z`
- Resume3 main-pass result: `skipped 232`, `executed 468`, `incomplete 1`, `persisted 699`
- Cleanup pass start: `2026-06-22T22:13:05Z`
- Cleanup pass result: `skipped 699`, `executed 1`, `incomplete 0`, `persisted 700`
- Final main checkpoints: `700/700`
- Final incomplete checkpoints: `0`
- Double-grade checkpoints: `140/140` (`70` pass1, `70` pass2)
- Final `irr.json`: produced

One Gemini `503 UNAVAILABLE` error recurred during Resume3 for `OUT-D1F83275`, but the retry/quarantine patch handled it correctly: the record went to `incomplete_grades/`, was not counted as complete, and was successfully re-graded in the cleanup pass.

## Final IRR Decision

Final PROTOCOL_LOCK Section 8 decision: HALT.

| Metric | Value |
|---|---:|
| Main records graded | 700 |
| Main min pairwise kappa | 0.296355119519109 |
| Halt threshold | 0.40 |
| `irr.json` halt flag | `true` |
| Double-grade sample size | 70 |
| Double-grade pass1 min kappa | -0.06779661016949157 |
| Double-grade pass2 min kappa | 0.08114558472553701 |

Main-pass pairwise kappa table:

| Pair | Kappa |
|---|---:|
| `mission_intent_match:judge_1_gpt4o|judge_2_claude_opus` | 0.3305590736385019 |
| `mission_intent_match:judge_1_gpt4o|judge_3_gemini_pro` | 0.7093375317912074 |
| `mission_intent_match:judge_2_claude_opus|judge_3_gemini_pro` | 0.296355119519109 |
| `gap_classification:judge_1_gpt4o|judge_2_claude_opus` | 0.6768011150797109 |
| `gap_classification:judge_1_gpt4o|judge_3_gemini_pro` | 0.44920017293558145 |
| `gap_classification:judge_2_claude_opus|judge_3_gemini_pro` | 0.7132230068459922 |

Lowest-kappa judge pair: `judge_2_claude_opus|judge_3_gemini_pro` on `mission_intent_match`.

## Final Cost And Tokens

Main sample (`700` records):

| Judge | Calls | Parse OK | Errors | Input Tokens | Output Tokens | Cost USD |
|---|---:|---:|---:|---:|---:|---:|
| `judge_1_gpt4o` | 700 | 700 | 0 | 4,861,024 | 299,654 | 15.149115 |
| `judge_2_claude_opus` | 700 | 700 | 0 | 5,654,619 | 571,538 | 25.536927 |
| `judge_3_gemini_pro` | 700 | 700 | 0 | 5,278,900 | 291,946 | 8.058359 |

Double-grade sample (`140` scored records across two 70-record passes):

| Judge | Calls | Parse OK | Errors | Input Tokens | Output Tokens | Cost USD |
|---|---:|---:|---:|---:|---:|---:|
| `judge_1_gpt4o` | 140 | 140 | 0 | 1,011,700 | 59,098 | 3.120236 |
| `judge_2_claude_opus` | 140 | 140 | 0 | 1,178,834 | 116,090 | 5.277852 |
| `judge_3_gemini_pro` | 140 | 140 | 0 | 1,107,992 | 58,243 | 1.676204 |

Total Phase 8 sampled grading cost captured in artifacts: `$58.818693`.

## System-Level Ensemble Summary

Each system has `100` graded records in the D-08 sample.

| System | Mission Mean | Min Cov | Target Cov | Constraint Cov | Trace Mean | Disagreement Rate | Gap TP | Gap FN | Sonnet Delta vs Other Judges |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `baseline_1` | 1.000 | 0.880 | 0.675 | 0.837 | 2.000 | 0.240 | 100 | 0 | 0.041 |
| `baseline_2` | 0.260 | 0.265 | 0.172 | 0.266 | 1.260 | 0.950 | 5 | 95 | 0.056 |
| `baseline_3` | 1.000 | 0.962 | 0.703 | 0.910 | 1.020 | 0.300 | 100 | 0 | 0.083 |
| `baseline_4` | 1.000 | 0.888 | 0.662 | 0.836 | 2.000 | 0.130 | 100 | 0 | 0.053 |
| `baseline_5` | 1.000 | 0.848 | 0.643 | 0.848 | 2.000 | 0.220 | 100 | 0 | 0.067 |
| `baseline_6` | 1.000 | 0.875 | 0.639 | 0.834 | 2.000 | 0.210 | 100 | 0 | 0.036 |
| `mandate_primary` | 0.940 | 0.179 | 0.069 | 0.010 | 2.000 | 0.270 | 0 | 100 | -0.301 |

B1/Sonnet self-grading inspection: the Sonnet judge's rough composite score on B1 records averaged `+0.041` above the other two judges, which is directionally consistent with the D-08 self-grading bias caveat but smaller than the largest observed positive delta (`baseline_3`, `+0.083`). MANDATE-primary shows a negative Sonnet delta (`-0.301`).

## Final Artifacts

- `08_grading/by_record/*.json`: 700 complete per-record checkpoints
- `08_grading/judge_1_gpt4o/scores.jsonl`: 700 rows
- `08_grading/judge_2_claude_opus/scores.jsonl`: 700 rows
- `08_grading/judge_3_gemini_pro/scores.jsonl`: 700 rows
- `08_grading/ensemble_aggregated/ensemble_scores.jsonl`: 700 rows
- `08_grading/double_grade/pass1_scores.jsonl`: 70 rows
- `08_grading/double_grade/pass2_scores.jsonl`: 70 rows
- `08_grading/double_grade/pass1/by_record/*.json`: 70 checkpoints
- `08_grading/double_grade/pass2/by_record/*.json`: 70 checkpoints
- `08_grading/irr.json`: final IRR and halt decision

## Final Escalation Queue

1. PROTOCOL_LOCK Section 8 halt is binding because main-pass minimum pairwise kappa is `0.296355119519109 < 0.40`.
2. Diagnose judge disagreement before HANDOFF_14. The lowest pair is Sonnet-Gemini on `mission_intent_match`; double-grade kappas are also below threshold.
3. Decide whether to publish under the discovery-paper/halt framing, revise the judge mix, or drop the cross-system scoring layer as contemplated in the D-08 halt path.
