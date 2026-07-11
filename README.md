# MANDATE 2026Q2 Evaluation — Replication Package

**Proposed repository name:** `mandate-eval-primary-2026q2` (matches the apparatus freeze tag).

This repository is the evidence and replication package for the pre-registered
2026Q2 comparative evaluation of **MANDATE** (Multi-Agent Nominal Decomposition
for Autonomous Task Execution), a tolerance-based task-specification framework
for autonomous agents. The evaluation measured three MANDATE conditions against
six baseline systems on a frozen three-domain corpus (120 tasks × 10 seeds)
plus a 30-task out-of-domain hold-out, graded 12,000 records at full coverage
under a three-judge ensemble (Claude Opus, GPT-4o, Gemini 2.5 Pro), and added
cross-vendor execution (4 LLM families), a 350-perturbation adversarial suite,
and ablations. Every deviation from the pre-registered protocol is documented
(13 entries, D-01–D-13).

**The headline claim, stated the way the data supports it:** canonical MANDATE
produces schema-valid, fully hash-traced, refusal-capable mandate-as-code at
scale — across domains, LLM vendor families, and adversarial perturbation —
with semantic coverage competitive with (not superior to) the strongest
agentic baseline under identical raw-text input. MANDATE's measured
contribution is the structural governance layer, not raw planning coverage.

## Read this first

| You want to… | Go to |
|---|---|
| Read the results | `supplement_pdfs/Empirical Evidence Supplemental.pdf` |
| Verify a specific claim against data | `docs/CLAIM_TO_DATA_MAP.md` |
| Replicate (tiered, from free to cluster) | `docs/REPLICATION_INSTRUCTIONS.md` + `docs/PARTIAL_REPLICATION.md` |
| See what routed where and why | `DEPOSIT_MAPPING.md` |
| Check the locked protocol + halt rules | `pre_registration/PROTOCOL_LOCK.md` |
| See every protocol deviation | `pre_registration/DEVIATIONS.md` + supplement Deviation Table (13 rows) |
| Know what cannot be replicated | `docs/KNOWN_GAPS.md` |

## Quickstart (read-only verification, no compute)

```bash
# Record counts match the supplement:
wc -l replication_package/v1_main/system_outputs/*.jsonl
# → mandate_primary 1200+300, cond_a 1200+300, cond_b 1200+300,
#   baseline_1 1206+300, baseline_2..6 1206 each
#   (each baseline file = 1200 TASK-MAIN-* + 6 TASK-CAL-* calibration records;
#    graded main-matrix n = 1200 per baseline, +300 hold-out for baseline_1)

# Full-coverage v2 grades (the comparative table's source):
wc -l replication_package/v1_main/grading/v2_full_coverage/ensemble_scores.jsonl   # 12000

# Structural validity of canonical MANDATE (Claim 1):
python3 -c "
import json
ok=sum(json.loads(l)['ok'] for l in open('replication_package/v1_main/system_outputs/cond_a_main.jsonl'))
print('cond_a main ok:', ok, '/ 1200')"

# Phase A adversarial results (100% prompt-injection structural pass):
wc -l replication_package/v2_complete/perturbations_mandate/*.jsonl   # 3500 + 350 + 350
```

## Package layout

- `supplement_pdfs/` — the three supplement documents (Empirical Evidence
  Supplemental, v2 Protocol Amendment, Engineering and Operational Provenance).
- `pre_registration/` — the locked protocol package: PROTOCOL_LOCK.md (κ≥0.40
  halt rule), analysis plan, prompts, forms, calibration tasks, DEVIATIONS.md.
- `replication_package/v0_pilot/`, `v0_5_pilot/` — the April 2026 pilot tiers
  backing the paper's §12 pilot tables.
- `replication_package/v1_main/` — the 2026Q2 main matrix: frozen corpus,
  ground truth, perturbation suite, per-system RunRecords (consolidated JSONL),
  v1 sampled grading (700) and v2 full-coverage grading (12,000), per-finding
  extracts, RunRecord schema.
- `replication_package/v2_complete/` — cross-vendor runs (1,200), MANDATE-side
  perturbation records (4,200), A3/A5 ablations (3,000), the all-ablations MVP
  (1,200; auxiliary), partial Phase B perturbation grades (14,685; paused at
  80.7% under Deviation D-13), Phase A structural-invariance report.
- `code/` — apparatus snapshot (7-role pipeline, judges, baselines,
  perturbation generator) + run scripts.
- `engineering_provenance/` — full handoff chronology (119 files) + cost
  ledger with the closeout addendum. Reviewers can skip this directory.
- `docs/` — replication instructions, environment spec, claim-to-data map,
  partial-replication guide, known gaps.

## Provenance

Frozen artifacts are pinned by git tags in the evaluation tree:
`corpus_freeze_v1`, `gt_freeze_v1`, `baseline_freeze_v1`,
`perturbation_freeze_v1`, `outputs_freeze_v1_1` (commit `5f4de54`);
apparatus tag `mandate-eval-primary-2026q2-v1` (commit `4f8af83`).
The evaluation executed against `mlt-stack 1.0.0rc1` (canonical MANDATE
implementation); artifacts verify against later stack releases, but
byte-faithful re-execution should use 1.0.0rc1.

## Status disclosures (read before citing)

- **Phase B perturbation grading is partial:** paused 2026-07-08 at
  14,685/18,200 main-pass grades (80.7%) under budget Deviation D-13;
  baseline_4 perturbation generation halted at 3,021/3,500 (86.3%);
  baselines 5–6 perturbation runs scoped out under D-12 (baseline_4 is the
  multi-agent-shell class representative). No cross-system semantic
  adversarial claims are made from partial grades. Resumable via
  `grade-v2 --skip-existing` against frozen records.
- **Confidence intervals** for the pre-registered contrast family were
  delivered 2026-07-10 (`analysis/bootstrap_contrasts_results.json`;
  script `code/scripts/bootstrap_contrasts.py`, seed 20260710); the wider
  9-system grid remains descriptive. Subjective judge outcomes
  (trace_completeness α=0.194, fabrication_count α=0.216) fell below the
  reliability threshold and are flagged wherever used; structural claims
  derive from artifact inspection.

  Note on `v1_main/grading/v1_sampled/judges_config.json`: the file
  records the pre-registered ensemble (Opus); the v1 cycle executed with
  Sonnet substituted under deviation D-08 and v2 restored Opus under
  D-10. `pre_registration/DEVIATIONS.md` carries the four long-form
  deviation narratives; the complete 13-entry structured table is §9 of
  the Empirical Evidence Supplemental in `supplement_pdfs/`.
- Cond-A receives pre-extracted structured input and is an upper-bound
  characterization, **not** an apples-to-apples comparator against baselines;
  the fair MANDATE comparator is Cond-B.

## Citation

Cite the paper and this repository by URL. See `CITATION.cff` and
`prior_published_paper/CITATION_TO_PAPER.md`.

## Licenses

- **Code** (`code/`, scripts): Apache License 2.0 — see `LICENSE`.
- **Data** (RunRecords, corpus, ground truth, grades): CC BY 4.0 — see `LICENSE-DATA`.
- **Pre-registration prompts and forms:** CC0.
- **Paper text:** not redistributed here; cite via the journal/preprint.
