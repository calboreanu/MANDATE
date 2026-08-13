# Codex Handoff 09: Main Corpus Anchor Scaffolds (PROMPTS Section 2)

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-03 (preconditions updated 2026-06-04 after HANDOFF_19b + DEVIATIONS.md SME-skip pivot)
**Estimated wall clock:** 15 to 25 minutes (120 Anthropic calls).
**Blocked on:** `corpus_freeze_v1` tag present (cut by HANDOFF_19b 2026-06-04).

---

## Mission

Produce a candidate anchor for each of the 120 selected main-corpus tasks by running PROMPTS Section 2 anchor scaffolding through Claude Opus 4.6. Under the SME-skip deviation recorded in `00_preregistration/DEVIATIONS.md` 2026-06-04, this scaffold output IS the ground truth for the formal Phase 6 study, not a draft for SME review. The scaffolder runs at the patched apparatus settings (default `max_tokens=4096` after HANDOFF_06b/c).

**Definition of done.** 120 scaffolded-anchor records in `04_ground_truth/main_scaffolds/anchor_scaffolds.jsonl`, each `parse_ok: true`, with the PROMPTS Section 2 schema (mission_intent, minimum, target, constraints, suspected_gaps), tagged with the PI-assigned task_id, source request_text, and the raw_json field for diagnosis. One handoff report.

## Preconditions

Confirm each:

- `03_corpus/main/main_selection.json` exists with `selected` of length exactly 120, 40 per domain.
- `03_corpus/main/candidates_main.jsonl` exists (the 262-candidate pool the selection resolves against).
- `corpus_freeze_v1` tag exists in the project git repo (cut by HANDOFF_19b after selections were materialized to `04_ground_truth/`). SME realism audit was lifted per `00_preregistration/DEVIATIONS.md` 2026-06-04; the freeze gate is now selection-materialization complete, not SME-accept.
- Apparatus scaffolder patched (HANDOFF_06c precondition; reproduces here): `apparatus.corpus.scaffolder.AnchorScaffolder.__init__` default `max_tokens=4096` and `ScaffoldedAnchor.to_dict` includes `raw_json`.
- `ANTHROPIC_API_KEY` is in `.env`; balance comfortably above $20 (120 Opus 4.6 calls at ~$0.10 each is roughly $12).

## Decision boundary

You may decide:
- Output paths under `04_ground_truth/main_scaffolds/`.
- A single retry on a transient Anthropic API error per task.

You must escalate:
- A scaffold that does not parse as JSON twice in a row on the same task.
- A selection file shape error (not 120 entries, not 40 per domain, task_id missing).
- A persistent Anthropic auth or rate-limit error.

You may not:
- Change a task's request_text after loading.
- Edit a scaffold after generation. The SMEs revise; you do not.
- Decide ground truth.

---

## Task 1: Confirm preconditions and load the selection

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate
python3 -c "
import json, os, collections
from apparatus.corpus.cli import _load_dotenv
_load_dotenv()
assert os.environ.get('ANTHROPIC_API_KEY','').startswith('sk-ant'), 'key missing'
sel = json.load(open('03_corpus/main/main_selection.json'))
chosen = sel['selected']
assert len(chosen) == 120, f'expected 120 selections, got {len(chosen)}'
by_dom = collections.Counter(c['domain'] for c in chosen)
assert sorted(by_dom.values()) == [40, 40, 40], f'must be 40 per domain, got {by_dom}'
for c in chosen:
    assert c.get('task_id'), 'every selection needs a task_id'
print('selection OK:', dict(by_dom))
"
git -C "$PWD" tag -l corpus_freeze_v1 | grep -q corpus_freeze_v1 && \
  echo "corpus_freeze_v1 tag present" || \
  { echo "corpus_freeze_v1 NOT tagged; halt"; exit 2; }
```

**Success criteria.** Selection prints OK; corpus_freeze_v1 tag present.

## Task 2: Build the resolved tasks file

```zsh
mkdir -p 04_ground_truth/main_scaffolds
python3 -c "
import json
sel = json.load(open('03_corpus/main/main_selection.json'))
cands = [json.loads(l) for l in open(
    '03_corpus/main/candidates_main.jsonl')]
out = []
for s in sel['selected']:
    match = [c for c in cands
             if c['domain'] == s['domain']
             and c.get('category') == s['category']
             and c['candidate_idx'] == s['candidate_idx']]
    assert len(match) == 1, f'no unique match for {s}'
    c = match[0]
    out.append({'task_id': s['task_id'], 'text': c['text'],
                'domain': c['domain'], 'category': c['category'],
                'source_candidate_idx': c['candidate_idx'],
                'derived_from': c.get('derived_from', {})})
with open('04_ground_truth/main_scaffolds/main_tasks_resolved.jsonl',
          'w') as f:
    for r in out:
        f.write(json.dumps(r, ensure_ascii=False)+'\n')
print('wrote', len(out), 'resolved main tasks')
"
```

**Success criteria.** `main_tasks_resolved.jsonl` has 120 lines, each with `task_id`, `text`, `domain`, `category`, `derived_from`.

## Task 3: Run PROMPTS Section 2 anchor scaffolding

```zsh
python3 -m apparatus.corpus.cli scaffold \
  --tasks 04_ground_truth/main_scaffolds/main_tasks_resolved.jsonl \
  --out 04_ground_truth/main_scaffolds \
  --max-tokens 4096
```

**Success criteria.** `04_ground_truth/main_scaffolds/anchor_scaffolds.jsonl` has 120 lines, every record `parse_ok: true`, `source_model: claude-opus-4-6`. The patched scaffolder now also writes `raw_json` on every record (HANDOFF_06c).

**On parse failure.** A handful of failures across 120 tasks is acceptable; report the count and bump `--max-tokens 8192` for the failed subset by re-resolving only those task_ids into a smaller JSONL and re-running the scaffold against it. A persistent parse failure on the same task with `max_tokens=8192` means the model produced prose; record `raw_json` head and tail in the report and stop.

## Task 4: Merge derived_from into each scaffold for SME review

```zsh
python3 -c "
import json
scaffs = [json.loads(l) for l in open(
    '04_ground_truth/main_scaffolds/anchor_scaffolds.jsonl')]
resolved = {r['task_id']: r for r in (json.loads(l) for l in open(
    '04_ground_truth/main_scaffolds/main_tasks_resolved.jsonl'))}
out = []
for s in scaffs:
    r = resolved.get(s['task_id'], {})
    s['derived_from'] = r.get('derived_from', {})
    out.append(s)
with open('04_ground_truth/main_scaffolds/anchor_scaffolds.jsonl',
          'w') as f:
    for s in out:
        f.write(json.dumps(s, ensure_ascii=False, default=str)+'\n')
print('merged derived_from into', len(out), 'scaffolds')
"
```

## Task 5: Sanity (120 unique task ids, scaffolds parse, derived_from attached)

```zsh
python3 -c "
import json
rows = [json.loads(l) for l in open(
    '04_ground_truth/main_scaffolds/anchor_scaffolds.jsonl')]
ids = [r['task_id'] for r in rows]
assert len(ids) == 120
assert len(set(ids)) == 120, f'duplicate task ids'
parsed = sum(1 for r in rows if r['parse_ok'])
with_d = sum(1 for r in rows if r.get('derived_from', {}).get('reference_id'))
print('scaffolds:', len(rows), 'parsed_ok:', parsed,
      'with derived_from:', with_d)
assert parsed == 120 and with_d == 120
"
```

---

## Final report

`handoffs/HANDOFF_09_report_<YYYY-MM-DD>.md`:

```markdown
# Handoff 09 Report: Main Anchor Scaffolds

**Codex session:** <id>
**Eval host:** <hostname>
**Date:** <YYYY-MM-DD>
**Wall clock:** <minutes>

## Verdict

PROCEED | HALT (one word)

## Evidence

- main_selection.json shape OK:        yes | no
- corpus_freeze_v1 tag present:        yes | no
- resolved main tasks:                 <n>/120
- scaffolds produced:                  <n>/120
- scaffolds parsed_ok:                 <n>/120
- scaffolds with derived_from:         <n>/120
- Anthropic model used:                claude-opus-4-6
- Anthropic input tokens (total):      <n>
- Anthropic output tokens (total):     <n>
- estimated API cost (USD):            $<x.xx>

## Anything the PI must decide before proceeding

- circulate the 120 scaffolds to the SMEs for the independent-then-review
  ground-truth workflow (FORMS Section 1)
- the SME IRR overlap is the 12-task subset; the external spot-check is
  the 24-task stratified subset (PROTOCOL_LOCK Section 8)

## Deviations from this handoff

<short list, empty if none>
```

Commit the resolved tasks file, the scaffolds, and the handoff report in a single commit with message `Handoff 09: main anchor scaffolds for SME review (120 tasks)`.
