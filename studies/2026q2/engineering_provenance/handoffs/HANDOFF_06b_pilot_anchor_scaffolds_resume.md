# Codex Handoff 06b: Pilot anchor scaffolds, resume with corrected resolver

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-04
**Estimated wall clock:** 5 to 15 minutes (six Anthropic Opus 4.6 calls).
**Blocked on:** None. HANDOFF_06 halted cleanly on a resolver bug in my handoff body, not in the data.

---

## Why this exists

HANDOFF_06 Task 2 resolves each selection entry against `candidates_with_sources.jsonl` by `(domain, candidate_idx)`. Codex correctly halted because that pair is not unique: the source-conditioned generator restarts `candidate_idx` at 1 per `(domain, category)` cell, so a domain's `full_specification` candidate 1 and its `gap_triggering` candidate 1 collide. Both `pilot_selection.json` and the upcoming `holdout_selection.json` carry `category` on every entry, so the fix is to add `category` to the resolver match.

The selection files themselves are correct — `03_corpus/pilot/pilot_selection.json` (6 entries) and `03_corpus/holdout/holdout_selection.json` (30 entries) both include `category` on every record. This handoff replays HANDOFF_06 with the resolver corrected to use `(domain, category, candidate_idx)`.

**Definition of done.** Same as HANDOFF_06: six scaffolded-anchor records in `04_ground_truth/pilot_scaffolds/anchor_scaffolds.jsonl`, each parseable JSON with the PROMPTS Section 2 schema. One handoff report.

## Preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

python3 - <<'PY'
import json, collections
sel = json.load(open('03_corpus/pilot/pilot_selection.json'))
chosen = sel['selected']
assert len(chosen) == 6, f'expected 6 selections, got {len(chosen)}'
by_dom = collections.Counter(c['domain'] for c in chosen)
assert sorted(by_dom.values()) == [2,2,2], f'must be 2 per domain, got {by_dom}'
for c in chosen:
    assert c.get('task_id'), 'every selection needs a task_id'
    assert isinstance(c.get('candidate_idx'), int), 'candidate_idx must be int'
    assert c.get('category'), 'every selection needs category for the corrected resolver'
print('selection OK:', dict(by_dom))
PY
```

**Success criteria.** Selection prints OK with 2-per-domain split and every entry carrying `category`.

## Task 1: Build the tasks file with the corrected resolver

Identical to HANDOFF_06 Task 2 except the match condition adds `category`.

```zsh
mkdir -p 04_ground_truth/pilot_scaffolds

python3 - <<'PY'
import json
sel = json.load(open('03_corpus/pilot/pilot_selection.json'))
cands = [json.loads(l) for l in open(
    '03_corpus/pilot/candidates_with_sources.jsonl')]
out = []
for s in sel['selected']:
    match = [c for c in cands
             if c['domain'] == s['domain']
             and c.get('category') == s['category']
             and c['candidate_idx'] == s['candidate_idx']]
    assert len(match) == 1, f'no unique match for {s}'
    c = match[0]
    out.append({
        'task_id': s['task_id'],
        'text': c['text'],
        'domain': c['domain'],
        'category': c['category'],
        'source_candidate_idx': c['candidate_idx'],
        'source_documents': c.get('source_documents', []),
    })
with open('04_ground_truth/pilot_scaffolds/pilot_tasks_resolved.jsonl', 'w') as f:
    for r in out:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
print('wrote', len(out), 'resolved pilot tasks')
print('source_documents per task:', [len(r['source_documents']) for r in out])
PY
```

**Success criteria.** `04_ground_truth/pilot_scaffolds/pilot_tasks_resolved.jsonl` has six lines, each with `task_id`, `text`, `domain`, `category`, `source_documents`. No `no unique match` assertion fires.

## Task 2: Run PROMPTS Section 2 anchor scaffolding

Same as HANDOFF_06 Task 3.

```zsh
python3 -m apparatus.corpus.cli scaffold \
  --tasks 04_ground_truth/pilot_scaffolds/pilot_tasks_resolved.jsonl \
  --out 04_ground_truth/pilot_scaffolds
```

**Success criteria.** `04_ground_truth/pilot_scaffolds/anchor_scaffolds.jsonl` has six lines. Each line is a JSON object with `task_id`, `request_text`, `mission_intent` (non-empty), `minimum`, `target`, `constraints`, `suspected_gaps`, `source_model` of `claude-opus-4-6`, `parse_ok: true`.

## Task 3: Merge source_documents into each scaffold

Same as HANDOFF_06 Task 4.

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
print('merged source_documents into', len(out), 'scaffolds')
PY
```

## Decision boundary

Same as HANDOFF_06.

## Notes for downstream handoffs

The same `(domain, category, candidate_idx)` resolver pattern must be used in:

- HANDOFF_09 main anchor scaffolds (120 tasks) — when this fires, its Task 2 resolver should match on `(domain, category, candidate_idx)` against `03_corpus/main/candidates_main.jsonl`.
- The hold-out scaffold handoff when it gets written.

I will note this in HANDOFF_09 before sending it to Codex. The selection files (`main_selection.json`, `holdout_selection.json`, `pilot_selection.json`) already carry `category`, so the change is resolver-side only.

## Report

`handoffs/HANDOFF_06b_report_<YYYY-MM-DD>.md` with:
- six scaffold records produced
- per-task `parse_ok` boolean
- per-task `mission_intent` first 80 chars (sanity that the scaffolds are substantive)
- Anthropic cost
- PROCEED verdict

Commit message: `Handoff 06b: pilot anchor scaffolds, resume with corrected (domain, category, candidate_idx) resolver`.
