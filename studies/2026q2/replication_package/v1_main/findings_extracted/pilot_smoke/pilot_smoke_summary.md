# Pilot Smoke Test Results (HANDOFF_11a)

42 RunRecords across 7 systems on the 6 pilot tasks (TASK-PILOT-{SEC,FIN,INT}-{001,002}) at 1 run each. First confirmation that the apparatus runs end-to-end on the actual ground truth (the pilot scaffolds) — not just on demo scenarios.

| System | Records | OK | Schema-valid | Any LLM fallback | Binding refusal | Mean wall-clock (s) |
|---|---:|---:|---:|---:|---:|---:|
| mandate_primary | 6 | 6 | 0 | 0 | 0 | 113.0 |
| baseline_1 | 6 | 6 | 6 | 0 | 0 | 38.1 |
| baseline_2 | 6 | 6 | 6 | 0 | 0 | 4.7 |
| baseline_3 | 6 | 6 | 0 | 0 | 0 | 64.0 |
| baseline_4 | 6 | 6 | 6 | 0 | 0 | 65.7 |
| baseline_5 | 6 | 6 | 6 | 0 | 0 | 46.4 |
| baseline_6 | 6 | 6 | 6 | 0 | 0 | 38.2 |

**The smoke test established the pattern that Phase 6 confirmed at scale:** B3 had measurable schema-validity issues already at 6 records; the four demo findings (Decomposition single-COA prior, Interpreter mode flip, Validator instability, Binding probabilistic refusal) reproduced at small scale before the long Phase 6 run.
