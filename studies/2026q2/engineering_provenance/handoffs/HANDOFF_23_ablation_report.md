# HANDOFF_23 A3/A5 Ablation Report

Generated: 2026-06-26T02:44:20.015425+00:00

## Per-Ablation Summary

| Ablation | OK records | OK-rate | Mean wall ms | Nonempty gap reports | Nonempty registry refs |
| --- | ---: | ---: | ---: | ---: | ---: |
| A3 no_gap_analysis | 1500/1500 | 100.0% | 3.6 | 0 | 1500 |
| A5 no_registry | 1500/1500 | 100.0% | 3.6 | 0 | 1500 |

## Comparative Table

| System | OK records | OK-rate | Mean wall ms | Mandate-as-code records | Gap-report status records | Mean COAs | Mean trace length |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MANDATE-primary | 1480/1500 | 98.7% | 106018.5 | 1480 | 20 | 0.00 | 5.93 |
| A3 no_gap_analysis | 1500/1500 | 100.0% | 3.6 | 1500 | 0 | 0.00 | 6.00 |
| A5 no_registry | 1500/1500 | 100.0% | 3.6 | 1500 | 0 | 0.00 | 6.00 |

## Structural Checks

- A3 gap-report suppression: 1500/1500 records have empty gap_reports.
- A5 registry suppression: 0/1500 records have empty/absent registry_reference.

## Artifact Field Presence

A3 artifact fields:

```json
{
  "anchor": 1500,
  "courses_of_action": 1500,
  "generated": 1500,
  "mandate_id": 1500,
  "metadata": 1500,
  "recommendation": 1500,
  "registry_reference": 1500,
  "trace": 1500,
  "version": 1500
}
```

A5 artifact fields:

```json
{
  "anchor": 1500,
  "courses_of_action": 1500,
  "generated": 1500,
  "mandate_id": 1500,
  "metadata": 1500,
  "recommendation": 1500,
  "registry_reference": 1500,
  "trace": 1500,
  "version": 1500
}
```

## Implications

- A3 tests whether gap-report emission is an output phenomenon while the pipeline still runs.
- A5 tests whether registry resolution is modular under the same local Ollama role stack.

Verdict: HALT-FAIL (A5 emitted registry_reference)
