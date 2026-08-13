# Codex Handoff 26: Quarantine 300 contaminated MP hold-out records, re-run cleanly, re-anonymize, cut outputs_freeze_v1_1

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-13
**Estimated wall clock:** Ollama healthcheck + quarantine ~5 minutes. MP hold-out re-run ~31 hours (300 runs × ~370s). Re-anonymize + freeze ~10 minutes. Total ~32 hours.
**Estimated API cost:** $0 (re-run is Ollama only; baselines and anonymization don't burn API).
**Blocked on:** Ollama restarted and healthy; PI checklist applied (no TRACE Phase 8, RAM free, AC power, sleep disabled).

---

## Why this exists

HANDOFF_11b-ii reported PROCEED with 9000 RunRecords and cut `outputs_freeze_v1`. Post-hoc analysis surfaced that all 300 MANDATE-primary hold-out records were contaminated by an Ollama outage between Task 1 (baselines) and Task 2 (hold-out). Every role on every MP hold-out record reported `llm_fallback=True` with reason `Ollama connection error: [Errno 61] Connection refused`. Wall clock per record was ~2 seconds instead of ~370 seconds. The 300 records measured the deterministic-fallback path, not MANDATE-primary v1.

The 1200 MP main matrix records and the 7500 API-bound baseline records (B1-B6 main + B1 hold-out) are **unaffected**. Only the 300 MP hold-out records are bad. The previous anonymization mapping included the contaminated records, so it must be regenerated alongside the corrected outputs. `outputs_freeze_v1` is preserved as historical record; this handoff cuts `outputs_freeze_v1_1`.

See `00_preregistration/DEVIATIONS.md` 2026-06-13 entry for the full rationale.

**Definition of done.**

1. The 300 contaminated MP hold-out records quarantined to `/tmp/handoff_26_contaminated_quarantine_<date>/`.
2. 300 fresh MP hold-out records produced cleanly with Ollama-backed role pipeline (per-record wall clock ~370s, no all-roles-fallback contamination, `any_llm_fallback=True` on individual records is permitted as legitimate Binding refusal data).
3. The full 9000-record output tree re-anonymized with a fresh seed.
4. `outputs_freeze_v1_1` tag cut at the new commit.
5. Original `outputs_freeze_v1` tag unchanged.
6. One handoff report.

## Pre-handoff PI checklist

Codex cannot do these from inside the project. Confirm on the eval host before sending the handoff:

1. **Ollama restarted.** `pkill ollama; sleep 5; ollama serve &`. Verify with `curl -sS http://localhost:11434/api/tags`.
2. **TRACE Phase 8 driver killed.** `ps -ef | grep -i trace | grep -v grep` then kill.
3. **~32 GB RAM free.** Close editors, browsers, heavy apps.
4. **AC power.** 31 hours of sustained 32B Ollama; battery is suicide.
5. **Sleep disabled.** `pmset -a sleep 0; pmset -a displaysleep 0; caffeinate -d &`.

## Preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# 1. Ollama responds and the six mandate-* models are loaded
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

# 2. Real-call healthcheck (the one that actually proves Ollama serves the models)
START=$(date +%s)
curl -sS --max-time 60 http://localhost:11434/api/generate \
  -d '{"model":"mandate-intake","prompt":"healthcheck","stream":false,"options":{"num_predict":16}}' \
  | python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
assert 'response' in d and d.get('done'), f'healthcheck malformed: {d}'
print(f'healthcheck response[:60]: {d[\"response\"][:60]!r}')
" || { echo "HALT: healthcheck failed"; exit 1; }
echo "healthcheck completed in $(($(date +%s) - START))s"

# 3. The 9000 records are on disk and the 300 MP holdout are confirmed contaminated
python3 - <<'PY'
import json, glob
mp_main = sorted(glob.glob('07_system_outputs/mandate_primary/*.json'))
mp_holdout = sorted(glob.glob('07_system_outputs/mandate_primary/holdout/*.json'))
assert len(mp_main) == 1200, f'expected 1200 MP main, got {len(mp_main)}'
assert len(mp_holdout) == 300, f'expected 300 MP holdout, got {len(mp_holdout)}'

# Verify the 300 holdout records carry the Ollama-crash contamination signature
contam = 0
for f in mp_holdout:
    r = json.load(open(f))
    rts = r.get('role_timings') or []
    if rts and all(t.get('llm_fallback') for t in rts):
        contam += 1
assert contam == 300, f'expected all 300 contaminated, got {contam}'
print(f'confirmed: 300/300 MP holdout records contaminated')

# Verify MP main is clean
mp_main_contam = 0
for f in mp_main:
    r = json.load(open(f))
    rts = r.get('role_timings') or []
    if rts and all(t.get('llm_fallback') for t in rts):
        mp_main_contam += 1
assert mp_main_contam == 0, f'unexpected: {mp_main_contam} MP main records contaminated'
print(f'confirmed: 1200/1200 MP main clean (none contaminated)')
PY

# 4. AEGIS-eval still at v1 baseline
grep "mandate-eval-primary-2026q2-v1" AEGIS-eval/_AEGIS_EVAL_README.txt >/dev/null \
  || { echo "HALT: AEGIS-eval contaminated"; exit 1; }
grep -q "llm_refused_with_error" AEGIS-eval/src/mandate/roles/binding.py \
  && { echo "HALT: v2 patch contamination in binding.py"; exit 1; }
echo "AEGIS-eval at v1 baseline"

# 5. outputs_freeze_v1 present; outputs_freeze_v1_1 absent
git tag --list | grep -E "^outputs_freeze_v1$" >/dev/null \
  || { echo "HALT: outputs_freeze_v1 missing"; exit 1; }
git tag --list | grep -E "^outputs_freeze_v1_1$" \
  && { echo "HALT: outputs_freeze_v1_1 already exists"; exit 1; }
echo "outputs_freeze_v1 present, outputs_freeze_v1_1 ready to cut"
```

**Success criteria.** All five preconditions print confirmation.

## Decision boundary

You may decide:
- Whether to commit incrementally every ~100 hold-out records.
- One Ollama-side retry on a transient connection error per task. Halt immediately on a second consecutive Connection-refused.

You must escalate:
- ANY new MP hold-out record with `all roles llm_fallback=True`. That is the contamination signature; do not commit such records to the canonical output dir, quarantine and stop.
- A second Ollama crash during the re-run.
- Healthcheck duration above 60s.

You may NOT treat as a halt (Phase 6 data):
- `any_llm_fallback=True` on individual records where at least ONE role has `llm_fallback=False`. That's a legitimate Binding refusal or single-role fallback, valuable hold-out signal.
- `schema_valid=False` on any record.

You may not:
- Modify AEGIS-eval tree.
- Modify ground truth.
- Re-run the 1200 MP main matrix or the 7500 API-bound baselines (those are clean).
- Move or delete `outputs_freeze_v1` (it stays as historical record).

---

## Task 1: Quarantine the 300 contaminated MP hold-out records

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

QUAR="/tmp/handoff_26_contaminated_quarantine_$(date +%Y%m%d-%H%M%S)"
mkdir -p "$QUAR"

# Move the contaminated records (and the holdout ledger) to quarantine
mv 07_system_outputs/mandate_primary/holdout/*.json "$QUAR/"
[ -f 07_system_outputs/mandate_primary/holdout/ledger.jsonl ] && \
  mv 07_system_outputs/mandate_primary/holdout/ledger.jsonl "$QUAR/"

echo "quarantined to: $QUAR"
ls -1 "$QUAR" | head -5
echo "...  total: $(ls -1 "$QUAR" | wc -l) files"

# Confirm the canonical holdout dir is empty
n=$(ls 07_system_outputs/mandate_primary/holdout/*.json 2>/dev/null | wc -l)
[ "$n" -eq 0 ] || { echo "HALT: $n files remain in canonical dir"; exit 1; }
echo "canonical 07_system_outputs/mandate_primary/holdout/ is empty"
```

**Success criteria.** 300 records (plus ledger.jsonl if present) in the quarantine dir; canonical hold-out dir empty.

## Task 2: Re-run MP hold-out fresh

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

python3 -m apparatus.run run-system \
  --system mandate_primary \
  --aegis ./AEGIS-eval \
  --ollama-mode \
  --code-ref mandate-eval-primary-2026q2-v1 \
  --tasks 04_ground_truth/holdout_tasks.jsonl \
  --runs 10 \
  --output 07_system_outputs/mandate_primary/holdout \
  --seed-base 20260605
```

**Wall clock estimate.** 300 runs × ~370s = ~31 hours.

**No --skip-existing** — we just quarantined everything, so nothing exists to skip. The seed-base 20260605 matches the original to preserve reproducibility against the same task IDs.

**Success criteria.** 300 fresh records in `07_system_outputs/mandate_primary/holdout/`. Apply the contamination watchdog after every ~50 records (Task 3 below).

## Task 3: Watchdog after each ~50 records committed

```zsh
python3 - <<'PY'
import json, glob, sys
n = 0
contamination = []
fast_legit = []
for f in glob.glob('07_system_outputs/mandate_primary/holdout/*.json'):
    n += 1
    r = json.load(open(f))
    rts = r.get('role_timings') or []
    wc = r.get('wall_clock_ms') or 0
    if rts and all(t.get('llm_fallback') for t in rts):
        contamination.append((f, wc))
    elif wc < 60_000:
        fast_legit.append((f, wc, r.get('task_id')))

print(f"records: {n}")
print(f"contamination (all roles llm_fallback=True): {len(contamination)}")
print(f"fast legitimate (single-role failure): {len(fast_legit)}")
if contamination:
    print("HALT: contamination detected. Sample:")
    for f, wc in contamination[:5]: print(f"  {f}: {wc}ms")
    sys.exit(1)
print("OK: no Ollama-crash contamination")
PY
```

**Success criteria at each checkpoint.** No contamination. Continue.

**On HALT.** Stop, do not auto-restart. Investigate Ollama state.

## Task 4: Re-anonymize the corrected output tree

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

# Remove the contaminated anonymization mapping and output tree
rm -f 07_system_outputs/anonymization_mapping.json
rm -rf 08_grading/anonymized_outputs

# Re-anonymize with a fresh seed reflecting the regeneration
python3 -m apparatus.run anonymize \
  --in 07_system_outputs \
  --out 08_grading/anonymized_outputs \
  --mapping-path 07_system_outputs/anonymization_mapping.json \
  --seed 20260613
```

**Success criteria.** `08_grading/anonymized_outputs/` carries 9000 records. `anonymization_mapping.json` lists every system→token mapping (gitignored).

## Task 5: Cut outputs_freeze_v1_1

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

git add 07_system_outputs/ 08_grading/anonymized_outputs/

git tag --list | grep -E "^outputs_freeze_v1_1$" \
  && { echo "HALT: outputs_freeze_v1_1 already exists"; exit 1; }

git commit -m "Phase 6 hold-out contamination corrected

HANDOFF_26. Replaces the 300 contaminated MP hold-out records produced
by HANDOFF_11b-ii Task 2 (every role fell back due to Ollama Connection
refused; wall_clock ~2s vs expected ~370s). Re-ran fresh against
restarted Ollama with refined contamination watchdog
(all_roles_llm_fallback=True signature).

outputs_freeze_v1 left in place as historical record. The 1200 MP main
matrix and 7500 API-bound baselines were not regenerated."

git tag -a outputs_freeze_v1_1 -m "Phase 6 main matrix + corrected hold-out outputs frozen

Supersedes outputs_freeze_v1 for analysis purposes. The 300 MP hold-out
records under outputs_freeze_v1 were contaminated by an Ollama outage
in HANDOFF_11b-ii; HANDOFF_26 quarantined them and produced 300 clean
hold-out records.

Same 9000-record matrix as v1; 300 records differ (MP hold-out only).
B1-B6 main, B1 hold-out, and MP main matrix are byte-identical to v1."

git log --oneline -3
git tag --list "outputs_freeze*"
```

**Success criteria.** Tag `outputs_freeze_v1_1` exists. `outputs_freeze_v1` is unchanged at its original commit.

## Report

`handoffs/HANDOFF_26_report_<YYYY-MM-DD>.md` with:
- Quarantine path
- New MP hold-out record count (target: 300)
- Watchdog trigger count (target: 0)
- Per-domain breakdown of the new hold-out records (Intake failure rate, Binding refusal rate, COA count, Interpreter mode, Validator gap-flag rate — same Task 4 of HANDOFF_25 shape)
- Re-anonymization output count (target: 9000)
- outputs_freeze_v1_1 tag hash
- Confirmation outputs_freeze_v1 unchanged
- PROCEED verdict

Commit message: `Handoff 26: regenerate 300 MP hold-out + re-anonymize + outputs_freeze_v1_1 (HANDOFF_11b-ii contamination corrected)`.

## What 26 unblocks

After 26 PROCEED, the deposit-ready Phase 6 state is `outputs_freeze_v1_1`. HANDOFF_13 (three-judge grading on anonymized outputs) reads from `08_grading/anonymized_outputs/` and is the next big handoff. The contaminated `outputs_freeze_v1` remains in the git log as the historical record of the contamination event, citable from DEVIATIONS.md.
