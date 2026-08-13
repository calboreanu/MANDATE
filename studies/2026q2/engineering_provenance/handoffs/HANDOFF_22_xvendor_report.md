# HANDOFF_22 cross-vendor Cond-B status

Updated: 2026-06-26T02:41:50.153219+00:00

Selection:
- 75 task IDs x 4 runs = 300 records
- Rule: HANDOFF_22 adapted to on-disk 120-task main corpus: 25 task IDs per domain, run with runs_per_task=4 to yield 100 records per domain and 300 records total.

| Vendor | Model | State | Records | OK-rate | Mean ms | Fallback | Trace completeness | Mean COAs | Mean gaps |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| qwen | `qwen2.5:32b` | completed | 300/300 | 100.0% | 132053.3 | 5.3% | 100.0% | 0.00 | 4.81 |
| llama | `llama3.2:3b` | completed | 300/300 | 100.0% | 60996.1 | 100.0% | 100.0% | 0.00 | 4.52 |
| mistral | `mistral:7b` | completed | 300/300 | 100.0% | 35523.1 | 66.7% | 100.0% | 0.00 | 5.61 |
| phi | `phi3:14b` | completed | 300/300 | 100.0% | 128166.2 | 100.0% | 100.0% | 0.00 | 3.76 |

Verdict: PROCEED
