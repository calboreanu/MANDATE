# HANDOFF 25 Report: Pytest Harnesses for Table 1 Evaluation Outputs

**Date:** 2026-07-01
**Codex session:** desktop session
**Scope:** AEGIS-eval frozen MANDATE Table 1 evidence gates

## Verdict

PROCEED

## Preconditions

- Stage 4 grading complete: `08_grading_v2/by_record/` has 12000 JSON records; `08_grading_v2/incomplete_grades/` has 0.
- HANDOFF_22 cross-vendor report: `Verdict: PROCEED`; Phi-3 completed 300/300.
- HANDOFF_24 Phase A table present at `09_analysis/HANDOFF_24_structural_invariance_phase_a.md`.
- Baseline full AEGIS suite before the harness: `1 failed, 1436 passed, 27 skipped`; the single failure was `tests/aegis/test_ingestion_regression_pack_script.py::test_ingestion_regression_pack_manifest`.

## What Changed

Added a frozen-output Table 1 harness:

- `AEGIS-eval/scripts/eval_table1_harness/__init__.py`
- `AEGIS-eval/scripts/eval_table1_harness/mapping.py`
- `AEGIS-eval/tests/mandate/test_table1_harness.py`

The new test module adds 12 row-level pytest gates for Table 1 rows 2-13 plus one coverage invariant asserting rows 2-13 are all mapped.

## Mapping Table

| Row | Metric | Frozen evidence source | Generator / source command | Gated frozen value | Tolerance |
|---:|---|---|---|---|---|
| 2 | Anchor field extraction | `eval_anchor_extraction_results.json` | `eval_anchor_extraction.py` | 20/44 complete extractions (45.45%) | exact counts; 1e-12 fraction |
| 3 | Gap detection precision | `eval_gap_detection_results.json` | `eval_gap_detection.py` | 30/31 precision (96.77%) | exact counts; 5e-5 fraction |
| 4 | Gap detection recall | `eval_gap_detection_results.json` | `eval_gap_detection.py` | 30/63 recall (47.62%) | exact counts; 5e-5 fraction |
| 5 | Trace chain integrity | `eval_trace_integrity_results.json` | `eval_trace_integrity.py` | 1/1 traced artifact passes | exact counts |
| 6 | Anchor hash (Algorithm 1) | `eval_anchor_hash_results.json` | `eval_anchor_hash.py` | 1/1 checked anchor hash passes | exact counts |
| 7 | COA diversity | `eval_coa_diversity_results.json` | `eval_coa_diversity.py` | 4/4 diversity indicators true on the COA artifact | exact counts |
| 8 | Cross-domain pipeline | `run6_pipeline.txt` | `pytest tests/mandate/test_domain*.py tests/mandate/test_domain_pipeline.py` | 90/90 domain-pipeline tests pass | exact pytest summary |
| 9 | Constraint grammar | `run7_constraints.txt` | `pytest tests/mandate/test_constraints.py` | 55/55 constraint tests pass, 1 skipped | exact pytest summary |
| 10 | NIST AI RMF mapping | `eval_rmf_mapping_results.json` | `eval_rmf_mapping.py` | 11/11 subcategories covered | exact counts; exact fraction |
| 11 | Registry matching | `eval_registry_matching_results.json` | `eval_registry_matching.py` | 1/1 registry reference has a valid match type | exact counts |
| 12 | Readiness scores | `eval_readiness_score_results.json` | `eval_readiness_scores.py` | 1/1 artifact gap report has readiness score; 0 invalid percentages | exact counts |
| 13 | Timing | `run11_timing.txt` | bash timing capture over the evidence pack | eval scripts alone `<0.2s`; all runs combined `~2.0s` | exact text markers |

## Verification

Targeted harness:

```text
13 passed in 0.02s
```

MANDATE slice:

```text
512 passed, 1 skipped in 1.44s
```

Full AEGIS suite after the harness:

```text
1 failed, 1449 passed, 27 skipped in 138.54s (0:02:18)
```

The only full-suite failure is the same pre-existing ingestion-regression manifest test observed in the precondition baseline. The Table 1 harness itself passes.

## Regeneration

No regeneration command was added. The handoff halt rule forbids a harness that requires regenerating `eval_*.py` outputs, and the evidence pack already contains frozen JSON outputs plus root-level `run*.txt` logs. The harness consumes those frozen artifacts only.

Rows 8, 9, and 13 do not have separate `eval_*_results.json` files in this AEGIS-eval extract. They are gated against the matching frozen run logs (`run6_pipeline.txt`, `run7_constraints.txt`, `run11_timing.txt`) from the same evidence pack.

## Notes

The HANDOFF_25 draft listed several expected filenames that are not present on disk:

- `eval_trace_chain_results.json` -> actual `eval_trace_integrity_results.json`
- `eval_nist_rmf_results.json` -> actual `eval_rmf_mapping_results.json`
- `eval_readiness_results.json` -> actual `eval_readiness_score_results.json`
- `eval_cross_domain_results.json`, `eval_constraint_grammar_results.json`, and `eval_timing_results.json` are absent; frozen `run*.txt` evidence is used instead.

The harness asserts the values recoverable from the frozen evidence pack in this AEGIS-eval extract. Some draft handoff values were stale relative to those frozen outputs, most notably anchor complete extraction (20/44, not 7/7), gap recall (30/63, not 30/31), trace integrity (1/1, not 2/2), registry matching (1/1, not 5/5), and timing (`<0.2s` eval-script total, not `<100ms`). This report records those source-of-truth adjustments.

## Closing Statement

Rows 2-13 of Table 1 are now pytest-gated under `AEGIS-eval/tests/mandate/test_table1_harness.py`; row 1 was already pytest-gated by the full suite. The audit caveat that Table 1 evaluation outputs can drift silently is closed for the frozen evidence artifacts present in this extract.
