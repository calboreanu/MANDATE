# MANDATE Empirical Evaluation — Deposit Mapping

**Purpose.** Single source of truth for what goes where. Every MANDATE
testing artifact found across this machine is catalogued below and
assigned to one of four destinations:

- **GH** = GitHub replication-package deposit (code + data reviewers
  download to reproduce results). *(Originally "GitHub/Zenodo"; GitHub-only
  per PI decision 2026-07-08 — see GITHUB_DEPOSIT_PLAN distribution update.)*
- **SUPP** = Academic supplement attached to the manuscript (the PDF
  reviewers read alongside the paper).
- **BOTH** = Goes to both, with different forms (data in GH, citation
  in SUPP).
- **OPS** = Project-internal operational record; not redistributed.

**Scope.** This catalog covers every evidence directory found in the
comprehensive sweep of `~/Desktop`, `~/Desktop - lattice-ws01`,
`~/Documents`, the Mandate Data deposit folder, and the 2026Q2
apparatus tree. Entries are organized by evidence tier (T0 prior
published paper → T5 v2, closed out 2026-07-08 under Deviations
D-12/D-13) and then by artifact.

**Cross-document consistency.** This catalog is authoritative.
`GITHUB_DEPOSIT_PLAN.md` (Zenodo package directory structure) and
the supplement's `\subsection{Relationship to Prior Published Work}`
both reference this file.

**Consolidation addendum (2026-07-08).** The loose MANDATE artifacts
formerly on `~/Desktop` were consolidated after closeout; see
`~/Documents/Research & Publications/MANDATE/_Archive_20260708/CONSOLIDATION_MANIFEST_20260708.md`
for the full accounting. Effects on this catalog:

- **Handoff source paths moved.** All `~/Desktop/HANDOFF_*.md` files
  (13e–25, including the GH-destined 19a–d/20/22 rows below) now live at
  `~/Documents/Research & Publications/MANDATE/_Archive_20260708/desktop_strays/`.
  Pull GH-destined handoffs from there at deposit-mint time; canonical
  copies of most also remain in the apparatus tree `handoffs/` directory.
- **New auxiliary evidence registered:** `ablation_mvp/` (moved into this
  deposit folder from `~/Desktop/MANDATE_ablation_mvp/`) — 1,200-record
  deterministic demonstration (8 systems × 150 tasks) that the canonical
  engine and all seven pre-registered ablations run end-to-end with a
  judge-ready layout. Destination: **GH (auxiliary)**; not cited by the v2
  supplement; complements the A3/A5 full-scale ablation runs and the
  described-only status of A1/A2/A4/A6/A7.
- Working audits/reviews/briefings not previously catalogued
  (MANDATE_IMPLEMENTATION_AUDIT, MANDATE_INDEPENDENT_REVIEW_{PROMPT,RESULT},
  MANDATE_TECH_DEBT, MLT_realness_audit_opus, v2_salvage_audit,
  COWORKER_BRIEFING_2026Q2_{COMPLETION_REPORT,HIGH_LEVERAGE_WORK},
  MLT_audits/) are classified **OPS** and archived at the same location.

---

## Evidence Tiers Overview

| Tier | Time   | What                                      | Evidence Class                | Primary Use                              |
|------|--------|-------------------------------------------|-------------------------------|------------------------------------------|
| T0   | <2026  | Published MANDATE paper Section 12        | v0 single-system pilot        | Cited as prior published baseline        |
| T1   | 2026Q1 | 2026Q2 pre-registration (eval_package/)   | Locked protocol               | Methodology provenance + GH replication  |
| T2   | Apr 26 | mandate/ Section 12 prep + LaTeX tables   | v0 data backing the paper     | GH historical evidence                   |
| T3   | Apr 26 | AEGIS/logs/ cross-profile pilot           | v0.5 multi-config pilot       | Already in supplement §6.7; GH data      |
| T4   | 2026Q2 | Mandate Data/ main matrix (v1 frozen)     | v1 headline corpus            | Both: full data in GH, findings in SUPP  |
| T5   | 2026Q2 | v2 records + apparatus patches            | v2 closed out (Cond-X/A/B)    | Both: Stage 4 landed 2026-07-01; Phase B grading paused at 80.7% under D-13 (D-12 scoped b5/b6 out) |

---

## T0 — Published MANDATE Paper (Frontiers in AI submission)

**Source root:** `~/Documents/Research & Publications/MANDATE/publication_ready_final/`

This is **the paper itself.** Authored by Elias Calboreanu, submitted
to Frontiers in AI, rejected twice on empirical grounds, then desk-
rejected at Requirements Engineering. The 2026Q2 evaluation is the
explicit corrective response to that reviewer feedback.

| Artifact                                                    | Destination | Rationale                                                                                          |
|-------------------------------------------------------------|-------------|----------------------------------------------------------------------------------------------------|
| `main.tex` + `main.pdf`                                     | SUPP cite   | The paper this supplement supports. Cited in supplement §1.1; full text not redistributed in GH.   |
| `references.bib`                                            | SUPP cite   | Existing supplement adds Calboreanu (2026) entry here.                                             |
| `response_to_reviewers.tex` + `.pdf`                        | SUPP cite   | Provides reviewer feedback text quoted in supplement §1.1; not redistributed.                      |
| `sections/12-evaluation-results.tex`                        | SUPP cite   | Source for the v0 evidence summarized in supplement §1.1. Cite by section number.                  |
| `sections/tables/tab_static-eval.tex` (13 metrics, 499/500) | BOTH        | Reproduce in supplement §1.1 as Table~\ref{tab:v0-static}. Source `.tex` mirrored into GH.         |
| `sections/tables/tab_det-vs-llm.tex` (8 scenarios)          | BOTH        | Reproduce in supplement §1.1 as Table~\ref{tab:v0-det-vs-llm}. Source `.tex` mirrored into GH.    |
| `sections/tables/tab_llm-run.tex` (40/48, 83% LLM)          | BOTH        | Reproduce in supplement §1.1 as Table~\ref{tab:v0-llm-run}. Source `.tex` mirrored into GH.        |
| Other 20 `sections/tables/*.tex`                            | SUPP cite   | Available via paper citation; not reproduced in supplement.                                        |
| All other `sections/*.tex` (00–13, 99)                      | SUPP cite   | Paper internal sections; not redistributed in deposit.                                             |
| `main.bbl`, `main.aux`, `main.toc`, `main.out`              | OPS         | Build artifacts.                                                                                    |

**Provenance line in supplement §1.1:** "v0 pilot results were
published in Calboreanu (2026, in review at Frontiers in AI),
Section~12. The reviewer feedback motivating the 2026Q2 evaluation
is reproduced verbatim from the file `response_to_reviewers.pdf`
maintained with the paper repository."

---

## T1 — 2026Q2 Pre-Registration (the locked protocol)

**Source root:** `~/Documents/Research & Publications/MANDATE/eval_package/`

This is the **pre-registration package** that the 2026Q2 evaluation
implements. Critical for credibility: it was locked *before* any
2026Q2 data was collected. The supplement's PROTOCOL_LOCK §8
κ≥0.40 halt rule comes from this directory.

| Artifact                                       | Destination | Rationale                                                                                              |
|------------------------------------------------|-------------|--------------------------------------------------------------------------------------------------------|
| `README_START_HERE.md`                         | GH          | Explains pre-registration rationale and the reviewer-rejection origin story.                           |
| `00_PLAYBOOK_v2.md`                            | GH          | Master 90-minute protocol; defines all phases.                                                         |
| `00_PREREGISTRATION_TEMPLATE.md`               | GH          | The pre-registration form filled out and locked at protocol freeze.                                    |
| `PROTOCOL_LOCK.md`                             | GH + SUPP   | §8 κ≥0.40 halt rule cited throughout supplement. SUPP cite by section number.                          |
| `ANALYSIS_PLAN.md`                             | GH + SUPP   | Statistical analysis plan including the power analysis cited in supplement Appendix X.                 |
| `PROMPTS.md`                                   | GH + SUPP   | All prompts (Phase 0 through Phase 8 grading). Supplement §2 cites by prompt ID.                       |
| `FORMS.md`                                     | GH          | SME signoff, realism audit, spot-check, failure coding forms. Required for re-running phases.           |
| `CHECKLIST.md`                                 | GH          | Deliverables checklist enforced at phase boundaries.                                                   |
| `SETUP.md`                                     | GH          | Environment setup for replicators.                                                                     |
| `Q1_AUDIT_AND_ENHANCEMENTS.md`                 | GH          | Pre-locked Q1 audit + planned enhancements (pre-data).                                                 |
| `Q1_PLUS_UNBOUNDED_SCALING.md`                 | GH          | Scaling plan for the 1500-record matrix.                                                               |
| `calibration_tasks/*.json` (6 tasks)           | GH + SUPP   | Hand-authored calibration tasks used as positive control. Supplement §2 cites count and origin.        |
| `02_strongest_baseline_selection_rule.md`      | GH          | The locked rule for pre-specifying strongest baseline against the calibration set.                     |

**Provenance line in supplement §1.1:** "The 2026Q2 protocol was
locked at the pre-registration deposit captured at
`eval_package/PROTOCOL_LOCK.md` and its companion files. All design
decisions in this supplement defer to that locked package."

---

## T2 — April 2026 Section 12 Evaluation Prep

**Source root:** `~/Desktop - lattice-ws01/mandate/`

This is the directory where the **published paper's Section 12 data
was generated** in April 2026. Contains the 11-run progress log, the
LaTeX tables that appear in the paper, the deterministic and LLM-mode
eval results, and the 8 paper-derived scenarios.

| Artifact                                                | Destination | Rationale                                                                                              |
|---------------------------------------------------------|-------------|--------------------------------------------------------------------------------------------------------|
| `PROGRESS_LOG.md` (21 KB, 11 runs)                      | GH          | Per-run documentation backing the paper Section 12 claims. v0 evidence trail.                          |
| `LATEX_TABLES.md` (8.8 KB)                              | GH          | LaTeX-ready tables exactly as published. Cross-check against `publication_ready_final/sections/tables/`.|
| `EVIDENCE_FRAMING.md` (in `live_runs/`)                 | GH          | Explains what the deterministic vs LLM runs prove for the paper. Useful framing context.               |
| `aegis_eval_results.tar.gz`                             | GH          | Source archive backing static-eval. Mirror as `v0_pilot/aegis_eval_results.tar.gz` in GH package.       |
| `eval_results/*.json` (8 eval JSONs)                    | GH          | Per-scenario deterministic eval results. v0 raw evidence.                                              |
| `eval_results/*.log` (17 run logs)                      | GH          | Run-time stdout/stderr for the 11 documented runs. Failure forensics.                                  |
| `live_runs/outputs/` (8 scenario artifacts + results)   | GH          | LLM-mode artifact outputs (the 40/48 LLM-mode executions tabulated in tab_llm-run).                    |
| `live_runs/outputs_production_config/`                  | GH          | Production-config rerun outputs (post-tuning).                                                         |
| `live_runs/scenarios/` (8 scenario JSONs)               | GH          | The 8 paper-derived scenarios (CISO Report, Undef Min/Tgt, Unknown Pattern, Missing Capability, Unassess Risk, Ransomware IR, OSINT Intel). |
| `live_runs/run_with_llm.py`                             | GH          | LLM runner script (Ollama + llama3.2/qwen2.5:14b/mistral). Required for replication.                   |
| `live_runs/run_with_production_config.py`               | GH          | Production-config runner. Required for replication.                                                    |
| All paper-derived scenarios subset                      | SUPP cite   | Supplement §1.1 cites count (8) and origin (paper Section 6.4 walkthrough).                            |

**GH package location:** `replication_package/v0_pilot/` (mirrored
from `lattice-ws01/mandate/`).

---

## T3 — April 2026 Cross-Profile Pilot

**Source root:** `~/Desktop - lattice-ws01/AEGIS/logs/`

15 cross-profile eval runs from April 22-23, 2026. Three apparatus
configurations (deterministic / base Qwen3-untuned / tuned
`mandate-*` fine-tunes) against the 6-case `authorized_lab` pentest
corpus. **Already integrated into supplement §6.7.**

| Artifact                                          | Destination | Rationale                                                                                               |
|---------------------------------------------------|-------------|---------------------------------------------------------------------------------------------------------|
| 15 cross-profile eval JSON files                  | GH + SUPP   | SUPP §6.7 reports aggregates; GH carries raw 15 logs.                                                   |
| AUTHLAB-RUN-001 raw run logs (3 files)            | GH          | Original AUTHLAB run logs; failure forensics provenance.                                                |
| `authorized_lab` corpus (6 pentest cases)         | GH          | Required to replicate the pilot. Mirror as `replication_package/v0_5_pilot/authorized_lab/`.            |
| Adapter manifests (Qwen3 LoRA configs)            | GH          | LoRA rank/alpha/seed for the tuned profile. Required for replication.                                   |
| Per-profile findings tabulated 5/6 ok pattern     | SUPP        | §6.7 reproduces the 3×5 aggregate table verbatim.                                                       |
| Iteration history (interpreter compaction rollback) | SUPP cite | §6.7 "Three pilot observations" paragraph (b) cites this iteration.                                     |

**GH package location:** `replication_package/v0_5_pilot/`. Source
extraction script lives at `standalone data results/v1_pilot_cross_profile/`
and emits the aggregates deterministically from these logs.

---

## T4 — 2026Q2 Main Matrix (v1 frozen, the headline)

**Source root:** `~/Desktop/Mandate Data/` and apparatus tree at
`~/Desktop - lattice-ws01/MANDATE Evaluation/mandate_eval_2026Q2/`.

The 2026Q2 main matrix at the `outputs_freeze_v1_1` tag (commit
`5f4de54`). 9036 RunRecords across seven systems on a 120-task
source-conditioned corpus and 30-task hold-out. Phase 8 three-judge
grading completed on a 700-record stratified sample with HALT under
PROTOCOL_LOCK §8.

### T4.A — The three supplement PDFs (manuscript attachments)

| Artifact                                       | Destination | Rationale                                                                                       |
|------------------------------------------------|-------------|-------------------------------------------------------------------------------------------------|
| `Empirical Evidence Supplemental.pdf`/`.tex`   | SUPP        | The 33-page academic supplement attached to the manuscript. The artifact reviewers read.        |
| `v2 Protocol Amendment.pdf`/`.tex`             | SUPP        | 5-page forward methodology amendment. Attached to manuscript.                                   |
| `Engineering and Operational Provenance.pdf`/`.tex` | SUPP    | 46-page deposit record. Attached to manuscript supplementary materials.                         |
| `README.md`                                    | BOTH        | Deposit guide. Same file in SUPP (deposit folder) and GH (replication package root).            |
| `DEPOSIT_MAPPING.md` (this file)               | BOTH        | Authoritative routing catalog. Same in SUPP and GH.                                             |
| `GITHUB_DEPOSIT_PLAN.md`                       | BOTH        | Zenodo package directory structure. Same in SUPP and GH.                                        |
| `BUILD.md`                                     | BOTH        | LaTeX build instructions for the three supplement PDFs.                                         |

### T4.B — Frozen RunRecords (the corpus that backs every claim)

Apparatus path: `~/Desktop - lattice-ws01/MANDATE Evaluation/mandate_eval_2026Q2/07_system_outputs/` at `outputs_freeze_v1_1`.

| Artifact                                              | Destination | Rationale                                                                                          |
|-------------------------------------------------------|-------------|----------------------------------------------------------------------------------------------------|
| 1500 MANDATE-primary RunRecords (main matrix)         | GH          | The headline corpus. Every supplement claim about MANDATE-primary derives from these.              |
| 1180 hold-out RunRecords (out-of-domain generalization) | GH        | The 30 hold-out tasks × experiments; cited in supplement §3.4.                                     |
| 7236 baseline RunRecords (B1-B6, 1206 per baseline)   | GH          | All six baselines on all 120 tasks × 10 seeds. Cross-system comparison in supplement §5.            |
| 700-record stratified sample (Phase 8 grading inputs) | GH          | The sample fed to three-judge ensemble grading. Supplement §5.4 + Appendix X.                      |
| Three-judge grades (GPT-4o, Opus 4.6, Gemini 2.5 Pro) | GH          | Raw grades + agreement statistics. Supplement §5.4.                                                |
| Anonymized RunRecord schema documentation             | GH          | Schema for replicators consuming the JSONL.                                                        |

### T4.C — Standalone data results (already in deposit)

Path: `~/Desktop/Mandate Data/standalone data results/`

| Subdirectory                       | Destination | Rationale                                                                                           |
|------------------------------------|-------------|-----------------------------------------------------------------------------------------------------|
| `finding_1_decomposition/`         | BOTH        | 1480-record COA distribution + DAG samples. SUPP §4.1; GH JSONL + verbatim MD.                      |
| `finding_2_interpreter/`           | BOTH        | Per-domain mode rates + verbatim mode samples. SUPP §4.2; GH per-record JSONL.                      |
| `finding_3_validator/`             | BOTH        | Flag rationales (flagged + unflagged samples). SUPP §4.3; GH JSONL.                                 |
| `finding_4_binding/`               | BOTH        | Refusal samples by domain + refusal reason patterns. SUPP §4.4; GH JSONL.                           |
| `finding_5_intake/`                | BOTH        | All 20 Intake content-tripwire failures verbatim. SUPP §4.5; GH JSONL.                              |
| `cross_system/`                    | BOTH        | Cross-system anchor density + schema validity tables. SUPP §5.1-5.2; GH JSONL.                      |
| `dataset_inventory/`               | BOTH        | Per-system record counts + wall-clock distributions. SUPP §3; GH JSONL.                             |
| `baseline_calibration/`            | BOTH        | B1-B6 calibration summaries (used for strongest-baseline selection). SUPP §2; GH JSONL.             |
| `corpus_residue/`                  | BOTH        | Unused corpus pool audit. SUPP §8; GH JSONL.                                                        |
| `perturbations/`                   | BOTH        | 350-perturbation suite inventory. SUPP §7; GH JSONL.                                                |
| `pilot_smoke/`                     | BOTH        | 7×6 pilot smoke results. SUPP §6.6; GH JSONL.                                                       |
| `demo_scenarios/`                  | BOTH        | Volt Typhoon, CrowdStrike, SVB demo evidence. SUPP §6.1-6.4; GH JSONL.                              |
| `demo_memos/`                      | GH          | Demo-era findings memos (pre-Phase-6). Reference material.                                          |
| `deviations/`                      | BOTH        | v1 deviation log machine-readable. SUPP §9 Deviation Table; GH JSONL.                               |
| `handoff_chronology/`              | GH          | Full handoff execution log (engineering provenance). Operational record.                            |
| `handoff_costs/`                   | GH          | Per-handoff cost attestation. Engineering provenance.                                               |
| `realism_infrastructure/`          | GH          | SME realism audit machinery (forward-compat). Methodology.                                          |
| `v1_pilot_cross_profile/`          | BOTH        | April 2026 cross-profile findings + aggregates. SUPP §6.7; GH JSONL.                                |
| `v2_patch/`                        | GH          | v2 candidate Binding-refusal-as-gap patch trail. Forward methodology.                               |

### T4.D — Apparatus code (required for replication)

Apparatus path: `~/Desktop - lattice-ws01/MANDATE Evaluation/mandate_eval_2026Q2/`.

| Subdirectory                                          | Destination | Rationale                                                                                         |
|-------------------------------------------------------|-------------|---------------------------------------------------------------------------------------------------|
| `mandate-eval-primary-2026q2-v1` frozen tag (commit `4f8af83`) | GH | The apparatus snapshot reviewers replicate against. Mirror as `replication_package/code/`.        |
| `code/rag/embeddings/build_report.json`               | GH          | Source-document fetch report referenced in supplement §2.1. Required for corpus replication.      |
| `code/judges/`                                        | GH          | Three-judge ensemble grading code. Required to reproduce §5.4.                                    |
| `code/baselines/`                                     | GH          | B1-B6 baseline shells. Required to reproduce §5.                                                  |
| `code/perturbations/`                                 | GH          | Perturbation generator. Required to reproduce §7.                                                 |
| `seeds/20260603.json`                                 | GH          | Chunk-sampling seed file. Required for corpus replication.                                        |

### T4.E — Frozen tag chain

Five tags pinned at v1 close:

| Tag                          | Commit    | Contents                                          | Destination |
|------------------------------|-----------|---------------------------------------------------|-------------|
| `corpus_freeze_v1`           | -         | 120-task main + 30-task hold-out + 6-task pilot   | GH          |
| `baseline_freeze_v1`         | -         | B1-B6 RunRecords (7236 total)                     | GH          |
| `gt_freeze_v1`     | -         | SME-ratified ground-truth references              | GH          |
| `perturbation_freeze_v1`     | -         | 350-perturbation suite                             | GH          |
| `outputs_freeze_v1_1`        | `5f4de54` | 9036 RunRecords (1500+1180 MANDATE + 7236 baseline) | GH        |
| `mandate-eval-primary-2026q2-v1` | `4f8af83` | Apparatus code snapshot                         | GH          |

---

## T5 — v2 Work In Progress (Cond-X / Cond-A / Cond-B)

**Source root:** `~/Desktop - lattice-ws01/MANDATE Evaluation/mandate_eval_2026Q2/`
(v2 branch + working tree)

The v2 re-evaluation under canonical MANDATE with full pre-registration
coverage. Three measured conditions, shape-neutral rubric, full-coverage
Opus grading at 20% IRR, reactivated O5 adversarial outcome.

| Artifact                                            | Destination | Rationale                                                                                          |
|-----------------------------------------------------|-------------|----------------------------------------------------------------------------------------------------|
| Cond-X (regrade of v1 outputs under v2 rubric)      | GH (when ready) | Tests whether v1 schema-mismatch was the dispositive issue.                                    |
| Cond-A (pre-extracted structured input)             | GH (when ready) | Isolates apparatus contribution from upstream RAG.                                              |
| Cond-B (LLM-augmented Interpreter end-to-end)       | GH (when ready) | The headline v2 condition.                                                                      |
| Three-judge full-coverage Opus grading at 20% IRR   | GH (when ready) | The reactivated headline grading.                                                                |
| O5 adversarial outcome                              | GH (when ready) | Reactivated under D-11; addresses Reviewer 3 robustness ask.                                    |
| HANDOFF_19a / 19b / 19c / 19d (DomainProfile patches) | GH         | Apparatus patch chronology. Cited in v2 Protocol Amendment.                                      |
| HANDOFF_20 (Stage 4 full-coverage v2 grading)       | GH          | Forward methodology handoff to Codex.                                                            |
| HANDOFF_22 (multi-vendor Cond-B, if drafted)        | GH          | Addresses Reviewer 3 "comparative evaluation" complaint directly.                                |
| `~/Desktop/HANDOFF_19d_domain_profile_mapping.md`   | GH          | Engineering provenance for the auto-mapping patch.                                                |
| `~/Desktop/HANDOFF_20_stage4_full_coverage_v2_grading.md` | GH    | Engineering provenance for v2 Stage 4.                                                            |
| `v2 Protocol Amendment.tex/.pdf`                    | SUPP        | The 5-page amendment attached to the manuscript.                                                 |
| Salvage audit machine artifacts                     | GH          | Cited in Engineering and Operational Provenance.                                                  |

---

## OPS — Operational / Unrelated (excluded from deposit)

These directories were inspected during the comprehensive sweep and
contain MANDATE-adjacent or AEGIS-operational material that does
**not** belong in either the GH replication package or the academic
supplement. Listed here for completeness so future audits don't
re-investigate them.

| Source path                                                                | Class         | Why excluded                                                                                     |
|----------------------------------------------------------------------------|---------------|--------------------------------------------------------------------------------------------------|
| `~/Desktop - lattice-ws01/AEGIS-cleanup/logs/`                             | Operational   | KAN-751 acceptance + readiness gate logs (Apr 23-24, 2026). AEGIS engineering, not eval.         |
| `~/Desktop - lattice-ws01/AEGIS-cleanup/`                                  | Operational   | AEGIS codebase variant. Not MANDATE eval.                                                        |
| `~/Desktop - lattice-ws01/AEGIS-codex-authorized-lab-trace-ci/`            | Operational   | CI codebase variant. Not MANDATE eval.                                                           |
| `~/Desktop - lattice-ws01/AEGIS_archive_2026-04-13/`                       | Operational   | Pre-April-22 archive snapshot. Superseded.                                                       |
| `~/Desktop - lattice-ws01/TRACE Evaluation/`                               | Separate plane | TRACE plane (separate research project), not MANDATE.                                            |
| `~/Desktop - lattice-ws01/R1_audit_handoff/`                               | Operational   | Automation code-LOC counting. Not eval data.                                                     |
| `~/Desktop - lattice-ws01/R1_data_request/measurement_output.txt`          | Operational   | v3 automation measurement. Not eval data.                                                         |
| `~/Desktop - lattice-ws01/closed-loop-demo/` (×2)                          | Operational   | Demo videos and storyboards. Marketing/demo material.                                            |
| `~/Desktop/SWIFT/`, `~/Desktop/ONEnONE/`, `~/Desktop/Repos/`, etc.         | Unrelated     | Unrelated personal/Lattice projects. Outside MANDATE scope.                                      |
| `~/Documents/Dissertation/`, `~/Documents/Career/`                         | Unrelated     | Personal documents. Outside MANDATE scope.                                                       |

---

## Cross-Reference: Reviewer Objection → 2026Q2 Component → Evidence Tier

This is the bridge that makes the deposit coherent: every reviewer
objection from the two Frontiers in AI rejections maps to a specific
2026Q2 design choice, which maps to a specific tier of evidence.

| Reviewer objection (from `response_to_reviewers.pdf`)                    | 2026Q2 design response                                            | Evidence tier      | Where in supplement |
|--------------------------------------------------------------------------|-------------------------------------------------------------------|--------------------|---------------------|
| R1 "Empirical work preliminary" (8 scenarios × 1 backend)                | 1500-record main matrix × 7 systems × 10 seeds                    | T4                 | §3, §4, §5          |
| R3 "Absence of comparative evaluation"                                   | 6 pre-specified baselines (B1-B6) + three-judge ensemble grading  | T4                 | §2.2, §5            |
| R3 "Self-referential validation"                                         | Source-conditioned corpus authoring from 18 public docs           | T4                 | §2.1                |
| R3 "Robustness not demonstrated"                                         | 350-perturbation suite (7 types × 50 trials)                      | T4                 | §7                  |
| R3 "Scalability not demonstrated"                                        | 154-hour Ollama serial wall clock + per-domain stratification     | T4                 | §3.3                |
| R3 "No out-of-domain generalization"                                     | 30-task software_engineering hold-out (4th domain)                | T4                 | §3.4                |
| R3 "Single-vendor LLM execution" (Qwen3 only)                            | Multi-vendor Cond-B planned (HANDOFF_22)                          | T5 (pending)       | v2 Amendment §3     |
| R3 "Validation against rule-based system only"                           | Calibration tasks + SME ground truth + three independent judges   | T1 + T4            | §2.3, §2.4          |
| R1 "Limited domain coverage" (1 domain in paper)                         | 3 in-domain (security_ops, financial, intelligence) + hold-out    | T4                 | §2.1, §3.4          |
| R1 "No pre-registration"                                                  | Full pre-registration deposit (eval_package/)                    | T1                 | §1.1                |

---

## Routing Decision Audit Trail

Every routing decision in the tables above was made under the
following rules:

1. **If the artifact is required for a reviewer to reproduce a
   numerical claim**, it goes to **GH** (the data must be downloadable).
2. **If the artifact is required for a reviewer to *understand* a
   numerical claim** (interpret it in context), it goes to **SUPP**
   (the document must carry enough context to be read standalone).
3. **If both apply**, the artifact goes to **BOTH**: full data in GH,
   table/summary/citation in SUPP.
4. **If the artifact is project-internal engineering (handoffs, cost
   logs, salvage audits)**, it goes to **GH only** under
   `engineering_provenance/`. Reviewers can inspect; supplement does
   not depend on it.
5. **If the artifact is operational (CI logs, demo videos, archived
   snapshots)**, it goes to **OPS** and is excluded from both
   deposit destinations.

**Audit trigger:** Any future addition to the deposit must update
this catalog. Any reviewer question of the form "where is X?" should
be answerable from this file alone.

---

## v2 Update Trigger Points

The catalog above will need updates at these points:

- **When Stage 4 completes** (full-coverage Opus grading per Framing 2):
  T5 rows for Cond-X/A/B move from "(when ready)" to dated GH
  inclusion. Add new finding rows if Findings 6+ emerge.
- **When HANDOFF_22 is drafted and run** (multi-vendor Cond-B):
  T5 row "Multi-vendor Cond-B" moves from "(pending)" to GH
  inclusion. Update reviewer-mapping row R3 "Single-vendor LLM".
- **When the v2 deposit tag is minted** (`mandate-eval-primary-2026q2-v2`):
  Add new tag row to T4.E. Update SUPP rows for the v2 Empirical
  Evidence Supplemental section that supersedes v1 §5.4.
- **When the paper is resubmitted**: Update T0 status from "in review"
  to whatever the resubmission status is.

---

*Last updated: 2026-06-24. Maintained alongside the three supplement
PDFs in `~/Desktop/Mandate Data/`.*
