# Claim-to-Data Map

Every load-bearing claim in the paper §12 Tier 2 and the Empirical Evidence
Supplemental, mapped to the exact in-repo file(s) that back it. Paths are
relative to the repository root. "Supp." = Empirical Evidence Supplemental.

| # | Claim (as stated) | Data | How to check |
|---|---|---|---|
| 1 | Canonical MANDATE structural validity at scale: Cond-A 1,500/1,500, Cond-B 1,500/1,500 ok | `replication_package/v1_main/system_outputs/cond_{a,b}_{main,holdout}.jsonl` | sum `ok` over 1,200+300 lines per condition |
| 2 | MANDATE-primary 1,480/1,500 (98.7%) with 20 reproducible Intake-tripwire failures on 2 tasks × 10 seeds | `v1_main/system_outputs/mandate_primary_{main,holdout}.jsonl`; verbatim failures in `v1_main/findings_extracted/finding_5_intake/` | count ok=false; confirm task IDs TASK-MAIN-SEC-038/040 |
| 3 | v2 comparative table (9 systems × 6 outcomes; Cond-B 0.864 min-cov vs ReAct 0.968; trace 2.000 vs 0.384) | `v1_main/grading/v2_full_coverage/ensemble_scores.jsonl` + `anonymization_mapping_full.json` | group by system, mean per outcome |
| 4 | Cond-A = structured-input upper bound (0.981 min-cov), not apples-to-apples | same as #3; input-condition documented in Supp. §2.5 and per-record `output` provenance | — |
| 5 | v1 κ halt: min pairwise κ 0.296 < 0.40 → pre-registered v2 supersession | `v1_main/grading/v1_sampled/v1_irr_report.json` (canonical IRR artifact, staged 2026-07-10); halt rule in `pre_registration/PROTOCOL_LOCK.md` §8 | read `min_pairwise_kappa` (0.2964, mission_intent_match, opus\|gemini) |
| 6 | Subjective-outcome reliability caveat (α: trace 0.194, fabrication 0.216; objective: gap 0.701, min-cov 0.612) | `v1_main/grading/v1_sampled/double_grade/pass{1,2}_scores.jsonl` (per-judge, staged 2026-07-10) + `v1_irr_report.json` | recompute α per outcome from pass1 `judge_scores` (verified: gap/min-cov/fab exact; trace 0.203 interval-metric vs 0.194 reported, metric-choice sensitivity) |
| 7 | Cross-vendor structural validity 1,200/1,200 with per-vendor fallback rates (Llama/Phi 100%; Mistral 66.7% overall; Qwen 5.3% overall, 16% SEC-only) | `v2_complete/cross_vendor/cond_b_xvendor_*.jsonl` | sum `ok`; rate of `any_llm_fallback` per vendor per domain (verified 2026-07-10, all 12 cells) |
| 8 | Phase A adversarial: Cond-A/B 100% ok all 7 types; MP 94% on contradictory_constraints; 100% prompt-injection structural pass ×3 conditions | `v2_complete/perturbations_mandate/*.jsonl`; report `v2_complete/HANDOFF_24_structural_invariance_phase_a.md` | group by perturbation_type, ok-rate + trace length ≥6 |
| 9 | Binding structured refusal at scale: 244/1,500 (anchor demands more COAs than Decomposition emits; refusal object omits `decision_summary`, logged as byte-identical schema-validation fallback; deterministic path completes the record) | `v1_main/findings_extracted/finding_4_binding/per_record_refusal.jsonl` (+ verbatim refusal JSON at demo scale in Supp. §4.4) | count `binding_fallback: true` = 244; confirm single byte-identical `fallback_reason` prefix; per-domain rates FIN 2.0/INT 40.2/SEC 13.5/hold-out 7.0% |
| 10 | Decomposition single-COA prior across 1,480 records | `v1_main/findings_extracted/finding_1_decomposition/`; recompute from `mandate_primary_main.jsonl` | count COAs per record |
| 11 | Out-of-domain hold-out structurally valid through the same pipeline | `v1_main/system_outputs/*_holdout.jsonl` | sum `ok` per system |
| 12 | A3 ablation clean at scale; A5 emits registry_reference despite ablation (Finding 7) | `v2_complete/ablations/a{3,5}_*.jsonl` | check `gap_reports` emptiness (A3) and `registry_reference` presence (A5) |
| 13 | All seven ablations run end-to-end (auxiliary MVP) | `v2_complete/ablation_mvp/` | per-dir record counts + SUMMARY.md |
| 14 | Phase B pause: 14,685/18,200 grades (80.7%); b4 halted 3,021/3,500; b5/b6 scoped out | `v2_complete/grading_v2/perturbation_ensemble_scores_partial.jsonl` (line count verified = 14,685), `phase_b_status_at_closeout.json`; Deviations D-12/D-13 in Supp. §9 + `pre_registration/DEVIATIONS.md` | `wc -l`; read status JSON (its b4 figure, 2,993, is a mid-drain snapshot; final tree count 3,021) |
| 15 | Cost reality: projections Sonnet-priced; Opus restoration ~5×/grade; realized spend exceeds projection | `engineering_provenance/cost_log/cost_ledger.md` (closeout addendum) + CSV/JSON | read flags + addendum |
| 16 | Pilot tables (500-test suite 99.8%; 8 scenarios; 32/32 property checks; 40/48 LLM invocations) | `replication_package/v0_pilot/` (+ `v0_5_pilot/` for cross-profile 5/6) | open eval JSONs; compare to `paper_section_12_tables/` |
| 17 | Freeze-tag provenance chain | evaluation tree git tags (listed in README §Provenance); apparatus snapshot in `code/` | `git tag -l` in the source tree |

| 18 | Pairwise contrast CIs + Holm-corrected paired tests (paper Table v2-contrasts; e.g. Cond-B vs B3 min-cov Δ −0.112 [−0.129, −0.095]) | `analysis/bootstrap_contrasts_results.json` + `analysis/bootstrap_contrasts_table.md` | rerun `code/scripts/bootstrap_contrasts.py` (seed 20260710, B=10,000; ~4s) |

**What is deliberately NOT claimable from this repo:** cross-system semantic
adversarial-resistance rankings (Phase B partial, #14); substantive
superiority at the Cond-A/B3 boundary (CI excludes zero but sits below the
pre-registered MDE, #18); human-expert baseline comparisons (never run —
`docs/KNOWN_GAPS.md`).
