# Codex Handoff 11b-ii: Phase 6 baselines + hold-out + anonymize + freeze

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-05
**Estimated wall clock:** ~50-80 hours total (B1-B6 main matrix with 3-way API concurrency, plus hold-out and anonymize).
**Estimated API cost:** ~$455 (B1-B6 main + B1 hold-out).
**Blocked on:** HANDOFF_11b-i PROCEED. PI explicit go-ahead after reviewing 11b-i per-domain demo-finding numbers.

---

## Why this is its own handoff

HANDOFF_11b was split per PI direction. This is half-two: the API-bound baselines + hold-out matrix + anonymization + `outputs_freeze_v1` tag. 11b-i delivered MANDATE-primary main (1200 records, $0). 11b-ii closes Phase 6 to the deposit-ready state (Option B scope: perturbations deferred to HANDOFF_11c).

**Definition of done.** 7800 RunRecords added on top of 11b-i's 1200:

```
07_system_outputs/baseline_1/                  1200 records  (B1 main)
07_system_outputs/baseline_2/                  1200 records  (B2 main)
07_system_outputs/baseline_3/                  1200 records  (B3 main)
07_system_outputs/baseline_4/                  1200 records  (B4 main)
07_system_outputs/baseline_5/                  1200 records  (B5 main)
07_system_outputs/baseline_6/                  1200 records  (B6 main)
07_system_outputs/mandate_primary/holdout/      300 records  (MP holdout, Ollama)
07_system_outputs/baseline_1/holdout/           300 records  (B1 holdout, API)
```

Plus an anonymized copy of the full 9000-record output tree at `08_grading/anonymized_outputs/`. Plus the `outputs_freeze_v1` tag. Plus one handoff report.

## Preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# 1. HANDOFF_11b-i complete: 1200 MANDATE-primary main records, at least 1190 ok
files=$(ls 07_system_outputs/mandate_primary/*.json 2>/dev/null | wc -l)
[ "$files" -eq 1200 ] || { echo "11b-i incomplete: $files/1200 records"; exit 1; }
ok=$(python3 -c "
import json, glob
files = glob.glob('07_system_outputs/mandate_primary/*.json')
print(sum(1 for f in files if json.load(open(f)).get('ok')))
")
[ "$ok" -ge 1190 ] || { echo "11b-i ok rate too low: $ok/1200"; exit 1; }
echo "11b-i present: 1200 records, $ok ok"

# 2. Freeze tetrad still in place
for T in corpus_freeze_v1 baseline_freeze_v1 gt_freeze_v1 perturbation_freeze_v1; do
  git tag --list | grep -E "^${T}$" >/dev/null || { echo "$T missing"; exit 1; }
done
echo "freeze tetrad present"

# 3. Both API keys
python3 -c "
import os
from pathlib import Path
for line in Path('.env').read_text().splitlines():
    if '=' in line:
        k, v = line.split('=', 1); os.environ[k] = v
assert os.environ.get('ANTHROPIC_API_KEY','').startswith('sk-ant')
assert os.environ.get('OPENAI_API_KEY','').startswith('sk-')
print('both API keys set')
"

# 4. Main + hold-out task files
[ "$(wc -l < 04_ground_truth/main_tasks.jsonl)" -eq 120 ] || exit 1
[ "$(wc -l < 04_ground_truth/holdout_tasks.jsonl)" -eq 30 ] || exit 1
echo "task files present"

# 5. AEGIS-eval still at v1
grep "mandate-eval-primary-2026q2-v1" AEGIS-eval/_AEGIS_EVAL_README.txt >/dev/null \
  || { echo "AEGIS-eval contaminated"; exit 1; }
test -f AEGIS-eval/src/mandate/roles/binding.py || exit 1
echo "AEGIS-eval still at v1"

# 6. outputs_freeze_v1 does not already exist
git tag --list | grep -E "^outputs_freeze_v1$" \
  && { echo "outputs_freeze_v1 already exists"; exit 1; }
echo "outputs_freeze_v1 absent (will cut at end of this handoff)"
```

**Success criteria.** All six preconditions print confirmation.

## Decision boundary

You may decide:
- Run B1-B6 main loop with up to 3-way API concurrency to compress wall clock.
- Interleave runs across Anthropic and OpenAI baselines if either provider rate-limits.
- One retry on transient API errors per task per system.
- Whether to commit incrementally per system (recommended: yes).

You must escalate:
- An entire baseline producing `ok=False` on more than 12 of 1200 main runs.
- Persistent API rate-limit not clearing on exponential backoff up to 60s.
- Total API cost above $600 (signals runaway tokens).

You may NOT treat as a halt (Phase 6 data):
- `schema_valid=False` on any RunRecord (Phase 6 O4 data).
- `any_llm_fallback=True` on MANDATE-primary hold-out runs.
- B3 producing structurally-flat JSON (B3's characterized behavior).

You may not:
- Modify the v1 AEGIS-eval tree.
- Modify `04_ground_truth/`.
- Re-run any 11b-i record (those are the locked MANDATE-primary main data).

---

## Task 1: Baselines B1-B6 on the 120 main tasks × 10 runs each

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

for B in baseline_1 baseline_2 baseline_3 baseline_4 baseline_5 baseline_6; do
  python3 -m apparatus.run run-system \
    --system $B \
    --tasks 04_ground_truth/main_tasks.jsonl \
    --runs 10 \
    --output 07_system_outputs/$B \
    --seed-base 20260605
done
```

**Wall clock estimate.** ~50-80 hours total with 3-way concurrency across the six API-backed baselines (B3 is the slowest at ~120s/call multi-turn; B4-B6 at ~120s/call multi-agent; B1+B2 at ~30s/call single-prompt).

**Cost estimate.**
- B1: ~$35
- B2: ~$24
- B3: ~$172
- B4-B6: ~$216 ($72 each)
- **Total Task 1: ~$447**

**Success criteria.** 7200 RunRecords across the six baseline directories. `ok=True` on at least 7128 (1% floor).

## Task 2: Hold-out runs (MANDATE-primary + B1 on 30 hold-out × 10 runs)

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

# MANDATE-primary on hold-out (Ollama)
python3 -m apparatus.run run-system \
  --system mandate_primary \
  --aegis ./AEGIS-eval \
  --ollama-mode \
  --code-ref mandate-eval-primary-2026q2-v1 \
  --tasks 04_ground_truth/holdout_tasks.jsonl \
  --runs 10 \
  --output 07_system_outputs/mandate_primary/holdout \
  --seed-base 20260605

# B1 (strongest baseline) on hold-out (API)
python3 -m apparatus.run run-system \
  --system baseline_1 \
  --tasks 04_ground_truth/holdout_tasks.jsonl \
  --runs 10 \
  --output 07_system_outputs/baseline_1/holdout \
  --seed-base 20260605
```

**Wall clock estimate.** MANDATE-primary: 300 × 370s = ~31 hours Ollama. B1: 300 × 30s = ~2.5 hours API.

**Cost estimate.** $0 + ~$8.70 = ~$8.70.

**Success criteria.** 600 RunRecords total (300 + 300).

## Task 3: Anonymize for Phase 8 grading

```zsh
python3 -m apparatus.run anonymize \
  --in 07_system_outputs \
  --out 08_grading/anonymized_outputs \
  --mapping-path 07_system_outputs/anonymization_mapping.json \
  --seed 20260605
```

**Success criteria.** `08_grading/anonymized_outputs/` carries all 9000 RunRecords (1200 MP main + 7200 baseline main + 300 MP holdout + 300 B1 holdout) with system identities blinded. `anonymization_mapping.json` lists every system→token mapping (file is `.gitignore`d so it never lands in the repo).

## Task 4: Cut outputs_freeze_v1

```zsh
git add 07_system_outputs/ 08_grading/anonymized_outputs/

git tag --list | grep -E "^outputs_freeze_v1$" \
  && { echo "outputs_freeze_v1 already exists"; exit 1; }

git commit -m "Phase 6 main matrix + hold-out outputs complete

HANDOFF_11b-i + 11b-ii. 9000 RunRecords across 7 systems on the 120
main tasks at 10 runs each plus MANDATE-primary + B1 on 30 hold-out
tasks at 10 runs each. Anonymized copies at 08_grading/anonymized_outputs/
for Phase 8 grading.

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

`handoffs/HANDOFF_11b_ii_report_<YYYY-MM-DD>.md` with:

- Per-baseline counts, ok rate, schema_valid rate, total wall clock, total API cost
- Hold-out leg: MANDATE-primary + B1 record counts, schema_valid rates
- Anonymization integrity check (mapping size, anonymized file count, sample identity blinding)
- `outputs_freeze_v1` tag hash
- Final 9000-record summary table (per-system row across the main + hold-out matrix)
- PROCEED verdict

Commit message: `Handoff 11b-ii: Phase 6 baselines + hold-out + anonymize + outputs_freeze_v1`.

## What 11b-ii completes

After 11b-ii PROCEED:
- The four-tag freeze trifecta becomes a quintet: corpus + baseline + gt + perturbation + outputs.
- Phase 6 main matrix data collection is closed.
- Phase 8 (three-judge grading on the anonymized outputs) becomes the next big handoff (HANDOFF_13).
- HANDOFF_11c (perturbations, ~$1200) becomes a separate scope question informed by 11b results.

Phase 6 perturbation runs and ablation runs remain explicitly deferred per the scope decision and the upstream-MANDATE-team dependency, respectively.
