# Codex Handoff 23: Stabilize Ollama and resume HANDOFF_11b-i with watchdog

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-05
**Estimated wall clock:** Stabilize phase 5 to 15 minutes; resume phase ~110 hours (1068 remaining MANDATE-primary records × ~370s/run).
**Estimated API cost:** $0 (local Ollama only).
**Blocked on:** Eval host has Ollama installed and the six `mandate-*` models loaded; the TRACE Phase 8 driver and any other Metal-using process is killed before resume; eval host has at least 32 GB of free RAM after killing concurrent processes.

---

## Why this exists

HANDOFF_11b-i ran 132/1200 MANDATE-primary main records cleanly, then Ollama disappeared mid-run. Resume attempts produced fast all-role fallback records (the apparatus silently falls back to deterministic on every role when Ollama is unreachable, producing records that look superficially valid but carry no actual LLM signal). Codex correctly killed the contamination, restored the ledger to the 132-record clean checkpoint, and halted.

The 132 records on disk are valid Phase 6 data and stay. This handoff:

1. Verifies Ollama is healthy with a real generation call, not just a tag-listing check.
2. Resumes 11b-i from record 133 to record 1200.
3. Adds a wall-clock watchdog that halts the loop if any new record completes in less than 60s — that's the fast-fallback contamination signature; a real MANDATE-primary run takes ~370s.
4. Post-run, verifies the 1068 new records do not contain fast-fallback contaminants.

**Definition of done.** 1200 total RunRecords at `07_system_outputs/mandate_primary/`, none with `wall_clock_ms < 60000`, none with all six roles `llm_used=False`. One handoff report.

## Pre-handoff PI checklist

Before firing this handoff, the PI confirms the following on the eval host (Codex cannot do these from inside the project):

1. **Restart Ollama cleanly.** `pkill ollama; sleep 5; ollama serve &` (or whatever the project's preferred Ollama-launch incantation is). Confirm with `curl -sS http://localhost:11434/api/tags`.

2. **Kill the TRACE Phase 8 driver** if it is still running. Codex saw it during the failure diagnosis; concurrent Metal work on 32B models is a likely cause of the Ollama crash. `ps -ef | grep -i trace | grep -v grep` then kill anything from the TRACE project.

3. **Free RAM.** Close editors, browsers, any other heavy app. Apple Silicon's unified memory means a Chrome instance with 30 tabs is competing with Ollama for the same physical RAM the 32B models load into. Aim for 32 GB free per `vm_stat | head -10` or Activity Monitor's Memory tab.

4. **Confirm AC power.** A 5+ day sustained 32B Ollama run on battery will thermal-throttle and crash. Keep the eval host on AC for the duration.

5. **Disable sleep / Display Sleep.** `pmset -a sleep 0; pmset -a displaysleep 0; caffeinate -d &` or equivalent. Power-management waking up during a long Ollama call has been a reproducible cause of mid-run failures.

Codex's preconditions below assume these steps are done; if any of them is incomplete the handoff will halt early.

## Preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# 1. Ollama responds to API tag query
curl -sS --max-time 5 http://localhost:11434/api/tags >/dev/null \
  || { echo "HALT: Ollama not reachable at localhost:11434"; exit 1; }
echo "Ollama API responsive"

# 2. The six mandate-* role models are loaded
curl -sS http://localhost:11434/api/tags | python3 -c "
import sys, json
d = json.load(sys.stdin)
names = sorted(m['name'] for m in d.get('models', []))
need = ['mandate-intake','mandate-interpreter','mandate-decomp','mandate-procedure','mandate-binding','mandate-validation']
missing = [n for n in need if not any(x.startswith(n) for x in names)]
print('mandate-* missing:', missing if missing else 'none')
assert not missing
"

# 3. HEALTHCHECK: a real generation call to mandate-intake completes in less than 60s
echo "Running Ollama healthcheck (real generation call against mandate-intake)..."
START=$(date +%s)
RESP=$(curl -sS --max-time 60 http://localhost:11434/api/generate \
  -d '{"model":"mandate-intake","prompt":"healthcheck","stream":false,"options":{"num_predict":16}}' 2>&1)
END=$(date +%s)
DUR=$((END-START))
echo "  healthcheck duration: ${DUR}s"
echo "$RESP" | python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
assert 'response' in d, f'no response field in healthcheck: {d}'
assert d.get('done'), f'healthcheck did not complete: {d}'
print(f'  response[:80]: {d[\"response\"][:80]!r}')
" || { echo "HALT: Ollama healthcheck failed"; exit 1; }
if [ "$DUR" -gt 30 ]; then
  echo "WARNING: healthcheck took ${DUR}s; under load the real runs may be slow but not stuck"
fi

# 4. Confirm no run-system or contention processes are running
pgrep -fl "run-system|apparatus.run" | grep -v grep && {
  echo "HALT: a run-system process is already running; kill it first"
  exit 1
}
pgrep -fl "trace.*phase.*8" 2>/dev/null | grep -v grep && {
  echo "HALT: TRACE Phase 8 driver still running; kill it before resume"
  exit 1
}
echo "no contention processes detected"

# 5. Checkpoint state: 132 clean records present
n=$(ls 07_system_outputs/mandate_primary/*.json 2>/dev/null | wc -l)
[ "$n" -eq 132 ] || { echo "HALT: expected 132 checkpoint records, found $n"; exit 1; }
ok=$(python3 -c "
import json, glob
files = glob.glob('07_system_outputs/mandate_primary/*.json')
print(sum(1 for f in files if json.load(open(f)).get('ok')))
")
[ "$ok" -eq 132 ] || { echo "HALT: $ok/132 ok; checkpoint has contamination"; exit 1; }
echo "checkpoint state: 132/132 clean"

# 6. Verify no fast-fallback contamination already on disk
python3 - <<'PY'
import json, glob
fast = 0
all_fb = 0
for f in glob.glob('07_system_outputs/mandate_primary/*.json'):
    r = json.load(open(f))
    if (r.get('wall_clock_ms') or 0) < 60_000:
        fast += 1
    rts = r.get('role_timings') or []
    if rts and all(not t.get('llm_used') for t in rts):
        all_fb += 1
assert fast == 0, f"HALT: {fast} fast-fallback records on disk; ledger contaminated"
assert all_fb == 0, f"HALT: {all_fb} all-role-fallback records on disk; ledger contaminated"
print("no fast-fallback or all-role-fallback contamination detected")
PY

# 7. AEGIS-eval still at v1 (HANDOFF_22's restoration intact)
grep "mandate-eval-primary-2026q2-v1" AEGIS-eval/_AEGIS_EVAL_README.txt >/dev/null \
  || { echo "AEGIS-eval contaminated"; exit 1; }
test -f AEGIS-eval/src/mandate/roles/binding.py \
  || { echo "binding.py missing"; exit 1; }
grep -q "llm_refused_with_error" AEGIS-eval/src/mandate/roles/binding.py \
  && { echo "v2 patch contamination in binding.py"; exit 1; }
echo "AEGIS-eval still at v1 baseline"
```

**Success criteria.** All seven preconditions print confirmation. Healthcheck duration is recorded (typical: 5-15s; if 60s+ that's a yellow flag but not a halt).

## Decision boundary

You may decide:
- Commit incrementally every 100 records as 11b-i did.
- One Ollama-side retry on a transient connection error, but if `Connection refused` appears, halt immediately and do NOT auto-retry. The previous failure mode was apparatus continuing through connection-refused into fast-fallback contamination.

You must escalate:
- Any new record with `wall_clock_ms < 60000`. That is the fast-fallback signature; stop the loop, do not commit the bad record. The watchdog in Task 2 catches this.
- A second Ollama crash during this resume. If Ollama dies again, halt; we are in a deeper infrastructure problem than this handoff can solve.
- Healthcheck duration above 60s. The healthcheck targets the lightest role (mandate-intake) with a 16-token completion budget; if that takes longer than 60s, the host is overloaded.

You may NOT treat as a halt:
- `schema_valid=False` on any RunRecord (Phase 6 O4 data).
- `any_llm_fallback=True` on individual runs that completed in 300+ seconds (genuine Binding-refusal data, NOT the fast-fallback contamination).

You may not:
- Modify AEGIS-eval tree.
- Modify `04_ground_truth/`.
- Re-run the existing 132 checkpoint records.
- Remove the watchdog or weaken the wall-clock floor.

---

## Task 1: Resume MANDATE-primary main (records 133 through 1200)

The harness ledger is append-only and re-runs overwrite same-id RunRecord files harmlessly. Re-firing the same command as HANDOFF_11b-i Task 1 will pick up at the next pending (task_id, run_idx) tuple after the 132 already-committed records.

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

**Wall clock estimate.** 1068 remaining runs × ~370s = ~110 hours serial. Commit incrementally every ~100 records.

**Resume convention.** Same as 11b-i: same-id RunRecords overwrite harmlessly. If Ollama crashes again mid-resume, the ledger preserves whatever committed before the crash.

## Task 2: Run watchdog after each ~100-record commit

After every commit checkpoint (every ~100 new records, or every ~10 hours of wall clock), run this check. If it returns HALT, stop the loop, do NOT continue, and report the count of contamination records.

```zsh
python3 - <<'PY'
import json, glob, sys
n = 0
fast = []
all_fb = []
for f in glob.glob('07_system_outputs/mandate_primary/*.json'):
    r = json.load(open(f))
    n += 1
    wc = r.get('wall_clock_ms') or 0
    if wc < 60_000:
        fast.append((f, wc))
    rts = r.get('role_timings') or []
    if rts and all(not t.get('llm_used') for t in rts):
        all_fb.append(f)
print(f"records: {n}")
print(f"fast (wall_clock_ms < 60s):   {len(fast)}")
print(f"all-role-fallback contaminated: {len(all_fb)}")
if fast or all_fb:
    print("HALT: contamination detected. Stop the loop. Sample:")
    for f, wc in fast[:5]: print(f"  {f}: {wc}ms")
    for f in all_fb[:5]: print(f"  {f}: all-role-fallback")
    sys.exit(1)
print("OK: no contamination")
PY
```

**Success criteria at each checkpoint.** Print returns "OK: no contamination". Continue.

**On HALT.** Stop the run loop, do not auto-restart. The contamination signature means Ollama died again or another concurrent process is stealing GPU/RAM. Investigate the eval host state and report.

## Task 3: Final summary on 1200 records

```zsh
python3 - <<'PY'
import json, glob, collections
files = sorted(glob.glob('07_system_outputs/mandate_primary/*.json'))
print(f"records: {len(files)} (target 1200)")

ok = sum(1 for f in files if json.load(open(f)).get('ok'))
fast = sum(1 for f in files if (json.load(open(f)).get('wall_clock_ms') or 0) < 60_000)
print(f"ok: {ok}/{len(files)}")
print(f"fast-fallback contamination: {fast} (target 0)")

by_dom = collections.defaultdict(lambda: {"n":0, "any_llm_fb":0, "binding_refusal":0,
                                          "n_coas":collections.Counter(),
                                          "interp_det":0, "interp_clean":0,
                                          "validator_gap":0})
for fpath in files:
    r = json.load(open(fpath))
    tid = r.get("task_id","")
    if "-FIN-" in tid:   dom = "financial_reporting"
    elif "-SEC-" in tid: dom = "security_operations_reporting"
    elif "-INT-" in tid: dom = "intelligence_collection_tasking"
    else:                dom = "unknown"
    d = by_dom[dom]
    d["n"] += 1
    if r.get("any_llm_fallback"): d["any_llm_fb"] += 1
    if "Binding" in (r.get("fallback_roles") or []): d["binding_refusal"] += 1
    art = (r.get("output") or {}).get("artifact") or {}
    coas = art.get("courses_of_action") or []
    d["n_coas"][len(coas)] += 1
    anchor = art.get("anchor") or {}
    minimum = anchor.get("minimum") or {}
    min_desc = (minimum.get("description") if isinstance(minimum, dict) else str(minimum))
    if min_desc and ("Minimally satisfy" in min_desc or "Fully achieve" in min_desc):
        d["interp_det"] += 1
    else:
        d["interp_clean"] += 1
    rec = art.get("recommendation") or {}
    rationale = rec.get("rationale") or ""
    if ("insufficien" in rationale.lower() or "potential" in rationale.lower()
            or "may not" in rationale.lower()):
        d["validator_gap"] += 1

for dom, d in sorted(by_dom.items()):
    n = d["n"]
    if not n: continue
    print(f"\n=== {dom} ({n} records) ===")
    print(f"  any_llm_fallback:       {d['any_llm_fb']}/{n}  ({d['any_llm_fb']/n*100:.1f}%)")
    print(f"  Binding refusal:        {d['binding_refusal']}/{n}  ({d['binding_refusal']/n*100:.1f}%)")
    print(f"  COA count distribution: {dict(d['n_coas'])}")
    print(f"  Interpreter modes:      clean={d['interp_clean']}, det_prefix={d['interp_det']}")
    print(f"  Validator gap-flagged:  {d['validator_gap']}/{n}  ({d['validator_gap']/n*100:.1f}%)")
PY
```

**Success criteria.** 1200 records, all ok, zero fast-fallback. Per-domain demo-finding numbers recorded.

## Report

`handoffs/HANDOFF_23_report_<YYYY-MM-DD>.md` with:

- Records completed in this resume (target: 1068; total now 1200)
- Per-domain summary from Task 3
- Number of Ollama restarts or healthcheck issues encountered during the resume
- Total resume wall clock
- Watchdog trigger count (target: zero)
- PROCEED verdict

After HANDOFF_23 PROCEED, fire HANDOFF_11b-ii (baselines + hold-out + anonymize + outputs_freeze_v1) per the original split plan.

Commit message: `Handoff 23: stabilize Ollama and resume 11b-i to 1200 records (with fast-fallback watchdog)`.
