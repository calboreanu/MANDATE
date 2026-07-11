# Codex Handoff 11b-i: Phase 6 MANDATE-primary on 120 main tasks × 10 runs

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-05
**Estimated wall clock:** ~123 hours of Ollama serial compute (1200 runs × ~370s/run observed in HANDOFF_11a).
**Estimated API cost:** $0 (local Ollama only).
**Blocked on:** HANDOFF_11a PROCEED + HANDOFF_22 PROCEED (apparatus verified + v1 tree restored).

---

## Why this is its own handoff

HANDOFF_11b is split into two handoffs per PI direction. This is half-one: the long-running MANDATE-primary Ollama leg only, costing nothing in API spend but ~5 days of continuous local compute. Once 11b-i lands, the PI reviews the 1200 records against the four demo findings (Decomposition single-COA prior, Interpreter content-tripwire, Validator instability, Binding probabilistic refusal) before firing HANDOFF_11b-ii (the $450 baselines + hold-out + anonymize + freeze leg).

**Definition of done.** 1200 RunRecords at `07_system_outputs/mandate_primary/`. Every record `ok=True` on at least 1190 (1% schema-validity floor). Per-role `llm_used` and `llm_fallback` populated. One handoff report summarizing the four demo findings at scale.

## Preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# 1. Freeze tetrad + 11a smoke records (sanity that the apparatus chain is intact)
for T in corpus_freeze_v1 baseline_freeze_v1 gt_freeze_v1 perturbation_freeze_v1; do
  git tag --list | grep -E "^${T}$" >/dev/null || { echo "$T missing"; exit 1; }
done
n=$(ls 07_system_outputs/mandate_primary_pilot/*.json 2>/dev/null | wc -l)
[ "$n" -eq 6 ] || { echo "11a smoke records missing"; exit 1; }
echo "freezes + 11a smoke present"

# 2. main_tasks.jsonl materialized
[ "$(wc -l < 04_ground_truth/main_tasks.jsonl)" -eq 120 ] || { echo "main_tasks wrong size"; exit 1; }
echo "main_tasks.jsonl: 120 lines"

# 3. AEGIS-eval at v1 with binding.py present (HANDOFF_22 PROCEED)
grep "mandate-eval-primary-2026q2-v1" AEGIS-eval/_AEGIS_EVAL_README.txt >/dev/null \
  || { echo "AEGIS-eval not at v1"; exit 1; }
test -f AEGIS-eval/src/mandate/roles/binding.py || { echo "binding.py missing"; exit 1; }
# v1 baseline check (no v2 patch markers)
grep -q "llm_refused_with_error" AEGIS-eval/src/mandate/roles/binding.py \
  && { echo "binding.py carries v2 patch markers"; exit 1; }
echo "AEGIS-eval at v1 baseline"

# 4. llm_rag_index on production MITRE ATT&CK
python3 -c "
import json
cfg = json.load(open('AEGIS-eval/configs/llm_defaults.json'))
idx = cfg['llm_rag_index']
assert 'demo/' not in idx
assert 'enterprise-attack' in idx
print(f'llm_rag_index: {idx}')
"

# 5. Ollama running with the six mandate-* role models
curl -sS http://localhost:11434/api/tags | python3 -c "
import sys, json
d = json.load(sys.stdin)
names = sorted(m['name'] for m in d.get('models', []))
need = ['mandate-intake','mandate-interpreter','mandate-decomp','mandate-procedure','mandate-binding','mandate-validation']
missing = [n for n in need if not any(x.startswith(n) for x in names)]
print('mandate-* missing:', missing if missing else 'none')
assert not missing
"
```

**Success criteria.** All five preconditions print confirmation.

## Decision boundary

You may decide:
- Whether to commit incrementally (e.g., every 100 records). Recommended: yes — a multi-day Ollama run benefits from incremental commits so a mid-run interruption preserves verified state. The harness ledger is append-only, so re-running the same command after an interruption picks up where it left off (same-id RunRecords overwrite harmlessly).
- One retry on a transient Ollama error per task per run.

You must escalate:
- More than 12 of 1200 runs (1% threshold) producing `ok=False`. That signals an apparatus-level failure mode.
- Wall clock above 150 hours total (~25% over estimate; signals Ollama queue saturation or a stuck system).
- AEGIS-eval `llm_rag_index` modified during the run. Should never happen.

You may NOT treat as a halt (Phase 6 data):
- `schema_valid=False` on any RunRecord.
- `any_llm_fallback=True` on individual runs. The Binding-refusal probabilistic behavior is expected at the ~10-25% rate per the upstream-team note.
- Per-role timing variation.

You may not:
- Modify the v1 AEGIS-eval tree mid-run.
- Apply the v2 candidate Binding-refusal patch. Phase 6 measures v1.
- Modify `04_ground_truth/main_tasks.jsonl`.
- Modify the `--seed-base 20260605` value.

---

## Task 1: Run MANDATE-primary on 120 main tasks × 10 runs

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

**Wall clock estimate.** 1200 runs × ~370s = ~123 hours serial.

**Resume convention.** If interrupted (Ollama crash, eval host restart, intentional stop), re-run the same command. The harness ledger is append-only and re-runs overwrite same-id RunRecord files harmlessly.

## Task 2: Per-domain × per-category summary

```zsh
python3 - <<'PY'
import json, glob, collections
files = sorted(glob.glob("07_system_outputs/mandate_primary/*.json"))
print(f"records: {len(files)}")
ok = sum(1 for f in files if json.load(open(f)).get("ok"))
print(f"ok rate: {ok}/{len(files)}")

# Per-domain breakouts using task_id naming convention TASK-MAIN-{DOM}-NNN
by_dom = collections.defaultdict(lambda: {"ok": 0, "n_coas": collections.Counter(),
                                          "interpreter": collections.Counter(),
                                          "validator_gap": 0,
                                          "binding_refusal": 0,
                                          "any_llm_fallback": 0,
                                          "total": 0})
for f in files:
    r = json.load(open(f))
    tid = r.get("task_id","")
    if "-FIN-" in tid:   dom = "financial_reporting"
    elif "-SEC-" in tid: dom = "security_operations_reporting"
    elif "-INT-" in tid: dom = "intelligence_collection_tasking"
    else:                dom = "unknown"
    d = by_dom[dom]
    d["total"] += 1
    if r.get("ok"): d["ok"] += 1
    if r.get("any_llm_fallback"): d["any_llm_fallback"] += 1
    if "Binding" in (r.get("fallback_roles") or []):
        d["binding_refusal"] += 1

    art = (r.get("output") or {}).get("artifact") or {}
    coas = art.get("courses_of_action") or []
    d["n_coas"][len(coas)] += 1

    anchor = art.get("anchor") or {}
    minimum = anchor.get("minimum") or {}
    min_desc = (minimum.get("description") if isinstance(minimum, dict)
                else str(minimum))
    if min_desc and ("Minimally satisfy" in min_desc or "Fully achieve" in min_desc):
        d["interpreter"]["deterministic_prefix"] += 1
    else:
        d["interpreter"]["clean_distillation"] += 1

    rec = art.get("recommendation") or {}
    rationale = rec.get("rationale") or ""
    if ("insufficien" in rationale.lower() or "potential" in rationale.lower()
            or "may not" in rationale.lower()):
        d["validator_gap"] += 1

for dom, d in sorted(by_dom.items()):
    print(f"\n=== {dom} ({d['total']} records) ===")
    print(f"  ok rate:                  {d['ok']}/{d['total']}")
    print(f"  any_llm_fallback:         {d['any_llm_fallback']}/{d['total']}  ({d['any_llm_fallback']/max(d['total'],1)*100:.1f}%)")
    print(f"  Binding refusal:          {d['binding_refusal']}/{d['total']}  ({d['binding_refusal']/max(d['total'],1)*100:.1f}%)")
    print(f"  COA count distribution:   {dict(d['n_coas'])}")
    print(f"  Interpreter modes:        clean={d['interpreter']['clean_distillation']}, deterministic_prefix={d['interpreter']['deterministic_prefix']}")
    print(f"  Validator gap-flagged:    {d['validator_gap']}/{d['total']}  ({d['validator_gap']/max(d['total'],1)*100:.1f}%)")
PY
```

**Success criteria.** Print completes. Numbers are recorded in the report.

## Report

`handoffs/HANDOFF_11b_i_report_<YYYY-MM-DD>.md` with:

- Total RunRecords / ok rate / any_llm_fallback rate
- Per-domain breakouts (4 demo findings × 3 main domains)
- Total wall clock (intuition: ~123 hours)
- Any unexpected failure modes outside the four demo findings
- PROCEED verdict

After 11b-i PROCEED, the PI reviews the per-domain demo-finding numbers. If they match expectation (Decomposition single-COA stable across 1200, Interpreter mode mix similar to 11a's 4:2 deterministic-prefix:clean ratio, Validator gap-flag rate around 10-20%, Binding refusal rate around 10-25%), HANDOFF_11b-ii is a confident fire. If anything is materially off, we pause and investigate before committing the $450 baselines spend.

Commit message: `Handoff 11b-i: Phase 6 MANDATE-primary main (1200 records, $0)`.
