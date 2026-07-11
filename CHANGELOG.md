# Changelog — MANDATE 2026Q2 Evaluation Deposit

## v2-closeout+contrasts — 2026-07-10

- Claim-to-data mapping pass: every §12 Tier-2 number recomputed from
  deposit data (comparative table 63/63 values exact; structural counts;
  cross-vendor 12/12 cells; perturbation strata; IRR artifacts).
- Bootstrap contrasts delivered (pre-registered in the v2 Amendment
  statistical-power section): `code/scripts/bootstrap_contrasts.py`,
  results in `analysis/` (seed 20260710, B=10,000; per-record + task-
  clustered CIs; Holm-corrected paired Wilcoxon on 120 task means).
- v1 IRR evidence staged into the deposit:
  `v1_main/grading/v1_sampled/v1_irr_report.json` (canonical kappa/alpha
  artifact) and `double_grade/pass{1,2}_scores.jsonl` (per-judge scores;
  alpha recomputation verified).
- CLAIM_TO_DATA_MAP corrections: rows 5/6 now executable; row 7 Qwen
  fallback corrected to 5.3% overall (16% SEC-only); row 9 rewritten to
  the disk-verifiable refusal signature; row 14 annotated for the b4
  2,993-vs-3,021 snapshot-timing difference; row 18 added (contrasts).
- KNOWN_GAPS #3 (CIs) closed; #5 annotated.
- Supplement updated: new Pairwise Contrasts subsection; threats items
  on CIs and multiple-comparison correction marked delivered; D-10 row
  qualified (v2 20% double-grade IRR not executed before D-13 pause);
  grading-methodology paragraph states executed IRR per cycle.

## v2-closeout — 2026-07-08

- Stage 4 v2 full-coverage grading complete: 12,000/12,000 records, zero
  incompletes, shape-neutral rubric, pre-registered Opus/GPT-4o/Gemini ensemble
  (Deviations D-09/D-10).
- Cross-vendor Cond-B complete: 1,200/1,200 across Qwen 2.5 32B, Llama 3.2 3B,
  Mistral 7B, Phi-3 14B, with per-vendor deterministic-fallback disclosure.
- O5 adversarial Phase A complete (2026-07-01): 4,200 MANDATE-condition
  records; 100% structural pass on prompt injection across all three
  conditions (D-11).
- Ablations A3/A5 at 1,500-record scale; all-ablations MVP (1,200 records)
  added as auxiliary evidence.
- Phase B baseline perturbation generation: B1–B3 complete (3,500 each);
  B4 halted at 3,021/3,500 (86.3%) at closeout; B5–B6 scoped out (D-12).
- Phase B semantic grading paused at 14,685/18,200 (80.7%) under budget
  Deviation D-13; resumable from frozen records.
- Deviation table extended to 13 entries (added D-12, D-13).
- Cost ledger closeout addendum: grading projections were Sonnet-priced;
  D-10's Opus restoration raised per-grade cost ~5×; provider dashboards
  authoritative for realized spend.

## v1 — 2026-06

- Frozen corpus (120 main + 30 hold-out + 6 pilot), ground truth,
  350-perturbation suite, baseline configs (freeze tags).
- Main-matrix generation: MANDATE-primary, Cond-A, Cond-B, baselines B1–B6.
- v1 sampled grading (N=700) engaged the PROTOCOL_LOCK §8 κ halt
  (min pairwise κ = 0.296 < 0.40), triggering the pre-registered v2
  shape-neutral rubric supersession (D-08/D-09).
- Five substantive findings characterized from on-disk records
  (content-tripwires, binding refusal, decomposition prior).
