# Codex Handoff 06c: Pilot anchor scaffolds, resume with patched scaffolder

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-04
**Estimated wall clock:** 5 to 15 minutes (six Anthropic Opus 4.6 calls; ~$1).
**Blocked on:** None. HANDOFF_06b halted with 0/6 parse_ok; the apparatus side has been patched on project main before this handoff.

---

## Why this exists

HANDOFF_06b produced 6 scaffold records but every one failed JSON parsing with `unbalanced JSON object in model output`. Root cause: `AnchorScaffolder.__init__` hard-coded `max_tokens=2048` and the CLI did not expose an override. Opus 4.6 on real source-grounded pilot tasks hits the 2048 ceiling mid-JSON, leaving an unclosed brace that `extract_json` then reports as unbalanced. The `raw_json` field was also dropped from `to_dict`, so the 06b artifact carries empty raw responses that prevented downstream diagnosis.

Three apparatus patches landed on project main:

1. `apparatus/corpus/scaffolder.py`: default `max_tokens` bumped 2048 → 4096; `to_dict` now includes `raw_json` for diagnosis on failure.
2. `apparatus/corpus/cli.py` scaffold subparser: new `--max-tokens` (default 4096) and `--temperature` (default 0.0) flags; `cmd_scaffold` plumbs them through.
3. `apparatus/corpus/tests/test_cli.py`: two pre-existing test assertions updated to cover all four corpus domains (HANDOFF_08 DOMAIN_GUIDANCE expansion fallout); 73 / 73 passing after the change.

**Definition of done.** Same as HANDOFF_06b: six scaffold records at `04_ground_truth/pilot_scaffolds/anchor_scaffolds.jsonl`, every record carrying `parse_ok: true` and a complete PROMPTS Section 2 anchor structure. One handoff report.

## Preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# Patches present
python3 -c "
from apparatus.corpus.scaffolder import AnchorScaffolder, ScaffoldedAnchor
import inspect
sig = inspect.signature(AnchorScaffolder.__init__)
assert sig.parameters['max_tokens'].default == 4096, 'scaffolder max_tokens default not bumped'
d = ScaffoldedAnchor(task_id='x', request_text='y').to_dict()
assert 'raw_json' in d, 'to_dict missing raw_json field'
print('scaffolder patches present')
"

python3 -m apparatus.corpus.cli scaffold --help 2>&1 | grep -E "max-tokens|temperature" \
  || { echo "scaffold CLI flags missing"; exit 1; }
echo "CLI flags present"

# Resolved pilot tasks file from HANDOFF_06b is still on disk (6 tasks)
test -f 04_ground_truth/pilot_scaffolds/pilot_tasks_resolved.jsonl \
  || { echo "pilot_tasks_resolved.jsonl missing — re-run HANDOFF_06b Task 1 first"; exit 1; }
N=$(wc -l < 04_ground_truth/pilot_scaffolds/pilot_tasks_resolved.jsonl)
[ "$N" -eq 6 ] || { echo "expected 6 resolved tasks, got $N"; exit 1; }

# Anthropic key
python3 -c "
import os
from pathlib import Path
for line in Path('.env').read_text().splitlines():
    if '=' in line:
        k, v = line.split('=', 1); os.environ[k] = v
assert os.environ.get('ANTHROPIC_API_KEY','').startswith('sk-ant'), 'Anthropic key missing'
print('Anthropic key set')
"
```

**Success criteria.** All three checks print confirmation. The HANDOFF_06b `pilot_tasks_resolved.jsonl` file is reused — Tasks 1 of 06b already resolved the selection correctly.

## Decision boundary

You may decide:
- A single retry on a transient Anthropic API rate-limit error per task.

You must escalate (the failure mode that triggered 06b):
- More than two of six scaffolds with `parse_ok: false` after the retry. The raw response is now captured in `raw_json` on every record; include the first 600 chars of the longest failing response in the report so we can see exactly where the model truncates if it still does.
- Persistent Anthropic auth failures.

You may not:
- Modify the PROMPTS Section 2 prompt body. The prompt is locked.
- Modify the JSON parser. `extract_json` was traced and is correct.
- Skip the `raw_json` capture on failure.

## Tasks

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# Reuse the resolved pilot tasks file from HANDOFF_06b (6 tasks already on disk).
# Re-run scaffolding with the patched scaffolder. Default --max-tokens is now
# 4096; if a scaffold still truncates we can bump to 8192 from the flag.
python3 -m apparatus.corpus.cli scaffold \
  --tasks 04_ground_truth/pilot_scaffolds/pilot_tasks_resolved.jsonl \
  --out 04_ground_truth/pilot_scaffolds \
  --max-tokens 4096

# Inspect parse_ok rates and show any failing raw_json head
python3 - <<'PY'
import json
recs = [json.loads(l) for l in open(
    "04_ground_truth/pilot_scaffolds/anchor_scaffolds.jsonl")]
ok = sum(1 for r in recs if r.get("parse_ok"))
print(f"scaffolds: {len(recs)}  parse_ok: {ok}/{len(recs)}")
for r in recs:
    tid = r.get("task_id")
    if r.get("parse_ok"):
        mi = (r.get("mission_intent") or "")[:80]
        print(f"  OK  {tid}: mission_intent[:80] = {mi!r}")
    else:
        raw = (r.get("raw_json") or "")
        print(f"  FAIL {tid}: error = {r.get('error','')[:140]!r}")
        print(f"        raw_json length: {len(raw)}")
        print(f"        raw_json head: {raw[:300]!r}")
        print(f"        raw_json tail: {raw[-200:]!r}")
PY
```

**Success criteria.** `parse_ok: 6/6`. If any failures occur, the report carries the raw_json head/tail for each so we can decide whether to bump `--max-tokens` to 8192 or escalate to a prompt-side issue.

## Task 2: Merge source_documents into the scaffolds

Identical to HANDOFF_06 Task 4.

```zsh
python3 - <<'PY'
import json
scaffs = [json.loads(l) for l in open(
    '04_ground_truth/pilot_scaffolds/anchor_scaffolds.jsonl')]
resolved = {r['task_id']: r for r in (json.loads(l) for l in open(
    '04_ground_truth/pilot_scaffolds/pilot_tasks_resolved.jsonl'))}
out = []
for s in scaffs:
    r = resolved.get(s['task_id'], {})
    s['source_documents'] = r.get('source_documents', [])
    out.append(s)
with open('04_ground_truth/pilot_scaffolds/anchor_scaffolds.jsonl', 'w') as f:
    for s in out:
        f.write(json.dumps(s, ensure_ascii=False) + '\n')
print(f'merged source_documents into {len(out)} scaffolds')
PY
```

## Report

`handoffs/HANDOFF_06c_report_<YYYY-MM-DD>.md` with:
- 6 scaffold records total
- parse_ok rate (target: 6/6)
- Per-task first-80-chars of `mission_intent` (sanity that the scaffolds are substantive)
- Anthropic cost
- If any failure: raw_json head/tail for each failing record
- PROCEED verdict

Commit message: `Handoff 06c: pilot anchor scaffolds, resume with patched scaffolder (max_tokens default 4096 + raw_json capture)`.
