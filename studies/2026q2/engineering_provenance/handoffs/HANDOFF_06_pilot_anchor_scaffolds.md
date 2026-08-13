# Codex Handoff 06: Pilot Anchor Scaffolds (PROMPTS Section 2)

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-03
**Estimated wall clock:** 5 to 15 minutes (six Anthropic calls).
**Blocked on:** Handoff 02 PROCEED, the Handoff 02 grounded candidate set `03_corpus/pilot/candidates_with_sources.jsonl` exists, and `03_corpus/pilot/pilot_selection.json` exists at the project root with exactly six PI-selected pilot tasks.

---

## Mission

Produce a candidate anchor for each of the six PI-selected pilot tasks by running PROMPTS Section 2 anchor scaffolding through Claude Opus 4. The output is what the SMEs will review in Phase 3 of the pilot (FORMS Section 1: SME forms independent judgement first, then reads this scaffold). Codex does not produce ground truth here; the SMEs do.

**Definition of done.** Six scaffolded-anchor records in `04_ground_truth/pilot_scaffolds/anchor_scaffolds.jsonl`, each parseable JSON with the PROMPTS Section 2 schema (mission_intent, minimum, target, constraints, suspected_gaps), tagged with the PI-assigned task_id and the source request_text. One handoff report.

## Preconditions

Confirm each:

- Handoff 02 reported PROCEED and `03_corpus/pilot/candidates_with_sources.jsonl` exists (the grounded candidate set; if only `candidates_deduped.jsonl` exists, the Handoff 02 grounding step did not complete and this handoff should not start).
- `03_corpus/pilot/pilot_selection.json` exists, has `selected` of length exactly 6, and contains exactly two entries per domain across all three domains (security_operations_reporting, financial_reporting, intelligence_collection_tasking). Each entry has `domain`, `candidate_idx`, and a non-empty `task_id`.
- `ANTHROPIC_API_KEY` is available (the CLI auto-loads `.env`).

If `pilot_selection.json` is missing or malformed, stop and report; do not select tasks on behalf of the PI.

## Decision boundary

You may decide:
- Output paths under `04_ground_truth/pilot_scaffolds/` and intermediate file names.
- A single retry on a transient Anthropic API error.

You must escalate:
- A scaffold that does not parse as JSON, twice in a row, on the same task. Record the raw response in the report and stop.
- A selection file with the wrong shape (not six entries, not two per domain, missing task_id, candidate_idx not present in `candidates_deduped.jsonl`).

You may not:
- Change a task's request_text after it is loaded from the candidate file.
- Edit a scaffold after generation. The SME revises it; you do not.
- Decide ground truth. The scaffold is a draft, not the answer.

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
sel = json.load(open('03_corpus/pilot/pilot_selection.json'))
chosen = sel['selected']
assert len(chosen) == 6, f'expected 6 selections, got {len(chosen)}'
by_dom = collections.Counter(c['domain'] for c in chosen)
assert sorted(by_dom.values()) == [2,2,2], f'must be 2 per domain, got {by_dom}'
for c in chosen:
    assert c.get('task_id'), 'every selection needs a task_id'
    assert isinstance(c.get('candidate_idx'), int), 'candidate_idx must be int'
print('selection OK:', dict(by_dom))
"
```

**Success criteria.** The script prints `selection OK: {...}` with each domain at 2. Any assertion failure means the selection file does not satisfy the protocol; report and stop.

## Task 2: Build the tasks file from the selection

Resolve each `(domain, candidate_idx)` pair to its candidate from `candidates_with_sources.jsonl` (the grounded set produced after Handoff 02), attach the PI-assigned `task_id`, carry the `source_documents` field through, and write the resolved tasks to a JSONL the scaffolder reads.

```zsh
mkdir -p 04_ground_truth/pilot_scaffolds
python3 -c "
import json
sel = json.load(open('03_corpus/pilot/pilot_selection.json'))
cands = [json.loads(l) for l in open(
    '03_corpus/pilot/candidates_with_sources.jsonl')]
out = []
for s in sel['selected']:
    match = [c for c in cands
             if c['domain'] == s['domain']
             and c['candidate_idx'] == s['candidate_idx']]
    assert len(match) == 1, f'no unique match for {s}'
    c = match[0]
    out.append({'task_id': s['task_id'], 'text': c['text'],
                'domain': c['domain'], 'category': c['category'],
                'source_candidate_idx': c['candidate_idx'],
                'source_documents': c.get('source_documents', [])})
with open('04_ground_truth/pilot_scaffolds/pilot_tasks_resolved.jsonl','w') as f:
    for r in out:
        f.write(json.dumps(r, ensure_ascii=False)+'\n')
print('wrote', len(out), 'resolved pilot tasks')
print('source_documents per task:',
      [len(r['source_documents']) for r in out])
"
```

**Success criteria.** `04_ground_truth/pilot_scaffolds/pilot_tasks_resolved.jsonl` has six lines, each with `task_id`, `text`, `domain`, `category`, and a `source_documents` list (typically three entries each from the Handoff 02 grounding).

## Task 3: Run PROMPTS Section 2 anchor scaffolding

```zsh
python3 -m apparatus.corpus.cli scaffold \
  --tasks 04_ground_truth/pilot_scaffolds/pilot_tasks_resolved.jsonl \
  --out 04_ground_truth/pilot_scaffolds
```

**Success criteria.** `04_ground_truth/pilot_scaffolds/anchor_scaffolds.jsonl` has six lines. Each line is a JSON object with `task_id`, `request_text`, `mission_intent` (non-empty), `minimum`, `target`, `constraints`, `suspected_gaps`, `source_model` of `claude-opus-4-6`, `parse_ok: true`.

**On parse failure.** If any one scaffold reports `parse_ok: false`, look at its `error` field. A transient JSON-truncation error may be resolved by re-running just that task once. A persistent failure (the model wrote prose, not JSON) is rare with this prompt; report it with the raw response and stop. Do not edit the scaffold to fix it; the prompt is locked.

## Task 4: Merge source_documents into each scaffold for SME review

The locked PROMPTS Section 2 scaffolder prompt is intentionally conservative and is built from the request text alone, not the source documents. The source_documents the Handoff 02 grounding produced ride alongside the scaffold output so the SMEs see real fetched references during their independent-then-review workflow (FORMS Section 1), without polluting the model's draft. This step merges them in by `task_id`.

```zsh
python3 -c "
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
with open('04_ground_truth/pilot_scaffolds/anchor_scaffolds.jsonl','w') as f:
    for s in out:
        f.write(json.dumps(s, ensure_ascii=False, default=str)+'\n')
print('merged source_documents into', len(out), 'scaffolds')
print('source_documents counts:', [len(s['source_documents']) for s in out])
"
```

## Task 5: Quick sanity (six unique task ids, scaffolds parse, sources attached)

```zsh
python3 -c "
import json
rows = [json.loads(l) for l in open(
    '04_ground_truth/pilot_scaffolds/anchor_scaffolds.jsonl')]
ids = [r['task_id'] for r in rows]
assert len(ids) == 6
assert len(set(ids)) == 6, f'duplicate task ids: {ids}'
parsed = sum(1 for r in rows if r['parse_ok'])
with_sources = sum(1 for r in rows if r.get('source_documents'))
print('scaffolds:', len(rows), 'parsed_ok:', parsed,
      'with_sources:', with_sources)
print('ids:', ids)
"
```

**Success criteria.** Six scaffolds, six unique ids, all parsed_ok, all six carrying a non-empty `source_documents` list.

---

## Final report

Write `handoffs/HANDOFF_06_report_<YYYY-MM-DD>.md`:

```markdown
# Handoff 06 Report: Pilot Anchor Scaffolds

**Codex session:** <id>
**Eval host:** <hostname>
**Date:** <YYYY-MM-DD>
**Wall clock:** <minutes>

## Verdict

PROCEED | HALT (one word)

## Evidence

- pilot_selection.json shape OK:       yes | no
- resolved pilot tasks:                <n>/6
- scaffolds produced:                  <n>/6
- scaffolds parsed_ok:                 <n>/6
- scaffolds with source_documents:     <n>/6
- task ids in scaffold output:         <list>
- Anthropic model used:                claude-opus-4-6
- Anthropic input tokens (total):      <n>
- Anthropic output tokens (total):     <n>
- estimated API cost (USD):            $<x.xx>

## Anything the PI must decide before proceeding

- review the six scaffolds in 04_ground_truth/pilot_scaffolds/anchor_scaffolds.jsonl
- circulate them to the pilot SMEs for the independent-then-review workflow
  (FORMS Section 1)

## Deviations from this handoff

<short list, empty if none>
```

Commit the resolved tasks file, the scaffolds, and the handoff report in a single commit with a message like `Handoff 06: pilot anchor scaffolds for SME review`.
