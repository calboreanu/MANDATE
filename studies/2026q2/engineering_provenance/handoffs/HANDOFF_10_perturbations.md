# Codex Handoff 10: Perturbation Suite (Phase 5)

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-03
**Estimated wall clock:** 30 to 45 minutes (350 Anthropic calls).
**Blocked on:** `corpus_freeze_v1` tag exists; main corpus, ground truth signed off; Anthropic balance at least $15.

---

## Mission

Generate the 350-perturbation suite from the frozen main corpus. PROTOCOL_LOCK Section 1 specifies seven perturbation types at 50 trials each, drawn from a 30-task stratified base subset of the 120 main tasks; PROMPTS Section 3 supplies the seven type-specific prompts verbatim. The output is one JSONL the Phase 6 harness reads. Codex runs the generator; the spot-check (FORMS Section 5, 30 percent of generated perturbations reviewed) is human SME work done after.

**Definition of done.** `06_perturbations/perturbation_suite.jsonl` with exactly 350 records, every record carrying `perturbation_id`, `perturbation_type`, `sub_type` (for prompt injection), `base_task_id`, `request_text`, and the locked metadata fields the harness reads. One handoff report.

## Preconditions

Confirm each:

- `git tag -l corpus_freeze_v1` shows the tag (study cannot perturb a moving corpus).
- `03_corpus/main/main_selection.json` and `03_corpus/main/candidates_main.jsonl` exist.
- `ANTHROPIC_API_KEY` is in `.env`; balance is at least $15 (350 Claude Opus 4.6 calls).
- `apparatus/perturbations/` is built and unit-tested (the perturbation generator and PROMPTS Section 3 prompts).

## Decision boundary

You may decide:
- One retry on a transient Anthropic API error per perturbation.
- Output paths inside the documented tree.

You must escalate:
- A perturbation whose prompt could not be parsed or produced empty text twice in a row.
- A persistent Anthropic auth or rate-limit error.
- Any deviation in the per-type count (50 per type) once the run completes.

You may not:
- Edit a perturbation after generation.
- Run the harness on the suite.
- Anonymize or grade the suite.

---

## Task 1: Confirm preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate
python3 -c "
import os
from apparatus.corpus.cli import _load_dotenv
_load_dotenv()
assert os.environ.get('ANTHROPIC_API_KEY','').startswith('sk-ant'), 'key missing'
print('key set')
"
git -C "$PWD" tag -l corpus_freeze_v1 | grep -q corpus_freeze_v1 && \
  echo "corpus_freeze_v1 present" || { echo "halt: corpus_freeze_v1 missing"; exit 2; }
```

## Task 2: Generate the suite

```zsh
python3 -m apparatus.corpus.cli generate-perturbations \
  --selection 03_corpus/main/main_selection.json \
  --pool 03_corpus/main/candidates_main.jsonl \
  --out 06_perturbations \
  --per-type 50 \
  --base-count 30 \
  --seed 20260605
```

**Success criteria.**
- `06_perturbations/perturbation_suite.jsonl` exists with 350 lines.
- Per-type counts: 50 surface_noise, 50 ambiguity_injection, 50 contradictory_constraints, 50 prompt_injection (split 17/17/16 across direct_command, role_play, hidden_instruction), 50 missing_required_field, 50 out_of_distribution_input, 50 length_perturbation.
- Every record carries a non-empty `perturbation_id`, `perturbation_type`, `base_task_id`, and `request_text`.

## Task 3: Sanity

```zsh
python3 -c "
import json, collections
rows = [json.loads(l) for l in open('06_perturbations/perturbation_suite.jsonl')]
print('total:', len(rows))
assert len(rows) == 350
ctype = collections.Counter(r['perturbation_type'] for r in rows)
print('by type:', dict(ctype))
inj = [r for r in rows if r['perturbation_type'] == 'prompt_injection']
sub = collections.Counter(r['sub_type'] for r in inj)
print('injection subtypes:', dict(sub))
assert set(ctype.keys()) == {'surface_noise','ambiguity_injection',
    'contradictory_constraints','prompt_injection',
    'missing_required_field','out_of_distribution_input',
    'length_perturbation'}
assert all(c == 50 for c in ctype.values())
"
```

---

## Final report

```markdown
# Handoff 10 Report: Perturbation Suite

**Codex session:** <id>
**Eval host:** <hostname>
**Date:** <YYYY-MM-DD>
**Wall clock:** <minutes>

## Verdict

PROCEED | HALT (one word)

## Evidence

- corpus_freeze_v1 tag present:        yes | no
- base task count:                     30
- perturbations generated:             <n>/350
- per-type counts:                     surface_noise=<n>, ambiguity=<n>, ...
- injection subtypes:                  direct=<n>, role_play=<n>, hidden=<n>
- Anthropic model used:                claude-opus-4-6
- Anthropic input tokens (total):      <n>
- Anthropic output tokens (total):     <n>
- estimated API cost (USD):            $<x.xx>

## Anything the PI must decide before proceeding

- circulate 30 percent (105 perturbations) to SMEs for the spot-check
  (FORMS Section 5); halt if SME-flagged misclassifications exceed
  the protocol's allowance

## Deviations from this handoff

<short list, empty if none>
```

Commit the suite and the report in a single commit with message `Handoff 10: 350-perturbation suite (Phase 5)`.
