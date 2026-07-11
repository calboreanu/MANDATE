# Baseline Calibration Results (HANDOFF_04, 04b, 04c)

36 RunRecords across 6 baselines on the 6 calibration tasks (TASK-CAL-{FIN,INT,SEC}-{001,002}). Calibration confirmed each baseline runs end-to-end against a live key and produced the schema-validity rates that later replicated at Phase 6 main matrix scale.

| Baseline | Records | OK | Schema-valid | Rate |
|---|---:|---:|---:|---:|
| baseline_1 | 6 | 6 | 6 | 100.0% |
| baseline_2 | 6 | 6 | 5 | 83.3% |
| baseline_3 | 6 | 6 | 0 | 0.0% |
| baseline_4 | 6 | 6 | 6 | 100.0% |
| baseline_5 | 6 | 6 | 6 | 100.0% |
| baseline_6 | 6 | 6 | 6 | 100.0% |

## Replication to Phase 6 scale

The B3 0/6 calibration schema-validity result replicated at 0/1205 at the Phase 6 main matrix. The same structural failure mode (ReAct producing arrays of strings instead of arrays of objects) is stable across 200x more records.
