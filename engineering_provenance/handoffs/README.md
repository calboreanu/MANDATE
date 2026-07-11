# Codex Handoffs

Self-contained task packages a Codex (or human) operator can execute on the eval host to move the MANDATE evaluation forward without copy-paste from the PI. Each handoff is one file, one mission, one report.

## Pattern

Every handoff carries the same shape, so they read the same way:

- **Mission and definition of done.** What the handoff produces, and the one-line test for success.
- **Preconditions.** What must be true before starting. Stop and report if any is false.
- **Decision boundary.** What the operator may decide on the spot, what must escalate to the PI, what they may not do.
- **Sequential tasks.** Each task has a command, a verification, success criteria, and an on-failure rule.
- **Final report.** A templated markdown handed back to the PI. Verdict is one word: PROCEED or HALT.

## Open handoffs

| # | Audience | File | Mission | Estimated wall clock | Blocks on |
|---|----------|------|---------|----------------------|-----------|
| 01 | Codex (eval host) | `HANDOFF_01_mandate_verification.md` | Recreate `AEGIS-eval/`, run A1 in Ollama mode, refresh provenance, run the apparatus suite. The audit-required re-verification. | 30 to 90 min | nothing |
| 02 | Codex (eval host) | `HANDOFF_02_corpus_pilot.md` | Execution plan §13 action 7: generate the six pilot-task candidate set, dedup, leakage audit against the training corpus. | 10 to 30 min | Handoff 01 PROCEED |
| 03 | Codex (eval host) | `HANDOFF_03_main_corpus.md` | Source-first authoring of the 120-task main corpus across the three pre-registered domains (~200 candidate deduped pool for PI 40-per-domain selection). | 90 to 150 min | Handoff 06 PROCEED, PI-confirmed source list (intel coverage in particular) |
| 05 | MANDATE upstream | `HANDOFF_05_upstream_ablations.md` | Build the five AEGIS-variant ablations A1, A2, A4, A6, A7 as separate tags. The two config-switch ablations A3, A5 already run from the primary tag. | 2-3 engineer-weeks | nothing (parallel) |
| 06 | Codex (eval host) | `HANDOFF_06_pilot_anchor_scaffolds.md` | PROMPTS Section 2 anchor scaffolds for the six PI-selected pilot tasks. Produces the SME-review input. | 5 to 15 min | PI writes `03_corpus/pilot/pilot_selection.json` |
| 07 | Codex (eval host) | `HANDOFF_07_source_first_corpus.md` | PROMPTS Section 1 post-reconciliation: build per-domain real-document indexes (HTML and PDF), generate source-derived candidates with `derived_from` per candidate. Supersedes Handoff 02's synthetic pilot. | 60 to 120 min | pypdf installable, outbound HTTPS to source hosts |
| 09 | Codex (eval host) | `HANDOFF_09_main_anchor_scaffolds.md` | PROMPTS Section 2 anchor scaffolds for the 120 selected main-corpus tasks. Same shape as Handoff 06, scaled. SME-review input for ground-truth construction. | 15 to 25 min | corpus_freeze_v1 tag, main_selection.json |
| 10 | Codex (eval host) | `HANDOFF_10_perturbations.md` | Phase 5: 350-perturbation suite generated from the 30-task stratified base. Seven types at 50 trials each per PROTOCOL_LOCK Section 1. | 30 to 45 min | corpus_freeze_v1 tag, ground truth signed off |
| 04 | Codex (eval host) | `HANDOFF_04_baselines_b4_b6.md` | Phase 4 calibration: B4 / B5 / B6 multi-agent baselines on the six calibration tasks. | 30 to 60 min per baseline | corpus_freeze_v1, baseline model choice (memo Section 4) |
| 08 | Codex (eval host) | `HANDOFF_08_holdout_corpus.md` | 30-task hold-out 4th-domain corpus via source-first. Default hold-out: software_engineering_specification. | 30 to 60 min | hold-out 4th domain confirmed (memo Section 1) |
| 11 | Codex (eval host) | `HANDOFF_11_phase6_main_run.md` | Phase 6: main run across every system at pre-registered run counts, anonymization, outputs_freeze_v1. | hundreds of hours | pre-registration deposited, three freeze tags |
| 12 | Codex (eval host) | `HANDOFF_12_phase7_ablations.md` | Phase 7: seven ablations on the 30-task ablation subset at 10 runs each. | tens to hundreds of hours | outputs_freeze_v1, upstream variant tags for A1/A2/A4/A6/A7 |
| 13 | Codex (eval host) | `HANDOFF_13_phase8_grading.md` | Phase 8: three-judge grading over every anonymized output, IRR halt check. | dozens of hours | ablation_freeze_v1, all three judge API keys, IRR threshold pre-registered |
| 14 | Codex (eval host) | `HANDOFF_14_phase9_analysis.md` | Phase 9: execute analysis notebooks 01 through 10 against the real data. | 30 to 90 min | Phase 8 PROCEED, MANDATE_STRONGEST_BASELINE designated |
| 15 | Codex + PI | `HANDOFF_15_deposit_replication.md` | Final report and Zenodo replication-package deposit. | 4 to 8 hours | Phase 9 PROCEED, deviation log signed |

## Reports

Each completed handoff writes `HANDOFF_<NN>_report_<YYYY-MM-DD>.md` alongside the handoff file. Reports are committed to the project record. The PI reads the report verdict and decides the next handoff.

## What is not in a handoff

Decisions: the items in `00_preregistration/DECISIONS_AND_PROPOSALS_memo_v1.md` are the PI's, not Codex's. Recruitment, signoff, and grading are humans-only. Upstream MANDATE coding (for the five AEGIS-variant ablations A1, A2, A4, A6, A7) lives with the MANDATE team, not in these handoffs.
