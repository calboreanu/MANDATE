# HANDOFF_20 Stage 4 Report - 2026-06-24

## Verdict

HALT

## Scope Executed

Stage 4 setup and partial full-coverage v2 grading were executed.

Completed:

- D-10 judge restoration: `08_grading/judges_config.json` now uses `claude-opus-4-6`, `gpt-4o-2024-11-20`, and `gemini-2.5-pro`.
- v2 anonymization tree: `08_grading_v2/anonymized_outputs/` contains `12000` anonymized records.
- v1 D-08 IRR backup: `08_grading/irr.json` moved to `08_grading_v2/_v1_d08_irr.json.bak`.
- `grade-v2` CLI compatibility patch: `--rubric v2` and `--full-coverage` are accepted by the parser.
- Provider launch probes: Anthropic `3/3`; Gemini `3/3`.
- Stage 4 main grading launched with the handoff command.
- Partial checkpoint preserved: `1470` successful `by_record` outputs.

Not completed:

- Main full-coverage grading (`12000` target).
- 20% double-grade IRR sample.
- IRR halt-or-PROCEED check.
- Cross-condition analysis.

## Setup Commits

- `8b86af8b` - D-10 restoration: judges_config Anthropic judge restored to `claude-opus-4-6`.
- `8f49bb9e` - HANDOFF_20 setup: v2 anonymization tree and v1 IRR backup.
- `d1f83929` - HANDOFF_20: accept grade-v2 full-coverage rubric flags.

New unrelated `HANDOFF_22` commits appeared on top of main while Stage 4 was running. They were not modified by this handoff.

## Stage 3 Input Counts Confirmed

- Cond-A main: `1200`
- Cond-A holdout: `300`
- Cond-B main: `1200`
- Cond-B holdout: `300`
- v1 anonymized records on disk before v2 setup: `9000`

## Anonymization

- v1 mapping entries: `9000`
- v2 additions: `3000`
- merged full mapping entries: `12000`
- grader-visible anonymized files: `12000`
- symlinked v1 anonymized files: `9000`
- new Cond-A/Cond-B anonymized files: `3000`
- mapping/file ID set equality: passed
- v2 anon ID collision with v1: `0`

System counts in the merged mapping:

- `baseline_1`: `1500`
- `baseline_2`: `1200`
- `baseline_3`: `1200`
- `baseline_4`: `1200`
- `baseline_5`: `1200`
- `baseline_6`: `1200`
- `mandate_primary`: `1500`
- `cond_a`: `1500`
- `cond_b`: `1500`

## Grading Launch

Command launched:

```zsh
.venv/bin/python -m apparatus.run grade-v2 \
  --anonymized 08_grading_v2/anonymized_outputs \
  --ground-truth 04_ground_truth/ground_truth.json \
  --judges-config 08_grading/judges_config.json \
  --rubric v2 \
  --out 08_grading_v2 \
  --full-coverage \
  --double-grade-pct 0.20 \
  --double-grade-seed 20260624 \
  --skip-existing \
  --max-workers 5
```

The command was interrupted manually with `Ctrl-C` after a degraded Gemini window was confirmed. Successful per-record checkpoints had already been flushed by `GradingPipeline.grade_all`.

## Partial Results Preserved

- Successful main checkpoints: `1470 / 12000`
- Double-grade checkpoints: `0`
- Incomplete quarantines: `27`
- Incomplete rate at pause: `1.84%`
- Stderr log: `logs/HANDOFF_20_stage4_grade_v2.stderr`

Incomplete records by judge:

- `judge_3_gemini_pro`: `20`
- `judge_2_claude_opus`: `7`

Top incomplete causes:

- Gemini `503 UNAVAILABLE / high demand`: `19`
- Opus unbalanced JSON object in model output: `7`
- Gemini empty model output: `1`

The total incomplete rate did not exceed the handoff's 5% threshold. However, the recent failure window shifted to repeated Gemini `503 UNAVAILABLE` errors, and checkpoint freshness degraded while the grader repeatedly spent GPT/Opus calls around failed Gemini completions.

## Provider Probe At Halt

Gemini probe during the degraded window:

- Probe 1: retryable `503 UNAVAILABLE`, high-demand message.
- Probe 2: OK.
- Probe 3: OK.
- Result: `2/3` succeeded.
- Probe decision: `WAIT - provider still degraded; re-run this probe in 30-60 minutes`.

The active grading process produced additional Gemini `503` incompletes while the probe was running. The process was then stopped to preserve spend and prevent further incomplete accumulation.

## Resume Action Queue

1. Wait 30-60 minutes, then run:

```zsh
.venv/bin/python -m apparatus.grading.probe_gemini --probes 3
```

2. Resume only if Gemini returns `3/3` OK or the PI explicitly accepts degraded-provider continuation.

3. Re-run the same Stage 4 grading command:

```zsh
.venv/bin/python -m apparatus.run grade-v2 \
  --anonymized 08_grading_v2/anonymized_outputs \
  --ground-truth 04_ground_truth/ground_truth.json \
  --judges-config 08_grading/judges_config.json \
  --rubric v2 \
  --out 08_grading_v2 \
  --full-coverage \
  --double-grade-pct 0.20 \
  --double-grade-seed 20260624 \
  --skip-existing \
  --max-workers 5 \
  2> >(tee -a logs/HANDOFF_20_stage4_grade_v2.stderr >&2)
```

Expected resume behavior:

- Existing `1470` successful `by_record` checkpoints are skipped.
- Existing `27` incomplete records are not in `by_record`, so they are naturally retried.
- The main pass continues toward `12000` successful checkpoints.

## Notes For Resumption

- `--max-workers` currently parallelizes the three judges within a record, not multiple records at once. The run is therefore slower than the handoff's 24-36 hour planning estimate, but it is checkpointing correctly.
- The observed main-pass cost projection from recent checkpoints was approximately `$1.0K`, well below the $9,000 halt ceiling.
- No IRR decision can be made from this partial run.

## Escalations

- Gemini provider degradation during Stage 4 full-coverage grading.
- Resume should wait for a clean Gemini probe or PI direction.
