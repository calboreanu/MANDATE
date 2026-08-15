# MANDATE 2026Q2 Study Evidence

**Publication release:** MANDATE `2.0.8`

**Study snapshot:** `2026.08.13.1`

**Repository and path:** `calboreanu/MANDATE`, `studies/2026q2/`

This directory is the deposited evidence and verification package included in
the MANDATE v2 publication release. It supports the
protocol-governed 2026Q2 comparative evaluation of **MANDATE** (Multi-Agent Nominal Decomposition
for Autonomous Task Execution), a tolerance-based task-specification framework
for autonomous agents. The evaluation measured three MANDATE conditions against
six baseline systems on a frozen three-domain corpus (120 tasks × a recorded
10-run schedule)
plus a 30-task out-of-domain hold-out, graded 12,000 records at full coverage
under a three-judge ensemble (Claude Opus, GPT-4o, Gemini 2.5 Pro), and added
cross-vendor execution (4 LLM families), a 350-perturbation adversarial suite,
and ablations. The deposit documents 13 keyed deviations (D-01–D-13;
standalone structured ledger at `pre_registration/DEVIATION_LEDGER.md`) plus
unkeyed differences between the locked plan and the executed study. The keyed
ledger is not an exhaustive inventory of every plan-to-execution difference.
The campaign is protocol-governed,
not pre-registered: the released registration carries an unfilled lock-date
field and no externally timestamped pre-data registration, and the executed
analysis deviates materially from the locked plan (hypothesis dispositions in
the manuscript's Supplementary Information).

The corpus is model-generated and author-selected. Claude Opus produced task
candidates from public-document chunks; deduplication left 262 candidates.
A source-balanced domain/category water-fill proposed 40 tasks per main
domain, after which the author finalized the 120-task main corpus. The
30-task software-engineering hold-out was author-selected from 44 generated
candidates. Independent SME realism review and signed ground-truth
ratification were not completed. The corpus is therefore a fixed evaluation
artifact, not a probability sample from a defined task population.

**The study result, stated as one result:** MANDATE produced schema-valid,
fully hash-traced specification artifacts at scale. Under the retained
three-judge full-coverage rubric, pooled minimum-coverage reliability was
Krippendorff α = 0.855 across all 12,000 graded records (the 10,800-record,
nine-system main matrix plus 1,200 hold-out records from MANDATE-primary,
Cond-A, Cond-B, and B1). On the main corpus only, the decisive Cond-B/B3
population (2,400 records) had α = 0.618, with within-system values of 0.446
for Cond-B (1,200 records) and 0.766 for B3 (1,200 records). The observed ensemble contrast was
Δ = −0.112, with the same direction for all three judges and 112/120
tasks; its magnitude is descriptive because reliability depends on the
analysis set and the protocol specified no Krippendorff-α cutoff. The retained structured result fields also exposed a result-state defect in
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

This is one study result with several evidence tiers. Historical directory
labels remain only to preserve the executed chronology, immutable hashes, and
citation anchors; they are not separate study results or current releases.

## Read this first

| You want to… | Go to |
|---|---|
| Read the results | `supplement_pdfs/Empirical Evidence Supplemental.pdf` |
| Verify a specific claim against data | `docs/CLAIM_TO_DATA_MAP.md` |
| Confirm the publication release identity | `docs/PUBLICATION_RELEASE.md` |
| Run the targeted release-integrity verifier | `python3 code/scripts/verify_study_release.py` |
| Verify every deposited evidence file | `shasum -a 256 -c EVIDENCE_SHA256SUMS.txt` |
| Recompute hashes for every declared 2026Q2 trace source-of-record family | `python3 code/figure_scripts/verify_trace_hashes_full.py --root .` |
| Recompute measured judge reliability | `python3 code/figure_scripts/compute_reliability.py` |
| Understand the routing-purpose test | `docs/CORRECTED_ROUTING_VALIDATION_20260812.md` |
| Inspect retained raw grading depth | `replication_package/retained_study_data/` |
| Replicate (tiered, from free to cluster) | `docs/REPLICATION_INSTRUCTIONS.md` + `docs/PARTIAL_REPLICATION.md` |
| Understand the deposited scope | `docs/CLAIM_TO_DATA_MAP.md` + `docs/EXCLUSIONS.md` |
| Check the locked protocol + halt rules | `pre_registration/PROTOCOL_LOCK.md` |
| See the 13 keyed deviations and long-form narratives | `pre_registration/DEVIATION_LEDGER.md` + `pre_registration/DEVIATIONS.md` + supplement Deviation Table (13 rows) |
| Know what cannot be replicated | `docs/KNOWN_GAPS.md` |
| See which planned paths are intentionally absent (and why) | `docs/EXCLUSIONS.md` |
| Check label errata in frozen artifacts (v1 judge "Opus"/Sonnet) | `docs/ERRATA.md` |

## Quickstart (read-only verification, no compute)

```bash
git clone https://github.com/calboreanu/MANDATE.git
cd MANDATE
git checkout v2.0.8
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
- `pre_registration/` — the protocol archive: PROTOCOL_LOCK.md (κ≥0.40 halt
  rule), analysis plan, prompts, forms, calibration tasks, and the complete
  keyed deviation record. The archive preserves the locked plan alongside
  execution records; it does not present the protocol as if it were executed
  without additional unkeyed differences, and it is not evidence of an
  externally timestamped pre-registration.
- `replication_package/v0_pilot/`, `v0_5_pilot/` — historical pilot evidence
  backing the paper's §12 pilot tables.
- `replication_package/v1_main/` — the frozen comparative-campaign component:
  corpus, model-authored unratified reference scaffolds, perturbation suite, per-system RunRecords (consolidated
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
  plotting scripts, the declared-source trace-hash verifier, and the
  full-coverage reliability script used by the manuscript.
- `engineering_provenance/` — historical execution records and the cost ledger.
  These files are retained verbatim for transparency and are not current
  instructions or publication prose. Reviewers can skip this directory.
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
  `code/figure_scripts/compute_reliability.py`): across the 12,000-record
  pooled population (10,800 main-matrix records across nine systems plus
  1,200 hold-out records across MANDATE-primary, Cond-A, Cond-B, and B1),
  minimum coverage 0.855;
  target 0.586; constraint 0.589; mission-intent
  0.536; gap classification 0.449; fabrication 0.218; trace completeness
  0.218 interval / 0.027 nominal. For minimum coverage, the decisive
  main-corpus Cond-B/B3 population has α = 0.618 (2,400 records), with
  within-Cond-B α = 0.446 and within-B3 α = 0.766 (1,200 records each).
  The locked protocol
  specified no Krippendorff-α acceptance cutoff; these estimates describe
  measurement agreement and analysis-set sensitivity. The earlier sampled v1 values are halt-rule
  history. Judged claims are read jointly with these values; structural
  claims derive from artifact inspection.

  Note on `v1_main/grading/v1_sampled/judges_config.json`: the file
  records the protocol-locked ensemble (Opus); the v1 cycle executed with
  Sonnet substituted under deviation D-08 and v2 restored Opus under
  D-10. `pre_registration/DEVIATIONS.md` carries the four long-form
  deviation narratives; all 13 keyed entries are in the structured table at §9 of
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
- **Data** (RunRecords, corpus, reference scaffolds, grades): CC BY 4.0 — see `LICENSE-DATA`.
- **Registration prompts and forms** (`pre_registration/`): CC0.
- **Paper text:** not redistributed here; cite via the journal/preprint.
