# Handoff 04c Report: B3 calibration completion

**Codex session:** desktop session
**Eval host:** lattice-ws01
**Date:** 2026-06-04
**Wall clock:** ~4 minutes

## Verdict

PROCEED

## Evidence

- baseline completed: `baseline_3`
- runs per task: 1
- seed base: 20260604
- Anthropic key check: present
- 04b B1 artifacts present: 6 RunRecords
- 04b B2 artifacts present: 6 RunRecords
- B3 final records: 6
- B3 `ok=True`: 6
- B3 `schema_valid=True`: 0
- B3 Anthropic cost: $0.196533
- B3 input tokens: 15,211
- B3 output tokens: 10,060

## Per-Task Schema Validity

| task_id | ok | schema_valid | schema_errors |
|---|---:|---:|---:|
| TASK-CAL-FIN-001 | True | False | 20 |
| TASK-CAL-FIN-002 | True | False | 32 |
| TASK-CAL-INT-001 | True | False | 17 |
| TASK-CAL-INT-002 | True | False | 4 |
| TASK-CAL-SEC-001 | True | False | 4 |
| TASK-CAL-SEC-002 | True | False | 32 |

## Verification Command

```text
baseline_3: 6 records, 6 ok, 0 schema_valid, $0.1965
  TASK-CAL-FIN-001: ok=True, schema_valid=False, errors=20
  TASK-CAL-FIN-002: ok=True, schema_valid=False, errors=32
  TASK-CAL-INT-001: ok=True, schema_valid=False, errors=17
  TASK-CAL-INT-002: ok=True, schema_valid=False, errors=4
  TASK-CAL-SEC-001: ok=True, schema_valid=False, errors=4
  TASK-CAL-SEC-002: ok=True, schema_valid=False, errors=32
```

## Phase 6 O4 Implication

B3 schema-validity rate on this calibration set is 0/6; Phase 6 will measure this across the 120 main tasks.

## Output Locations

- `07_system_outputs/baseline_3/`: six RunRecord JSON files plus `ledger.jsonl`

## Anything the PI must decide before proceeding

- None for Handoff 04c. The B1-B3 calibration matrix is complete as measurement data under the corrected rule.

## Deviations

- None from Handoff 04c. `schema_valid=False` was recorded as O4 measurement data and was not treated as a halt condition.
