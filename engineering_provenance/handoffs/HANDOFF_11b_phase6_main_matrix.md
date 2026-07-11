# Codex Handoff 11b: Phase 6 main matrix + hold-out (Option B)

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-05
**Estimated wall clock:** **multi-day**. Roughly 154 hours of MANDATE-primary Ollama serial compute (1500 Ollama-mode runs at ~370s each from HANDOFF_11a per-task observation), plus parallel API calls for baselines (10-20 hours total).
**Estimated API cost:** **$370 to $450** total. Most of the spend is B3 (ReAct Claude, multi-turn) and B4-B6 (multi-agent Claude).
**Blocked on:** HANDOFF_11a PROCEED (apparatus verified end-to-end at smoke-test scale).

---

## Why this exists

HANDOFF_11a's pilot smoke proved 42/42 records on the actual ground truth, all `ok=True`, $1.50 in, the apparatus is sound. The four substantive demo findings reproduced cleanly at smoke-test scale:

- COA count distribution: 1 COA per task, 6/6 runs (Decomposition single-COA prior reaffirmed)
- Interpreter modes: 4/6 deterministic-prefix, 2/6 clean distillation (content-tripwire confirmed)
- Validator gap-flagged: 1/6 (instability confirmed)
- Binding refusal fallbacks: 0/6 (probabilistic, none on this slice)

11b commits to the formal Phase 6 main + hold-out matrix that the protocol pre-registered, restricted to what's actually runnable today (the unavailable ablation variants are deferred to upstream MANDATE work per HANDOFF_05, the human-expert upper bound is dropped per the SME-skip deviation, perturbations are deferred to HANDOFF_11c).

Phase 6 reads ground truth from the four-tag freeze trifecta:

```
04_ground_truth/main_tasks.jsonl                          120 tasks
04_ground_truth/main_scaffolds/anchor_scaffolds.jsonl     120 scaffolds = ground truth (SME-skip per DEVIATIONS.md)
04_ground_truth/holdout_tasks.jsonl                        30 tasks
04_ground_truth/holdout_scaffolds/anchor_scaffolds.jsonl   30 scaffolds = ground truth
```

The formal study runs against MANDATE-primary v1 (frozen `mandate-eval-primary-2026q2-v1`). The v2 candidate Binding-refusal patch on `feature/binding-refusal-as-gap-sideload` is NOT installed for this run. Binding refusals on financial-domain tasks will surface as `any_llm_fallback=True` and the model's `{"error": ...}` payloads will be discarded by the v1 parser — that's measured baseline behavior per the deposit.

**Definition of done.** 9000 RunRecords distributed as:

```
07_system_outputs/mandate_primary/             1200 records  (120 main tasks × 10 runs)
07_system_outputs/baseline_1/                  1200 records
07_system_outputs/baseline_2/                  1200 records
07_system_outputs/baseline_3/                  1200 records
07_system_outputs/baseline_4/                  1200 records
07_system_outputs/baseline_5/                  1200 records
07_system_outputs/baseline_6/                  1200 records
07_system_outputs/mandate_primary/holdout/      300 records  (30 hold-out × 10 runs)
07_system_outputs/baseline_1/holdout/           300 records  (B1 as strongest baseline, per HANDOFF_04 calibration)
```

Plus an anonymized copy of the entire output tree at `08_grading/anonymized_outputs/` with mapping at `07_system_outputs/anonymization_mapping.json` (gitignored). Plus the `outputs_freeze_v1` tag. Plus one handoff report.

## Why B1 is the hold-out strongest baseline

From HANDOFF_04 and HANDOFF_04c calibration on the six calibration tasks:

```
B1 single-prompt Claude:        6/6 schema-valid, ~$0.029/call, single API call
B2 single-prompt GPT-4o:        5/6 schema-valid, ~$0.020/call, single API call
B3 ReAct Claude:                0/6 schema-valid, ~$0.143/call (multi-turn)
B4 AutoGen PlannerReviewer:     6/6 schema-valid, ~$0.060/call (multi-agent)
B5 CrewAI SequentialCrew:       6/6 schema-valid, ~$0.060/call
B6 LangGraph GraphRevision:     6/6 schema-valid, ~$0.060/call
```

B1 is the parsimonious "strongest single-call" baseline: highest schema validity at lowest cost. The demo-era B1-vs-MANDATE comparison was on B1 (HANDOFF_27, $0.033/call, denser anchor than MANDATE-primary by 9 minimum entries vs 1). The hold-out leg is `mandate_primary + B1`.

## Preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# 1. Freeze tetrad complete
for T in corpus_freeze_v1 baseline_freeze_v1 gt_freeze_v1 perturbation_freeze_v1; do
  git tag --list | grep -E "^${T}$" >/dev/null || { echo "$T missing"; exit 1; }
done
echo "freeze tetrad present"

# 2. HANDOFF_11a smoke records present (sanity that the apparatus runs)
for S in mandate_primary baseline_1 baseline_2 baseline_3 baseline_4 baseline_5 baseline_6; do
  n=$(ls 07_system_outputs/${S}_pilot/*.json 2>/dev/null | wc -l)
  [ "$n" -eq 6 ] || { echo "${S}_pilot has $n records, expected 6"; exit 1; }
done
echo "11a smoke records present"

# 3. Main + hold-out task files materialized
[ "$(wc -l < 04_ground_truth/main_tasks.jsonl)" -eq 120 ] || { echo "main_tasks wrong size"; exit 1; }
[ "$(wc -l < 04_ground_truth/holdout_tasks.jsonl)" -eq 30 ] || { echo "holdout_tasks wrong size"; exit 1; }
echo "task files present"

# 4. AEGIS-eval restored to v1 (HANDOFF_22 PROCEED)
grep "mandate-eval-primary-2026q2-v1" AEGIS-eval/_AEGIS_EVAL_README.txt >/dev/null \
  || { echo "AEGIS-eval not at v1"; exit 1; }
test -f AEGIS-eval/src/mandate/roles/binding.py || { echo "binding.py missing"; exit 1; }
# v1 baseline check (NO v2 patch markers)
grep -q "llm_refused_with_error" AEGIS-eval/src/mandate/roles/binding.py \
  && { echo "binding.py carries v2 patch markers"; exit 1; }
echo "AEGIS-eval at v1 baseline (no v2 contamination)"

# 5. llm_rag_index on production MITRE ATT&CK
python3 -c "
import json
cfg = json.load(open('AEGIS-eval/configs/llm_defaults.json'))
idx = cfg['llm_rag_index']
assert 'demo/' not in idx, 'demo RAG index swapped in'
assert 'enterprise-attack' in idx, 'production index not set'
print(f'llm_rag_index: {idx}')
"

# 6. Ollama running with the six mandate-* role models
curl -sS http://localhost:11434/api/tags | python3 -c "
import sys, json
d = json.load(sys.stdin)
names = sorted(m['name'] for m in d.get('models', []))
need = ['mandate-intake','mandate-interpreter','mandate-decomp','mandate-procedure','mandate-binding','mandate-validation']
missing = [n for n in need if not any(x.startswith(n) for x in names)]
print('mandate-* missing:', missing if missing else 'none')
assert not missing
"

# 7. Both API keys with sufficient balance (rough check)
python3 -c "
import os
from pathlib import Path
for line in Path('.env').read_text().splitlines():
    if '=' in line:
        k, v = line.split('=', 1); os.environ[k] = v
assert os.environ.get('ANTHROPIC_API_KEY','').startswith('sk-ant')
assert os.environ.get('OPENAI_API_KEY','').startswith('sk-')
print('both API keys set; balance check is the PI\\'s responsibility before firing this handoff')
"
```

**Success criteria.** All seven preconditions print confirmation lines.

## Decision boundary

You may decide:
- Whether to run the seven systems serially or with limited parallelism. Recommended: MANDATE-primary serial (Ollama queue depth), B1-B6 with up to 3 concurrent API streams.
- Whether to interleave system runs to balance Anthropic vs OpenAI quota pressure.
- One retry on a transient API or Ollama error per task per system.
- Whether to commit incrementally per Task (recommended: commit after each system completes, so a mid-run interruption preserves verified state).

You must escalate:
- An entire system producing `ok=False` on more than 10 out of 1200 main runs (1% threshold).
- A persistent API rate-limit that does not clear after exponential backoff up to 60 seconds.
- AEGIS-eval `llm_rag_index` modified during the run (swap-then-restore demo pattern; should never happen here).
- Total API cost above $600 (signals runaway tokens or misconfigured model).
- Wall clock above 200 hours total for MANDATE-primary (Ollama queue saturation).

You may NOT treat as a halt (Phase 6 data):
- `schema_valid=False` on any RunRecord. Phase 6 O4 measures this.
- `any_llm_fallback=True` on MANDATE-primary runs. Phase 6 measures Binding-refusal rate at scale.
- B3 producing structurally-flat JSON. B3's characterized behavior per HANDOFF_04c.
- Per-role timing variation. Wall clock per role is variable; record it as data.

You may not:
- Modify the v1 AEGIS-eval tree.
- Apply the v2 candidate Binding-refusal patch. Phase 6 measures v1.
- Modify `04_ground_truth/` artifacts.
- Modify the `--seed-base 20260605` value mid-run; the seed is the per-run determinism guarantee.

---

## Task 1: MANDATE-primary on the 120 main tasks × 10 runs (Ollama mode)

**Wall clock estimate.** 1200 runs × ~370s/run (from HANDOFF_11a observation: 2220s for 6 tasks ÷ 6 = 370s) = ~123 hours serial.

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

python3 -m apparatus.run run-system \
  --system mandate_primary \
  --aegis ./AEGIS-eval \
  --ollama-mode \
  --code-ref mandate-eval-primary-2026q2-v1 \
  --tasks 04_ground_truth/main_tasks.jsonl \
  --runs 10 \
  --output 07_system_outputs/mandate_primary \
  --seed-base 20260605
```

**Success criteria.** 1200 RunRecords at `07_system_outputs/mandate_primary/`. `ok=True` on at least 1190 (1% schema-validity floor). Per-role `llm_used` and `llm_fallback` populated on every record.

**Resume convention.** The harness ledger is append-only and re-runs overwrite same-id RunRecord files harmlessly per the apparatus contract. If interrupted, re-run the same command from a fresh shell.

**Cost: $0** (local Ollama).

## Task 2: Baselines B1-B6 on the 120 main tasks × 10 runs each

**Wall clock estimate.** Run in parallel where possible. Per-baseline:
- B1 (single-prompt Claude): ~30s/call × 1200 = 10 hours (or much less with parallelism)
- B2 (single-prompt GPT-4o): ~30s/call × 1200 = 10 hours
- B3 (ReAct Claude): ~120s/call × 1200 = 40 hours
- B4-B6 (multi-agent): ~120s/call × 1200 × 3 = 120 hours

With 3-way concurrency across the API-backed baselines, real wall clock is ~50-80 hours.

```zsh
for B in baseline_1 baseline_2 baseline_3 baseline_4 baseline_5 baseline_6; do
  python3 -m apparatus.run run-system \
    --system $B \
    --tasks 04_ground_truth/main_tasks.jsonl \
    --runs 10 \
    --output 07_system_outputs/$B \
    --seed-base 20260605
done
```

**Success criteria.** 7200 RunRecords across the six baseline directories. `ok=True` on at least 7128 (1% floor).

**Cost estimate.**
- B1: 1200 × $0.029 = $35
- B2: 1200 × $0.020 = $24
- B3: 1200 × $0.143 = $172
- B4-B6: 3 × 1200 × $0.060 = $216
- **Total: ~$447**

## Task 3: Hold-out runs (MANDATE-primary + B1 on 30 hold-out tasks × 10 runs)

**Wall clock estimate.** MANDATE-primary: 300 × 370s = ~31 hours. B1: 300 × 30s = ~2.5 hours.

```zsh
# MANDATE-primary on hold-out
python3 -m apparatus.run run-system \
  --system mandate_primary \
  --aegis ./AEGIS-eval \
  --ollama-mode \
  --code-ref mandate-eval-primary-2026q2-v1 \
  --tasks 04_ground_truth/holdout_tasks.jsonl \
  --runs 10 \
  --output 07_system_outputs/mandate_primary/holdout \
  --seed-base 20260605

# B1 (strongest baseline) on hold-out
python3 -m apparatus.run run-system \
  --system baseline_1 \
  --tasks 04_ground_truth/holdout_tasks.jsonl \
  --runs 10 \
  --output 07_system_outputs/baseline_1/holdout \
  --seed-base 20260605
```

**Success criteria.** 600 RunRecords total (300 + 300).

**Cost estimate.** $0 + 300 × $0.029 = $8.70.

## Task 4: Anonymize for Phase 8 grading

```zsh
python3 -m apparatus.run anonymize \
  --in 07_system_outputs \
  --out 08_grading/anonymized_outputs \
  --mapping-path 07_system_outputs/anonymization_mapping.json \
  --seed 20260605
```

**Success criteria.** `08_grading/anonymized_outputs/` carries all 9000 RunRecords with system identities blinded. `anonymization_mapping.json` lists every system→token mapping (file is `.gitignore`d so it never lands in the repo).

## Task 5: Cut the outputs freeze tag

```zsh
git add 07_system_outputs/ 08_grading/anonymized_outputs/

git tag --list | grep -E "^outputs_freeze_v1$" && { echo "outputs_freeze_v1 already exists"; exit 1; }

git commit -m "Phase 6 main matrix + hold-out outputs complete

HANDOFF_11b. 9000 RunRecords across 7 systems on the 120 main tasks at
10 runs each plus MANDATE-primary + B1 on 30 hold-out tasks at 10
runs each. Anonymized copies at 08_grading/anonymized_outputs/ for
Phase 8 grading.

Perturbation suite (HANDOFF_11c) deferred per Option B scope decision.
Ablation variants (HANDOFF_05 upstream MANDATE work) deferred.
Human-expert upper bound dropped per SME-skip deviation
(00_preregistration/DEVIATIONS.md 2026-06-04)."

git tag -a outputs_freeze_v1 -m "Phase 6 main matrix + hold-out outputs frozen

9000 RunRecords. MANDATE-primary v1 (mandate-eval-primary-2026q2-v1,
commit 4f8af83) against pilot/main/holdout scaffold ground truth.
B1-B6 baselines run against the same task files. v2 Binding-refusal
patch NOT installed (separate evaluation per HANDOFF_17d).

Scope: Option B (main matrix + hold-out, defer perturbations).
HANDOFF_11c will run perturbations if PI decides the ~$1200 spend is
warranted by 11b results."
```

**Success criteria.** Tag `outputs_freeze_v1` present.

## Report

`handoffs/HANDOFF_11b_report_<YYYY-MM-DD>.md` with:

- Per-system run count, ok rate, schema_valid rate, total wall clock, total API cost
- MANDATE-primary demo-finding observations at scale:
  - COA count distribution across 1200 main runs
  - Interpreter mode distribution (clean vs deterministic-prefix)
  - Validator gap-flagged rate
  - Binding refusal fallback rate
  - Any_llm_fallback rate by role
- Per-domain breakouts (the four pre-registered domains × four categories)
- Anonymization integrity check (mapping size, anonymized file count, sample identity blinding)
- `outputs_freeze_v1` tag hash
- PROCEED verdict

Commit message: `Handoff 11b: Phase 6 main matrix + hold-out (9000 records, outputs_freeze_v1)`.

## What 11b tells us before 11c

- If MANDATE-primary's per-role `llm_fallback` rates are bounded (Binding refusal stays in the 10-25% range per the upstream-team note's expectation), the v2 patch's potential value is documented but not urgent.
- If B3 schema validity stays at 0% across 1200 main runs, the ReAct framework's measurement is conclusive at the deposit level.
- If the four demo findings hold at scale (Decomposition single-COA prior, Interpreter content-tripwire, Validator instability, Binding probabilistic refusal), the upstream-team note becomes the formal study's principal substantive finding.
- HANDOFF_11c (perturbation suite, ~$1200) becomes a scope question informed by 11b's measured-vs-expected gap. If 11b matches expectation, 11c's O5 (adversarial resistance) result is its own data; if 11b surprises, 11c may be premature.
