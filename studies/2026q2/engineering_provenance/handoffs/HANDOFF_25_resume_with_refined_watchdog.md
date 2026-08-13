# Codex Handoff 25: Resume 11b-i from 1132 with refined watchdog + SEC-038 restore

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-10
**Estimated wall clock:** ~7 hours (68 remaining runs × ~370s, with 20 of those expected to be ~40s legitimate Intake failures on SEC-038/SEC-040).
**Estimated API cost:** $0 (local Ollama only).
**Blocked on:** Ollama healthy; eval host quiescent.

---

## Why this exists

HANDOFF_24 caught `TASK-MAIN-SEC-038 r01/r02` failing fast in the Intake role with `Invalid constraint syntax`. Codex correctly halted under the watchdog rule I wrote, but two diagnostic errors followed from the rule:

1. **The watchdog rule was too coarse.** It conflates Ollama-crash contamination (all six roles `llm_used=False`, wall_clock under ~5s) with legitimate single-role failures (Intake LLM ran for ~40s then failed validation). The first is contamination that must reject; the second is Phase 6 measurement data that must keep.

2. **Two legitimate ok=False records were quarantined as contamination.** The SEC-038 r01 and r02 records carry the actual MANDATE-primary failure on that task and are valid Phase 6 data. They live at `/tmp/handoff24_postreboot_quarantine_20260610_1172/`.

The substantive finding is recorded as the fifth content-tripwire in `00_preregistration/DEVIATIONS.md` 2026-06-10 and `demo/UPSTREAM_MANDATE_NOTE_decomposition_bias.md`. The `mandate-intake` fine-tune treats the natural-language phrase "Here's the constraint:" as a directive to emit a constraint, generates an English sentence as the constraint value, and `validate_constraint()` rejects it. Two tasks (SEC-038 and SEC-040) contain that phrase; both are expected to produce ok=False records under the v1 frozen apparatus.

This handoff:

1. Restores the SEC-038 quarantined records from `/tmp/`.
2. Resumes 11b-i with `--skip-existing` from the now-1134 checkpoint to the 1200 target.
3. Uses a refined watchdog that halts ONLY on the Ollama-crash signature (wall_clock < 60s AND all roles `llm_used=False`), not on legitimate single-role failures.
4. Expects 20 ok=False records from SEC-038 (8 more) and SEC-040 (10) on the Intake content-tripwire, plus 40 normal records from the other remaining tasks.

**Definition of done.** 1200 total RunRecords. Per-record summary includes:
- The 132 + 1000 successful records from the prior phases (1132).
- The 2 restored SEC-038 Intake failures (r01, r02) — restored from quarantine.
- 18 more legitimate Intake failures (SEC-038 r03..r10 + SEC-040 r01..r10) — produced this run.
- 48 normal full-pipeline records from SEC-039, SEC-041, SEC-042, SEC-043 (4 tasks × 10 runs each) plus the 8 unfinished from earlier — actual count depends on the task ordering. The total is 1200.

No fast-fallback contamination (per refined watchdog), no all-role-fallback contamination.

## Preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# 1. --skip-existing patch still on project main
python3 -m apparatus.run run-system --help 2>&1 | grep -q "skip-existing" \
  || { echo "HALT: --skip-existing flag missing"; exit 1; }

# 2. Harness tests for resume contract still pass
python3 -m pytest apparatus/tests/test_harness.py -q 2>&1 | tail -3

# 3. Ollama healthy
curl -sS --max-time 5 http://localhost:11434/api/tags >/dev/null \
  || { echo "HALT: Ollama not reachable"; exit 1; }
START=$(date +%s)
curl -sS --max-time 60 http://localhost:11434/api/generate \
  -d '{"model":"mandate-intake","prompt":"healthcheck","stream":false,"options":{"num_predict":16}}' \
  | python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
assert 'response' in d and d.get('done')
print(f'healthcheck response: {d[\"response\"][:60]!r}')
" || { echo "HALT: healthcheck failed"; exit 1; }
echo "healthcheck completed in $(($(date +%s) - START))s"

# 4. Checkpoint state: 1132 clean records
n=$(ls 07_system_outputs/mandate_primary/*.json 2>/dev/null | wc -l)
[ "$n" -eq 1132 ] || { echo "HALT: expected 1132 checkpoint records, found $n"; exit 1; }
python3 - <<'PY'
import json, glob, sys
ok = 0
for f in glob.glob('07_system_outputs/mandate_primary/*.json'):
    r = json.load(open(f))
    if r.get('ok'): ok += 1
assert ok == 1132, f'expected 1132 ok, got {ok}'
print('checkpoint: 1132/1132 ok')
PY

# 5. Quarantine directory still present with the 2 SEC-038 records
QUAR=/tmp/handoff24_postreboot_quarantine_20260610_1172
[ -d "$QUAR" ] || { echo "HALT: quarantine dir missing at $QUAR"; exit 1; }
n_quar=$(ls "$QUAR"/mandate_primary__TASK-MAIN-SEC-038*.json 2>/dev/null | wc -l)
[ "$n_quar" -eq 2 ] || { echo "HALT: expected 2 SEC-038 records in quarantine, found $n_quar"; exit 1; }
echo "quarantine has 2 SEC-038 records ready to restore"

# 6. AEGIS-eval still at v1 (HANDOFF_22's restoration intact)
grep "mandate-eval-primary-2026q2-v1" AEGIS-eval/_AEGIS_EVAL_README.txt >/dev/null \
  || { echo "HALT: AEGIS-eval contaminated"; exit 1; }
test -f AEGIS-eval/src/mandate/roles/binding.py \
  || { echo "HALT: binding.py missing"; exit 1; }
grep -q "llm_refused_with_error" AEGIS-eval/src/mandate/roles/binding.py \
  && { echo "HALT: v2 patch contamination"; exit 1; }
echo "AEGIS-eval still at v1"
```

**Success criteria.** All six preconditions print confirmation.

## Task 1: Restore the SEC-038 quarantined records

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
QUAR=/tmp/handoff24_postreboot_quarantine_20260610_1172

# Verify the records are real Intake-failure records (not fast-fallback contamination)
python3 - <<'PY'
import json, glob
for f in sorted(glob.glob(f"{__import__('os').environ['QUAR']}/mandate_primary__TASK-MAIN-SEC-038*.json")):
    r = json.load(open(f))
    rts = r.get('role_timings') or []
    all_fb = rts and all(not t.get('llm_used') for t in rts)
    intake = next((t for t in rts if t.get('role_name') == 'Intake'), {})
    intake_used_llm = intake.get('llm_used', False)
    wc = r.get('wall_clock_ms') or 0
    print(f"  {f.split('/')[-1]}:")
    print(f"    wall_clock_ms: {wc:.0f}  intake.llm_used: {intake_used_llm}  all_roles_fb: {all_fb}")
    print(f"    ok: {r.get('ok')}")
    # The record we want to restore: Intake ran the LLM, then failed.
    # NOT what we want: all_roles_fb=True (that would be Ollama-crash contamination).
    if all_fb:
        print(f"    REJECT: this looks like Ollama-crash contamination, not Intake failure")
PY
QUAR=$QUAR python3 - <<'PY'
import os
print(f"QUAR={os.environ['QUAR']}")
PY

# If both records show intake.llm_used=True (the model ran) and all_roles_fb=False,
# move them to the canonical output dir.
cp "$QUAR"/mandate_primary__TASK-MAIN-SEC-038__r01.json \
    07_system_outputs/mandate_primary/
cp "$QUAR"/mandate_primary__TASK-MAIN-SEC-038__r02.json \
    07_system_outputs/mandate_primary/

# Verify the restored count
n=$(ls 07_system_outputs/mandate_primary/*.json | wc -l)
echo "after restore: $n records (expected 1134)"
```

**Success criteria.** 1134 records present. Both SEC-038 records show `intake.llm_used=True` and `all_roles_fb=False` (i.e., they are legitimate Intake failures, not Ollama-crash contamination).

**On HALT.** If the quarantined SEC-038 records show all-role-fallback signatures, do NOT restore them — they would be contamination. In that case, the SEC-038 r01/r02 runs need to be re-executed fresh by the resume in Task 2 (the apparatus's `--skip-existing` flag will skip the existing 1132 and execute r01/r02 anew, expecting the same Intake failure to reproduce).

## Task 2: Resume MANDATE-primary main with refined watchdog

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

**Wall clock estimate.** 66 remaining runs (assuming restore step worked):
- 18 expected Intake failures (SEC-038 r03..r10 + SEC-040 r01..r10) at ~40s each = ~12 min
- 48 normal runs at ~370s each = ~5 hours
- Total: ~5.2 hours

If the restore step in Task 1 was skipped (quarantined records were not safe to restore), the count is 68 remaining runs (2 more SEC-038 to re-execute). Wall clock ~5.3 hours.

**Resume convention.** Same as HANDOFF_24. If anything fails mid-run, re-fire — the `--skip-existing` flag prevents re-execution of completed records.

## Task 3: Refined watchdog (after the run completes)

The watchdog now halts ONLY on the Ollama-crash signature (all-roles-fallback under 60s). Legitimate single-role failures (Intake content-tripwire on SEC-038/SEC-040) are recorded as Phase 6 data.

```zsh
python3 - <<'PY'
import json, glob, sys
n = 0
contamination = []   # all-role-fallback signature (Ollama crash)
fast_legit = []      # fast but at least one role ran the LLM (legitimate fail)
bad_json = []
for f in glob.glob('07_system_outputs/mandate_primary/*.json'):
    n += 1
    try:
        r = json.load(open(f))
    except Exception as e:
        bad_json.append((f, repr(e)))
        continue
    wc = r.get('wall_clock_ms') or 0
    rts = r.get('role_timings') or []
    all_fb = rts and all(not t.get('llm_used') for t in rts)
    if wc < 60_000 and all_fb:
        contamination.append((f, wc))
    elif wc < 60_000:
        fast_legit.append((f, wc, r.get('task_id'), r.get('ok')))

print(f"records: {n}")
print(f"contamination (all-roles-fb, fast):   {len(contamination)}")
print(f"fast legitimate (single-role fail):   {len(fast_legit)}")
print(f"unreadable JSON:                       {len(bad_json)}")
if contamination:
    print("HALT: contamination detected. Sample:")
    for f, wc in contamination[:5]: print(f"  {f}: {wc}ms")
    sys.exit(1)
if bad_json:
    print("HALT: unreadable JSON files. Sample:")
    for f, e in bad_json[:3]: print(f"  {f}: {e}")
    sys.exit(1)
print("OK: no Ollama-crash contamination")
print(f"\nFast-legitimate-fail records (expected on SEC-038 + SEC-040 = 20):")
for f, wc, tid, ok in fast_legit[:25]:
    print(f"  {tid} wall_clock={wc:.0f}ms ok={ok}")
PY
```

**Success criteria.** `contamination` is 0. `fast_legit` is 20 (or 18 if Task 1 restore was skipped — the canonical SEC-038 r01/r02 then come from re-execution in Task 2). All `fast_legit` records carry `task_id` in `{TASK-MAIN-SEC-038, TASK-MAIN-SEC-040}`.

**On HALT.** Same triage as HANDOFF_24. Ollama-crash contamination means infrastructure issue; halt and report. Unreadable JSON means filesystem issue; halt and report.

## Task 4: Final summary on 1200 records (per-domain demo-finding breakouts)

Same as HANDOFF_24 Task 3, plus an additional Intake-failure count by task_id:

```zsh
python3 - <<'PY'
import json, glob, collections
files = sorted(glob.glob('07_system_outputs/mandate_primary/*.json'))
print(f"records: {len(files)} (target 1200)")
ok = sum(1 for f in files if json.load(open(f)).get('ok'))
print(f"ok: {ok}/{len(files)}")

# Intake failures by task_id
intake_fails = collections.Counter()
for f in files:
    r = json.load(open(f))
    if not r.get('ok'):
        # Determine which role failed (first role with status=fail)
        rts = r.get('role_timings') or []
        first_fail = next((t for t in rts if t.get('status') == 'fail'), None)
        if first_fail and first_fail.get('role_name') == 'Intake':
            intake_fails[r.get('task_id')] += 1
print(f"\nIntake-failure records by task_id:")
for tid, n in intake_fails.most_common():
    print(f"  {tid}: {n} runs failed in Intake")

# Per-domain demo-finding summary (Task 3 of HANDOFF_24, unchanged)
by_dom = collections.defaultdict(lambda: {"n":0, "ok":0, "any_llm_fb":0, "binding_refusal":0,
                                          "n_coas":collections.Counter(),
                                          "interp_det":0, "interp_clean":0,
                                          "validator_gap":0, "intake_fail":0})
for fpath in files:
    r = json.load(open(fpath))
    tid = r.get("task_id","")
    if "-FIN-" in tid:   dom = "financial_reporting"
    elif "-SEC-" in tid: dom = "security_operations_reporting"
    elif "-INT-" in tid: dom = "intelligence_collection_tasking"
    else:                dom = "unknown"
    d = by_dom[dom]
    d["n"] += 1
    if r.get("ok"): d["ok"] += 1
    if r.get("any_llm_fallback"): d["any_llm_fb"] += 1
    if "Binding" in (r.get("fallback_roles") or []): d["binding_refusal"] += 1
    rts = r.get('role_timings') or []
    first_fail = next((t for t in rts if t.get('status') == 'fail'), None)
    if first_fail and first_fail.get('role_name') == 'Intake':
        d["intake_fail"] += 1
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
    print(f"  ok rate:                {d['ok']}/{n}  ({d['ok']/n*100:.1f}%)")
    print(f"  Intake failures:        {d['intake_fail']}/{n}  ({d['intake_fail']/n*100:.1f}%)")
    print(f"  any_llm_fallback:       {d['any_llm_fb']}/{n}  ({d['any_llm_fb']/n*100:.1f}%)")
    print(f"  Binding refusal:        {d['binding_refusal']}/{n}  ({d['binding_refusal']/n*100:.1f}%)")
    print(f"  COA count distribution: {dict(d['n_coas'])}")
    print(f"  Interpreter modes:      clean={d['interp_clean']}, det_prefix={d['interp_det']}")
    print(f"  Validator gap-flagged:  {d['validator_gap']}/{n}  ({d['validator_gap']/n*100:.1f}%)")
PY
```

## Report

`handoffs/HANDOFF_25_report_<YYYY-MM-DD>.md` with:
- Records restored from quarantine (0 or 2)
- Records executed this resume (target: 66 or 68)
- Total records at end (target: 1200)
- Per-domain summary from Task 4 including Intake-failure breakdown
- Watchdog refined-rule trigger count (target: 0)
- Per-task Intake-failure count for SEC-038 and SEC-040 (target: 10 each)
- PROCEED verdict

After HANDOFF_25 PROCEED, fire HANDOFF_11b-ii (baselines + hold-out + anonymize + outputs_freeze_v1).

Commit message: `Handoff 25: resume 11b-i to 1200 with refined watchdog (5th content-tripwire: Intake on SEC-038/SEC-040 recorded as data)`.
