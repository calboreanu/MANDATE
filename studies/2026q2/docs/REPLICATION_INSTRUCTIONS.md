# MANDATE 2026Q2 Replication Instructions

This document tells a reviewer how to verify the deposited empirical claims and
which additional components are required for regeneration. It pairs with
`docs/CLAIM_TO_DATA_MAP.md`, `docs/EXCLUSIONS.md`, and
`docs/ENVIRONMENT.md`.

> **Conventions (deposit layout).** Clone `https://github.com/calboreanu/MANDATE`, check out tag `v2.0.2`, and `cd studies/2026q2`. All commands in this document run **from that study root** (the directory containing `replication_package/`, `code/`, and `docs/`) and use the deposit's own paths. Frozen data lives under `replication_package/` (`v1_main/system_outputs/` ships the RunRecords as consolidated JSONL, one record per line; `v1_main/findings_extracted/` ships the pre-computed finding extracts). Apparatus code lives under `code/` and is invoked as `python3 -m apparatus.<entrypoint>` from inside `code/`. Compute tiers write to a scratch `work/` directory at the study root so the frozen `replication_package/` tree is never modified.
>
> *Historical note:* the evaluation itself executed on the eval host from an "apparatus root" (`mandate_eval_2026Q2/` with `07_system_outputs/`, `04_ground_truth/`, `08_grading/`, `08_grading_v2/`, interpreter `.venv/bin/python`) beside a "deposit root" (`Mandate Data/` with `standalone data results/`). Frozen evidence files and handoff documents record those paths verbatim as provenance (see the README "Provenance note on absolute paths"); they do not exist in this repository, and no command below depends on them. The provenance tags are unchanged: apparatus code tag `mandate-eval-primary-2026q2-v1` (commit `4f8af83`), frozen outputs tag `outputs_freeze_v1_1` (commit `5f4de54`).

---

## Environment

- **Python:** the evaluation executed under **Python 3.12.12** (pyenv-managed
  venv on the eval host). The historical host manifest admitted Python 3.11 or
  newer, but the venv that produced the attested results was 3.12.12 — **use
  Python 3.12.12** for byte-faithful reproduction. The historical host manifest
  is not part of this deposit; the repository-root `requirements.txt` is the
  released dependency manifest.
- **Dependencies:** install from the repo-root **`requirements.txt`** (added 2026-07-17; pins derive from the attested eval-host freeze `pre_registration/provenance_pip_freeze.txt`, with per-line verification notes):

```bash
python3 -m venv .venv && source .venv/bin/activate   # any 3.12.12 interpreter
pip install -r requirements.txt
```

- **Tier 1 needs none of this.** The read-only tier uses only the Python standard library (any recent `python3` works, no packages, no keys, no network).
- The eval host invoked the interpreter as `.venv/bin/python`; commands below say `python3` — any activated 3.12.12 environment is equivalent.
- Hardware, Ollama models, API keys, and resource budgets: `docs/ENVIRONMENT.md`.

## Acquiring mlt-stack (canonical MANDATE implementation)

The canonical MANDATE implementation under test is **`mlt-stack 1.0.0rc1`**, imported by the apparatus as `mlt.*` (`code/apparatus/systems/mandate_canonical.py`, `code/apparatus/preprocess/extract_mission_input.py`, the ablation/cross-vendor scripts, and — transitively via `apparatus.systems` — `code/apparatus/verify_mandate_primary.py`). It is **not vendored in this deposit and is not on PyPI**: it is a proprietary Swift Group component (The Swift Group, LLC holds commercial licensing rights to MANDATE-based products, as disclosed in `pre_registration/00_PLAYBOOK_v2.md`), and — like the AEGIS reference implementation, which is likewise not redistributed (`replication_package/v0_pilot/README.md`) — it is **distributed on request for replication purposes**: contact the maintainer/author (see `CITATION.cff`) requesting `mlt-stack 1.0.0rc1` for replication of this deposit.

- Byte-faithful re-execution must use **exactly 1.0.0rc1**: the stack repository has since advanced (v1.0.3 at deposit time — `code/README.md`); artifacts verify against later releases, but re-execution should not use them.
- Without mlt-stack, `import apparatus.systems` fails (`ModuleNotFoundError: No module named 'mlt'`), which gates every `run-system` / `run-cond-a` / `run-cond-b` invocation (Tiers 3–4). `code/apparatus/verify_mandate_primary.py` detects this and exits with code 3 and an acquisition message.
- The released RunRecords pin the evaluated stack identity. Exact source access
  for regeneration is available to reviewers on request; the public release
  does not claim to vendor that proprietary core.
- **Tier 1 and Tier 2 do not require mlt-stack** (verified: the `grade-v2` CLI and grading modules import without `mlt.*`).

## Offline replication status (recorded from the 2026-07-17 pre-push smoke test)

Every Tier-1 command below was executed from a clean checkout of this repository in an offline-equivalent sandbox (no API keys, no mlt-stack, stdlib Python) on 2026-07-17; all passed with exactly the expected values (per-command results are quoted inline in Tier 1).

| Tier | Runnable offline from a fresh clone? | Needs beyond this repository |
|---|---|---|
| **1** | **Yes — verified, all commands pass** | nothing (stdlib `python3`) |
| **2** | No (network + spend) | judge SDKs + `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/`GOOGLE_API_KEY`. Does **not** need mlt-stack (CLI presence verified without it) |
| **3** | No | **mlt-stack 1.0.0rc1** (all `run-*` paths import `apparatus.systems` → `mlt.mandate`) + API keys (+ Ollama for Cond-B local backends) |
| **4** | No | **mlt-stack 1.0.0rc1** + Ollama + Apple Silicon + the six `mandate-*` fine-tunes + the frozen AEGIS-eval tree (for MANDATE-primary / A1 verification) |

---

## What this package replicates

The supplement makes five affirmative claims (§1.2). They rest on structural counts and verbatim model outputs that are *on disk* — the frozen RunRecords are themselves the evidence, so the strongest verification path requires no re-execution at all.

- **Claim 1** — The original campaign produced pipeline/schema-complete mandate artifacts at scale (Cond-A 1500/1500, Cond-B 1500/1500, MANDATE-primary 1480/1500 with 20 documented Intake-tripwire deltas). V1 `ok=true` was not an executability guarantee; the V3 corrected-routing tier supplies the repaired-contract evidence.
- **Claim 2** — High-precision/recall specification-defect detection (96.8%/96.8% on the structurally-complete subset; 47.6% whole-corpus recall, transparently disclosed).
- **Claim 3** — Structural invariants hold across execution modes *and* LLM vendor families (the cross-vendor Cond-B pilot is the strongest single piece of evidence).
- **Claim 4** — MANDATE surfaces consequential governance signals (AEGIS 51-defect convergence, Binding refusal cascade, Intake tripwire, Decomposition single-COA prior).
- **Claim 5** — Cross-domain generalization (3 in-domain corpora + a 30-task out-of-domain hold-out).

This repository publishes one versioned study result. The historical `v0`,
`v0.5`, `v1`, `v2`, and `v3` strings remain only in frozen paths and tags that
preserve execution chronology and hashes. The components are the pilot,
comparative campaign, full-coverage grading and cross-vendor evidence, and the
focused successor routing-contract check.

---

## Replication tiers

| Tier | What you reproduce | Compute | Keys / hardware | Rough cost |
|---|---|---|---|---|
| **1** | Read-only verification of the frozen counts and verbatim samples | none | none | $0 |
| **2** | Re-grade the frozen outputs under the v2 rubric | LLM API | GPT-4o, Opus, Gemini keys | ~$50–200 (sample) / ~$7,700 (full 12k) |
| **3** | Re-run baselines and Cond-A/B on the frozen corpus | LLM API | API keys + mlt-stack (+ Ollama for Cond-B) | ~$500–2,000 per baseline |
| **4** | Full replication incl. MANDATE-primary fine-tunes | local GPU | Mac mini M4 Pro + Ollama + mlt-stack | multi-day |

Most reviewers should stop at Tier 1; it verifies the affirmative case directly. Tier 2 closes the comparative-grading objection. Tiers 3–4 are documented for completeness.

---

## Tier 1 — Read-only verification (no compute required)

No keys, no environment, no network. Run plain shell/Python over the JSONL from the repository root. *(Smoke-tested 2026-07-17: every command below reproduced its expected output exactly.)*

### 1.0 Successor routing contract

```bash
python3 code/scripts/verify_v3_corrected_routing.py
```

Expected: JSON with `"ok": true`, `"records": 3000`,
`"primary_denominator_N": 2999`, and
`"executable_with_blocking": 0`. The verifier uses the frozen V1 corpus and
comparison records, deterministic-gzip V3 outputs, campaign ledger, trace
artifacts, and archive hashes. It requires only the Python standard library.

### 1.1 System record counts

```bash
# Main-matrix RunRecords per system (expect: mandate_primary/cond_a/cond_b 1200, baselines 1206 each)
for s in mandate_primary cond_a cond_b baseline_1 baseline_2 baseline_3 baseline_4 baseline_5 baseline_6; do
  printf "%-18s %s\n" "$s" "$(wc -l < replication_package/v1_main/system_outputs/${s}_main.jsonl)"
done

# Hold-out RunRecords (expect: 300 each; shipped for the three MANDATE conditions + baseline_1)
for s in mandate_primary cond_a cond_b baseline_1; do
  printf "%-18s holdout %s\n" "$s" "$(wc -l < replication_package/v1_main/system_outputs/${s}_holdout.jsonl)"
done
```

*Smoke result 2026-07-17:* `mandate_primary/cond_a/cond_b = 1200`, `baseline_1..6 = 1206`; hold-outs all `300`. ✔

The authoritative inventory is `replication_package/v1_main/findings_extracted/dataset_inventory/record_counts.md`. Note the "1500" figures in the supplement are **1200 main + 300 hold-out** per system; the baselines are 1206 main each (1,200 `TASK-MAIN-*` records + 6 `TASK-CAL-*` calibration records; graded main-matrix n = 1200 per baseline).

### 1.2 Evaluated-build pipeline/schema completion (`ok` rate)

```bash
# MANDATE-primary: expect 1180 / 1200 ok on main (the 20 deltas are the Intake tripwire)
python3 - <<'PY'
import json
for s in ["mandate_primary", "cond_a", "cond_b"]:
    recs = [json.loads(l) for l in open(f"replication_package/v1_main/system_outputs/{s}_main.jsonl")]
    ok = sum(1 for r in recs if r.get("ok"))
    print(f"{s:16s} {ok}/{len(recs)} ok (main)")
PY
```

Expected: `mandate_primary 1180/1200`, `cond_a 1200/1200`, `cond_b 1200/1200`. (The consolidated JSONL files contain RunRecords only — non-record metadata files such as `_handoff_22_task_selection.json` were excluded at consolidation; see `replication_package/v1_main/README.md`.) Adding the 300 all-valid hold-out records per system yields the supplement's `1480/1500` (MANDATE-primary) and `1500/1500` (Cond-A, Cond-B). A successful reproduction is matching these counts exactly. These counts establish historical pipeline/schema completion, not executability; run §1.0 for the repaired execution-state contract.

*Smoke result 2026-07-17:* `1180/1200`, `1200/1200`, `1200/1200`. ✔

### 1.3 Claim 4 — the 20 Intake tripwire failures, verbatim

```bash
# The 20 verbatim Intake failures are enumerated in one file:
cat replication_package/v1_main/findings_extracted/finding_5_intake/all_20_intake_errors.md

# Reproduce the count from the records. NOTE: the trigger phrase is in the task
# *inputs*, not the output records, so count the ok=false MANDATE-primary records:
python3 - <<'PY'
import json
from collections import Counter
recs = [json.loads(l) for l in open("replication_package/v1_main/system_outputs/mandate_primary_main.jsonl")]
print(Counter(r["task_id"] for r in recs if r.get("ok") is False))  # -> SEC-038:10, SEC-040:10
PY

# ...and confirm the trigger phrase sits in exactly the two SEC task inputs:
grep -c "Here's the constraint:" replication_package/v1_main/corpus/main_tasks.jsonl   # -> 2
```

The failures are confined to `TASK-MAIN-SEC-038` and `TASK-MAIN-SEC-040` (10 seeds each = 20). Successful reproduction: exactly those two task IDs, 10 seeds each.

*Smoke result 2026-07-17:* `Counter({'TASK-MAIN-SEC-038': 10, 'TASK-MAIN-SEC-040': 10})`; grep count `2`. ✔

### 1.4 Claim 3 — cross-vendor structural invariance (pre-computed)

The cross-vendor analysis is extracted to `replication_package/v1_main/findings_extracted/cross_vendor/` (raw per-vendor RunRecords: `replication_package/v2_complete/cross_vendor/`):

```bash
cat replication_package/v1_main/findings_extracted/cross_vendor/findings.md
python3 -c "import json;d=json.load(open('replication_package/v1_main/findings_extracted/cross_vendor/per_vendor_aggregates.json'));[print(v,a['n_ok'],a['ok_rate'],a['p2_trace_completeness_rate']) for v,a in d['vendors'].items()]"
```

Expected: Qwen, Llama, Mistral, and Phi-3 each 300/300 ok with P2 trace completeness 1.00 (1,200/1,200 across all four vendor families; Phi-3 completed 2026-06-26). The per-task pairing file (`per_task_cross_vendor_invariance.jsonl`, 300 lines) shows 100% cross-vendor trace completeness.

*Smoke result 2026-07-17:* `llama 300 1.0 1.0`, `mistral 300 1.0 1.0`, `phi 300 1.0 1.0`, `qwen 300 1.0 1.0`; pairing file 300 lines. ✔

### 1.5 Claims 2 & 5 — defect detection and cross-domain

- **Claim 2:** inspect `replication_package/v1_main/findings_extracted/cross_system/` and the gap-detection eval outputs; the 96.8%/96.8% figure is on the 31-example structurally-complete subset, and the 47.6% whole-corpus recall is disclosed in the published paper §12 (the 33 input-only examples are a corpus-design boundary, not detection failures).
- **Claim 5:** confirm the four domains — `security_operations_reporting`, `financial_reporting`, `intelligence_collection_tasking` (in-domain, 40 tasks each) and `software_engineering_specification` (30-task hold-out) — all produce structurally valid output:

```bash
python3 -c "import json; recs=[json.loads(l) for l in open('replication_package/v1_main/system_outputs/mandate_primary_holdout.jsonl')]; print('holdout ok:', sum(1 for r in recs if r.get('ok')), '/', len(recs))"
```

*Smoke result 2026-07-17:* `holdout ok: 300 / 300`. ✔

---

## Tier 2 — Re-grade from frozen outputs (LLM compute required; no mlt-stack)

Reproduce the three-judge grades from the frozen RunRecords without re-running any system. This is the comparative-evaluation tier. **Not runnable offline** — requires `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY` in `.env` inside `code/`, plus the SDK pins from `requirements.txt`. It does **not** require mlt-stack.

**Step 0 — explode the consolidated JSONL.** The deposit ships RunRecords as consolidated JSONL; the apparatus CLI consumes directories of per-record JSON files. From the repo root:

```bash
python3 - <<'PY'
import json, os
src = "replication_package/v1_main/system_outputs/cond_b_main.jsonl"   # repeat per system as needed
dst = "work/system_outputs/cond_b"
os.makedirs(dst, exist_ok=True)
for line in open(src):
    r = json.loads(line)
    with open(os.path.join(dst, r["run_id"] + ".json"), "w") as f:
        f.write(line)
print("wrote", len(os.listdir(dst)), "records to", dst)
PY
```

**Step 1 — health-probe the judges first** (the grading daemon gates on these; Gemini in particular returns intermittent 503s). From `code/`:

```bash
cd code
python3 -m apparatus.probe_anthropic --probes 3
python3 -m apparatus.grading.probe_gemini --probes 3
python3 -m apparatus.run grade-v2 --help | grep -q "v2" && echo "grade-v2 CLI present"
```

*(The `grade-v2 CLI present` check was verified 2026-07-17 in the offline sandbox — the grading CLI loads without mlt-stack; the probes themselves need keys/network.)*

**Step 2 — anonymize the outputs** (judges must not see system identity). Still from `code/`; write to `work/`, never into `replication_package/`:

```bash
python3 -m apparatus.run anonymize \
  --in ../work/system_outputs/cond_b \
  --out ../work/grading_v2/anonymized_outputs \
  --mapping-path ../work/grading_v2/anonymization_mapping.json
```

(The frozen mapping used for the shipped grades is `replication_package/v1_main/system_outputs/anonymization_mapping.json`, with the v2 additions under `replication_package/v1_main/grading/v2_full_coverage/`; keep any mapping file out of grader access.)

**Step 3 — grade.** Sampled (cheap, ~$50–200) or full coverage (~$7,700, ~12,000 records):

```bash
# Cheap path: deterministic 200-record sample
python3 -m apparatus.run grade-v2 \
  --anonymized ../work/grading_v2/anonymized_outputs \
  --ground-truth ../replication_package/v1_main/ground_truth/ground_truth.json \
  --sample-size 200 --sample-seed 20260623 \
  --out ../work/grading_v2 --skip-existing

# Full coverage + protocol-specified 20% IRR double-grade
python3 -m apparatus.run grade-v2 \
  --anonymized ../work/grading_v2/anonymized_outputs \
  --ground-truth ../replication_package/v1_main/ground_truth/ground_truth.json \
  --full-coverage --double-grade-pct 0.20 --double-grade-seed 20260623 \
  --out ../work/grading_v2 --max-workers 3 --skip-existing
```

**Expected:** per-record grades under `work/grading_v2/by_record/`; compare against the shipped `replication_package/v1_main/grading/v2_full_coverage/ensemble_scores.jsonl` (12,000 lines) and the agreement statistics in `replication_package/v1_main/grading/v1_sampled/v1_irr_report.json`. Under PROTOCOL_LOCK §8, κ < 0.40 triggers a documented HALT — reproducing the HALT *is* the expected v1 outcome for the affected strata (see `docs/ERRATA.md` for the v1 judge-model labeling erratum before comparing per-judge outputs). Use `--skip-existing` to resume after any interruption.

---

## Tier 3 — Re-run baselines and conditions on the frozen corpus (requires mlt-stack)

**Recorded seed schedules (measured from the frozen records; seed = base + run number, `code/apparatus/run.py`):**

| Condition | Base | Runs | Recorded seeds |
|---|---|---|---|
| Cond-A / Cond-B / successor routing check | 20260623 | 1-10 | 20260624-20260633 |
| Cross-vendor Cond-B | 20260623 | 1-4 | 20260624-20260627 |
| MANDATE-primary, baselines B1-B6 | 20260605 | 1-10 | 20260606-20260615 |
| Baseline calibration (`TASK-CAL-*`, single pass) | - | - | 20260605 |

The frozen baseline main files carry 1,206 records each: 120 tasks x 10 runs plus the six ungraded calibration-task records at seed 20260605; graded denominators exclude the calibration records (1,200).

Regenerate RunRecords from the frozen 120-task corpus. Requires **mlt-stack 1.0.0rc1** (see "Acquiring mlt-stack" — every `run-*` entry point imports `apparatus.systems`, which imports `mlt.mandate`), API keys, and substantial wall clock (~24h/baseline; ~$500–2,000 each). From `code/`:

```bash
cd code
# Baselines B1–B6 (10 seeds per task over the main corpus)
python3 -m apparatus.run run-system \
  --system baseline_1 \
  --tasks ../replication_package/v1_main/corpus/main_tasks.jsonl \
  --runs 10 --seed-base 20260605 \
  --output ../work/system_outputs/baseline_1_repro
# (recorded schedule: seeds 20260606-20260615 = 20260605 + run number)
# repeat for baseline_2 .. baseline_6

# Cond-A: upstream extractor -> canonical MLT MANDATE
python3 -m apparatus.run run-cond-a --all \
  --tasks ../replication_package/v1_main/corpus/main_tasks.jsonl \
  --extraction-model claude-sonnet-4-6 \
  --runs-per-task 10 --seed 20260623 \
  --out ../work/system_outputs/cond_a_repro --skip-existing

# Cond-B: canonical MANDATE with LLM-augmented Interpreter (Anthropic backend)
python3 -m apparatus.run run-cond-b --all \
  --tasks ../replication_package/v1_main/corpus/main_tasks.jsonl \
  --llm-backend anthropic --llm-model claude-sonnet-4-6 \
  --runs-per-task 10 --seed 20260623 \
  --out ../work/system_outputs/cond_b_repro --skip-existing
```

**Verify** the reproduced records match the frozen counts/ok-rates from Tier 1 (use `--skip-existing` to resume). The published numbers were produced at `outputs_freeze_v1_1` (commit `5f4de54`); exact byte-equality is not expected for LLM-backed runs, but structural counts (ok-rate, trace completeness, COA/gap structure) should reproduce.

---

## Tier 4 — Full replication including MANDATE-primary fine-tunes (hardware + mlt-stack required)

The MANDATE-primary system runs six fine-tuned Qwen3 role models locally via Ollama on a **Mac mini M4 Pro**. Full wall clock is multi-day (the v1 main matrix was ~154 Ollama serial hours). This is documented, not the expected reviewer path; see `docs/ENVIRONMENT.md` for the full hardware/Ollama spec. MANDATE-primary additionally needs the frozen AEGIS-eval tree (tag `mandate-eval-primary-2026q2-v1`; proprietary, supplied on request like mlt-stack) passed via `--aegis`; before pinning results, gate on `code/apparatus/verify_mandate_primary.py` (Workstream A1 — exits 3 with an acquisition message if mlt-stack is absent).

```bash
# Confirm Ollama + the six fine-tuned role models are loaded
ollama list   # expect the six mandate-* role models (intake, interpreter, decomposition, procedure, binding, validation)

cd code
# MANDATE-primary in fine-tuned Ollama mode
python3 -m apparatus.run run-system \
  --system mandate_primary --ollama-mode \
  --tasks ../replication_package/v1_main/corpus/main_tasks.jsonl \
  --runs 10 --seed-base 20260605 \
  --aegis <AEGIS-eval root> \
  --output ../work/system_outputs/mandate_primary_repro

# Cross-vendor Cond-B (the HANDOFF_22 pilot) over the frozen stratified-75 selection
# (75 tasks x 4 runs = 300 records per vendor; recorded seeds 20260624-20260627)
mkdir -p ../work
python3 - <<'PY'
import json
sel = json.load(open("../replication_package/v2_complete/cross_vendor/task_selection_75.json"))
keep = set(sel["task_ids"])
with open("../replication_package/v1_main/corpus/main_tasks.jsonl") as src, \
     open("../work/xvendor_tasks_75.jsonl", "w") as dst:
    for line in src:
        if json.loads(line)["task_id"] in keep:
            dst.write(line)
PY
for m in qwen2.5:32b llama3.2:3b mistral:7b phi3:14b; do
  python3 -m apparatus.run run-cond-b --all \
    --tasks ../work/xvendor_tasks_75.jsonl \
    --llm-backend ollama --llm-model "$m" \
    --runs-per-task 4 --seed 20260623 \
    --out "../work/system_outputs/cond_b_xvendor/${m%%:*}" --skip-existing
done
```

Then re-run Tier 1 §1.4 against the regenerated cross-vendor records (compare with `replication_package/v2_complete/cross_vendor/*.jsonl`), and regenerate the Phase 9 tables/figures:

```bash
python3 -m apparatus.run run-analysis    # executes notebooks 01–10
```

*(Note: the Phase 9 notebooks belong to the upstream evaluation tree and are not part of this deposit; `run-analysis` is documented for reviewers working with the full upstream apparatus. The deposited equivalents of its outputs are the finding extracts and `analysis/bootstrap_contrasts_results.json`.)*

---

## Verifying claims (claim → exact check)

| Claim | Files to inspect | What to expect | Successful reproduction |
|---|---|---|---|
| **1** Structural validity at scale | `replication_package/v1_main/system_outputs/{mandate_primary,cond_a,cond_b}_{main,holdout}.jsonl` | 1480/1500, 1500/1500, 1500/1500 | ok-counts match exactly; 20 deltas are SEC-038/040 |
| **2** Defect detection | `replication_package/v1_main/findings_extracted/cross_system/`, gap-detection eval JSON | 96.8%/96.8% on 31-complete subset; 47.6% whole-corpus | numbers reproduce; 33 input-only excluded by design |
| **3** Structural invariance | `replication_package/v1_main/findings_extracted/cross_vendor/` (+ raw `v2_complete/cross_vendor/`), paper Table det-vs-llm, §6.7 | 1,200/1,200 across Qwen/Llama/Mistral/Phi-3; P2 = 1.00 | per-vendor ok-rate & P2 = 1.00 |
| **4** Governance signals | `replication_package/v1_main/findings_extracted/finding_4_binding/`, `finding_5_intake/`, AEGIS audit | 51-defect 9-round convergence; refusal rates 2.0/40.2/13.5/7.0%; 20 tripwire fails | exact-match convergence sequence; per-domain refusal rates |
| **5** Cross-domain | `replication_package/v1_main/system_outputs/*_holdout.jsonl`, `v1_main/corpus/` | 3 in-domain (40 each) + 30 hold-out, all structurally valid | hold-out 300/300 structurally valid |

---

## Known limitations

These are honest, documented boundaries of what can be replicated:

- **SME ground-truth pool is unavailable** (documented deviation). The signed-anchor ground truth is described and the scaffolds are shipped, but the human SME signoff process cannot be re-run by an external reviewer.
- **Cond-B RunRecords do not log API cost.** On disk, `api_cost_usd` is `null` on every Cond-B record (the audit/supplement describe this as "`0.000000` by design"); either way, a reviewer rolling cost from RunRecords will understate Cond-B spend to zero. Use the cost ledger in `engineering_provenance/cost_log/` instead.
- **COA-count metric bug in the apparatus status (resolved in analysis).** The HANDOFF_22 status file reports `mean_coa_count = 0.0`, which is a bug: `code/scripts/run_handoff22_xvendor.py::_coa_count()` reads stale key names (`candidate_coas`/`candidate_courses_of_action`/`coas`) that do not exist in the records. The real field is `output.artifact.courses_of_action` (populated on every record); the authoritative cross-vendor means (Qwen 2.28, Llama 2.33, Mistral 2.33) are in `replication_package/v1_main/findings_extracted/cross_vendor/`. Reviewers should not treat the apparatus `mean_coa_count` as authoritative until the key list is patched.
- **9 of 13 published Table 1 metrics are not pytest-gated.** They are bundled JSON outputs from `eval_*.py` scripts; drift would not fail CI. A forward handoff (HANDOFF_25) adds assertion harnesses. Reviewers re-running these check the JSON outputs, not a pytest target.
- **Ablations.** A3 (no_gap_analysis) and A5 (no_registry) are reproducible from the shipped corpus; A1/A2/A4/A6/A7 are upstream-blocked and are described rather than re-runnable (see `replication_package/v2_complete/ablation_mvp/` for the 150-task all-ablations demonstration).
- **Phi-3 cross-vendor row completed 2026-06-26** at 300/300 structurally valid (1,200/1,200 across all four vendor families). The supplement's cross-vendor fallback table (§1.2 Claim 3) carries the per-vendor deterministic-fallback rates: on Llama 3.2 (3B) and Phi-3 (14B) the LLM-augmented Interpreter fails schema validation on 100% of records and the deterministic fallback produces the valid output.
- **Phase B perturbation grading is partial (D-13).** Semantic v2 grading of the 18,200-record scoped perturbation set was paused 2026-07-08 at 14,685 main-pass grades (80.7%); double-grade IRR pass 1 at 816/3,640, pass 2 not started. Baseline_5/6 perturbation runs were scoped out under D-12 (baseline_4 is the multi-agent-shell class representative). Resume with `grade-v2 ... --skip-existing` against the frozen records; no regeneration required. Phase A structural results are complete and independent of grading (`replication_package/v2_complete/`).
- **Environment pin drift:** the historical eval-host manifest admitted Python
  3.11 or newer while the evaluation venv was 3.12.12; pin to 3.12.12 for
  byte-faithful reproduction. This deposit's released manifest is the
  repository-root `requirements.txt` (see the "Environment" section above and
  `docs/ENVIRONMENT.md`).
- **Promised-but-excluded artifacts** are enumerated with status in `docs/EXCLUSIONS.md`; frozen-artifact label discrepancies in `docs/ERRATA.md`.

---

## Troubleshooting

- **`ollama: command not found` / model not loaded** — install Ollama and pull the models: `ollama pull qwen2.5:32b llama3.2:3b mistral:7b phi3:14b`. For MANDATE-primary, the six fine-tuned `mandate-*` role models must be present (`ollama list`).
- **`ModuleNotFoundError: No module named 'mlt'`** — you invoked a Tier 3/4 `run-*` command (or `verify_mandate_primary.py`) without mlt-stack installed. See "Acquiring mlt-stack" above. Tier 1 and Tier 2 do not need it.
- **Gemini returns HTTP 503 mid-grade** — this is intermittent. Probe before grading (`python3 -m apparatus.grading.probe_gemini --probes 3`); gate the grade run on the probe passing, and resume with `grade-v2 ... --skip-existing`. The production run used a resume daemon (`code/scripts/handoff20_resume_daemon.py`) that polls the probe every 15 min and resumes when 5/5 probes pass in two consecutive intervals.
- **`grade-v2 CLI not present`** — the v2 rubric plumbing landed in HANDOFF_19 Stage 1; confirm `code/apparatus/grading/rubric_v2.py` is importable.
- **Anthropic/OpenAI auth errors** — keys are read from `.env` (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`); never commit `.env`.
- **Grading sees system identity** — you skipped `anonymize`, or pointed the grader at raw exploded system outputs instead of the anonymized directory. Keep every `anonymization_mapping*.json` out of grader access.
- **Counts don't match** — remember "1500" = 1200 main + 300 hold-out, and baselines carry 6 extra `TASK-CAL-*` calibration records (1206 main lines). The consolidated JSONL files in `replication_package/v1_main/system_outputs/` already exclude non-record metadata files; if you are instead working from the upstream evaluation tree, confirm you are at tag `outputs_freeze_v1_1` (`5f4de54`) and exclude `_handoff_22_task_selection.json` and `ledger.jsonl`.

---

Command paths were rewritten against the released deposit layout and the
read-only verification tier was smoke-tested from a clean checkout. Command
signatures were checked against `code/apparatus/run.py` at the frozen campaign
snapshot.
