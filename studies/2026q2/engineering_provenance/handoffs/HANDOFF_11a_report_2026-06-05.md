# Handoff 11a Report: Phase 6 Pilot Smoke Test

**Codex session:** desktop session
**Eval host:** lattice-ws01
**Date:** 2026-06-05
**Wall clock:** ~37 minutes serialized RunRecord wall-clock for Handoff 11a execution

## Verdict

PROCEED

## Per-system Results

| system | records | ok | schema_valid_or_artifact | any_llm_fallback_runs | API cost | wall clock |
|---|---:|---:|---:|---:|---:|---:|
| `mandate_primary` | 6 | 6 | 6 | 0 | `$0.0000` | `678s` |
| `baseline_1` | 6 | 6 | 6 | n/a | `$0.2011` | `229s` |
| `baseline_2` | 6 | 6 | 6 | n/a | `$0.0324` | `28s` |
| `baseline_3` | 6 | 6 | 0 | n/a | `$0.3517` | `384s` |
| `baseline_4` | 6 | 6 | 6 | n/a | `$0.4400` | `394s` |
| `baseline_5` | 6 | 6 | 6 | n/a | `$0.2424` | `278s` |
| `baseline_6` | 6 | 6 | 6 | n/a | `$0.2378` | `229s` |

Total RunRecords:

```text
42 records
42 ok=True
```

Output directories:

```text
07_system_outputs/mandate_primary_pilot/
07_system_outputs/baseline_1_pilot/
07_system_outputs/baseline_2_pilot/
07_system_outputs/baseline_3_pilot/
07_system_outputs/baseline_4_pilot/
07_system_outputs/baseline_5_pilot/
07_system_outputs/baseline_6_pilot/
```

## Demo-finding Observations

MANDATE-primary on the six pilot tasks:

```text
COA count distribution:    {1: 6}
Interpreter mode counts:   {'deterministic_prefix': 4, 'clean_distillation': 2}
Validator gap-flagged:     1/6 runs
Binding refusal fallbacks: 0/6 runs
```

Interpretation:

- Decomposition single-COA prior reproduced exactly: all six MANDATE-primary pilot runs emitted one COA.
- Interpreter content-tripwire behavior reproduced as a mixed pattern: four deterministic-prefix outputs and two clean distillations.
- Validator gap acknowledgment remained sparse/unstable at pilot scale: one of six runs showed the rationale-pattern flag.
- Binding refusal did not fire in this smoke run: zero Binding fallbacks, which is within the handoff's expected `0-2` range.

## Cost and Runtime

Total API cost across all seven systems:

```text
$1.505282
```

Serialized RunRecord wall-clock total:

```text
2220.6 seconds
```

No retry was used. The total API cost was below the `$25` escalation boundary, and runtime remained below the `90 minute` escalation boundary.

## Anything that did NOT match demo-era expectations

- No apparatus-level surprises. Every system produced all six expected records with `ok=True`.
- `baseline_3` again produced no `schema_valid_or_artifact` count under the handoff summary script, matching the HANDOFF_04c expectation that B3's structurally-flat JSON is data rather than a halt.
- MANDATE-primary had zero `any_llm_fallback` runs in this smoke. This does not contradict the demo-era Binding-refusal finding; the handoff expected 0-2 Binding fallbacks at this scale.

## Provenance and Boundary Checks

- Freeze tetrad was present before execution: `corpus_freeze_v1`, `baseline_freeze_v1`, `gt_freeze_v1`, `perturbation_freeze_v1`.
- `AEGIS-eval/` was verified at `mandate-eval-primary-2026q2-v1` after HANDOFF_22 restored the missing marker and source files.
- `AEGIS-eval/configs/llm_defaults.json` retained production `llm_rag_index`: `rag/embeddings/enterprise-attack.jsonl`.
- The v2 Binding-refusal patch was not applied for this Phase 6 pilot smoke.
- No `04_ground_truth/` artifacts were modified.
- No anonymization was performed, per handoff scope.

## Deviations from this handoff

- HANDOFF_11a was re-fired immediately after HANDOFF_22 restored `AEGIS-eval/`. The earlier same-date HALT report at this path was overwritten by this successful rerun report; the original HALT remains preserved in commit `28f6f42`.
