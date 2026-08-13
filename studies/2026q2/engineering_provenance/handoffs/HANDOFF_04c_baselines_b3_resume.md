# Codex Handoff 04c: Finish B3 calibration with corrected escalation rule

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-04
**Estimated wall clock:** 15 to 25 minutes (six calibration tasks × one baseline × one run).
**Blocked on:** None. HANDOFF_04b reported a HALT on B3 due to a too-strict escalation rule in my handoff body. Codex applied the rule correctly; the rule was wrong.

---

## Why this exists

HANDOFF_04b's escalation gate read: *"Any baseline emitting `ok=False` or `schema_valid=False` on more than one of the six tasks."*

That treated `schema_valid=False` as a halt condition. It is not. `schema_valid` is exactly what Phase 6 outcome O4 measures: what fraction of each system's outputs validate against the pre-registered baseline-specification schema. The single-prompt B2 (GPT-4o) producing one bare-number threshold instead of a stringified one, and the ReAct B3 emitting `constraints` as arrays-of-strings or as keyed objects instead of arrays-of-`{predicate, rationale}`, are not apparatus bugs — they are the measured behaviors the formal study is designed to compare against MANDATE-primary's role-decomposed pipeline.

Codex correctly halted B3 at task 3 of 6 to avoid Anthropic spend on what looked like an apparatus-flagged failure mode. With the rule corrected, we want B3 to complete all six calibration tasks so the 18-record matrix is complete, and the schema-validity rates can be recorded as Phase 6 O4 input.

**Definition of done.** `07_system_outputs/baseline_3/` carries six RunRecord JSON files (one per calibration task), every record `ok=True`, schema-validity recorded per record (some will be `False`; that is data, not failure). HANDOFF_04b's B1 (6/6 ok, 6/6 valid) and B2 (6/6 ok, 5/6 valid) artifacts remain as-is. One handoff report.

## Preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

python3 -c "
import os
from pathlib import Path
for line in Path('.env').read_text().splitlines():
    if '=' in line:
        k, v = line.split('=', 1); os.environ[k] = v
assert os.environ.get('ANTHROPIC_API_KEY','').startswith('sk-ant'), 'Anthropic key missing'
print('Anthropic key set')
"

# Confirm 04b B1 and B2 artifacts are present (don't re-run those)
ls 07_system_outputs/baseline_1/*.json 2>/dev/null | wc -l   # expect 6
ls 07_system_outputs/baseline_2/*.json 2>/dev/null | wc -l   # expect 6

# Confirm 04b B3 partial state (3 of 6) — these will be overwritten by re-run
ls 07_system_outputs/baseline_3/*.json 2>/dev/null
```

**Success criteria.** Anthropic key set. B1 has 6 records, B2 has 6 records, B3 has 3 partial records (to be re-overwritten).

## Tasks

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# Re-run B3 from scratch on all six calibration tasks. Re-runs overwrite
# same-id RunRecords harmlessly (HANDOFF_11 resume convention).
python3 -m apparatus.run run-system \
  --system baseline_3 \
  --tasks 02_calibration/tasks \
  --runs 1 \
  --output 07_system_outputs/baseline_3 \
  --seed-base 20260604

python3 - <<'PY'
import json, glob
b = 'baseline_3'
files = sorted(glob.glob(f'07_system_outputs/{b}/*.json'))
rows = [json.load(open(p)) for p in files]
ok = sum(1 for r in rows if r['ok'])
sv = sum(1 for r in rows if (r.get('output') or {}).get('schema_valid'))
cost = sum((r.get('api_cost_usd') or 0) for r in rows)
print(f'{b}: {len(rows)} records, {ok} ok, {sv} schema_valid, ${cost:.4f}')
# Per-task breakdown of schema validity (this is Phase 6 O4 input)
for p in files:
    r = json.load(open(p))
    out = r.get('output') or {}
    tid = r.get('task_id','?')
    print(f"  {tid}: ok={r['ok']}, schema_valid={out.get('schema_valid')}, errors={len(out.get('schema_errors') or [])}")
PY
```

## Decision boundary

You may decide:
- A single retry on a transient Anthropic API rate-limit error per task.

You must escalate (this list is now narrower than 04b's; only real failures halt):
- A baseline emitting `ok=False` on more than one task (system-level failure).
- A persistent Anthropic auth failure that does not clear on one retry.
- Total cost above $5 for B3's six calibration tasks (runaway tokens).

You may **NOT** treat as a halt:
- `schema_valid=False`. This is Phase 6 O4 measurement data, not a failure.
- A B3 output structurally simpler than the schema (array-of-strings, keyed-object-instead-of-array, missing optional fields). That is what ReAct produces; recording it is the point.

You may not:
- Modify the six calibration task files.
- Modify the baseline-specification schema.
- "Fix" the B3 ReAct prompt to coerce JSON-mode enforcement. The pre-registered B3 is the system under test; we measure what it does, we do not improve it post-hoc.

## Report

`handoffs/HANDOFF_04c_report_<YYYY-MM-DD>.md` with:
- B3 final counts: total / ok / schema_valid
- Per-task schema-validity breakdown (six rows, task_id and schema_valid boolean)
- Anthropic cost
- A one-sentence Phase 6 O4 implication line (e.g., "B3 schema-validity rate on this calibration set is X/6; phase 6 will measure this across 120 main tasks.")
- PROCEED verdict (the calibration matrix is complete after this handoff)

Commit message: `Handoff 04c: B3 calibration completion (schema_valid is data, not halt)`.
