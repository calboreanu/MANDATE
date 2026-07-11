# Codex Handoff 11a: Phase 6 pilot smoke test (Option C, 7 systems × 6 tasks × 1 run)

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-05
**Estimated wall clock:** 25 to 60 minutes total (Ollama serial for MANDATE-primary on 6 tasks + parallel API calls for B1-B6).
**Estimated API cost:** $5 to $10 (no Ollama API cost).
**Blocked on:** Four-tag freeze trifecta in place (`corpus_freeze_v1`, `baseline_freeze_v1`, `gt_freeze_v1`, `perturbation_freeze_v1`). All present per HANDOFF_21 PROCEED.

---

## Why this exists

This is the Phase 6 pilot smoke test (Option C from the scope conversation). HANDOFF_11 as drafted is the full Phase 6 matrix (8400 main runs + 12,250 perturbation runs + 600 hold-out runs = ~21,000 RunRecords at ~$1640 API plus hundreds of hours of Ollama). Before committing that, this handoff exercises every pre-registered system once against the 6 pilot tasks so we know the apparatus side fires cleanly end-to-end against the actual ground-truth artifacts.

If 11a PROCEEDs cleanly, the main matrix (HANDOFF_11b) is a confident commit. If 11a surfaces an apparatus-side issue (schema mismatch, broken adapter, missing model alias), we catch it for $5 instead of $1640.

The four substantive demo findings should surface here at small scale and inform whether the larger run is worth the spend:
1. MANDATE-primary's Decomposition role producing one COA per task. Expected: 6/6 pilot tasks emit n_coas=1.
2. Interpreter content-tripwire behavior: clean structured anchor distillation vs deterministic-prefix paragraph echo. Expected: variance.
3. Validation gap-acknowledgment instability: same anchor-vs-COA-count mismatch flagged on some tasks and not others.
4. Binding structured-refusal behavior on financial-domain pilot tasks (TASK-PILOT-FIN-001, TASK-PILOT-FIN-002). The v2 patch is NOT installed in Phase 6 (it lives on `feature/binding-refusal-as-gap-sideload`, not on the v1 tag this run reads). Expected: some Binding role fallbacks counted as `any_llm_fallback=True`. Those are real Phase 6 data per the upstream-team note.

**Definition of done.** 42 RunRecords on disk:

```
07_system_outputs/mandate_primary_pilot/   6 records  (Ollama-mode, six fine-tuned roles)
07_system_outputs/baseline_1_pilot/         6 records  (single-prompt Claude)
07_system_outputs/baseline_2_pilot/         6 records  (single-prompt GPT-4o)
07_system_outputs/baseline_3_pilot/         6 records  (ReAct Claude)
07_system_outputs/baseline_4_pilot/         6 records  (AutoGen PlannerReviewer)
07_system_outputs/baseline_5_pilot/         6 records  (CrewAI SequentialCrew)
07_system_outputs/baseline_6_pilot/         6 records  (LangGraph GraphRevision)
```

Every RunRecord carries `ok=True` (system-level), `schema_valid` (per-output, recorded as data, false-OK on B2/B3 per HANDOFF_04c), `wall_clock_ms`, `api_cost_usd`, and (for MANDATE-primary) per-role `llm_used`, `llm_fallback`, `any_llm_fallback`. One handoff report summarizing per-system results plus observations on each of the four demo findings.

## Preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# 1. Freeze tetrad present
for T in corpus_freeze_v1 baseline_freeze_v1 gt_freeze_v1 perturbation_freeze_v1; do
  git tag --list | grep -E "^${T}$" >/dev/null || { echo "$T missing"; exit 1; }
done
echo "freeze tetrad present"

# 2. Pilot tasks materialized
[ -f 04_ground_truth/pilot_tasks.jsonl ] && \
  [ "$(wc -l < 04_ground_truth/pilot_tasks.jsonl)" -eq 6 ] || {
  echo "pilot_tasks.jsonl missing or wrong size"; exit 1;
}
echo "pilot tasks present"

# 3. Pilot ground-truth scaffolds present
[ -f 04_ground_truth/pilot_scaffolds/anchor_scaffolds.jsonl ] && \
  [ "$(wc -l < 04_ground_truth/pilot_scaffolds/anchor_scaffolds.jsonl)" -eq 6 ] || {
  echo "pilot_scaffolds missing"; exit 1;
}
echo "pilot scaffolds present"

# 4. Frozen MANDATE source tree at v1
test -d AEGIS-eval/ && test -f AEGIS-eval/_AEGIS_EVAL_README.txt || {
  echo "AEGIS-eval/ tree missing"; exit 1;
}
grep "mandate-eval-primary-2026q2-v1" AEGIS-eval/_AEGIS_EVAL_README.txt >/dev/null || {
  echo "AEGIS-eval tree not at v1"; exit 1;
}
echo "AEGIS-eval at v1"

# 5. Ollama running with the six mandate-* models
curl -sS http://localhost:11434/api/tags | python3 -c "
import sys, json
d = json.load(sys.stdin)
names = sorted(m['name'] for m in d.get('models', []))
need = ['mandate-intake','mandate-interpreter','mandate-decomp','mandate-procedure','mandate-binding','mandate-validation']
missing = [n for n in need if not any(x.startswith(n) for x in names)]
print('mandate-* missing:', missing if missing else 'none')
assert not missing
"

# 6. Both API keys
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

# 7. AEGIS llm_rag_index points at the production MITRE ATT&CK index (not a demo index)
python3 -c "
import json
cfg = json.load(open('AEGIS-eval/configs/llm_defaults.json'))
idx = cfg['llm_rag_index']
print(f'llm_rag_index: {idx}')
assert 'demo/' not in idx, 'demo RAG index swapped in; restore the production index'
"
```

**Success criteria.** All seven checks print confirmation lines.

## Decision boundary

You may decide:
- A single retry on a transient Ollama or API rate-limit error per task per system.
- Whether to run the seven systems serially or with limited parallelism. Recommended: MANDATE-primary serial (Ollama queue depth), B1-B6 with up to 3 concurrent (independent API streams).

You must escalate (these are real failure modes, not data):
- An entire system producing `ok=False` on all 6 tasks (apparatus-level failure for that system).
- AEGIS-eval `llm_rag_index` modified during the run (the demo-era swap-then-restore pattern; here we run against the production MITRE ATT&CK index for all tasks).
- Total API cost above $25 (signals a misconfigured model or runaway tokens).
- Wall clock above 90 minutes total (signals Ollama queue saturation or a stuck system).

You may NOT treat as a halt (these ARE data):
- `schema_valid=False` on any RunRecord. The four demo findings (Decomposition single-COA, Interpreter content-tripwire, Validator instability, Binding refusal) are expected behaviors at this scale.
- `any_llm_fallback=True` on a MANDATE-primary run (e.g. Binding refusing on a financial-domain pilot task). Record it as data; the per-role timing breakout will say which role and why.
- B3 producing structurally-flat JSON. HANDOFF_04c established this as B3's measured behavior.

You may not:
- Modify the v1 AEGIS-eval tree.
- Apply the v2 candidate Binding-refusal patch. Phase 6 measures v1; the v2 patch is a separate evaluation.
- Modify `04_ground_truth/` artifacts.
- Anonymize outputs in this handoff. The pilot smoke does not feed Phase 8 grading; anonymization happens in HANDOFF_11b on the main matrix.

---

## Task 1: MANDATE-primary on the 6 pilot tasks (Ollama mode, v1)

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

python3 -m apparatus.run run-system \
  --system mandate_primary \
  --aegis ./AEGIS-eval \
  --ollama-mode \
  --code-ref mandate-eval-primary-2026q2-v1 \
  --tasks 04_ground_truth/pilot_tasks.jsonl \
  --runs 1 \
  --output 07_system_outputs/mandate_primary_pilot \
  --seed-base 20260605
```

**Wall clock estimate.** 4 to 5 minutes per task × 6 tasks = 24-30 minutes serial. (Ollama-mode MANDATE-primary observed ~200s wall clock per task in the demo runs.)

**Success criteria.** 6 RunRecords at `07_system_outputs/mandate_primary_pilot/`, every `ok=True`. Per-role `llm_used` should be `True` for all six roles on most runs; `llm_fallback` may be `True` on some runs (the Binding-refusal behavior). Record both as data.

## Task 2: Baselines B1-B6 on the 6 pilot tasks

```zsh
for B in baseline_1 baseline_2 baseline_3 baseline_4 baseline_5 baseline_6; do
  python3 -m apparatus.run run-system \
    --system $B \
    --tasks 04_ground_truth/pilot_tasks.jsonl \
    --runs 1 \
    --output 07_system_outputs/${B}_pilot \
    --seed-base 20260605
done
```

**Wall clock estimate.** ~30 seconds per task per single-agent baseline (B1, B2), ~2 minutes per task per ReAct or multi-agent (B3, B4, B5, B6). Total: ~10-20 minutes.

**Success criteria.** 36 RunRecords across the six baseline directories, every `ok=True`. `schema_valid` varies per HANDOFF_04c calibration data.

## Task 3: Per-system summary

```zsh
python3 - <<'PY'
import json, glob, collections
print("="*78)
print("Phase 6 pilot smoke results")
print("="*78)
for sys_id in ["mandate_primary", "baseline_1", "baseline_2", "baseline_3",
               "baseline_4", "baseline_5", "baseline_6"]:
    files = sorted(glob.glob(f"07_system_outputs/{sys_id}_pilot/*.json"))
    if not files:
        print(f"  {sys_id}: NO records")
        continue
    rows = [json.load(open(p)) for p in files]
    ok = sum(1 for r in rows if r.get("ok"))
    sv = sum(1 for r in rows if (r.get("output") or {}).get("schema_valid") or
                                  (r.get("output") or {}).get("artifact"))
    fb = sum(1 for r in rows if r.get("any_llm_fallback"))
    cost = sum((r.get("api_cost_usd") or 0) for r in rows)
    wc = sum((r.get("wall_clock_ms") or 0) for r in rows)
    line = f"  {sys_id:18s}  {len(rows):2d} records  ok={ok}  schema_valid_or_artifact={sv}"
    if sys_id == "mandate_primary":
        line += f"  any_llm_fallback_runs={fb}"
    line += f"  cost=${cost:.4f}  wall_clock={wc/1000:.0f}s"
    print(line)
PY
```

## Task 4: MANDATE-primary demo-finding observations

```zsh
python3 - <<'PY'
import json, glob, collections
print("="*78)
print("MANDATE-primary demo-finding observations on the 6 pilot tasks")
print("="*78)
files = sorted(glob.glob("07_system_outputs/mandate_primary_pilot/*.json"))
n_coas_counts = collections.Counter()
interpreter_modes = collections.Counter()  # clean | deterministic_prefix
validator_gap_flag = 0
binding_refusal_count = 0
for p in files:
    r = json.load(open(p))
    art = (r.get("output") or {}).get("artifact") or {}
    coas = art.get("courses_of_action") or []
    n_coas_counts[len(coas)] += 1

    # Interpreter mode: detect deterministic-prefix shape
    anchor = art.get("anchor") or {}
    minimum = anchor.get("minimum") or {}
    min_desc = (minimum.get("description") if isinstance(minimum, dict)
                else str(minimum))
    if min_desc and ("Minimally satisfy" in min_desc or "Fully achieve" in min_desc):
        interpreter_modes["deterministic_prefix"] += 1
    else:
        interpreter_modes["clean_distillation"] += 1

    # Validator gap-flag detection
    rec = art.get("recommendation") or {}
    rationale = rec.get("rationale") or ""
    if ("insufficien" in rationale.lower() or "potential" in rationale.lower()
            or "may not" in rationale.lower()):
        validator_gap_flag += 1

    # Binding refusal detection
    fb_roles = r.get("fallback_roles") or []
    if "Binding" in fb_roles:
        binding_refusal_count += 1

print(f"  COA count distribution:    {dict(n_coas_counts)}")
print(f"  Interpreter mode counts:   {dict(interpreter_modes)}")
print(f"  Validator gap-flagged:     {validator_gap_flag}/6 runs")
print(f"  Binding refusal fallbacks: {binding_refusal_count}/6 runs")
PY
```

**Expected pattern (based on demo runs):**
- COA count: `{1: 6}` (Decomposition single-COA prior, robust across domains)
- Interpreter mode: mixed, depending on which chunks the Procedure-role retriever pulled
- Validator gap-flagged: 0-3 of 6 (unstable)
- Binding refusals: 0-2 of 6, most likely on the two FIN tasks

## Report

`handoffs/HANDOFF_11a_report_<YYYY-MM-DD>.md` with:
- Per-system table from Task 3
- Demo-finding observations from Task 4
- Total API cost across all 7 systems
- Total wall clock
- Anything that did NOT match the demo-era expectations (those are the surprises Phase 6b/c needs to know about)
- PROCEED verdict (smoke-test gate: all 42 records present with ok=True; schema_valid is data)

Commit message: `Handoff 11a: Phase 6 pilot smoke test (7 systems × 6 tasks × 1 run = 42 records)`.

## What 11a tells us before 11b

If 11a PROCEEDs cleanly and the four demo findings reproduce roughly as expected:
- The apparatus is verified end-to-end on the actual ground truth, not just the demo scenarios.
- HANDOFF_11b (Option B: main matrix + hold-out, ~$440) becomes a confident commit.
- HANDOFF_11c (Option A perturbations, ~$1200) becomes a separate scope question informed by 11a + 11b results.

If 11a surfaces a surprise — an apparatus-level system failure, a `code-ref` mismatch, a schema-validation crash on the actual scaffold ground truth — we catch it for $5 instead of $1640.
