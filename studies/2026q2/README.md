# MANDATE 2026Q2 Study — Deposited Evidence and Verification Package (with Partial Replication Apparatus)

**Study-release version:** `2026.08.13.1`

**Repository and path:** `calboreanu/MANDATE`, `studies/2026q2/`

This directory is the deposited evidence and verification package for the
protocol-governed 2026Q2 comparative evaluation of **MANDATE** (Multi-Agent Nominal Decomposition
for Autonomous Task Execution), a tolerance-based task-specification framework
for autonomous agents. The evaluation measured three MANDATE conditions against
six baseline systems on a frozen three-domain corpus (120 tasks × a recorded
10-run schedule)
plus a 30-task out-of-domain hold-out, graded 12,000 records at full coverage
under a three-judge ensemble (Claude Opus, GPT-4o, Gemini 2.5 Pro), and added
cross-vendor execution (4 LLM families), a 350-perturbation adversarial suite,
and ablations. Every deviation from the locked protocol is documented (13 entries,
D-01–D-13; standalone structured ledger at
`pre_registration/DEVIATION_LEDGER.md`). The campaign is protocol-governed,
not pre-registered: the released registration carries an unfilled lock-date
field and no externally timestamped pre-data registration, and the executed
analysis deviates materially from the locked plan (hypothesis dispositions in
the manuscript's Supplementary Information).

**The study result, stated as one result:** MANDATE produced schema-valid,
fully hash-traced specification artifacts at scale; on the one semantic
outcome whose measured full-coverage reliability clears the protocol floor
(minimum coverage, Krippendorff α = 0.855), it measures below the strongest
agentic comparator under identical raw-text input (Δ = −0.112, consistent in
direction across all three judges and 112/120 tasks). The retained structured result fields also exposed a result-state defect in
the evaluated `1.0.0rc1` implementation: blocking or insufficient
specifications could coexist with `ok=true`. The successor `1.0.3`-derived
implementation therefore underwent a focused, generation-only contract check
on the frozen canonical conditions. Its purpose was to determine whether every
record carrying a blocking or insufficient-for-automation signal was routed to
an explicit non-executable state. All 2,999 such records were non-executable;
zero routing-contract violations were observed. This post-hoc check establishes
conformance of that routing rule on the study corpus; it does not establish
gap-detection accuracy, executable-state specificity, downstream operational
fitness, or a controlled causal effect of the code change.

This directory is one study deposit within the public MANDATE repository.
Historical directory labels remain only
to preserve the executed chronology, immutable hashes, and citation anchors;
they are not separate study results or separate releases.

## Read this first

| You want to… | Go to |
|---|---|
| Read the results | `supplement_pdfs/Empirical Evidence Supplemental.pdf` |
| Verify a specific claim against data | `docs/CLAIM_TO_DATA_MAP.md` |
| Run the targeted release-integrity verifier | `python3 code/scripts/verify_study_release.py` |
| Recompute every deposited trace hash | `python3 code/figure_scripts/verify_trace_hashes_full.py --root .` |
| Recompute measured judge reliability | `python3 code/figure_scripts/compute_reliability.py` |
| Understand the routing-purpose test | `docs/CORRECTED_ROUTING_VALIDATION_20260812.md` |
| Inspect retained raw grading depth | `replication_package/retained_study_data/` |
| Replicate (tiered, from free to cluster) | `docs/REPLICATION_INSTRUCTIONS.md` + `docs/PARTIAL_REPLICATION.md` |
| See what routed where and why | `DEPOSIT_MAPPING.md` |
| Check the locked protocol + halt rules | `pre_registration/PROTOCOL_LOCK.md` |
| See every protocol deviation | `pre_registration/DEVIATIONS.md` + supplement Deviation Table (13 rows) |
| Know what cannot be replicated | `docs/KNOWN_GAPS.md` |
| See which planned paths are intentionally absent (and why) | `docs/EXCLUSIONS.md` |
| Check label errata in frozen artifacts (v1 judge "Opus"/Sonnet) | `docs/ERRATA.md` |

## Quickstart (read-only verification, no compute)

```bash
git clone https://github.com/calboreanu/MANDATE.git
cd MANDATE
git checkout study-release-2026.08.13.1
cd studies/2026q2

# Record counts match the supplement:
wc -l replication_package/v1_main/system_outputs/*.jsonl
# → mandate_primary 1200+300, cond_a 1200+300, cond_b 1200+300,
#   baseline_1 1206+300, baseline_2..6 1206 each
#   (each baseline file = 1200 TASK-MAIN-* + 6 TASK-CAL-* calibration records;
#    graded main-matrix n = 1200 per baseline, +300 hold-out for baseline_1)

# Full-coverage ensemble grades (the comparative table's source):
wc -l replication_package/v1_main/grading/v2_full_coverage/ensemble_scores.jsonl   # 12000

# Evaluated-build pipeline/schema completion (not executability):
python3 -c "
import json
ok=sum(json.loads(l)['ok'] for l in open('replication_package/v1_main/system_outputs/cond_a_main.jsonl'))
print('cond_a main ok:', ok, '/ 1200')"

# Adversarial structural results (100% prompt-injection structural pass):
wc -l replication_package/v2_complete/perturbations_mandate/*.jsonl   # 3500 + 350 + 350

# Targeted release-integrity verification (stdlib only; no keys or network):
python3 code/scripts/verify_study_release.py
```

## Package layout

- `supplement_pdfs/` — the three supplement documents (Empirical Evidence
  Supplemental, v2 Protocol Amendment, Engineering and Operational Provenance).
- `pre_registration/` — the locked protocol package: PROTOCOL_LOCK.md (κ≥0.40
  halt rule), analysis plan, prompts, forms, calibration tasks, DEVIATIONS.md.
- `replication_package/v0_pilot/`, `v0_5_pilot/` — historical pilot evidence
  backing the paper's §12 pilot tables.
- `replication_package/v1_main/` — the frozen comparative-campaign component:
  corpus, ground truth, perturbation suite, per-system RunRecords (consolidated
  JSONL), sampled grading (700), full-coverage grading (12,000), per-finding
  extracts, and the RunRecord schema. The directory name is historical.
- `replication_package/v2_complete/` — the historical path for additional
  cross-vendor runs (1,200), MANDATE-side
  perturbation records (4,200), A3/A5 ablations (3,000), the all-ablations MVP
  (1,200; auxiliary), partial Phase B perturbation grades (14,685; paused at
  80.7% under Deviation D-13), Phase A structural-invariance report.
- `replication_package/v3_corrected_routing/` — the historical path for the
  focused 3,000-record,
  generation-only routing-contract check on the 1.0.3-derived implementation,
  including consolidated outputs, ledger, analyses, patches, provenance, and
  a byte-exact split of the complete originator return archive. Its historical
  path label is retained for provenance; it is part of this study release.
- `replication_package/retained_study_data/` — deterministic, checksummed
  consolidation of the retained raw per-judge streams, including all 36,000
  records behind the 12,000 full-coverage ensemble results and 44,055 partial
  perturbation-judge records. The checksummed streams above are the retained set deposited with this
  release; anything beyond them is out of scope here (see
  `docs/EXCLUSIONS.md`).
- `code/` — apparatus snapshot (adapters for the six MANDATE roles plus the
  Cond-A extraction stage; judges, baselines, perturbation generator), run
  scripts, and `code/figure_scripts/` — the figure-data extraction and
  plotting scripts, the whole-deposit trace-hash verifier, and the
  full-coverage reliability script used by the manuscript.
- `engineering_provenance/` — full handoff chronology (119 files) + cost
  ledger with the closeout addendum. Reviewers can skip this directory.
- `docs/` — replication instructions, environment spec, claim-to-data map,
  partial-replication guide, known gaps, exclusions, errata.
- `requirements.txt` — pinned dependency manifest for `code/` (Tier 1 needs
  no installs; see the "Environment" section of
  `docs/REPLICATION_INSTRUCTIONS.md`).

## Provenance

Frozen artifacts are pinned by git tags in the evaluation tree:
`corpus_freeze_v1`, `gt_freeze_v1`, `baseline_freeze_v1`,
`perturbation_freeze_v1`, `outputs_freeze_v1_1` (commit `5f4de54`);
apparatus tag `mandate-eval-primary-2026q2-v1` (commit `4f8af83`).
The evaluation executed against `mlt-stack 1.0.0rc1` (canonical MANDATE
implementation); artifacts verify against later stack releases, but
byte-faithful re-execution should use 1.0.0rc1. mlt-stack is not vendored
here; see `docs/REPLICATION_INSTRUCTIONS.md` ("Acquiring mlt-stack").

The focused routing-check apparatus is reproduced by the patch series in
`replication_package/v3_corrected_routing/provenance/`, based on apparatus
commit `ab64056c9464f9ab294696698423c4167a703071` and ending at campaign
apparatus commit `74c62b02856254656905269d2bff9851dbfb1800`; its external
mlt-stack patch and campaign commit
`c0b58fb38b3c72ab6ece72f7576425892234976c` are preserved as provenance. This focused check used a committed
1.0.3-derived prompt stack, not a recovered hash-identical copy of the rc1
prompts.

**Provenance note on absolute paths.** Frozen evidence files in this
repository (pilot run logs, handoff records, extracted findings, and other
audit artifacts) record eval-host absolute paths exactly as executed — e.g.
`/Users/ws01admin/...` and host `lattice-ws01` working-tree paths. These are
inert provenance metadata: they identify where the runs happened, contain no
credentials or secrets, and were deliberately preserved unmodified rather
than rewritten, so that the frozen evidence remains byte-faithful to what the
audits attested. No command in `docs/REPLICATION_INSTRUCTIONS.md` depends on
them.

## Status disclosures (read before citing)

- **Phase B perturbation grading is partial:** paused 2026-07-08 at
  14,685/18,200 main-pass grades (80.7%) under budget Deviation D-13;
  baseline_4 perturbation generation halted at 3,021/3,500 (86.3%);
  baselines 5–6 perturbation runs scoped out under D-12 (baseline_4 is the
  multi-agent-shell class representative). No cross-system semantic
  adversarial claims are made from partial grades. Resumable via
  `grade-v2 --skip-existing` against frozen records.
- **Confidence intervals** for the protocol-specified primary contrast family were
  delivered 2026-07-10 (`analysis/bootstrap_contrasts_results.json`;
  script `code/scripts/bootstrap_contrasts.py`, seed 20260710); the wider
  9-system grid remains descriptive. **Measured full-coverage inter-judge
  reliability** (Krippendorff α from the retained streams, via
  `code/figure_scripts/compute_reliability.py`): minimum coverage 0.855
  (above the 0.667 floor); target 0.586; constraint 0.589; mission-intent
  0.536; gap classification 0.449; fabrication 0.218; trace completeness
  0.218 interval / 0.027 nominal. The earlier sampled v1 values are halt-rule
  history. Judged claims are read jointly with these values; structural
  claims derive from artifact inspection.

  Note on `v1_main/grading/v1_sampled/judges_config.json`: the file
  records the protocol-locked ensemble (Opus); the v1 cycle executed with
  Sonnet substituted under deviation D-08 and v2 restored Opus under
  D-10. `pre_registration/DEVIATIONS.md` carries the four long-form
  deviation narratives; the complete 13-entry structured table is §9 of
  the Empirical Evidence Supplemental in `supplement_pdfs/`; the precise
  file-level erratum (which fields say Opus, which prove Sonnet) is
  `docs/ERRATA.md`.
- Cond-A receives pre-extracted structured input and is an upper-bound
  characterization, **not** an apples-to-apples comparator against baselines;
  the fair MANDATE comparator is Cond-B.
- In the evaluated Cond-A/B campaign files, `ok=true` establishes schema/pipeline
  completion only; it must not be cited as evidence that the output was safe
  to execute. The successor contract adds explicit execution states and a
  fail-closed gate. See `docs/CORRECTED_ROUTING_VALIDATION_20260812.md`.

## Citation

Cite the paper and this repository by URL. See `CITATION.cff` and
`prior_published_paper/CITATION_TO_PAPER.md`.

## Licenses

- **Code** (`code/`, scripts): Apache License 2.0 — see `LICENSE`.
- **Data** (RunRecords, corpus, ground truth, grades): CC BY 4.0 — see `LICENSE-DATA`.
- **Registration prompts and forms** (`pre_registration/`): CC0.
- **Paper text:** not redistributed here; cite via the journal/preprint.
