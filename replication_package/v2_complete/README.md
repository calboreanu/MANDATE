# v2_complete — 2026Q2 v2-Cycle Evidence (T5, closed out 2026-07-08)

The v2 cycle's additional evidence beyond the main matrix. Everything here is
disk-verified; partial layers are labeled as such and are resumable, not
abandoned (Deviations D-12/D-13).

## cross_vendor/ (1,200 records; complete)
`cond_b_xvendor_{qwen,llama,mistral,phi}.jsonl` — 300 records each
(stratified 100 × FIN/INT/SEC), all structurally valid. Read with the
fallback disclosure: on Llama 3.2 (3B) and Phi-3 (14B) the LLM-augmented
Interpreter fails schema validation on 100% of records and the deterministic
fallback produces the valid output (per-record fields `any_llm_fallback`,
`fallback_roles`). Cross-vendor structural completeness demonstrates the
apparatus' defense-in-depth chain, **not** LLM-Interpreter invariance.

## perturbations_mandate/ (4,200 records; Phase A complete 2026-07-01)
- `mandate_primary_perturbations.jsonl` — 3,500 (350 perturbations × 10 seeds).
- `cond_a_perturbations.jsonl`, `cond_b_perturbations.jsonl` — 350 each
  (deterministic, 1 seed).
Phase A structural results: Cond-A and Cond-B 100% ok + full trace on all
seven perturbation types; MANDATE-primary 100% on six of seven, 94% on
contradictory_constraints; **100% structural pass on prompt_injection across
all three conditions.** Report: `HANDOFF_24_structural_invariance_phase_a.md`.

## ablations/ (3,000 records; complete)
`a3_no_gap_analysis_{main,holdout}.jsonl` (1,200+300) and
`a5_no_registry_{main,holdout}.jsonl` (1,200+300). A5 emits
registry_reference despite the ablation — the apparatus-level invariant
characterized as Finding 7.

## ablation_mvp/ (1,200 records; auxiliary)
Deterministic demonstration that the canonical engine (mlt-stack 1.0.0rc1)
and **all seven** pre-registered ablations run end-to-end (8 systems × 150
tasks, judge-ready layout). Auxiliary evidence; not cited by the v2
supplement; complements the full-scale A3/A5 runs above and the
described-only status of the source-level ablations.

## grading_v2/ (partial by documented deviation)
- `perturbation_ensemble_scores_partial.jsonl` — **14,685** main-pass
  perturbation grades (80.7% of the 18,200-record scoped set) at the D-13
  pause. Complete for all three MANDATE conditions (4,200/4,200) and
  baseline_2; near-complete for baseline_1 (3,498) and baseline_3 (3,487);
  baseline_4 ungraded at pause.
- `phase_b_status_at_closeout.json` — the launcher's status file at closeout
  (per-system generation and grading states, D-12 scope-outs).
**No cross-system semantic adversarial-resistance comparison should be drawn
from the partial grades.** Baseline perturbation raw records (B1–B3 at 3,500
each; B4 at 3,021) are not shipped in-repo; they remain on the frozen
evaluation tree and are consolidatable on request via the bulk staging
script in the submission bundle.
