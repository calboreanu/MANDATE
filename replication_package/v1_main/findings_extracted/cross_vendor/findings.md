# Cross-Vendor Cond-B Structural-Invariance Pilot (HANDOFF_22)

**Analysis date:** 2026-07-01 (regenerated) · **Source:** `07_system_outputs/cond_b_xvendor/` · **Vendors analyzed:** 4 of 4 (all completed 2026-06-25 through 2026-06-26)
**Condition:** Cond-B = *MANDATE v1.0.0rc1, LLM-augmented Interpreter, end-to-end* over the stratified-75-task × 4-run selection (300 records/vendor).

## Per-vendor aggregates

| Vendor | Model | n | ok-rate | mean wall (s) | P2 trace rate | mean COAs | mean gaps | anchor-hash uniq. | LLM fallback rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen 2.5 (32B) | qwen2.5:32b | 300 | 1.00 | 132.1 | 1.00 | 2.28 | 4.81 | 0.257 (77 uniq) | 5.3% |
| Llama 3.2 (3B) | llama3.2:3b | 300 | 1.00 | 61.0 | 1.00 | 2.33 | 4.52 | 0.250 (75 uniq) | 100.0% |
| Mistral (7B) | mistral:7b | 300 | 1.00 | 35.5 | 1.00 | 2.33 | 5.61 | 0.250 (75 uniq) | 66.7% |
| Phi-3 (14B) | phi3:14b | 300 | 1.00 | 128.2 | 1.00 | 2.28 | 3.76 | 0.260 (78 uniq) | 100.0% |

These per-vendor numbers reproduce the apparatus's own `HANDOFF_22_xvendor_status.json` metrics exactly for ok-rate, mean wall clock, trace completeness, and mean gap count — the cross-check that confirms the corrected field paths are the right ones. **COA count is the one metric where this analysis and the apparatus disagree: the apparatus reports 0.0 (a bug), the truth is ~2.3 (see COA note below).**

**LLM fallback rate is the critical caveat.** On Llama 3.2 and Phi-3, the any-role LLM fallback union reaches 100% of records (Interpreter-only schema-validation failures: Llama 64%, Phi-3 20%; the remainder of the union comes from the other roles); the apparatus' deterministic fallback path produces the structural completeness on those records. On Mistral, fallback is 66.7% (all-domain aggregate). Only Qwen 2.5 has a low fallback rate (5.3%). The 1200/1200 structural completeness demonstrates **apparatus safety-chain invariance across LLM capability tiers**, not LLM-Interpreter invariance across all four vendors uniformly.

Per-vendor per-domain fallback breakdown:

| Vendor | FIN | INT | SEC |
|---|---:|---:|---:|
| Qwen 2.5 (32B) | 0% | 0% | 16% |
| Llama 3.2 (3B) | 100% | 100% | 100% |
| Mistral (7B) | 4% | 96% | 100% |
| Phi-3 (14B) | 100% | 100% | 100% |

**COA distribution is bimodal (1 or 3, never 2).** Qwen 108×1-COA / 192×3-COA; Llama and Mistral 100×1 / 200×3; Phi-3 108×1 / 192×3. The single-COA cases are the constrained/fallback path; the 3-COA cases are full course-of-action generation. This bimodality is itself a structural signature of the Decomposition role.

**Reading the anchor-hash uniqueness column.** Uniqueness ≈ 0.25 is *expected and good*: it is ≈ 75 unique anchors / 300 records, i.e. the 4 runs of a given task collapse to (nearly) one anchor — evidence of **within-vendor determinism** at temperature 0. Qwen's 77 (vs. 75 tasks) shows 2 tasks with minor run-to-run anchor variation; Phi-3's 78 shows 3 tasks with variation. Llama and Mistral were perfectly deterministic within-vendor.

## Cross-vendor pairing (300 shared task_id × run_idx tuples, 4 vendors)

| Signal | Result |
|---|---|
| Tuples where **all 4 vendors** produce a P2-complete (≥6-entry) trace | **300 / 300 (100%)** |
| Mean cross-vendor variance of **COA count** | Near-zero (bimodal {1,3} pattern reproduces across vendors) |
| Mean cross-vendor variance of gap-report count | Variable across vendors (Mistral highest at 5.61 mean; Phi-3 lowest at 3.76) |
| Tuples where all 4 vendors emit the same `anchor_hash` | **0 / 300 (0%)** (expected: anchor content is LLM-dependent) |

## Bottom line

**Structural completeness is verified across 4 LLM vendor families (Qwen 2.5 32B, Llama 3.2 3B, Mistral 7B, Phi-3 14B).** Every one of 1200 records is structurally valid: 100% ok-rate, 100% six-entry hash-chained trace completeness, COA emission on every record, and gap-report emission on every record. On 2 of 4 vendors (Llama and Phi-3), that structural completeness relies on the apparatus' deterministic fallback path on every record, because at least one role's LLM path fails per record (any-role union 100%; Interpreter-only schema-validation failures are 64% and 20% respectively). The formal scaffold MANDATE imposes is therefore **apparatus-guaranteed** rather than LLM-provided on those two vendors: MANDATE's defense-in-depth chain (LLM attempts extraction; schema validator catches failures; deterministic fallback fires) produces the structural completeness across the full vendor mix.

**Honest caveat — invariance is structural, not semantic.** The `anchor_hash` is *never* identical across vendors (0/300): different LLM families extract different `minimum`/`target`/`constraints` content for the same task, so the anchors differ even though their structure is uniform. This is the expected behaviour of an LLM-augmented interpreter and is **not** a structural-invariance failure — the invariant is the *form* (roles, trace chain, COA/gap discipline, validity), not the verbatim *content*. Gap-count also varies across vendors (mean variance 3.43), consistent with content-level differences in how many specification gaps each model surfaces.

## COA-count note (RESOLVED — apparatus metric is buggy; this analysis is authoritative)

The apparatus `HANDOFF_22_xvendor_status.json` reports `mean_coa_count = 0.0` for all vendors. **That is a bug, not the truth.** Root cause: `scripts/run_handoff22_xvendor.py::_coa_count()` scans the artifact for the keys `("candidate_coas", "candidate_courses_of_action", "coas")` — none of which exist in the records — and returns `0` when none match. The real field is `output.artifact.courses_of_action`, present and fully populated on **300/300 records for every vendor**; each COA entry is a complete object (`coa_id`, `approach`, `procedures`, `task_dag`, `risk_assessment`, `off_nominal_triggers`). Verified: zero records carry any of the three keys the apparatus looks for. The authoritative mean COA counts (Qwen 2.28, Llama 2.33, Mistral 2.33) are computed from `courses_of_action` and reported above. **Recommended fix for the lead analyst:** add `"courses_of_action"` to the key list in `_coa_count()` (first position), then the apparatus status will self-correct on its next write.

## LaTeX table (paste-ready for supplement §1.2 Claim 3)

```latex
\begin{tabular}{llrrrrrr}
\toprule
Vendor & Model & $n$ & ok-rate & mean wall (s) & P2 rate & mean COAs & mean gaps \\
\midrule
Qwen 2.5 (32B) & qwen2.5:32b & 300 & 1.00 & 132.1 & 1.00 & 2.28 & 4.81 \\
Llama 3.2 (3B) & llama3.2:3b & 300 & 1.00 &  61.0 & 1.00 & 2.33 & 4.52 \\
Mistral (7B)   & mistral:7b  & 300 & 1.00 &  35.5 & 1.00 & 2.33 & 5.61 \\
Phi-3 (14B)    & phi3:14b    & 300 & 1.00 & 128.2 & 1.00 & 2.28 & 3.76 \\
\bottomrule
\end{tabular}
% Cross-vendor: 300/300 task-run tuples P2-complete across all 4 vendors (100%);
% COA-count cross-vendor variance 0.024 (near-invariant); gap-count variance 3.43;
% 0/300 share an identical anchor_hash (structural invariance holds; anchor content is vendor-dependent).
% COA means computed from output.artifact.courses_of_action; the apparatus status mean_coa_count=0.0 is a known bug (stale key list in _coa_count).
% LLM fallback rates (see per_vendor_aggregates.json): Qwen 5.3%, Llama 100%, Mistral 66.7%, Phi-3 100%.
```

All four vendor rows are populated from `per_vendor_aggregates.json` (regenerated 2026-07-01). Supplement §1.2 Claim~3 carries the authoritative per-vendor per-domain fallback breakdown.


*Correction 2026-07-17: fallback rates in this note are any-role union rates; earlier wording attributed them to Interpreter schema validation alone. See docs/ERRATA.md.*
