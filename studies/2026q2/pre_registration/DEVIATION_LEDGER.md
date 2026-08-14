# Complete Deviation Ledger (D-01 – D-13)

The complete thirteen-entry deviation ledger in structured form (following
Willroth & Atherton, 2024). This table is the standalone, machine-findable
enumeration cited by the manuscript's Supplementary Information (SI S2); the
chronological narrative for the major entries is preserved in
`pre_registration/DEVIATIONS.md`, and the full log lives under
`replication_package/v1_main/findings_extracted/deviations/`. Content matches
the deposit's Empirical Evidence Supplemental §9.

| # | Date | Type / severity | Actual change | Effect on conclusions |
|---|---|---|---|---|
| D-01 | 2026-06-04 | Scope: ground truth | SME realism audit not executed; ground truth is Claude Opus 4.6 anchor scaffolds | all grades measured against unratified model-authored scaffolds; SME validation open |
| D-02 | 2026-06-04 | Scope: ablations | A3/A5 run at 1,500-record scale; A5 reclassified source-level after Finding 7 | ablation analysis reports A3 at scale; A5 ships as source-level variant |
| D-03 | 2026-06-10 | Apparatus / minor | watchdog halt refined (wall-clock AND all-roles `llm_used=False`) | measurement integrity improved; legitimate Intake failures not over-quarantined |
| D-04 | 2026-06-13 | Apparatus / minor | 300 contaminated hold-out records (Ollama outage) quarantined and regenerated | 0/300 contamination in regenerated hold-out; `outputs_freeze_v1_1` cut at corrected commit |
| D-05 | 2026-06-16 | Finding promotion / substantial | Intake content-tripwire (20/1,200) promoted to substantive finding | reproducible across all 10 seeds; trigger phrase identified |
| D-06 | 2026-06-04 | Scope: O5 phasing | O5 suite generated and frozen; runs scheduled with the full-coverage cycle | O5 outcome reports under the amended protocol |
| D-07 | 2026-06-17 | Apparatus / minor | grader patched for per-record checkpointing with regression tests | no methodology change; robustness improved |
| D-08 | 2026-06-18 | Sampling design / refinement | initial cycle ran stratified N=700 with Sonnet substituted for Opus and 10% IRR | superseded by full-coverage restoration (D-10) |
| D-09 | 2026-06-23 | Methodology refinement | shape-neutral rubric introduced; three measured conditions | the shape-neutral cycle is the source of cross-system claims |
| D-10 | 2026-06-23 | Methodology restoration | Opus judge restored; 20% double-grade specified | full-coverage grading completed 12,000/12,000; the double-grade component not executed before D-13 |
| D-11 | 2026-06-23 | Methodology restoration | O5 reactivated; Phase A complete (3,500 + 350 + 350) | structural-invariance outcome reported; semantic grading initiated as Phase B |
| D-12 | 2026-07-06 | Scope: Phase B baselines | perturbation runs scoped to B1–B4 (B4 as multi-agent-shell class representative) | CrewAI-/LangGraph-shell perturbation behavior not separately measured |
| D-13 | 2026-07-08 | Scope + budget | Phase B grading paused at 14,685/18,200 (80.7%); double-grade pass 1 at 816/3,640, pass 2 not started | no Phase B semantic claims; ungraded records preserved for future re-grade |

Note on D-10: the unexecuted 20% double-grade measures same-judge
repeatability. Cross-judge reliability of the shape-neutral full-coverage pass
has since been measured post hoc from the retained per-judge streams
(`figure_scripts/compute_reliability.py`; manuscript §5 and SI S3).
