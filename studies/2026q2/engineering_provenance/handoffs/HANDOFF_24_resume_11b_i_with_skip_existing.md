# Codex Handoff 24: Resume HANDOFF_11b-i safely with --skip-existing

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-08
**Estimated wall clock:** ~110 hours of Ollama serial compute (1068 remaining MANDATE-primary records × ~370s/run).
**Estimated API cost:** $0 (local Ollama only).
**Blocked on:** Apparatus patch committed on project main (this handoff verifies it as precondition); Ollama healthy; eval host quiescent (TRACE Phase 8 killed, RAM free, AC power, sleep disabled per HANDOFF_23 PI checklist).

---

## Why this exists

HANDOFF_23 caught a real apparatus bug: `apparatus.run run-system` had no resume support. Re-firing the same command on a partial output directory would re-execute every (task, run) tuple and overwrite committed records. Two of my handoffs incorrectly claimed "same-id RunRecords overwrite harmlessly" — that was wrong. The apparatus had no skip-existing semantics at all.

Patch landed on project main:
- `apparatus/harness/runner.py`: `run_matrix` accepts `skip_existing: bool = False`. When True, existing `<run_id>.json` files are loaded into the ledger and counted in the returned records, but the underlying `system.run()` is not called for those tuples.
- `apparatus/run.py`: `run-system` CLI accepts `--skip-existing`. Default False (backward-compatible).
- `apparatus/tests/test_harness.py`: two new tests cover (a) skip_existing=True does not re-execute existing records and does not rewrite their files, (b) skip_existing=True correctly resumes a partial checkpoint by executing only the missing tuples.
- All seven harness tests pass.

This handoff verifies the patch is present, the 132-record checkpoint is intact, the eval host is ready, and then resumes HANDOFF_11b-i with `--skip-existing` so the 132 existing records are loaded into the ledger without re-execution and the run continues to the remaining 1068.

**Definition of done.** 1200 total RunRecords at `07_system_outputs/mandate_primary/`. The 132 original checkpoint files unchanged on disk (same mtimes). 1068 new records added. No fast-fallback contamination. One handoff report.

## Pre-handoff PI checklist

Same as HANDOFF_23 (reproduced here for self-containment). Confirm on the eval host before sending to Codex:

1. **Ollama running.** `ollama serve &` or app-launched; verify with `curl -sS http://localhost:11434/api/tags`.
2. **TRACE Phase 8 driver killed.** `ps -ef | grep -i trace | grep -v grep` then kill anything from TRACE.
3. **~32 GB RAM free.** Close editors, browsers, anything heavy.
4. **AC power.** 5+ days of sustained 32B Ollama is thermal-suicide on battery.
5. **Sleep disabled.** `pmset -a sleep 0; pmset -a displaysleep 0; caffeinate -d &`.

## Preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# 1. The --skip-existing patch is on project main
python3 -m apparatus.run run-system --help 2>&1 | grep -q "skip-existing" \
  || { echo "HALT: --skip-existing flag missing from run-system CLI"; exit 1; }
echo "--skip-existing flag present"

# 2. The two new resume tests pass (regression guard)
python3 -m pytest apparatus/tests/test_harness.py::test_run_matrix_skip_existing_does_not_re_execute apparatus/tests/test_harness.py::test_run_matrix_skip_existing_resumes_partial_checkpoint -q 2>&1 | tail -3

# 3. Ollama responds to API tag query AND a real generation call
curl -sS --max-time 5 http://localhost:11434/api/tags >/dev/null \
  || { echo "HALT: Ollama not reachable"; exit 1; }
curl -sS http://localhost:11434/api/tags | python3 -c "
import sys, json
d = json.load(sys.stdin)
names = sorted(m['name'] for m in d.get('models', []))
need = ['mandate-intake','mandate-interpreter','mandate-decomp','mandate-procedure','mandate-binding','mandate-validation']
missing = [n for n in need if not any(x.startswith(n) for x in names)]
assert not missing, f'mandate-* missing: {missing}'
print('all six mandate-* models loaded')
"
START=$(date +%s)
curl -sS --max-time 60 http://localhost:11434/api/generate \
  -d '{"model":"mandate-intake","prompt":"healthcheck","stream":false,"options":{"num_predict":16}}' \
  | python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
assert 'response' in d and d.get('done'), f'healthcheck malformed: {d}'
print(f'healthcheck response: {d[\"response\"][:80]!r}')
" || { echo "HALT: healthcheck failed"; exit 1; }
echo "healthcheck completed in $(($(date +%s) - START))s"

# 4. Checkpoint state: 132 clean records, no fast-fallback contamination
n=$(ls 07_system_outputs/mandate_primary/*.json 2>/dev/null | wc -l)
[ "$n" -eq 132 ] || { echo "HALT: expected 132 checkpoint records, found $n"; exit 1; }
python3 - <<'PY'
import json, glob, sys
ok = 0
fast = 0
all_fb = 0
for f in glob.glob('07_system_outputs/mandate_primary/*.json'):
    r = json.load(open(f))
    if r.get('ok'): ok += 1
    if (r.get('wall_clock_ms') or 0) < 60_000: fast += 1
    rts = r.get('role_timings') or []
    if rts and all(not t.get('llm_used') for t in rts): all_fb += 1
assert ok == 132, f'expected 132 ok, got {ok}'
assert fast == 0, f'{fast} fast-fallback contaminants present'
assert all_fb == 0, f'{all_fb} all-role-fallback contaminants present'
print('checkpoint: 132/132 ok, 0 contamination')
PY

# 5. No active run-system or contention processes
pgrep -fl "run-system|apparatus.run" | grep -v grep && {
  echo "HALT: a run-system process is already running"; exit 1;
}
pgrep -fl "trace.*phase.*8" 2>/dev/null | grep -v grep && {
  echo "HALT: TRACE Phase 8 driver still running"; exit 1;
}
echo "no contention processes detected"

# 6. AEGIS-eval still at v1 baseline (no v2 patch contamination)
grep "mandate-eval-primary-2026q2-v1" AEGIS-eval/_AEGIS_EVAL_README.txt >/dev/null \
  || { echo "HALT: AEGIS-eval contaminated"; exit 1; }
test -f AEGIS-eval/src/mandate/roles/binding.py \
  || { echo "HALT: binding.py missing"; exit 1; }
grep -q "llm_refused_with_error" AEGIS-eval/src/mandate/roles/binding.py \
  && { echo "HALT: v2 patch contamination in binding.py"; exit 1; }
echo "AEGIS-eval still at v1 baseline"
```

**Success criteria.** All six preconditions print confirmation. Healthcheck duration is recorded (typical 5-15s).

## Decision boundary

You may decide:
- Commit incrementally every ~100 records (recommended — preserves state across mid-run interruptions).
- One Ollama-side retry on transient API error. Do NOT auto-retry on `Connection refused`; halt immediately.

You must escalate:
- Any new record with `wall_clock_ms < 60_000`. That's the fast-fallback signature.
- A second Ollama crash during this resume.
- Healthcheck duration above 60s.
- The skip count after Task 1 starts is NOT 132. The patch should load exactly the 132 existing records from disk; if it loads a different number, the apparatus or filesystem state is inconsistent — stop and report.

You may NOT treat as a halt:
- `schema_valid=False` on any RunRecord (Phase 6 O4 data).
- `any_llm_fallback=True` on individual runs that completed in 300+ seconds (genuine Binding-refusal data).

You may not:
- Modify AEGIS-eval tree.
- Modify `04_ground_truth/`.
- Re-run the existing 132 checkpoint records (the patch prevents this; do not work around it).
- Remove the watchdog or weaken the wall-clock floor.

---

## Task 1: Resume MANDATE-primary main with --skip-existing

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
  --seed-base 20260605 \
  --skip-existing
```

**Wall clock estimate.** 1068 new runs × ~370s = ~110 hours serial. Plus ~30 seconds total to load the 132 existing records into the ledger from disk.

**Expected console output at startup.** Codex should see a stream of `SKIP (existing)` lines for the first 132 entries (one per existing run_id), then the normal `ok=True wall_clock_ms` line per new execution. If you see fewer than 132 SKIPs, halt and report — the patch isn't behaving as the tests assert.

**Resume convention (now correct).** If Ollama crashes again mid-resume, re-fire the same command. The next run will skip everything written before the crash and pick up from the first missing tuple.

## Task 2: Watchdog after each ~100-record commit

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

**On HALT.** Stop the run loop, do not auto-restart. Investigate eval host state and report.

## Task 3: Final summary on 1200 records

Same as HANDOFF_23 Task 3. Per-domain breakouts of the four demo findings:

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

## Report

`handoffs/HANDOFF_24_report_<YYYY-MM-DD>.md` with:
- Records skipped at startup (target: 132)
- Records executed (target: 1068)
- Total records at end (target: 1200)
- Per-domain demo-finding summary from Task 3
- Number of Ollama restarts or healthcheck issues
- Total resume wall clock
- Watchdog trigger count (target: 0)
- PROCEED verdict

After HANDOFF_24 PROCEED, fire HANDOFF_11b-ii (baselines + hold-out + anonymize + outputs_freeze_v1) per the original split plan.

Commit message: `Handoff 24: resume 11b-i to 1200 records via --skip-existing (apparatus resume support patched)`.
