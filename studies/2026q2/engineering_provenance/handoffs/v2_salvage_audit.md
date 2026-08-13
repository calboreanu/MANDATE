# MANDATE v2 Pivot — Data Asset Salvage Audit

**Date:** 2026-06-23
**Scope:** `/Users/ws01admin/Desktop/Desktop - lattice-ws01/MANDATE Evaluation/mandate_eval_2026Q2/`
**Purpose:** Classify every material data asset on disk into KEEP / REFRAME / RE-GRADE-RE-PROCESS / RETIRE for the v2 pivot.

---

## Critical context found during audit

1. **"1500 records" is 150 unique tasks × 10 runs.** `04_ground_truth/ground_truth.json` contains 150 entries (120 `TASK-MAIN-*` + 30 `TASK-HOLDOUT-SES-*`). `07_system_outputs/mandate_primary/` has 1200 main + 300 holdout artifacts. The Cond-X scoping in v2 should make this explicit.
2. **"Deterministic" is a partial misnomer.** Every `mandate_primary` record carries `llm_used: true` for all six MANDATE roles (Intake / Interpreter / Decomposition / Procedure / Binding / Validation) against local Ollama models with `seed: 20260606` and `llm_role_temperatures: 0.0–0.2`. Cond-X label should read "MANDATE-primary, low-temperature LLM, raw-text input, drifted fork" rather than "deterministic-no-structure".
3. **Schema mismatch confirmed.** `apparatus/grading/rubric.py` lines 48–58 score `minimum_coverage` as a count of ground-truth `{dimension, threshold, rationale}` fields. `AEGIS-eval/src/mandate/schemas/mandate-as-code.schema.json` defines `minimum` as a free-form `object`. MANDATE-primary records emit `minimum: {"description": "..."}` and get ~0.22; the five baselines whose prompts asked for the array shape get ~0.75+. The grading was structurally biased.
4. **Empty scaffold directories everywhere.** Many advertised v1 deliverables (`signed_anchors/`, `signoff_packets/`, `ablations/a1..a7/`, `mandate_backends/*`, `human_expert/`, `hold_out/`, `incomplete_grades/`, all `tags/` dirs) are zero-byte placeholders. None of them constrain v2.

---

## Section 1 — Corpus (`03_corpus/`)

| Path | What it is | Class | Why | Size |
|---|---|---|---|---|
| `03_corpus/main/` | NL task corpus, 262 candidates → 120 selected, with `dedup_report.json`, `leakage_audit.json`, `selection_proposal.md` | **KEEP** | Schema-agnostic natural language; exactly what Cond-A's extractor and Cond-B's interpreter need. Provenance to NIST/SOX/COSO/etc. intact. | 591 KB jsonl + 35 KB selection + 423 KB proposal |
| `03_corpus/holdout/` | Out-of-domain holdout, 44 candidates → 30 selected (software_engineering_specification) | **KEEP** | Same NL schema as main; preserves OOD generalization test for Cond-A/B. | 128 KB |
| `03_corpus/pilot/` | 15 pilots, `pilot_selection.json` selects 6; `SUPERSEDED.md` deprecates older lineage | **KEEP** | NL pilots for smoke runs. Honor `SUPERSEDED.md`. | 500 KB |
| `03_corpus/candidates_source_first/`, `_main/`, `_holdout/` | Pre-dedup candidate pools | **KEEP** | Lineage required for replication package. | 956+612+104 KB |
| `03_corpus/realism_audits/` | Realism audit shell | **RETIRE** | Empty. Actual realism rater templates live at `04_ground_truth/realism/`. | 0 |
| `03_corpus/leakage_audit/`, `candidates/`, `tags/`, `domain_financial/`, `domain_intel/`, `domain_security/` | Six empty placeholders | **RETIRE** | Zero-byte. Regenerate from `main/` if v2 wants per-domain shards. | 0 |

---

## Section 2 — Ground truth + anchors (`04_ground_truth/`)

| Path | What it is | Class | Why | Size |
|---|---|---|---|---|
| `04_ground_truth/ground_truth.json` | 150 anchor records: `mission_intent`, `minimum` (as `[{dimension, threshold, rationale}, ...]`), `target`, `constraints`, `suspected_gaps` | **REFRAME + RE-GRADE** | Schema-locked to the v1 rubric shape (verified 150/150). Content (mission language, thresholds, source citations) is high quality. New role: **rubric for semantic LLM-judging**, not a structural reference for canonical MANDATE outputs. | 1.85 MB |
| `04_ground_truth/main_tasks.jsonl` | 120 lines: `task_id → request text` lookup | **KEEP** | Schema-agnostic. All three v2 conditions need it. | small |
| `04_ground_truth/holdout_tasks.jsonl`, `pilot_tasks.jsonl` | 30 + 6 lines, same shape | **KEEP** | Same as above. | small |
| `04_ground_truth/main_scaffolds/anchor_scaffolds.jsonl` | 120 per-task scaffold builds (raw form of `ground_truth.json`) with same broken `minimum` shape | **REFRAME** | Use only as rubric source, never as a structural reference for canonical MANDATE. | 3.0 MB dir |
| `04_ground_truth/main_scaffolds/main_tasks_resolved.jsonl` | 120 lines: tasks joined with `derived_from` | **KEEP** | Schema-agnostic; reusable for source-citation tracing. | small |
| `04_ground_truth/holdout_scaffolds/`, `pilot_scaffolds/` | Same as main_scaffolds, smaller | **REFRAME** | `*_resolved.jsonl` KEEP; `anchor_scaffolds.jsonl` re-grade as rubric only. | 792 + 156 KB |
| `04_ground_truth/realism/rater_carter.csv`, `rater_mckay.csv` | 120 task rows × 2 raters, `rating`/`notes` blank | **KEEP** | Schema-agnostic templates. Re-run audit on the same NL tasks or extend to new conditions. | small |
| `04_ground_truth/signed_anchors/` | Cryptographic anchor signing | **RETIRE** | Empty directory — never produced in v1. No schema lock. Generate fresh for v2 if needed. | 0 |
| `04_ground_truth/signoff_packets/` | PI signoff packet output | **RETIRE** | Empty — never produced. | 0 |
| `04_ground_truth/{external_spotcheck, hold_out_domain, overlap_sample, scaffolds, tags}/` | Empty placeholders | **RETIRE** | Zero-byte; drop from manifest. | 0 |

---

## Section 3 — Perturbations (`06_perturbations/`)

| Path | What it is | Class | Why | Size |
|---|---|---|---|---|
| `06_perturbations/perturbation_suite.jsonl` | 350 NL perturbations, 7 types × 50 (surface_noise, ambiguity_injection, contradictory_constraints, prompt_injection, missing_required_field, out_of_distribution_input, length_perturbation), 30 base tasks | **KEEP** | Applied to `request_text` only — schema-agnostic. All three v2 conditions ingest directly. `missing_required_field` and `contradictory_constraints` become *more* informative under canonical MANDATE because the system will actually attempt extraction. | 1.0 MB |
| `06_perturbations/tags/` | Freeze tags dir | **RETIRE** | Empty. | 0 |

---

## Section 4 — System outputs (`07_system_outputs/`)

| Path | What it is | Class | Why | Size |
|---|---|---|---|---|
| `07_system_outputs/mandate_primary/` | 1500 records (120 main × 10 runs + 30 holdout × 10), drifted MANDATE (`code_ref: mandate-eval-primary-2026q2-v1`), `output_type: MANDATE_AS_CODE`, single-COA, `minimum: {description: ...}` | **KEEP as Cond-X** | These ARE Cond-X. Do not reuse for Cond-A/B — those require canonical MLT v1.0.0rc1 + structured `MissionInput`. Re-grade under v2 rubric to quantify the schema-mismatch effect. | 104 MB |
| `07_system_outputs/mandate_primary/ledger.jsonl` | 3396-line run audit log | **KEEP** | Audit trail. | small |
| `07_system_outputs/baseline_1/` | B1 single-prompt planner, Claude sonnet-4-6, 1500 records | **KEEP runs; RE-GRADE** | Independent LLM system, not coupled to MANDATE internals. But baseline prompts asked for `{dimension, threshold, rationale}` shape → partly schema-coupled. Either (a) re-prompt shape-neutral and re-run, or (b) re-grade under shape-agnostic v2 rubric. | 62 MB |
| `07_system_outputs/baseline_2/` | B2 single-prompt, GPT-4o, 1200 records | **KEEP; RE-GRADE** | Same as B1. | ~35 MB |
| `07_system_outputs/baseline_3/` | B3 ReAct (Claude), 1200 records — only baseline emitting `minimum` as dict | **KEEP; RE-GRADE** | Useful as natural-dict-emitting comparator. | ~25 MB |
| `07_system_outputs/baseline_4/` | B4 AutoGen planner+reviewer (Claude), 1200 | **KEEP; RE-GRADE** | Multi-agent comparator. | ~30 MB |
| `07_system_outputs/baseline_5/` | B5 CrewAI sequential crew (Claude), 1200 | **KEEP; RE-GRADE** | Multi-agent comparator. | ~30 MB |
| `07_system_outputs/baseline_6/` | B6 LangGraph draft/review/revise (Claude), 1200 | **KEEP; RE-GRADE** | Multi-agent comparator. | ~30 MB |
| `07_system_outputs/*_pilot/` (×7) | 6 pilot records each per system | **KEEP** | Cheap audit trail of pilot smoke runs. | ~tens of KB each |
| `07_system_outputs/hold_out/`, `human_expert/`, `tags/` | Empty scaffolds | **RETIRE** | Holdout actually inside `mandate_primary/holdout/` and `baseline_1/holdout/`. Freeze docs in `handoffs/HANDOFF_11b_ii_baselines_holdout_freeze.md`. | 0 |
| `07_system_outputs/ablations/{a1..a7}/` | Ablation matrix (no_role_separation … no_risk_metadata) | **RETIRE** | All empty — never executed. Design v2 ablations against canonical MLT roles. | 0 |
| `07_system_outputs/mandate_backends/{claude_sonnet, gemma3, llama3.3, mistral_large, qwen3_base}/` | Cross-backend study | **RETIRE** | All empty. Cond-B should drive this matrix in v2. | 0 |
| `07_system_outputs/anonymization_mapping.json` | 9000-entry anonymous-ID map | **RE-PROCESS** | v2 must add Cond-A/B IDs. Reuse Cond-X (mandate_primary) entries as-is; mint new IDs for Cond-A/B. | 1.9 MB |

---

## Section 5 — Phase 8 grading (`08_grading/`)

| Path | What it is | Class | Why | Size |
|---|---|---|---|---|
| `08_grading/sample_manifest.jsonl` (+ `_meta.json`) | 700 stratified records, 100 per system × 7, seed 20260618 | **RE-PROCESS** | v2 needs re-stratification across Cond-X, Cond-A, Cond-B + 6 baselines. Keep manifest design (deviation D-08 documented). | 73 KB |
| `08_grading/by_record/` | 700 per-record grades: judge_scores × 3 + ensemble across 8 rubric dimensions | **RE-GRADE** | Rubric-locked to v1 shape. MANDATE-primary systematically penalized. Salvage value: input to schema-mismatch effect study. | 6.7 MB |
| `08_grading/judge_1_gpt4o/scores.jsonl`, `judge_2_claude_opus/scores.jsonl`, `judge_3_gemini_pro/scores.jsonl` | 700 lines each = 2100 individual judge scores. Judges: gpt-4o-2024-11-20, claude-sonnet-4-6 (note: dir-name says opus, config says sonnet), gemini-2.5-pro | **RE-GRADE (keep raw as audit)** | Raw judge outputs are immutable audit material. Re-grade under v2 rubric using the same anonymized outputs and judge configs. | 5.3 MB total |
| `08_grading/irr.json` | Krippendorff α + pairwise κ across pass1 + pass2 double-grade | **REFRAME** | Halt=true at α 0.40 threshold. α = 0.70 (`minimum_coverage`), 0.60 (`gap_classification`), 0.46 (`mission_intent_match`), 0.28 (`trace_completeness`), 0.23 (`fabrication_count`). Use as: (a) prior on judge disagreement structure, (b) evidence that low-α dimensions need rubric refinement, (c) baseline for claiming v2 rubric improvement. | 3.3 KB |
| `08_grading/double_grade/pass1*, pass2*, manifest, sample_anon_ids.json` | Intra-judge stability check, 70 records (10% of 700), seed 20260618 | **RE-GRADE** | Same rubric flaw inherited. Keep current as v1 stability evidence; re-run under v2 rubric. | 1.1 MB |
| `08_grading/incomplete_grades/` | Quarantine for incomplete grading runs | **RETIRE** | Empty. | 0 |
| `08_grading/failed_attempts/` | 1 quarantined attempt: `HANDOFF_13e_revised_attempt_05_20260618_gemini_503/` | **KEEP** | Documents retry/quarantine semantics. Useful for v2 reproducibility narrative. | 60 KB |
| `08_grading/anonymized_outputs/` | 9000 anonymized system outputs ready for blinded judging | **RE-PROCESS** | Schema-mismatch issue is in the underlying artifacts, not in anonymization. Re-anonymize across Cond-X + Cond-A + Cond-B for v2. | 183 MB |
| `08_grading/ensemble_aggregated/ensemble_scores.jsonl` | 700-line median/aggregate across 3 judges | **RE-GRADE** | Aggregated outputs of v1 rubric. | 253 KB |
| `08_grading/judges_config.json`, `logs/` | Judge endpoint/model configs + 7 handoff stdout logs | **KEEP (audit)** | Reusable judge config + immutable run logs. | 32 KB logs |
| `08_grading/failure_coding/`, `human_vs_judge/`, `inter_grader_sample/` | Three empty placeholders | **RETIRE** | Zero-byte; design v2 equivalents if needed. | 0 |

---

## Section 6 — Demo evidence (`demo/`, recent handoffs)

| Path | What it is | Class | Why | Size |
|---|---|---|---|---|
| `demo/crowdstrike_outage/`, `svb_collapse/`, `volt_typhoon/` | Real-source-grounded showcase runs through drifted MP + Ollama. Each has `_fetch.py`, `sources/` (binaries + SHA-256 manifest + fetch_report.json), `output_ollama*/`, `rag/`, `tasks/` | **REFRAME (narratives) + RE-PROCESS (artifacts)** | The four qualitative findings (single-COA decomposition, Interpreter mode flip, Validator content-tripwire, Binding refusal) and source binary provenance are reusable narrative. The 13 RunRecords are drifted-MP artifacts and the Binding-refusal-as-gap patch is moot under canonical MLT (Binding refusal IS a valid GapSpec). Re-run all three scenarios under Cond-A and Cond-B. Keep `sources/` binaries verbatim. | 78 MB |
| `demo/EXECUTIVE_SUMMARY.md`, `MANDATE_DEMO_FINDINGS.md`, `RERUN_FROM_BINARIES.md`, `SOURCE_BINARIES_INVENTORY.md`, `UPSTREAM_MANDATE_NOTE_decomposition_bias.md` | Narrative + replication docs | **REFRAME** | Update to point at canonical MLT and v2 conditions. | small |
| `handoffs/HANDOFF_16*` (16, 16b, 16c demo-from-binaries) | Demo replication handoffs | **KEEP** | Decision provenance + replication procedure. | small |
| `handoffs/HANDOFF_17*` (17/17b/17c Binding-refusal-as-gap patch; 17d upstream migration) | Patch chronology | **KEEP** | 17–17c document a workaround moot under canonical MLT but recording it explains v2 simplification. 17d is direct v2 input. | small |
| `handoffs/HANDOFF_19b`, `20`, `21`, `23`, `24`, `25`, `26` | Materialize/freeze/holdout chain | **KEEP** | Supersede in HANDOFF_27 (v2 pivot) but preserve. HANDOFF_26 (holdout contamination) is methodology relevant to Cond-X re-confirmation. | small |
| `handoffs/v2_redesign_audit_role_schemas.md`, `MLT_realness_audit_opus.md` | Direct v2 design inputs | **KEEP** | MLT realness audit verified `mlt-stack 1.0.0rc1` as REAL: 418 passed / 8 skipped / 3 xfailed; real recursive-descent constraint parser, real Rego/Cedar translators, hash-chained trace. | small |
| `handoffs/` (94 files, 840 KB total) | Full historical record | **KEEP** | Decision provenance. | 840 KB |

---

## Section 7 — Apparatus code (`apparatus/`)

| Path | What it is | LOC | Class | Why |
|---|---|---|---|---|
| `apparatus/grading/rubric.py` | v1 grading rubric (MINIMUM/TARGET/CONSTRAINT coverage as field-count with dimension+threshold match) | 175 | **RETIRE** | Load-bearing schema-mismatch artifact. Lines 48–58 require array shape. Replace with a v2 rubric scoring semantic coverage of ground-truth dimensions against a free-form-object payload, plus separate Cond-A (pre-extracted MissionInput) vs Cond-B (LLM Interpreter end-to-end) handling. |
| `apparatus/grading/judge.py` | Judge calls + retry/backoff (5/15/45s schedule, fixed in HANDOFF_13f) for 503/429 | 313 | **KEEP** | Canonical and reusable. |
| `apparatus/grading/pipeline.py` | Checkpointing + 3-judge ensemble orchestration | 260 | **KEEP** | Reusable. |
| `apparatus/grading/ensemble.py` | Aggregation across judges + 0.40 IRR halt | 226 | **KEEP** | Reusable. |
| `apparatus/grading/probe_gemini.py` | Pre-flight Gemini probe | 144 | **KEEP** | Reusable. |
| `apparatus/run.py` | CLI driver: `run-system / anonymize / grade / run-analysis` | 448 | **KEEP (structurally)** | The four-stage shape is the right v2 driver. Update `run-system` to dispatch into canonical MLT (Cond-A/B). Point `grade` at v2 rubric. |
| `apparatus/baselines/base.py` | Baseline base class | 171 | **KEEP** | System-independent. |
| `apparatus/baselines/llm_client.py` | Anthropic/OpenAI/Gemini wrappers (shared with `judge.py`) | 165 | **KEEP** | Shared utility. |
| `apparatus/baselines/multi_agent.py` | B4/B5/B6 AutoGen/CrewAI/LangGraph adapters | 196 | **KEEP** | Baselines remain valid v2 comparators. |
| `apparatus/baselines/prompts.py` | Baseline prompts | 163 | **KEEP (audit) / REFRAME** | Current prompts ask for v1-shape spec; optionally re-prompt shape-neutral for v2. |
| `apparatus/baselines/react.py` (B3), `single_prompt.py` (B1/B2), `schema.py` | Specific baseline impls + schema helper | 85+51+100 | **KEEP** | Reusable. |

---

## Section 8 — Supplemental + deposit (`Mandate Data/`, `deposit/`)

| Path | What it is | Class | Why | Size |
|---|---|---|---|---|
| `Mandate Data/Empirical Evidence Supplemental.tex` + `.pdf` | Standalone LaTeX manuscript for MANDATE-primary 2026Q2 (anonymous submission, 2026-06-17) describing the 1500 records | **REFRAME** | v1-conditional; under v2 becomes the Cond-X chapter. Title/abstract rewrite; methodology + source-binary tables stay; numerical findings stay but reframed as "MANDATE on raw text without canonical anchor structure." | 1.9 MB dir |
| `Mandate Data/standalone data results/` | 17 subdirs of pre-computed aggregates (finding_{1..5}, dataset_inventory, baseline_calibration, cross_system, perturbations, handoff_chronology, handoff_costs, deviations, pilot_smoke, corpus_residue, realism_infrastructure, demo_memos, demo_scenarios, v2_patch) | **KEEP as Cond-X aggregates** | Valid descriptors of "MANDATE on raw text." Comparison points for Cond-A/B. | 48 files |
| `deposit/supplemental/appendix/` | appendix.tex + appendix.pdf | **REFRAME** | Reuse structure; rewrite for v2. | 216 KB |
| `deposit/supplemental/zenodo_package/` | CHANGELOG, CITATION.cff, DATA_DICTIONARY, LICENSE, README, croissant.json, `artifacts/`, `code/`, `containers/`, `docs/` | **REFRAME** | Packaging scaffold reusable; data manifests must regenerate once v2 outputs exist. Pre-registration deposit (HANDOFF_15) was conditional on Phase 9 PROCEED, which v2 invalidates — re-deposit under a new tag. | 80 KB |

---

## Section 9 — Pre-Phase-6 work (`01_pilot/` … `11_replication_package/`)

| Path | What it is | Class | Why | Size |
|---|---|---|---|---|
| `01_pilot/` | Pilot phase shell (grading/, runs/, signoffs/, tasks/ stubs) | **KEEP (methodology)** | Drop-target for v2 pilot. | 12 KB |
| `02_calibration/tasks/TASK-CAL-{FIN,INT,SEC}-00{1,2}.json` | Six calibration tasks across three domains | **KEEP** | Domain-independent of MANDATE version. Reusable for Cond-A/B calibration. | 24 KB |
| `05_baselines/calibration_logs/`, `frozen_configs/`, `tags/` | Baseline calibration shells | **KEEP** | Empty drop-targets for v2 baseline freeze. | 0 |
| `09_analysis/` | 10 numbered notebooks (descriptive → primary tests → Bayesian → subgroup → sensitivity → ablation → failure modes → final tables) + `03_power_confirmation_result.json` + `figures/` | **REFRAME** | Structure is correct; notebooks read from v1 grading outputs. Re-run after v2 grading produces compatible inputs. | 100 KB |
| `10_report/deviation_log.md` | Append-only deviation log | **KEEP** | The v2 pivot itself is the next deviation entry. | 4 KB |
| `11_replication_package/` | Empty | **KEEP (drop-target)** | Assemble at end of v2. | 0 |

---

## Section 10 — AEGIS-eval drifted code (`AEGIS-eval/`)

| Path | What it is | Size / LOC | Class | Why |
|---|---|---|---|---|
| `AEGIS-eval/src/mandate/` | Drifted experimental MANDATE source (71 files, 6793 LOC): `cli.py`, `constraints.py`, `domain.py` (PENTEST/IR/DEFENSE_INTEL profiles), `evaluation.py`, `gap_report.py`, `hashing.py`, `llm_support.py`, `metrics.py`, `models.py`, `nist_rmf.py`, `pipeline.py`, `registry.py`, `roles/{base,intake,interpreter,decomposition,procedure,binding,validation}.py`, `schema.py`, `schemas/{mandate-as-code,gap-report,trace-entry}.schema.json`, `success_registry.py` (1127 LOC), `trace_prov.py`, `translators/{cedar,rego}.py`, `validator.py` | 1.2 MB / 6793 LOC | **RETIRE** | Schema accepts `anchor.minimum` as free-form `object`; ground truth and rubric expect array. `domain.py` is pentest-centric, not aligned with v2 domain-profile pattern. Replace with canonical `mlt.mandate` at `/Users/ws01admin/Desktop/MLT-Governance-Stack` (`mlt-stack 1.0.0rc1`, verified REAL). |
| `AEGIS-eval/.worktrees/cowork_fixer/`, `lane_09_nightly_self_heal_sweep/`, `workstream-a/` | Three full AEGIS bundle worktrees | 14 MB each | **RETIRE** | Each pins the drifted MANDATE source. Frozen for Cond-X provenance only. |
| `AEGIS-eval.corrupted-backup-20260605-063244/` | Pre-restore snapshot referenced in HANDOFF_22 | 95 entries | **KEEP** | Historical-restore evidence until v2 freeze cuts. |
| **Replacement** | `apparatus/systems/mandate_canonical.py` adapter pointing at canonical MLT v1.0.0rc1 | (new) | — | Wires Cond-A (deterministic, pre-extracted MissionInput) and Cond-B (LLM Interpreter end-to-end). |

---

## Summary count

Counting at the level of distinct material assets (a directory of records counts as one; an empty placeholder counts as one).

| Section | KEEP | REFRAME | RE-GRADE / RE-PROCESS | RETIRE | Total |
|---|---|---|---|---|---|
| 1. Corpus | 4 | 0 | 0 | 7 | 11 |
| 2. Ground truth + anchors | 5 | 2 (+1 dual) | 1 (dual w/ REFRAME) | 7 | 15 |
| 3. Perturbations | 1 | 0 | 0 | 1 | 2 |
| 4. System outputs | 8 | 0 | 1 | 13 | 22 |
| 5. Phase 8 grading | 3 | 1 | 7 | 5 | 16 |
| 6. Demo + handoffs | 5 | 1 | 1 | 0 | 7 |
| 7. Apparatus code | 9 | 0 (rubric retire, prompts optional reframe) | 0 | 1 | 10 |
| 8. Supplemental + deposit | 1 | 3 | 0 | 0 | 4 |
| 9. Pre-Phase-6 | 5 | 1 | 0 | 0 | 6 |
| 10. AEGIS-eval drifted | 1 | 0 | 0 | 4 | 5 |
| **Total** | **42** | **8** | **10** | **38** | **98** |

(The `ground_truth.json` family is counted under both REFRAME and RE-GRADE because it is genuinely dual-purpose: keep the content, change the interpretation, and re-grade outputs against it under the v2 rubric.)

---

## Cross-cutting v2 punch list

1. **Rename Cond-X** to drop "deterministic" — records have `llm_used: true` everywhere. Suggested label: *"MANDATE-primary on raw text, drifted fork, low-temperature LLM"*.
2. **Write v2 rubric** replacing `apparatus/grading/rubric.py`, scoring semantic coverage of ground-truth `{dimension, threshold, rationale}` dimensions against canonical MANDATE's free-form-object payload; separate Cond-A (pre-extracted MissionInput) vs Cond-B (LLM Interpreter end-to-end) handling.
3. **Build adapter** `apparatus/systems/mandate_canonical.py` against canonical MLT v1.0.0rc1 (`/Users/ws01admin/Desktop/MLT-Governance-Stack`); keep AEGIS-eval drifted source as Cond-X freeze only.
4. **Keep**: `judge.py`, `pipeline.py`, `ensemble.py`, `probe_gemini.py`, all baselines, `apparatus/run.py` CLI shape, calibration tasks, deviation log, ground-truth content (reframed as rubric), corpus, perturbations.
5. **Re-grade the existing 700-sample under v2 rubric** to quantify the "schema-mismatch penalty" between v1 and v2 scoring of the same artifacts — this is a publishable methodological finding.
6. **Re-anonymize and re-stratify** the 700-sample manifest across Cond-X + Cond-A + Cond-B + 6 baselines; reuse Cond-X anon IDs as-is, mint new IDs for Cond-A/B.
7. **Open HANDOFF_27_v2_pivot_design.md**; supersede 19b/20/21/23/24/25 thread.
8. **Re-run demos** under Cond-A and Cond-B; preserve `demo/<scenario>/sources/` source binaries verbatim.
9. **Retire empty scaffolds** explicitly (38 paths total): `03_corpus/{realism_audits,leakage_audit,candidates,tags,domain_*}/`, `04_ground_truth/{signed_anchors,signoff_packets,external_spotcheck,hold_out_domain,overlap_sample,scaffolds,tags}/`, `06_perturbations/tags/`, `07_system_outputs/{hold_out,human_expert,tags,ablations/*,mandate_backends/*}/`, `08_grading/{incomplete_grades,failure_coding,human_vs_judge,inter_grader_sample}/` — or repopulate under v2.
