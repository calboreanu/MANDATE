# Handoff 04b Report: B1-B3 Phase 4 calibration

**Codex session:** desktop session
**Eval host:** lattice-ws01
**Date:** 2026-06-04
**Wall clock:** ~7 minutes before HALT

## Verdict

HALT

## Evidence

- calibration tasks found: 6
- rerun reason: OpenAI account/quota issue from prior attempt reported resolved
- systems attempted: `baseline_1`, `baseline_2`, `baseline_3`
- runs per task: 1
- seed base: 20260604
- Anthropic key check: present
- OpenAI key check: present
- apparatus baseline test gate: 35 passed

| baseline | provider/model | records | ok | schema_valid | input_tokens | output_tokens | cost_usd |
|---|---|---:|---:|---:|---:|---:|---:|
| baseline_1 | anthropic/claude-sonnet-4-6 | 6 | 6 | 6 | 2,986 | 11,372 | 0.179538 |
| baseline_2 | openai/gpt-4o | 6 | 6 | 5 | 2,705 | 2,734 | 0.034102 |
| baseline_3 | anthropic/claude-sonnet-4-6 | 3 | 3 | 0 | 6,113 | 4,289 | 0.082674 |
| total | mixed | 15 | 15 | 11 | 11,804 | 18,395 | 0.296314 |

Anthropic cost: $0.262212.

OpenAI cost: $0.034102.

Total recorded calibration cost: $0.296314, below the $10 escalation ceiling.

## B2 First-Call Auth Check Result

The `OPENAI_API_KEY` precondition was satisfied and the first B2 RunRecord completed with `ok=True` and `schema_valid=True`. The prior `insufficient_quota` condition is resolved for this eval host/key.

B2 still had one schema-invalid output:

```text
baseline_2__TASK-CAL-INT-001__r01:
minimum/0/threshold: 25 is not of type 'string', 'null'
```

This single B2 schema failure did not by itself cross the handoff's "more than one task" escalation threshold, but it remains part of the definition-of-done failure.

## B3 Schema Halt

B3 produced three RunRecords before the run was stopped. All three had `ok=True` but `schema_valid=False`, crossing the handoff escalation rule for more than one schema-invalid task in a baseline.

Examples:

```text
baseline_3__TASK-CAL-FIN-001__r01:
constraints is not of type 'array'
minimum is not of type 'array'
suspected_gaps is not of type 'array'
target is not of type 'array'

baseline_3__TASK-CAL-FIN-002__r01:
constraints/0 is not of type 'object'
minimum is not of type 'array'
suspected_gaps/0: 'field' is a required property
suspected_gaps/0: 'reason' is a required property

baseline_3__TASK-CAL-INT-001__r01:
constraints/0 is not of type 'object'
minimum is not of type 'array'
```

## Verification Command

```text
baseline_1: 6 records, 6 ok, 6 schema_valid
baseline_2: 6 records, 6 ok, 5 schema_valid
baseline_3: 3 records, 3 ok, 0 schema_valid
```

## Output Locations

- `07_system_outputs/baseline_1/`: six RunRecord JSON files plus `ledger.jsonl`
- `07_system_outputs/baseline_2/`: six RunRecord JSON files plus `ledger.jsonl`
- `07_system_outputs/baseline_3/`: three RunRecord JSON files plus `ledger.jsonl`; run stopped after the schema halt condition

## Anything the PI must decide before proceeding

- Decide whether B3's ReAct baseline needs prompt/parser/schema correction before calibration can proceed, because it produced multiple schema-invalid records even though each run returned `ok=True`.
- Decide whether to rerun or otherwise address the single B2 schema-invalid record after the B3 blocker is resolved.
- Do not treat B1-B3 as Phase 4 calibrated until all 18 records complete with `ok=True` and `schema_valid=True`.

## Deviations

- Prior H04b output directories were cleared before the rerun so stale failed B2 records from commit `90fcac8` could not be counted as current evidence.
- `baseline_3` was stopped after three schema-invalid records, to avoid additional Anthropic spend once the handoff escalation threshold had been crossed.
- No retry was attempted because the observed blocker was schema invalidity, not a transient API rate-limit error.
