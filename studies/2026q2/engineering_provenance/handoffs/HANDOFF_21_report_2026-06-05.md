# Handoff 21 Report: Ground Truth and Perturbation Freezes

**Codex session:** desktop session
**Eval host:** lattice-ws01
**Date:** 2026-06-05
**Wall clock:** <5 minutes

## Verdict

PROCEED

## Artifact Verification

| artifact | expected | observed | parse_ok |
|---|---:|---:|---:|
| `04_ground_truth/pilot_scaffolds/anchor_scaffolds.jsonl` | 6 | 6 | 6/6 |
| `04_ground_truth/main_scaffolds/anchor_scaffolds.jsonl` | 120 | 120 | 120/120 |
| `04_ground_truth/holdout_scaffolds/anchor_scaffolds.jsonl` | 30 | 30 | 30/30 |
| `06_perturbations/perturbation_suite.jsonl` | 350 | 350 | n/a |

Perturbation type counts:

```text
surface_noise=50
ambiguity_injection=50
contradictory_constraints=50
prompt_injection=50
missing_required_field=50
out_of_distribution_input=50
length_perturbation=50
```

## Freeze Tags

| tag | annotated tag hash | peeled commit |
|---|---|---|
| `baseline_freeze_v1` | `0fb2eff9be3b3f5f911db38532c9b1010f8b2d39` | `05fc0aa87baed57d2c1a5ad62f14f02028eaaf3e` |
| `corpus_freeze_v1` | `de4417dfaef4d6748d164bc31764b8d3180f5836` | `05fc0aa87baed57d2c1a5ad62f14f02028eaaf3e` |
| `gt_freeze_v1` | `5e624ac0d22def417f4de8af25981eb6722851b5` | `068fe94ae152d1ffed95074f231e81627f551e65` |
| `perturbation_freeze_v1` | `acf756c65926f72ccb8b634c13130c37f6f22279` | `068fe94ae152d1ffed95074f231e81627f551e65` |

Final freeze tag state:

```text
baseline_freeze_v1
corpus_freeze_v1
gt_freeze_v1
perturbation_freeze_v1
```

## Anything the PI must decide before proceeding

- None for Handoff 21. The four-tag freeze set is complete.

## Deviations from this handoff

- None. No ground-truth or perturbation artifact files were modified.
