# HANDOFF_13d Throughput Report

The HANDOFF_13d grading process was killed intentionally on 2026-06-17 after the diagnosis that the grader was running sequentially and only flushing outputs at the end of the full 9000-record main pass. With zero on-disk grading artifacts after more than 25 hours of execution, the crash/kill exposure for continuing the run was higher than the cost of stopping and patching.

## Process state at kill time

Captured before `SIGINT` in `Mandate Data/standalone data results/handoff_chronology/13d_running_state.txt`.

- PID: `5644`
- Elapsed: `01-01:26:08`
- CPU: `0.0`
- PMEM: `0.8`
- RSS: `555600`
- VSZ: `435734768`
- State: `S+`
- Command: `.venv/bin/python -u -m apparatus.run grade --anonymized 08_grading/anonymized_outputs --ground-truth 04_ground_truth/ground_truth.json --judges-config 08_grading/judges_config.json --out 08_grading --double-grade-pct 0.20 --double-grade-seed 20260616`

`lsof` showed no open `08_grading` or `/tmp` file handles at the time of the snapshot.

## API spend

Provider dashboard spend was not available from the shell session. The 13d API spend should be filled from the Anthropic, OpenAI, and Google dashboards if the deposit trail needs exact sunk-cost attribution.

- Anthropic (Claude Opus): not captured
- OpenAI (GPT-4o): not captured
- Google (Gemini 2.5 Pro): not captured
- Total estimated 13d burn: not captured

## What was preserved

- `04_ground_truth/ground_truth.json`
- `08_grading/judges_config.json`
- HANDOFF_13c double-grade CLI patch
- HANDOFF_13d Gemini `max_tokens=8192` patch
- HANDOFF_13e checkpoint/concurrency patch

## What was lost

- About 25 hours and 26 minutes of wall clock.
- API spend from the killed in-memory run.
- An unknown number of in-memory partial grading records.

No canonical grading artifacts were written before the kill: no `08_grading/judge_*`, no `08_grading/ensemble_aggregated/`, no `08_grading/double_grade/`, no `08_grading/by_record/`, and no `08_grading/irr.json`.

## Lesson captured for the apparatus

The grader now writes per-record checkpoints and supports `--skip-existing` resume. The main pass writes to `08_grading/by_record/<anon_id>.json`; the double-grade sample writes independent checkpoint namespaces under `08_grading/double_grade/pass1/by_record/` and `08_grading/double_grade/pass2/by_record/`. The patched `--max-workers` path runs the three judges for a record concurrently.
