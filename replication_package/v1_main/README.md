# v1_main — The 2026Q2 Main Matrix (T4)

The headline evaluation tier: frozen corpus, per-system RunRecords, and both
grading passes. All record files are consolidated JSONL (one RunRecord per
line), generated from the frozen per-record JSON files in the evaluation tree
at `outputs_freeze_v1_1` (commit `5f4de54`), in sorted filename order,
underscore-prefixed non-record files excluded.

## corpus/
- `main_tasks.jsonl` — 120 frozen main tasks (40 × {financial_reporting,
  intelligence_collection_tasking, security_operations_reporting}).
- `holdout_tasks.jsonl` — 30 out-of-domain software-engineering tasks.
Tag: `corpus_freeze_v1`.

## ground_truth/
- `ground_truth.json`, `ground_truth_perturbations.json` — planted-gap answer
  keys and perturbation ground truth. Tag: `gt_freeze_v1`. (The v1 κ statistic
  measures inter-judge agreement on this v1 answer key; see supplement §2.4.)

## perturbations/
- `perturbation_suite.jsonl` / `perturbation_suite_for_runs.jsonl` — the
  350-perturbation suite (7 types × 50). Tag: `perturbation_freeze_v1`.

## system_outputs/ (record counts, disk-verified 2026-07-08)

| File | Records | Notes |
|---|---|---|
| mandate_primary_main.jsonl | 1,200 | v1 fine-tuned Qwen3 role specialists; 1,180 ok + 20 documented Intake-tripwire failures |
| mandate_primary_holdout.jsonl | 300 | out-of-domain |
| cond_a_main.jsonl / cond_a_holdout.jsonl | 1,200 / 300 | canonical MANDATE, pre-extracted structured input (upper bound) |
| cond_b_main.jsonl / cond_b_holdout.jsonl | 1,200 / 300 | canonical MANDATE, raw text + LLM Interpreter (apples-to-apples condition) |
| baseline_1_main.jsonl / baseline_1_holdout.jsonl | 1,206 / 300 | single-prompt Claude Sonnet |
| baseline_2..6_main.jsonl | 1,206 each | GPT-4o single-prompt; ReAct; AutoGen/CrewAI/LangGraph pattern shells |
| anonymization_mapping.json | — | maps anonymized grading IDs to systems |

**Important contract clarification.** For the frozen V1 Cond-A/B records,
`ok=true` means the artifact completed the then-current pipeline/schema
checks. It does not mean the artifact was executable: the evaluated build
could emit `ok=true` alongside blocking gap signals. The repaired contract and
3,000-record corrective validation are deposited under
`../v3_corrected_routing/`; V1 files remain byte-faithful and unchanged.

Baseline `*_main.jsonl` files contain 1,200 `TASK-MAIN-*` records plus 6
`TASK-CAL-*` calibration records; the graded main-matrix n is 1,200 per
baseline (plus 300 hold-out for baseline_1). Cond-B RunRecords carry
`api_cost_usd = null` by design (see cost ledger flag #1).

## grading/

### v1_sampled/ (N=700 stratified; engaged the κ halt)
- `ensemble_scores.jsonl` — 700 graded records (100 per system × 7).
- `sample_manifest.jsonl` + `sample_manifest_meta.json` — deterministic seed
  20260618 sample.
- `double_grade_manifest.jsonl` — 10% IRR set (Deviation D-08).
- `judges_config.json` — judge ensemble configuration.
- Outcome: minimum pairwise Cohen's κ = 0.296 < 0.40 → PROTOCOL_LOCK §8 halt →
  pre-registered v2 supersession (rubric-shape artifact; see supplement §5.4
  and Finding 6).

### v2_full_coverage/ (the comparative table's source of record)
- `ensemble_scores.jsonl` — **12,000** per-record three-judge ensemble scores
  under the shape-neutral v2 rubric (Cond-X regrade + Cond-A + Cond-B +
  B1–B6), zero incompletes, completed 2026-07-01.
- `anonymization_mapping_full.json`, `anonymization_mapping_v2_additions.json`
  — required to attribute anonymized records to systems.

## findings_extracted/
Mirror of the deposit's per-finding standalone results: byte-exact verbatim
samples for the five substantive findings (decomposition prior, interpreter
mode-flip, validator instability, binding refusal ×244, intake tripwire ×20),
cross-system extracts, dataset inventory, deviation records, handoff costs.
This is the Tier-1 read-only verification surface: the JSONL files *are* the
evidence.

## schemas/
- `runrecord_schema_v1.json` (+ `.md`) — the RunRecord schema all record files
  validate against.
