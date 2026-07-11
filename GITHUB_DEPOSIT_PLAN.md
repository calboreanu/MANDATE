# GitHub / Zenodo Replication-Package Plan

**Purpose.** Concrete directory structure for the deposit that
reviewers download to reproduce every numerical claim in the
manuscript + the three supplement PDFs. Pairs with `DEPOSIT_MAPPING.md`
(the per-artifact routing catalog).

**Distribution model.** GitHub repository at submission, mirrored to
Zenodo for DOI minting. Zenodo is the citable archive; GitHub is the
working surface.

> **Distribution update (2026-07-08, PI decision):** GitHub-only. The
> Zenodo/DOI sections below are retained as historical planning record and
> are not being executed; the repository is cited by URL + version tag.
> Raw-depth bulk layers stay on the frozen evaluation tree with a
> consolidation script staged in the submission bundle.

**Naming convention.** Repository name proposal:
`mandate-eval-primary-2026q2` (matches the apparatus freeze tag).

---

## Status against 2026-06-25 audit

A full deposit audit was conducted on 2026-06-25 (see
`MANDATE_AUDIT_REPORT.md`). The deposit landed at
**MOSTLY-READY-WITH-FIXES**: the five freeze tags exist with correct
contents, the apparatus tag exists on the upstream AEGIS repo at the
documented commit, and the frozen artifacts on disk match the freeze
tag contents. Eight artifacts promised by this plan are not yet on
disk and must be produced before public release. They are tracked
below as Tier B items.

### Verified ready (no work needed)
- `corpus_freeze_v1` tag present + 120 main + 30 hold-out + 6 pilot tasks
- `baseline_freeze_v1` tag present + B1--B6 RunRecords
- `gt_freeze_v1` tag present + ratified scaffolds
- `perturbation_freeze_v1` tag present + 350-perturbation suite
- `outputs_freeze_v1_1` at commit `5f4de54` + 9036 RunRecords
- Apparatus tag `mandate-eval-primary-2026q2-v1` at `4f8af83`
- All 4 corpora have source-document text on disk (25 .txt files)
- `$15,256` cost estimate is internally arithmetic-consistent and
  calibrated against actual Cond-A spend ($32.14 across 1200 records).
  **Closeout note (2026-07-08):** the estimate's grading components were
  Sonnet-priced; D-10's Opus restoration raised per-grade cost ~5× and
  realized multi-provider spend exceeded the projection. See
  `engineering_provenance/cost_log/cost_ledger.md` closeout addendum and
  supplement Deviation Table rows D-12/D-13.

### To be produced before public release (audit Tier B)

| Artifact | Why missing | Effort | Owner |
|---|---|---|---|
| `docs/REPLICATION_INSTRUCTIONS.md` | Not yet authored | ~2h | Lead Analyst |
| `docs/ENVIRONMENT.md` (Mac mini M4 Pro + Ollama spec) | Not yet authored | ~1h | Lead Analyst |
| `runrecord_schema_v1.json` | Generate from sample records via jsonschema inference | ~1h | Codex |
| `engineering_provenance/cost_log/` | Aggregate per-phase costs from existing logs | ~2h | Codex |
| `11_replication_package/` | Empty directory; needs manifest pointing at frozen artifacts | ~1h | Codex |
| `environment.yml` Python version pin | Currently 3.11; venv is 3.12.12 | ~5 min | Codex |
| `build_report.json` + `manual_sources_manifest.json` merge | 15 of 18 sources have HTTP outcomes; intel 3 are in manual manifest with no outcome logs | ~30 min | Codex |
| Cond-B API cost logging | Currently `api_cost_usd=0.000000` by design; either patch apparatus or add top-level cost manifest | ~2h | Codex |
| `mandate-eval-primary-2026q2-v2` git tag | Stage 4 + HANDOFF_22/23 landed; HANDOFF_24 Phase B paused at 80.7% under D-13 — mint at the documented closeout state, or after a funded re-grade (PI decision) | (deposit-time) | Lead Analyst |
| Empty Zenodo skeletons `deposit/supplemental/zenodo_package/{code,artifacts,containers}/` | Populated at deposit-mint time | (deposit-time) | Lead Analyst |

### To be reconciled (audit Tier C / forward)

| Item | Issue | Resolution |
|---|---|---|
| Five canonical schema duplicates | `mandate-as-code.schema.json` (or equivalent) exists in 5 folders | Designate `Repos/MANDATE/schemas/mandate-as-code.schema.json` canonical; symlink others |
| Gap-type count 5 vs 6 | Paper Table tab\_gap-categories says 5; implementation schemas have 6 (with `MISSING_TTP` / `MISSING_PROCEDURE` split from `MISSING_CAPABILITY`) | Editorial reconciliation when paper is revised |
| EBNF grammar paper-vs-code | Paper Table 1 row 9 documents 12 patterns; implementation has 12 atomic patterns + `NOT` + `MATCHES` + set-brackets + typed literals (richer than paper) | Document extensions in paper appendix or update Table 1 |
| 9 of 13 Table 1 metrics not pytest-gated | They are bundled JSON outputs from `eval_*.py` scripts; drift wouldn't fail CI | HANDOFF_25 adds pytest harnesses asserting JSON outputs match published values |

---

## Top-level package layout

```
mandate-eval-primary-2026q2/
├── README.md                            # Quickstart, paper citation, DOI
├── CITATION.cff                         # Standard citation file
├── LICENSE                              # Code license
├── LICENSE-DATA                         # Data license (CC-BY-4.0 proposed)
├── DEPOSIT_MAPPING.md                   # Authoritative routing catalog (mirror)
├── GITHUB_DEPOSIT_PLAN.md               # This file (mirror)
├── CHANGELOG.md                         # Deposit version history
│
├── supplement_pdfs/                     # The three supplement PDFs (read-only mirror)
│   ├── Empirical Evidence Supplemental.pdf
│   ├── v2 Protocol Amendment.pdf
│   └── Engineering and Operational Provenance.pdf
│
├── prior_published_paper/               # T0: cite the paper, do not redistribute
│   └── CITATION_TO_PAPER.md             # Bibliographic pointer + reviewer-feedback summary
│
├── pre_registration/                    # T1: the locked protocol package
│   ├── README_START_HERE.md
│   ├── 00_PLAYBOOK_v2.md
│   ├── 00_PREREGISTRATION_TEMPLATE.md
│   ├── 02_strongest_baseline_selection_rule.md
│   ├── PROTOCOL_LOCK.md                 # The κ≥0.40 halt rule lives here
│   ├── ANALYSIS_PLAN.md
│   ├── PROMPTS.md
│   ├── FORMS.md
│   ├── CHECKLIST.md
│   ├── SETUP.md
│   ├── Q1_AUDIT_AND_ENHANCEMENTS.md
│   ├── Q1_PLUS_UNBOUNDED_SCALING.md
│   └── calibration_tasks/               # 6 hand-authored calibration tasks
│       ├── cal_01_*.json
│       └── ...
│
├── replication_package/                 # T2-T5: the actual data + code
│   │
│   ├── v0_pilot/                        # T2: April 2026 paper Section 12 prep
│   │   ├── README.md                    # What this tier contains + how it backs the paper
│   │   ├── PROGRESS_LOG.md
│   │   ├── LATEX_TABLES.md
│   │   ├── EVIDENCE_FRAMING.md
│   │   ├── aegis_eval_results.tar.gz    # 500-test static suite backing tab_static-eval
│   │   ├── eval_results/                # 8 deterministic eval JSONs + 17 logs
│   │   ├── live_runs/
│   │   │   ├── scenarios/               # 8 paper-derived scenarios
│   │   │   ├── outputs/                 # LLM-mode artifacts (40/48 LLM executions)
│   │   │   ├── outputs_production_config/
│   │   │   ├── run_with_llm.py
│   │   │   └── run_with_production_config.py
│   │   └── paper_section_12_tables/     # The 3 LaTeX tables reproduced in supplement §1.1
│   │       ├── tab_static-eval.tex
│   │       ├── tab_det-vs-llm.tex
│   │       └── tab_llm-run.tex
│   │
│   ├── v0_5_pilot/                      # T3: April 2026 cross-profile pilot (supplement §6.7)
│   │   ├── README.md
│   │   ├── authorized_lab/              # 6-case pentest corpus
│   │   ├── adapter_manifests/           # Qwen3 LoRA configs (rank/alpha/seed)
│   │   ├── logs/                        # 15 cross-profile eval JSONs
│   │   ├── authlab_run_001/             # AUTHLAB-RUN-001 raw run logs (3 files)
│   │   ├── ab_evaluation.py             # The script that emits the 5/6 ok pattern
│   │   └── profile_aggregates.json      # Extracted aggregates from 15 logs
│   │
│   ├── v1_main/                         # T4: the headline 2026Q2 main matrix
│   │   ├── README.md
│   │   ├── corpus/                      # corpus_freeze_v1
│   │   │   ├── main_corpus_120.jsonl    # 40 per domain × 3 domains
│   │   │   ├── holdout_corpus_30.jsonl  # 30 software_engineering tasks
│   │   │   ├── pilot_corpus_6.jsonl     # 6-task Phase 0 pilot
│   │   │   └── source_documents/        # 18 public docs (or build_report.json + URLs)
│   │   ├── ground_truth/                # gt_freeze_v1
│   │   │   └── sme_ratified_references.jsonl
│   │   ├── perturbations/               # perturbation_freeze_v1
│   │   │   └── perturbation_suite_350.jsonl
│   │   ├── system_outputs/              # outputs_freeze_v1_1 at 5f4de54
│   │   │   ├── mandate_primary_main_1500.jsonl    # 1500 main RunRecords
│   │   │   ├── mandate_primary_holdout_300.jsonl  # 300 hold-out RunRecords
│   │   │   ├── b1_single_claude/                  # 1206 B1 RunRecords
│   │   │   ├── b2_single_gpt/
│   │   │   ├── b3_react_claude/
│   │   │   ├── b4_autogen/
│   │   │   ├── b5_crewai/
│   │   │   └── b6_langgraph/
│   │   ├── grading/                     # Phase 8 grading inputs and grades
│   │   │   ├── stratified_sample_700.jsonl
│   │   │   ├── grades_gpt4o.jsonl
│   │   │   ├── grades_opus.jsonl
│   │   │   ├── grades_gemini.jsonl
│   │   │   └── agreement_statistics.json   # κ values, PROTOCOL_LOCK §8 halt evidence
│   │   ├── findings_extracted/          # Mirror of `standalone data results/`
│   │   │   ├── finding_1_decomposition/
│   │   │   ├── finding_2_interpreter/
│   │   │   ├── finding_3_validator/
│   │   │   ├── finding_4_binding/
│   │   │   ├── finding_5_intake/
│   │   │   ├── cross_system/
│   │   │   ├── dataset_inventory/
│   │   │   ├── baseline_calibration/
│   │   │   ├── corpus_residue/
│   │   │   ├── perturbations/
│   │   │   ├── pilot_smoke/
│   │   │   ├── demo_scenarios/
│   │   │   ├── demo_memos/
│   │   │   ├── deviations/
│   │   │   ├── handoff_chronology/
│   │   │   ├── handoff_costs/
│   │   │   ├── realism_infrastructure/
│   │   │   ├── v1_pilot_cross_profile/
│   │   │   └── v2_patch/
│   │   └── schemas/                     # Anonymized RunRecord JSON schema
│   │       └── runrecord_schema_v1.json
│   │
│   └── v2_progress/                     # T5: v2 work in progress
│       ├── README.md                    # Status; updates as work lands
│       ├── condition_x_regrade/         # Populated when Stage 4 completes
│       ├── condition_a_pre_extract/
│       ├── condition_b_llm_augmented/
│       ├── grading_opus_full_coverage/
│       ├── o5_adversarial/              # Populated under D-11
│       └── handoffs/                    # HANDOFF_19a..19d, 20, 22 chronology
│
├── code/                                # Apparatus snapshot (frozen tag 4f8af83)
│   ├── README.md                        # Build instructions
│   ├── mandate-eval-primary-2026q2-v1   # Or symlink to the right ref
│   │   ├── code/
│   │   │   ├── rag/embeddings/build_report.json
│   │   │   ├── judges/                  # Three-judge ensemble grading code
│   │   │   ├── baselines/               # B1-B6 baseline shells
│   │   │   ├── perturbations/           # Perturbation generator
│   │   │   ├── apparatus/               # 7-role MANDATE pipeline
│   │   │   └── analysis/                # Statistical analysis scripts
│   │   ├── seeds/
│   │   │   └── 20260603.json
│   │   ├── pyproject.toml
│   │   └── ...
│
├── engineering_provenance/              # Internal record (not required for replication)
│   ├── README.md                        # "Reviewers can skip this directory"
│   ├── handoffs/                        # Full handoff chronology
│   ├── patches/                         # Apparatus patches with verification logs
│   ├── salvage_audit/                   # v1 salvage audit machine artifacts
│   ├── cost_log/                        # Per-phase cost attestation
│   └── README_HANDOFF_INDEX.md          # Map handoff IDs to deposit additions
│
└── docs/                                # Reviewer guide
    ├── REPLICATION_INSTRUCTIONS.md      # Step-by-step replication
    ├── CLAIM_TO_DATA_MAP.md             # Each supplement claim → exact data file
    ├── ENVIRONMENT.md                   # Ollama + cluster spec for full replication
    ├── PARTIAL_REPLICATION.md           # What can be replicated without cluster
    └── KNOWN_GAPS.md                    # SME pool unavailable → what cannot be replicated
```

---

## Replication tiers (what reviewers can run, from easiest to hardest)

### Tier 1 — Read-only verification (no compute required)

Reviewers download the repository, open `findings_extracted/finding_5_intake/`,
and confirm the 20 verbatim Intake failure samples match the
supplement §4.5 text. **No replication required**; the JSONL files
*are* the evidence.

Covered by: `replication_package/v1_main/findings_extracted/*`,
`v1_main/grading/*.jsonl`, `prior_published_paper/CITATION_TO_PAPER.md`,
all three supplement PDFs.

### Tier 2 — Re-grade from frozen outputs (LLM compute required)

Reviewers download `v1_main/system_outputs/` and `v1_main/grading/`,
run the judges code in `code/judges/`, confirm that the published
grades reproduce within agreement-statistics tolerances. Requires
API keys for GPT-4o, Opus 4.6, Gemini 2.5 Pro. **~$50-200 in API
spend.**

Covered by: `code/judges/`, the three-judge ensemble code; documented
in `docs/PARTIAL_REPLICATION.md`.

### Tier 3 — Re-run baselines on the frozen corpus (LLM compute required)

Reviewers download `v1_main/corpus/`, run `code/baselines/b1..b6.py`,
confirm baseline RunRecords reproduce. Requires API keys + ~24h
wall-clock per baseline. **~$500-2000 in API spend per baseline.**

Covered by: `code/baselines/`, documented in
`docs/REPLICATION_INSTRUCTIONS.md`.

### Tier 4 — Full replication including MANDATE-primary fine-tunes (cluster required)

Reviewers replicate the LoRA fine-tunes (`mandate-intake`,
`mandate-interpreter`, etc.) on the documented training set, run
on a Mac mini M4 Pro cluster via Ollama. **Multi-day wall clock +
specific hardware.** Documented but not the expected path.

Covered by: full apparatus snapshot, documented in
`docs/ENVIRONMENT.md` and `docs/REPLICATION_INSTRUCTIONS.md`.

---

## DOI minting plan

**Primary DOI** (for paper citation):
- Mint at v1 manuscript submission with v1 frozen artifacts.
- Concept DOI: `10.5281/zenodo.[concept_id]` (all versions).
- Version DOI: `10.5281/zenodo.[v1_id]` (this version).
- Cited in paper as: "Replication package: [DOI URL]"

**Secondary DOI** (for v2 update):
- Mint at v2 deposit close (after Stage 4 + multi-vendor Cond-B).
- New version DOI under the same concept DOI.
- v2 supplement PDF cites both DOIs.

---

## License plan

- **Code:** Apache 2.0 (apparatus + analysis scripts).
- **Data:** CC-BY-4.0 (RunRecords, corpus, ground truth).
- **Prompts and forms:** CC0 (pre-registration package).
- **Paper text:** Not redistributed; cite via DOI.

---

## What the GitHub README must contain (top-level)

1. **One-paragraph paper summary** + DOI badge.
2. **Quickstart**: `git clone && cd && python docs/verify_install.py`.
3. **Pointer to the three supplement PDFs** for the read-only path.
4. **Pointer to `DEPOSIT_MAPPING.md`** for the routing catalog.
5. **Pointer to `docs/REPLICATION_INSTRUCTIONS.md`** for hands-on
   replication.
6. **The pre-registration provenance** (link to
   `pre_registration/PROTOCOL_LOCK.md`).
7. **The reviewer-objection map** (link to the corresponding section
   of `DEPOSIT_MAPPING.md`).
8. **Citation block** with `.bib`.
9. **License summary.**

---

## What this plan deliberately does NOT include

These were considered and excluded for the rationale shown:

| Excluded item                                    | Why not                                                                                                |
|--------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| Live network calls (e.g., fetching source docs)  | Build reproducibility on frozen artifacts only; redistribute extracted text not URLs.                  |
| SME ground-truth pool                            | SME pool unavailable per documented deviation; described, not redistributed.                           |
| AEGIS-cleanup CI logs                            | Operational, not eval. Excluded per `DEPOSIT_MAPPING.md` OPS rules.                                    |
| Demo videos                                       | Promotional material, not evaluation data. Excluded per OPS rules.                                     |
| Personal documents / unrelated projects          | Outside MANDATE scope. Excluded per OPS rules.                                                         |
| Full transcript of the closed-loop demo          | Demo provenance lives in supplement §6; raw demo materials are OPS.                                    |

---

## v2 update checklist

When the v2 deposit close arrives, perform the following:

- [ ] Mint new Zenodo version DOI under the existing concept DOI.
- [ ] Add `v2_complete/` directory under `replication_package/`
      with the same internal structure as `v1_main/`.
- [ ] Replace `replication_package/v2_progress/` with
      `replication_package/v2_complete/` (or keep both and rename).
- [ ] Update `CHANGELOG.md` with v2 additions.
- [ ] Update `docs/CLAIM_TO_DATA_MAP.md` for the v2 supplement claims.
- [ ] Update `DEPOSIT_MAPPING.md` T5 rows (mark "(when ready)" rows
      as included with dates).
- [ ] Run the supplement build to regenerate the three PDFs.
- [ ] Push v2 tag to GitHub; trigger Zenodo archive.

---

*Last updated: 2026-06-24. Maintained alongside `DEPOSIT_MAPPING.md`.*
