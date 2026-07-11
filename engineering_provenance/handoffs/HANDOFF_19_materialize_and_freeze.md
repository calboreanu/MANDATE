# Codex Handoff 19: Materialize selections to ground truth + cut freeze tags

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-04
**Estimated wall clock:** 5 to 10 minutes (no API calls; pure file generation + git tags).
**Blocked on:** HANDOFF_06b PROCEED (pilot scaffolds present); HANDOFF_04c PROCEED (B1-B3 calibration complete); HANDOFF_04 PROCEED (B4-B6 calibration complete); the deviation note `00_preregistration/DEVIATIONS.md` recording the SME-skip pivot exists on project main.

---

## Why this exists

Per `00_preregistration/DEVIATIONS.md` 2026-06-04, the SME realism audit is skipped for this run. The formal study moves from selection files directly to ground-truth tasks and freeze tags via automation. This handoff does three things:

1. Materializes the three selection JSON files (pilot, main, holdout) into `04_ground_truth/{pilot,main,holdout}_tasks.jsonl` using the corrected `(domain, category, candidate_idx)` resolver from HANDOFF_06b.
2. Cuts `corpus_freeze_v1` once the three task files are on disk.
3. Cuts `baseline_freeze_v1` once all six baselines have their calibration RunRecords.

**Definition of done.** Three task files at `04_ground_truth/{pilot_tasks,main_tasks,holdout_tasks}.jsonl` (6 / 120 / 30 lines respectively, each with `task_id`, `text`, `domain`, `category`, source attribution). Two annotated git tags: `corpus_freeze_v1` and `baseline_freeze_v1`. One handoff report. `gt_freeze_v1` is NOT cut by this handoff; that tag waits on HANDOFF_09 main scaffolds + the upcoming hold-out scaffolds handoff.

## Preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# Selections present
test -f 03_corpus/pilot/pilot_selection.json    || { echo "pilot_selection missing"; exit 1; }
test -f 03_corpus/main/main_selection.json      || { echo "main_selection missing"; exit 1; }
test -f 03_corpus/holdout/holdout_selection.json || { echo "holdout_selection missing"; exit 1; }

# Candidate pools present
test -f 03_corpus/pilot/candidates_with_sources.jsonl || { echo "pilot pool missing"; exit 1; }
test -f 03_corpus/main/candidates_main.jsonl    || { echo "main pool missing"; exit 1; }
test -f 03_corpus/holdout/candidates_holdout.jsonl || { echo "holdout pool missing"; exit 1; }

# Baseline calibration outputs present (6 records each)
for B in baseline_1 baseline_2 baseline_3 baseline_4 baseline_5 baseline_6; do
  n=$(ls 07_system_outputs/$B/*.json 2>/dev/null | wc -l)
  [ "$n" -eq 6 ] || { echo "$B has $n records, expected 6"; exit 1; }
done

# Deviation note present
test -f 00_preregistration/DEVIATIONS.md || { echo "deviation note missing"; exit 1; }

echo "preconditions OK"
```

**Success criteria.** All checks print no error; final line reads `preconditions OK`.

## Decision boundary

You may decide:
- Output paths for the materialized JSONLs as long as they land at the canonical `04_ground_truth/{pilot_tasks,main_tasks,holdout_tasks}.jsonl`.

You must escalate:
- Any selection that cannot be resolved against its candidate pool by `(domain, category, candidate_idx)`. Stop and report the unresolvable selection entries.
- Any baseline directory carrying a different RunRecord count than 6.
- An existing `corpus_freeze_v1` or `baseline_freeze_v1` tag in the project repo. Do not overwrite; report and stop.

You may not:
- Cut `gt_freeze_v1`. That tag waits on HANDOFF_09 main scaffolds + holdout scaffolds + this materialization to complete.
- Cut tags in upstream AEGIS. This handoff acts only on the project repository.
- Modify the selection JSON files.

---

## Task 1: Materialize pilot tasks

```zsh
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
        'derived_from': c.get('derived_from', {}),
    })
with open('04_ground_truth/pilot_tasks.jsonl', 'w') as f:
    for r in out:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
print(f'pilot_tasks.jsonl: {len(out)} entries')
assert len(out) == 6
PY
```

**Success criteria.** `04_ground_truth/pilot_tasks.jsonl` has exactly 6 lines.

## Task 2: Materialize main tasks

```zsh
python3 - <<'PY'
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
    out.append({
        'task_id': s['task_id'],
        'text': c['text'],
        'domain': c['domain'],
        'category': c['category'],
        'source_candidate_idx': c['candidate_idx'],
        'derived_from': c.get('derived_from', {}),
    })
with open('04_ground_truth/main_tasks.jsonl', 'w') as f:
    for r in out:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
print(f'main_tasks.jsonl: {len(out)} entries')
assert len(out) == 120
PY
```

**Success criteria.** `04_ground_truth/main_tasks.jsonl` has exactly 120 lines.

## Task 3: Materialize hold-out tasks

```zsh
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
with open('04_ground_truth/holdout_tasks.jsonl', 'w') as f:
    for r in out:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
print(f'holdout_tasks.jsonl: {len(out)} entries')
assert len(out) == 30
PY
```

**Success criteria.** `04_ground_truth/holdout_tasks.jsonl` has exactly 30 lines.

## Task 4: Cut the corpus freeze tag

```zsh
git add 04_ground_truth/pilot_tasks.jsonl \
        04_ground_truth/main_tasks.jsonl \
        04_ground_truth/holdout_tasks.jsonl

# Confirm the tag does not already exist
git tag --list | grep -E "^corpus_freeze_v1$" && { echo "corpus_freeze_v1 already exists"; exit 1; }

git commit -m "Materialize pilot/main/holdout task selections to 04_ground_truth/

HANDOFF_19. Selections at 03_corpus/{pilot,main,holdout}/*_selection.json
resolved via (domain, category, candidate_idx) against their candidate pools
and written to 04_ground_truth/{pilot,main,holdout}_tasks.jsonl. SME
realism-audit gate is lifted per 00_preregistration/DEVIATIONS.md
2026-06-04."

git tag -a corpus_freeze_v1 -m "Corpus freeze v1 (SME-skip per DEVIATIONS.md 2026-06-04)

pilot_tasks.jsonl    6 tasks    (2 per domain, 1 full + 1 gap)
main_tasks.jsonl   120 tasks    (40 per domain, source-conditioned)
holdout_tasks.jsonl 30 tasks    (software_engineering_specification 4th domain)

SME realism audit skipped per PI decision. Realism is an acknowledged caveat,
not a pre-grading precondition. See DEVIATIONS.md for full implications."

git log --oneline -1
git tag --list "corpus_freeze*"
```

**Success criteria.** Annotated tag `corpus_freeze_v1` exists. The commit that produced it touches only `04_ground_truth/{pilot,main,holdout}_tasks.jsonl`.

## Task 5: Cut the baseline freeze tag

```zsh
git tag --list | grep -E "^baseline_freeze_v1$" && { echo "baseline_freeze_v1 already exists"; exit 1; }

# No new files to commit; this is a stand-alone tag against the current HEAD
git tag -a baseline_freeze_v1 -m "Baseline freeze v1

B1-B6 calibration RunRecords on disk at 07_system_outputs/baseline_{1..6}/.
B1 6/6 ok, 6/6 schema-valid (single-prompt Claude)
B2 6/6 ok, 5/6 schema-valid (single-prompt GPT-4o; threshold-type variance)
B3 6/6 ok, 0/6 schema-valid (ReAct Claude; arrays-of-strings/keyed objects)
B4 6/6 ok, 6/6 schema-valid (AutoGen PlannerReviewer)
B5 6/6 ok, 6/6 schema-valid (CrewAI SequentialCrew)
B6 6/6 ok, 6/6 schema-valid (LangGraph GraphRevision)

Schema-validity rates are Phase 6 O4 measurement data, not failure modes."

git tag --list "baseline_freeze*"
```

**Success criteria.** Annotated tag `baseline_freeze_v1` exists at the same commit as `corpus_freeze_v1`.

## Report

`handoffs/HANDOFF_19_report_<YYYY-MM-DD>.md` with:
- Materialized task counts: pilot/main/holdout
- corpus_freeze_v1 tag hash and confirmation it points at the materialization commit
- baseline_freeze_v1 tag hash
- Any selection entries that failed to resolve (expected: zero)
- PROCEED verdict

Commit message at handoff level: `Handoff 19: materialize selections to ground truth + corpus_freeze_v1 + baseline_freeze_v1`.
