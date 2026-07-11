# Handoff 11b-ii Report: Phase 6 Baselines + Hold-out + Freeze

**Codex session:** desktop session
**Eval host:** lattice-ws01
**Date:** 2026-06-11
**Wall clock:** < 10 minutes before halt

## Verdict

HALT

## Stop Point

Task 1 halted during the initial three-lane baseline launch (`baseline_1`, `baseline_2`, `baseline_3`). `baseline_2` immediately produced persistent OpenAI authentication failures:

```text
AuthenticationError("Error code: 401 - {'error': {'message': 'Incorrect API key provided: sk-proj-...lbEA. You can find your API key at https://platform.openai.com/account/api-keys.', 'type': 'invalid_request_error', 'code': 'invalid_api_key', 'param': None}, 'status': 401}")
```

This is not Phase 6 data. It is an API credential failure. By the time the run was stopped, `baseline_2` had produced 362 `TASK-MAIN-*` records, all `ok=False` with the same `invalid_api_key` error, exceeding the handoff escalation boundary of more than 12 `ok=False` records for an entire baseline.

All active baseline lanes were stopped to prevent further spend.

## Preconditions

Preconditions passed with one explicit current-session override:

```text
11b-i present: 1200 records, 1180 ok, 20 predicted Intake tripwire failures
freeze tetrad present
both API keys syntactically set
task files present
AEGIS-eval still at v1
outputs_freeze_v1 absent
```

Deviation from the written handoff: the handoff's stale precondition expected at least 1190 ok records from 11b-i. The current PI-reviewed state is 1180 ok plus exactly 20 predicted Intake content-tripwire failures on `TASK-MAIN-SEC-038` and `TASK-MAIN-SEC-040`; the user's 2026-06-11 instruction explicitly treated that as a clean landing and unblocked 11b-ii.

## Partial Attempt

Partial records created before halt were quarantined outside the repository:

```text
/tmp/handoff11bii_halt_20260611_partial/
```

Quarantined partials:

```text
baseline_1: 1 record, 1 ok, estimated API cost $0.033756
baseline_2: 362 records, 0 ok, 362 invalid_api_key errors
baseline_3: 0 records
```

The canonical baseline output directories were cleaned back to their pre-handoff calibration-only state:

```text
baseline_1 main 0 cal 6
baseline_2 main 0 cal 6
baseline_3 main 0 cal 6
baseline_4 main 0 cal 6
baseline_5 main 0 cal 6
baseline_6 main 0 cal 6
```

Tracked calibration ledgers were restored. No partial baseline main records were committed.

## Tasks Not Run

Tasks 2-4 were not run:

- MANDATE-primary hold-out was not started.
- B1 hold-out was not started.
- Anonymization was not run.
- `outputs_freeze_v1` was not cut.

## Action Queue

1. Replace or repair `OPENAI_API_KEY` in `.env`. The key is present and starts with `sk-`, but OpenAI rejects it with HTTP 401 `invalid_api_key`.
2. Before rerunning 11b-ii, verify the OpenAI key with a minimal live OpenAI API call, not just a prefix check.
3. Re-fire HANDOFF_11b-ii after the key is fixed. The baseline output dirs have no partial `TASK-MAIN-*` files, so the next attempt starts clean.
4. Keep the 11b-i override in force: `1180/1200 ok` with the 20 predicted Intake tripwire records is the accepted MANDATE-primary main state.

## Deviations / Notes

- I launched `baseline_1`, `baseline_2`, and `baseline_3` concurrently, as allowed by the handoff's 3-way API concurrency boundary.
- I added `--skip-existing` to the baseline commands for resume safety. It did not skip any baseline main records because none existed at start.
- I stopped and cleaned up the partial baseline outputs after the `baseline_2` auth failure crossed the handoff escalation threshold.
- Existing tracked changes in `rag/embeddings/*` were unrelated to this handoff and were left unstaged.
