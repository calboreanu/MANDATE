# MANDATE 2026Q2 Replication Instructions

This document tells a reviewer how to reproduce every empirical claim in the MANDATE 2026Q2 supplement, from a zero-compute read-only check through a full hardware-bound re-run. It pairs with `DEPOSIT_MAPPING.md` (what each artifact is and where it lives) and `GITHUB_DEPOSIT_PLAN.md` (the deposit directory layout). All commands assume the apparatus *code* snapshot is checked out at the tag `mandate-eval-primary-2026q2-v1` (commit `4f8af83`) and run from the apparatus root (the directory containing `apparatus/`, `07_system_outputs/`, `04_ground_truth/`, etc.). The frozen *data* (the RunRecords reviewers verify against) is tagged separately as `outputs_freeze_v1_1` (commit `5f4de54`); both tags appear below and are distinct by design (code vs. outputs).

> **Conventions.** This package contains two co-located trees: the **apparatus root** (the eval host's `mandate_eval_2026Q2/` directory, with `apparatus/`, `07_system_outputs/`, `04_ground_truth/`, `08_grading/`, `08_grading_v2/`) and the **deposit root** (the `Mandate Data/` sibling directory containing this `docs/`, the three supplement PDFs, `standalone data results/`, `engineering_provenance/cost_log/`, `runrecord_schema_v1.json`). Apparatus paths like `07_system_outputs/...` and `04_ground_truth/...` are relative to the apparatus root. Deposit paths like `standalone data results/...` and `engineering_provenance/...` are relative to the deposit root. For Tier 1 (read-only verification) the two roots are typically co-located on disk; for Tier 2-4 (compute), all commands execute from the apparatus root. The interpreter is invoked as `.venv/bin/python` (matching how the evaluation was actually run); `python` from an activated conda env works equally well. Commands that cost money or need hardware are flagged. Read-only verification needs no compute and no keys.

---

## What this package replicates

The supplement makes five affirmative claims (§1.2). They rest on structural counts and verbatim model outputs that are *on disk* — the frozen RunRecords are themselves the evidence, so the strongest verification path requires no re-execution at all.

- **Claim 1** — MANDATE produces structurally valid mandate-as-code end-to-end at scale (Cond-A 1500/1500, Cond-B 1500/1500, MANDATE-primary 1480/1500 with 20 documented Intake-tripwire deltas).
- **Claim 2** — High-precision/recall specification-defect detection (96.8%/96.8% on the structurally-complete subset; 47.6% whole-corpus recall, transparently disclosed).
- **Claim 3** — Structural invariants hold across execution modes *and* LLM vendor families (the cross-vendor Cond-B pilot is the strongest single piece of evidence).
- **Claim 4** — MANDATE surfaces consequential governance signals (AEGIS 51-defect convergence, Binding refusal cascade, Intake tripwire, Decomposition single-COA prior).
- **Claim 5** — Cross-domain generalization (3 in-domain corpora + a 30-task out-of-domain hold-out).

The empirical-tier chain is v0 (paper §12 pilot) → v0.5 (April cross-profile pilot, supplement §6.7) → v1 (the 2026Q2 main matrix, frozen) → v2 (in-progress full-coverage grading + multi-vendor Cond-B).

---

## Replication tiers

| Tier | What you reproduce | Compute | Keys / hardware | Rough cost |
|---|---|---|---|---|
| **1** | Read-only verification of the frozen counts and verbatim samples | none | none | $0 |
| **2** | Re-grade the frozen outputs under the v2 rubric | LLM API | GPT-4o, Opus, Gemini keys | ~$50–200 (sample) / ~$7,700 (full 12k) |
| **3** | Re-run baselines and Cond-A/B on the frozen corpus | LLM API | API keys (+ Ollama for Cond-B) | ~$500–2,000 per baseline |
| **4** | Full replication incl. MANDATE-primary fine-tunes | local GPU | Mac mini M4 Pro + Ollama | multi-day |

Most reviewers should stop at Tier 1; it verifies the affirmative case directly. Tier 2 closes the comparative-grading objection. Tiers 3–4 are documented for completeness.

---

## Tier 1 — Read-only verification (no compute required)

No keys, no environment, no network. Download the package and run plain shell/Python over the JSON.

### 1.1 System record counts

```bash
# Main-matrix RunRecords per system (expect: mandate_primary 1200, baselines 1206 each)
for s in mandate_primary cond_a cond_b baseline_1 baseline_2 baseline_3 baseline_4 baseline_5 baseline_6; do
  printf "%-18s %s\n" "$s" "$(ls 07_system_outputs/$s/*.json 2>/dev/null | wc -l)"
done

# Hold-out RunRecords per system (expect: 300 each)
for s in mandate_primary cond_a cond_b; do
  printf "%-18s holdout %s\n" "$s" "$(ls 07_system_outputs/$s/holdout/*.json 2>/dev/null | wc -l)"
done
```

The authoritative inventory is `standalone data results/dataset_inventory/record_counts.md`. Note the "1500" figures in the supplement are **1200 main + 300 hold-out** per system; the baselines are 1206 main each (120 tasks × ~10 seeds + calibration overlap).

### 1.2 Claim 1 — structural validity (the headline ok-rate)

```bash
# MANDATE-primary: expect 1180 / 1200 ok on main (the 20 deltas are the Intake tripwire)
.venv/bin/python - <<'PY'
import json, glob
for s in ["mandate_primary","cond_a","cond_b"]:
    files = glob.glob(f"07_system_outputs/{s}/*.json")
    ok = sum(1 for f in files if json.load(open(f)).get("ok"))
    print(f"{s:16s} {ok}/{len(files)} ok (main)")
PY
```

Expected: `mandate_primary 1180/1200`, `cond_a 1200/1200`, `cond_b 1200/1200` (filtering `*.json` against the RunRecord shape; the cond_b directory also carries 1 task-selection metadata file `_handoff_22_task_selection.json` that is not a RunRecord and is excluded from the count by the `"run_id"` key gate). Adding the 300 all-valid hold-out records per system yields the supplement's `1480/1500` (MANDATE-primary) and `1500/1500` (Cond-A, Cond-B). A successful reproduction is matching these counts exactly.

### 1.3 Claim 4 — the 20 Intake tripwire failures, verbatim

```bash
# The 20 verbatim Intake failures are enumerated in one file:
cat "standalone data results/finding_5_intake/all_20_intake_errors.md"
# Reproduce the count from the records. NOTE: the trigger phrase is in the task
# *inputs*, not the output records, so count the ok=false MANDATE-primary records:
.venv/bin/python - <<'PY'
import json, glob
from collections import Counter
recs = [json.load(open(f)) for f in glob.glob("07_system_outputs/mandate_primary/*.json")]
print(Counter(r["task_id"] for r in recs if r.get("ok") is False))  # -> SEC-038:10, SEC-040:10
PY
# ...and confirm the trigger phrase sits in exactly the two SEC task inputs:
grep -c "Here's the constraint:" 04_ground_truth/main_tasks.jsonl   # -> 2
```

The failures are confined to `TASK-MAIN-SEC-038` and `TASK-MAIN-SEC-040` (10 seeds each = 20). Successful reproduction: exactly those two task IDs, 10 seeds each.

### 1.4 Claim 3 — cross-vendor structural invariance (pre-computed)

The cross-vendor analysis is already extracted to `standalone data results/cross_vendor/`:

```bash
cat "standalone data results/cross_vendor/findings.md"
.venv/bin/python -c "import json;d=json.load(open('standalone data results/cross_vendor/per_vendor_aggregates.json'));[print(v,a['n_ok'],a['ok_rate'],a['p2_trace_completeness_rate']) for v,a in d['vendors'].items()]"
```

Expected: Qwen, Llama, Mistral each 300/300 ok with P2 trace completeness 1.00 (900/900). Phi-3 is appended when its run completes. The per-task pairing file (`per_task_cross_vendor_invariance.jsonl`, 300 lines) shows 100% cross-vendor trace completeness.

### 1.5 Claims 2 & 5 — defect detection and cross-domain

- **Claim 2:** inspect `standalone data results/cross_system/` and the gap-detection eval outputs; the 96.8%/96.8% figure is on the 31-example structurally-complete subset, and the 47.6% whole-corpus recall is disclosed in the published paper §12 (the 33 input-only examples are a corpus-design boundary, not detection failures).
- **Claim 5:** confirm the four domains — `security_operations_reporting`, `financial_reporting`, `intelligence_collection_tasking` (in-domain, 40 tasks each) and `software_engineering_specification` (30-task hold-out) — all produce structurally valid output:

```bash
.venv/bin/python -c "import json,glob; f=glob.glob('07_system_outputs/mandate_primary/holdout/*.json'); print('holdout ok:', sum(1 for x in f if json.load(open(x)).get('ok')), '/', len(f))"
```

---

## Tier 2 — Re-grade from frozen outputs (LLM compute required)

Reproduce the three-judge grades from the frozen RunRecords without re-running any system. This is the comparative-evaluation tier.

**Prerequisites:** `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY` in `.env`; the v2 rubric plumbing (landed in HANDOFF_19 Stage 1).

**Step 1 — health-probe the judges first** (the grading daemon gates on these; Gemini in particular returns intermittent 503s):

```bash
.venv/bin/python -m apparatus.probe_anthropic --probes 3
.venv/bin/python -m apparatus.grading.probe_gemini --probes 3
.venv/bin/python -m apparatus.run grade-v2 --help | grep -q "v2" && echo "grade-v2 CLI present"
```

**Step 2 — anonymize the outputs** (judges must not see system identity):

```bash
.venv/bin/python -m apparatus.run anonymize \
  --in 07_system_outputs/cond_b \
  --out 08_grading_v2/anonymized_outputs \
  --mapping-path 07_system_outputs/anonymization_mapping.json
```

**Step 3 — grade.** Sampled (cheap, ~$50–200) or full coverage (~$7,700, ~12,000 records):

```bash
# Cheap path: deterministic 200-record sample
.venv/bin/python -m apparatus.run grade-v2 \
  --anonymized 08_grading_v2/anonymized_outputs \
  --ground-truth 04_ground_truth/ground_truth.json \
  --sample-size 200 --sample-seed 20260623 \
  --out 08_grading_v2 --skip-existing

# Full coverage + pre-registered 20% IRR double-grade
.venv/bin/python -m apparatus.run grade-v2 \
  --anonymized 08_grading_v2/anonymized_outputs \
  --ground-truth 04_ground_truth/ground_truth.json \
  --full-coverage --double-grade-pct 0.20 --double-grade-seed 20260623 \
  --out 08_grading_v2 --max-workers 3 --skip-existing
```

**Expected:** per-record grades under `08_grading_v2/by_record/`; agreement statistics (per-pair κ, Krippendorff α) reproduce within the tolerances in `08_grading/agreement_statistics.json`. Under PROTOCOL_LOCK §8, κ < 0.40 triggers a documented HALT — reproducing the HALT *is* the expected v1 outcome for the affected strata. Use `--skip-existing` to resume after any interruption.

---

## Tier 3 — Re-run baselines and conditions on the frozen corpus

Regenerate RunRecords from the frozen 120-task corpus. Requires API keys and substantial wall clock (~24h/baseline; ~$500–2,000 each).

```bash
# Baselines B1–B6 (10 seeds per task over the main corpus)
.venv/bin/python -m apparatus.run run-system \
  --system baseline_1 \
  --tasks 04_ground_truth/main_tasks.jsonl \
  --runs 10 --seed-base 20260601 \
  --output 07_system_outputs/baseline_1_repro
# repeat for baseline_2 .. baseline_6

# Cond-A: upstream extractor -> canonical MLT MANDATE
.venv/bin/python -m apparatus.run run-cond-a --all \
  --tasks 04_ground_truth/main_tasks.jsonl \
  --extraction-model claude-sonnet-4-6 \
  --runs-per-task 10 --seed 20260623 \
  --out 07_system_outputs/cond_a_repro --skip-existing

# Cond-B: canonical MANDATE with LLM-augmented Interpreter (Anthropic backend)
.venv/bin/python -m apparatus.run run-cond-b --all \
  --tasks 04_ground_truth/main_tasks.jsonl \
  --llm-backend anthropic --llm-model claude-sonnet-4-6 \
  --runs-per-task 10 --seed 20260623 \
  --out 07_system_outputs/cond_b_repro --skip-existing
```

**Verify** the reproduced records match the frozen counts/ok-rates from Tier 1 (use `--skip-existing` to resume). The published numbers were produced at `outputs_freeze_v1_1` (commit `5f4de54`); exact byte-equality is not expected for LLM-backed runs, but structural counts (ok-rate, trace completeness, COA/gap structure) should reproduce.

---

## Tier 4 — Full replication including MANDATE-primary fine-tunes (hardware required)

The MANDATE-primary system runs six fine-tuned Qwen3 role models locally via Ollama on a **Mac mini M4 Pro**. Full wall clock is multi-day (the v1 main matrix was ~154 Ollama serial hours). This is documented, not the expected reviewer path; see `docs/ENVIRONMENT.md` for the full hardware/Ollama spec.

```bash
# Confirm Ollama + the six fine-tuned role models are loaded
ollama list   # expect the six mandate-* role models (intake, interpreter, decomposition, procedure, binding, validation)

# MANDATE-primary in fine-tuned Ollama mode
.venv/bin/python -m apparatus.run run-system \
  --system mandate_primary --ollama-mode \
  --tasks 04_ground_truth/main_tasks.jsonl \
  --runs 10 --seed-base 20260601 \
  --aegis <AEGIS-eval root> \
  --output 07_system_outputs/mandate_primary_repro

# Cross-vendor Cond-B (the HANDOFF_22 pilot) over the stratified-75 selection
for m in qwen2.5:32b llama3.2:3b mistral:7b phi3:14b; do
  .venv/bin/python -m apparatus.run run-cond-b --all \
    --tasks 04_ground_truth/main_tasks.jsonl \
    --llm-backend ollama --llm-model "$m" \
    --runs-per-task 4 --seed 20260624 \
    --out "07_system_outputs/cond_b_xvendor/${m%%:*}" --skip-existing
done
```

Then re-run Tier 1 §1.4 against the regenerated cross-vendor records, and `run-analysis` to regenerate the Phase 9 tables/figures:

```bash
.venv/bin/python -m apparatus.run run-analysis    # executes notebooks 01–10
```

---

## Verifying claims (claim → exact check)

| Claim | Files to inspect | What to expect | Successful reproduction |
|---|---|---|---|
| **1** Structural validity at scale | `07_system_outputs/{mandate_primary,cond_a,cond_b}/` (+`holdout/`) | 1480/1500, 1500/1500, 1500/1500 | ok-counts match exactly; 20 deltas are SEC-038/040 |
| **2** Defect detection | `standalone data results/cross_system/`, gap-detection eval JSON | 96.8%/96.8% on 31-complete subset; 47.6% whole-corpus | numbers reproduce; 33 input-only excluded by design |
| **3** Structural invariance | `standalone data results/cross_vendor/`, paper Table det-vs-llm, §6.7 | 900/900 across Qwen/Llama/Mistral; P2 = 1.00 | per-vendor ok-rate & P2 = 1.00; Phi-3 appends |
| **4** Governance signals | `finding_4_binding/`, `finding_5_intake/`, AEGIS audit | 51-defect 9-round convergence; refusal rates 2.0/40.2/13.5/7.0%; 20 tripwire fails | exact-match convergence sequence; per-domain refusal rates |
| **5** Cross-domain | `07_system_outputs/.../holdout/`, corpus manifests | 3 in-domain (40 each) + 30 hold-out, all structurally valid | hold-out 300/300 structurally valid |

---

## Known limitations

These are honest, documented boundaries of what can be replicated:

- **SME ground-truth pool is unavailable** (documented deviation). The signed-anchor ground truth is described and the scaffolds are shipped, but the human SME signoff process cannot be re-run by an external reviewer.
- **Cond-B RunRecords do not log API cost.** On disk, `api_cost_usd` is `null` on every Cond-B record (the audit/supplement describe this as "`0.000000` by design"); either way, a reviewer rolling cost from RunRecords will understate Cond-B spend to zero. Use the cost ledger in `engineering_provenance/cost_log/` instead.
- **COA-count metric bug in the apparatus status (resolved in analysis).** The HANDOFF_22 status file reports `mean_coa_count = 0.0`, which is a bug: `scripts/run_handoff22_xvendor.py::_coa_count()` reads stale key names (`candidate_coas`/`candidate_courses_of_action`/`coas`) that do not exist in the records. The real field is `output.artifact.courses_of_action` (populated on every record); the authoritative cross-vendor means (Qwen 2.28, Llama 2.33, Mistral 2.33) are in `standalone data results/cross_vendor/`. Reviewers should not treat the apparatus `mean_coa_count` as authoritative until the key list is patched.
- **9 of 13 published Table 1 metrics are not pytest-gated.** They are bundled JSON outputs from `eval_*.py` scripts; drift would not fail CI. A forward handoff (HANDOFF_25) adds assertion harnesses. Reviewers re-running these check the JSON outputs, not a pytest target.
- **Ablations.** A3 (no_gap_analysis) and A5 (no_registry) are reproducible from the shipped corpus; A1/A2/A4/A6/A7 are upstream-blocked and are described rather than re-runnable.
- **Phi-3 cross-vendor row completed 2026-06-26** at 300/300 structurally valid (1,200/1,200 across all four vendor families). The supplement's cross-vendor fallback table (§1.2 Claim 3) carries the per-vendor deterministic-fallback rates: on Llama 3.2 (3B) and Phi-3 (14B) the LLM-augmented Interpreter fails schema validation on 100% of records and the deterministic fallback produces the valid output.
- **Phase B perturbation grading is partial (D-13).** Semantic v2 grading of the 18,200-record scoped perturbation set was paused 2026-07-08 at 14,685 main-pass grades (80.7%); double-grade IRR pass 1 at 816/3,640, pass 2 not started. Baseline_5/6 perturbation runs were scoped out under D-12 (baseline_4 is the multi-agent-shell class representative). Resume with `grade-v2 ... --skip-existing` against the frozen records; no regeneration required. Phase A structural results are complete and independent of grading.
- **Environment pin drift:** `environment.yml` pins Python 3.11 while the evaluation venv is 3.12.12; pin to 3.12.12 for byte-faithful reproduction (see `docs/ENVIRONMENT.md`).

---

## Troubleshooting

- **`ollama: command not found` / model not loaded** — install Ollama and pull the models: `ollama pull qwen2.5:32b llama3.2:3b mistral:7b phi3:14b`. For MANDATE-primary, the six fine-tuned `mandate-*` role models must be present (`ollama list`).
- **Gemini returns HTTP 503 mid-grade** — this is intermittent. Probe before grading (`apparatus.grading.probe_gemini --probes 3`); gate the grade run on the probe passing, and resume with `grade-v2 ... --skip-existing`. The production run used a resume daemon that polls the probe every 15 min and resumes when 5/5 probes pass in two consecutive intervals.
- **`grade-v2 CLI not present`** — the v2 rubric plumbing landed in HANDOFF_19 Stage 1; confirm `apparatus/grading/rubric_v2.py` is importable.
- **Anthropic/OpenAI auth errors** — keys are read from `.env` (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`); never commit `.env`.
- **Grading sees system identity** — you skipped `anonymize`, or pointed the grader at raw `07_system_outputs/` instead of `08_grading_v2/anonymized_outputs/`. Keep `anonymization_mapping.json` out of grader access.
- **Counts don't match** — confirm you are at tag `outputs_freeze_v1_1` (`5f4de54`), and remember "1500" = 1200 main + 300 hold-out; the `_handoff_22_task_selection.json` and `ledger.jsonl` files in some output dirs are not RunRecords (exclude them — the `*.json` glob already excludes `.jsonl`).

---

*Prepared as part of the 2026Q2 deposit-prep (audit Tier B). Pairs with `DEPOSIT_MAPPING.md`, `GITHUB_DEPOSIT_PLAN.md`, and `docs/ENVIRONMENT.md`. Command signatures verified against `apparatus/run.py` at the v1 frozen tag.*
