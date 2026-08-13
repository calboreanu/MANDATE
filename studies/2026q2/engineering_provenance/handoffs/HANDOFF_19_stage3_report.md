# HANDOFF 19 Stage 3 Report

## Verdict

HALT

## Scope Executed

Stage 3 launch began with the required Anthropic probe gate, then started Cond-A main.

Executed:

- Anthropic launch probe.
- Cond-A main, `--all`, 120 main tasks, `--runs-per-task 10`, `--skip-existing`.

Not executed:

- Cond-A holdout.
- Cond-B main.
- Cond-B holdout.

## Probe Results

Launch probe:

- `3/3` Anthropic probes succeeded.
- Stage 3 launch proceeded.

Throughput-halt re-probe:

- `3/3` Anthropic probes succeeded.
- Provider health was not the cause of the halt.

## Cond-A Main Checkpoint

At the throughput gate, Cond-A main had written 68 active RunRecord JSON files under `07_system_outputs/cond_a/`.

Ledger was normalized to match the active checkpoint files:

- `07_system_outputs/cond_a/cond_a__TASK-MAIN-*.json`: 68
- `07_system_outputs/cond_a/ledger.jsonl`: 68 lines

Checkpoint summary:

| Metric | Value |
| --- | ---: |
| Records written | 68 |
| `ok=True` | 68 |
| `ok=False` | 0 |
| Any LLM fallback | 0 |
| API cost so far | `$1.826436` |
| Mean wall clock per record | `27.56s` |
| Median wall clock per record | `26.57s` |
| Main tasks touched | 11 |
| Domain split | FIN 65, INT 2, SEC 1 |

Spot check:

- 20/20 sampled records schema-valid against canonical `mandate-as-code.schema.json`.
- 20/20 sampled records had first COA approach text other than `Minimal manual assessment approach`.

## Halt Trigger

The handoff-defined throughput trigger fired:

> After 30 min, `cond_a/` has < 100 records -> throughput problem; re-probe and investigate.

Observed checkpoint count was 68 records near the 30-minute gate, below the 100-record threshold.

The active Cond-A process was stopped with `Ctrl-C` after checkpoint preservation. The interrupt occurred while the next extraction call was in progress; no partial JSON record was written for that interrupted call.

## Diagnosis

This appears to be a throughput-envelope mismatch, not provider failure and not bad outputs.

Evidence:

- Launch probe passed 3/3.
- Re-probe after halt passed 3/3.
- 68/68 saved records are `ok=True`.
- No LLM fallbacks.
- Spot-check schema validity is 20/20.
- Mean per-record wall clock was ~27.6s, close to the instruction's own per-task expectation of ~25s extraction + sub-second MANDATE.

The threshold of 100 records in 30 minutes implies <=18s/record sustained throughput, while the observed successful Cond-A records are closer to 26-28s/record. At the observed rate, 1500 Cond-A records project to roughly 11-12 hours rather than the handoff's ~8.5-hour estimate.

The `--max-workers 5` flag did not provide parallelism; the CLI explicitly reports that Cond-A accepts `--max-workers` for handoff compatibility but runs checkpointed serially.

## Resume State

The partial Cond-A main checkpoint is safe. To resume exactly this leg:

```zsh
.venv/bin/python -m apparatus.run run-cond-a \
  --all \
  --tasks 04_ground_truth/main_tasks.jsonl \
  --out 07_system_outputs/cond_a \
  --extraction-model claude-sonnet-4-6 \
  --runs-per-task 10 \
  --seed 20260623 \
  --skip-existing \
  --checkpoint-every 50 \
  --max-workers 5
```

Expected behavior on resume:

- Existing 68 main records are skipped.
- Remaining 1132 main records execute.
- Ledger should be normalized to active JSON files after completion, as done here.

## Action Queue

1. PI decision needed: accept the observed serial Cond-A throughput and continue, or patch `run-cond-a` for real concurrency before resuming.
2. If continuing without concurrency patch, revise the Cond-A wall-clock expectation from ~8.5h to ~11-12h for main+holdout at the observed rate.
3. Do not diagnose this as an Anthropic outage; the probe passed before and after the halt.
4. Stage 3 remains incomplete. Cond-A holdout and all Cond-B Stage 3 legs remain unstarted.
