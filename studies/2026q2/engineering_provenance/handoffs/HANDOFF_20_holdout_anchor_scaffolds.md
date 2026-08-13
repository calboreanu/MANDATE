# Codex Handoff 20: Hold-out Anchor Scaffolds (PROMPTS Section 2, software_engineering_specification)

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-04
**Estimated wall clock:** 5 to 10 minutes (30 Anthropic Opus 4.6 calls; ~$3-4).
**Blocked on:** `corpus_freeze_v1` tag present; HANDOFF_06c PROCEED confirms the patched scaffolder is on disk.

---

## Mission

Same shape as HANDOFF_06c (pilot) and HANDOFF_09 (main), scaled to the 30 hold-out tasks in the 4th domain `software_engineering_specification`. Under the SME-skip deviation (`00_preregistration/DEVIATIONS.md` 2026-06-04), the scaffolds produced here are the hold-out ground truth for Phase 6 grading, not drafts for SME review.

**Definition of done.** 30 scaffolded-anchor records in `04_ground_truth/holdout_scaffolds/anchor_scaffolds.jsonl`, every record `parse_ok: true`, with the PROMPTS Section 2 schema, the PI-assigned task_id, source request_text, and raw_json. One handoff report.

## Preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# Selection + pool present
python3 - <<'PY'
import json, collections
sel = json.load(open('03_corpus/holdout/holdout_selection.json'))
chosen = sel['selected']
assert len(chosen) == 30, f'expected 30 selections, got {len(chosen)}'
by_dom = collections.Counter(c['domain'] for c in chosen)
assert by_dom == {'software_engineering_specification': 30}, f'all 30 must be software_engineering_specification, got {by_dom}'
for c in chosen:
    assert c.get('task_id'), 'every selection needs task_id'
    assert isinstance(c.get('candidate_idx'), int), 'candidate_idx must be int'
    assert c.get('category'), 'every selection needs category for the (domain, category, candidate_idx) resolver'
print('selection OK: 30 holdout tasks in software_engineering_specification')
PY

# corpus_freeze_v1 tag present
git tag --list | grep -E "^corpus_freeze_v1$" >/dev/null \
  || { echo "corpus_freeze_v1 missing"; exit 1; }

# Patched scaffolder present
python3 -c "
from apparatus.corpus.scaffolder import AnchorScaffolder, ScaffoldedAnchor
import inspect
sig = inspect.signature(AnchorScaffolder.__init__)
assert sig.parameters['max_tokens'].default == 4096, 'scaffolder not patched'
assert 'raw_json' in ScaffoldedAnchor(task_id='x', request_text='y').to_dict()
print('patched scaffolder present')
"

# Anthropic key
python3 -c "
import os
from pathlib import Path
for line in Path('.env').read_text().splitlines():
    if '=' in line:
        k, v = line.split('=', 1); os.environ[k] = v
assert os.environ.get('ANTHROPIC_API_KEY','').startswith('sk-ant')
print('Anthropic key set')
"
```

**Success criteria.** Selection OK with 30 tasks all in `software_engineering_specification`; freeze tag present; patched scaffolder present; Anthropic key set.

## Decision boundary

You may decide:
- A single retry on a transient Anthropic API rate-limit error per task.
- Bumping `--max-tokens 8192` for any subset of tasks that fail with the 4096 default.

You must escalate:
- More than 3 of 30 scaffolds with `parse_ok: false` after the retry. Include the raw_json head/tail for each failing record.
- Persistent Anthropic auth failures.

You may not:
- Modify the PROMPTS Section 2 prompt body.
- Modify the JSON parser.
- Skip raw_json capture on failure.

---

## Task 1: Resolve the 30 hold-out selections against the candidate pool

```zsh
mkdir -p 04_ground_truth/holdout_scaffolds

python3 - <<'PY'
import json
sel = json.load(open('03_corpus/holdout/holdout_selection.json'))
cands = [json.loads(l) for l in open(
    '03_corpus/holdout/candidates_holdout.jsonl')]
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
        'derived_from': c.get('derived_from', {}),
    })
with open('04_ground_truth/holdout_scaffolds/holdout_tasks_resolved.jsonl', 'w') as f:
    for r in out:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
print(f'wrote {len(out)} resolved holdout tasks')
assert len(out) == 30
PY
```

**Success criteria.** `04_ground_truth/holdout_scaffolds/holdout_tasks_resolved.jsonl` has 30 lines.

## Task 2: Run PROMPTS Section 2 anchor scaffolding

```zsh
python3 -m apparatus.corpus.cli scaffold \
  --tasks 04_ground_truth/holdout_scaffolds/holdout_tasks_resolved.jsonl \
  --out 04_ground_truth/holdout_scaffolds \
  --max-tokens 4096
```

**Success criteria.** `04_ground_truth/holdout_scaffolds/anchor_scaffolds.jsonl` has 30 lines, every record `parse_ok: true`.

## Task 3: Merge derived_from into each scaffold

```zsh
python3 - <<'PY'
import json
scaffs = [json.loads(l) for l in open(
    '04_ground_truth/holdout_scaffolds/anchor_scaffolds.jsonl')]
resolved = {r['task_id']: r for r in (json.loads(l) for l in open(
    '04_ground_truth/holdout_scaffolds/holdout_tasks_resolved.jsonl'))}
out = []
for s in scaffs:
    r = resolved.get(s['task_id'], {})
    s['derived_from'] = r.get('derived_from', {})
    out.append(s)
with open('04_ground_truth/holdout_scaffolds/anchor_scaffolds.jsonl', 'w') as f:
    for s in out:
        f.write(json.dumps(s, ensure_ascii=False, default=str) + '\n')
print(f'merged derived_from into {len(out)} scaffolds')
PY
```

## Task 4: Sanity

```zsh
python3 - <<'PY'
import json, collections
rows = [json.loads(l) for l in open(
    '04_ground_truth/holdout_scaffolds/anchor_scaffolds.jsonl')]
assert len(rows) == 30
ids = [r['task_id'] for r in rows]
assert len(set(ids)) == 30, 'duplicate task_ids in scaffolds'
parsed = sum(1 for r in rows if r.get('parse_ok'))
print(f'30 holdout scaffolds, {parsed} parse_ok, {len(set(ids))} unique task_ids')
# Source distribution sanity
srcs = collections.Counter(r.get('derived_from',{}).get('name','?') for r in rows)
for s, n in srcs.most_common():
    print(f'  {n:3d} from {s}')
PY
```

## Report

`handoffs/HANDOFF_20_report_<YYYY-MM-DD>.md` with:
- 30 scaffold records produced
- parse_ok rate (target: 30/30)
- Source distribution sanity (expected: 21 NIST 800-160 + 5 NIST 800-64 + 4 NIST 800-218)
- Anthropic cost
- Any failing raw_json head/tail
- PROCEED verdict

Commit message: `Handoff 20: hold-out anchor scaffolds (software_engineering_specification, 30 tasks)`.
