# MANDATE 2026Q2 Evaluation Apparatus: SOFTWARE_COMPLETE_v1

**Date:** 2026-06-03
**Apparatus tests:** 242 of 242 pass, 1 skipped (canned-PDF extraction, dependent on a pypdf release detail)
**Status:** Software side of the empirical evaluation is complete. Every component the protocol needs from the apparatus is built, unit-tested, and wired into the CLI. What remains is human work (SME ratings, SME ground-truth signoff, PI judgements, PI sign-offs, the deposit itself) and the runtime work Codex performs on the eval host (system runs, grading, analysis, the deposit).

## What is built

### Workstream A (MANDATE-primary)

- `apparatus/systems/mandate_primary.py` adapter with the corrected RAG retriever wiring and the thinnest input adapter (A2 recommendation).
- `apparatus/verify_mandate_primary.py` (A1) and `setup/run_a1_verification.sh` wrapper.
- `setup/recreate_aegis_eval.sh` produces the frozen `AEGIS-eval/` source.
- `apparatus/ablations/` (A4): seven ablation specs in `manifest.py`, `AblationSystem` in `system.py`. A3 (`emit_gaps=False`) and A5 (`success_registry=None`) are config switches and run today; A1, A2, A4, A6, A7 declare AEGIS-variant pins and refuse to run until the upstream tags exist.

### Workstream B (apparatus)

- `apparatus/harness/`: `RunRecord` + `RoleTiming` schema, append-only ledger, `run_matrix` orchestrator, the same-input contract.
- `apparatus/baselines/`: B1 (single-prompt Claude), B2 (single-prompt GPT), B3 (ReAct Claude), B4 (PlannerReviewer / AutoGen shape), B5 (SequentialCrew / CrewAI shape), B6 (GraphRevision / LangGraph shape). Mock-tested; framework integration is Phase 4 calibration on the eval host.
- `apparatus/perturbations/`: seven-type generator implementing PROMPTS Section 3 verbatim; CLI entry point at `apparatus.corpus.cli generate-perturbations`.
- `apparatus/anonymize.py`: identity stripping, random ID assignment, mapping kept separate; CLI at `apparatus.run anonymize`.
- `apparatus/grading/`: three-judge pipeline, locked PROMPTS Section 4 and 4a prompts, ensemble aggregation, schema-validity check, IRR with the 0.40 halt threshold; CLI at `apparatus.run grade`.
- `apparatus/scoring/`: O1 through O5 outcome scorers (count-weighted O1, gap classification mapping for O2a/O2b, fabrication count for O3, schema majority for O4, complement-of-compliance for O5), task-level median aggregator with PROTOCOL_LOCK Section 6.3 unit, run-cleanliness filter for the silent-fallback case.
- `apparatus/analysis/`: `power.py` (simulation-based power, drives Notebook 03), `models.py` (primary hypothesis tests with mixed-effects / GEE / robustness, Holm-Bonferroni, bootstrap CIs, operational-significance check), `descriptive.py` (corpus and system summaries + cost summary), `failure_modes.py` (the nine-category taxonomy).
- `09_analysis/`: ten notebooks. 03 (power) runs now; 01, 02, 04-10 are gated drivers that auto-skip until phase inputs exist and execute end to end via `apparatus.run run-analysis`.

### Workstream C (corpus)

- `apparatus/corpus/sources/`: per-domain authoritative source list (`curated_sources.py`), `fetch.py` (HTML + PDF via pypdf), `manual.py` (PI-downloaded PDFs with SHA-256 provenance), AEGIS-format Jaccard index build.
- `apparatus/corpus/source_conditioned.py` and the reconciled PROMPTS Section 1 source-conditioned variant (`_package/RECONCILIATION_LOG.md` Change 9).
- `apparatus/corpus/cli.py` subcommands: `source-build`, `source-generate`, `ingest-manual`, `dedup`, `leakage`, `scaffold`, `select-main`, `realism-form`, `realism-aggregate`, `generate-perturbations`, `pilot`. Auto-loads `.env`.
- `apparatus/corpus/selection.py`: stratified water-fill selection helper for 40-per-domain main-corpus selection.
- `apparatus/corpus/realism.py`: FORMS Section 4 rating aggregation, halt-rule check at mean < 2.5, Krippendorff alpha across raters.

### Apparatus top-level

- `apparatus/run.py` (Phase 6-9 entry points): `run-system`, `anonymize`, `grade`, `run-analysis`.

## Handoffs (Codex runbooks)

Sixteen handoff documents under `handoffs/` covering every phase of the protocol. Each is self-contained, decision-bounded, and produces a templated report.

| # | Audience | Mission |
|---|----------|---------|
| 01 | Codex | MANDATE-primary verification on the eval host |
| 02 | Codex (superseded) | Pilot corpus (synthetic, superseded by 07) |
| 03 | Codex (DONE) | Main corpus authoring |
| 04 | Codex | B4-B6 calibration |
| 05 | Upstream MANDATE | Five AEGIS-variant ablation tags |
| 06 | Codex | Pilot anchor scaffolds |
| 07 (+b/c/d) | Codex (DONE) | Source-first corpus iterations |
| 08 | Codex | Hold-out corpus (4th domain) |
| 09 | Codex | Main anchor scaffolds (120 tasks) |
| 10 | Codex | 350-perturbation suite |
| 11 | Codex | Phase 6 main run + anonymization |
| 12 | Codex | Phase 7 ablation runs |
| 13 | Codex | Phase 8 grading |
| 14 | Codex | Phase 9 analysis |
| 15 | Codex + PI | Final report + Zenodo deposit |

## What is not in the apparatus, by design

- **Human judgements.** The SME realism ratings on the 120 selected main tasks, the SME independent-then-review anchor authoring (FORMS Section 1), the SME 12-task IRR overlap, the external spot-check on 24 tasks, the 100-output human-vs-judge calibration, and the PI's selection and sign-off decisions are all human work. The apparatus provides templates, aggregators, halt-rule checks, and audit trails for each, but no apparatus produces the judgement itself.
- **The deposit itself.** The Zenodo deposit and the paper submission are PI actions. The replication package is assembled by the apparatus; the deposit lands the DOI.
- **Five of seven ablations.** A1 (no role separation), A2 (no tolerance bands), A4 (no Validation role), A6 (no search-trace), A7 (no NIST RMF metadata) need upstream MANDATE source variants. The apparatus refuses to silently substitute MANDATE-primary for an unbuilt variant. HANDOFF_05 specifies the variants for the upstream team.
- **Live framework integration of B4-B6.** The apparatus shells implement the AutoGen / CrewAI / LangGraph orchestration patterns with direct LLMClient calls; Phase 4 calibration on the eval host swaps in the live frameworks if the PI decides that contributes to validity. The protocol's measured behavior is the same either way (the framework, not the model, is the variable under test).

## Apparatus version

`mandate-eval-apparatus-2026q2-v1`. After this point, changes to the apparatus are recorded in `10_report/deviation_log.md` if they happen after deposit, in `_package/RECONCILIATION_LOG.md` if they happen before deposit.
