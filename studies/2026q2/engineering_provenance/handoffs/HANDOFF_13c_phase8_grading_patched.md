# Codex Handoff 13c: Phase 8 three-judge grading with patched apparatus

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-16
**Estimated wall clock:** 8 to 24 hours (three judges × 9036 outputs with API parallelism + 1807 double-grade sample).
**Estimated API cost:** **$1,500 to $2,000** total (unchanged from 13b).
**Blocked on:** Apparatus grader patch committed on project main (this handoff verifies as precondition); `outputs_freeze_v1_1` present; three judge API keys set.

---

## Why this exists

HANDOFF_13b correctly halted on two contract gaps Codex diagnosed:

1. **`apparatus.run grade` did not invoke `pipe.double_grade`** despite PROTOCOL_LOCK §8 requiring a 20% IRR sample. The grading pipeline has the method (`apparatus/grading/pipeline.py:86`) but the CLI never called it.
2. **HANDOFF_13b's `ground_truth.json` assembly was flat**, but the pipeline reads `gt.get("anchor", {})` (line 57). The judges would have received `{}` as ground truth and scored every output against nothing.

Both fixes landed on project main. Three commits to stage and commit before sending this handoff to Codex:

```
apparatus/run.py                       cmd_grade now runs pipe.double_grade
                                       when --double-grade-pct > 0
                                       new flags: --double-grade-pct, --double-grade-seed
apparatus/grading/tests/test_grading.py two new tests cover the pipeline
                                       double_grade flow and the new CLI flags
                                       (16/16 grading tests passing)
```

Stage and commit with: `Patch cmd_grade to support --double-grade-pct + --double-grade-seed (HANDOFF_13b 2026-06-16 halt diagnosis); two regression tests; pipeline.double_grade was already implemented but uncalled by the CLI`

This handoff also corrects Task 1's ground_truth.json assembly to match the pipeline's contract.

## Scope (unchanged from 13b)

```
1200  MANDATE-primary on 120 main tasks × 10 runs
1206  Baseline 1 on 120 main tasks × 10 runs   (6 over-budget per 11b-ii)
1206  Baseline 2 on 120 main tasks × 10 runs
1206  Baseline 3 on 120 main tasks × 10 runs
1206  Baseline 4 on 120 main tasks × 10 runs
1206  Baseline 5 on 120 main tasks × 10 runs
1206  Baseline 6 on 120 main tasks × 10 runs
 300  MANDATE-primary on 30 hold-out tasks × 10 runs (regenerated under HANDOFF_26)
 300  Baseline 1 on 30 hold-out tasks × 10 runs
─────
9036  total anonymized records  + 20% double-grade sample (~1807 records)
```

**Definition of done.** Same as 13b plus the `08_grading/double_grade/` subdirectory carries pass1_scores.jsonl, pass2_scores.jsonl, sample_anon_ids.json. The `irr.json` carries `double_grade` sub-report with pass1 and pass2 IRR. Halt-vs-proceed verdict on the main pass's kappa.

## SME-skip note for kappa interpretation

Carried forward from HANDOFF_13b. Under SME-skip, kappa measures judge-vs-judge agreement on Claude-Opus-generated answer key, not judge-vs-SME. Halt threshold (0.40) preserved unchanged.

## Preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# 1. The --double-grade-pct patch is on project main
python3 -m apparatus.run grade --help 2>&1 | grep -q "double-grade-pct" \
  || { echo "HALT: grader patch missing"; exit 1; }
echo "--double-grade-pct flag present"

# 2. Grading tests pass (regression guard)
python3 -m pytest apparatus/grading/tests/test_grading.py -q 2>&1 | tail -3

# 3. outputs_freeze_v1_1 present
git tag --list | grep -E "^outputs_freeze_v1_1$" >/dev/null \
  || { echo "HALT: outputs_freeze_v1_1 missing"; exit 1; }

# 4. Anonymized output count
n_anon=$(ls 08_grading/anonymized_outputs/*.json 2>/dev/null | wc -l)
[ "$n_anon" -ge 9000 ] || { echo "HALT: anonymized count $n_anon < 9000"; exit 1; }
echo "anonymized outputs: $n_anon records"

# 5. Three API keys
python3 -c "
import os
from pathlib import Path
for line in Path('.env').read_text().splitlines():
    if '=' in line:
        k, v = line.split('=', 1); os.environ[k] = v
assert os.environ.get('ANTHROPIC_API_KEY','').startswith('sk-ant')
assert os.environ.get('OPENAI_API_KEY','').startswith('sk-')
assert os.environ.get('GOOGLE_API_KEY','').strip()
print('all three API keys set')
"

# 6. Real-call healthcheck for each judge (under $0.10 total)
START=$(date +%s)
python3 - <<'PY'
import os
from pathlib import Path
for line in Path('.env').read_text().splitlines():
    if '=' in line:
        k, v = line.split('=', 1); os.environ[k] = v
import anthropic
c = anthropic.Anthropic()
r = c.messages.create(model="claude-opus-4-6", max_tokens=16,
                       messages=[{"role":"user","content":"healthcheck"}])
print(f"  Claude Opus healthcheck OK: {r.content[0].text[:40]!r}")
from openai import OpenAI
oc = OpenAI()
r = oc.chat.completions.create(model="gpt-4o-2024-11-20", max_tokens=16,
                                messages=[{"role":"user","content":"healthcheck"}])
print(f"  GPT-4o healthcheck OK: {r.choices[0].message.content[:40]!r}")
import google.generativeai as genai
genai.configure(api_key=os.environ['GOOGLE_API_KEY'])
m = genai.GenerativeModel('gemini-2.5-pro')
r = m.generate_content("healthcheck", generation_config={"max_output_tokens": 16})
print(f"  Gemini 2.5 Pro healthcheck OK: {r.text[:40]!r}")
PY
echo "all three judge APIs respond ($(($(date +%s) - START))s total)"
```

**Success criteria.** All six preconditions print confirmation.

## Decision boundary

Same as HANDOFF_13b. Add: total double-grade cost above $400 (sample of 1807 records × 3 judges) escalates. The double-grade sample-size formula: `floor(n_anon * 0.20)`.

## Task 1: Assemble ground_truth.json with the correct anchor-wrapped shape

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

python3 - <<'PY'
import json
out = {}

# Category lookups from selection JSONs (needed for grading rubric)
main_cat = {s['task_id']: s['category']
            for s in json.load(open('03_corpus/main/main_selection.json'))['selected']}
hold_cat = {s['task_id']: s['category']
            for s in json.load(open('03_corpus/holdout/holdout_selection.json'))['selected']}

# Main scaffolds: 120 entries
for line in open('04_ground_truth/main_scaffolds/anchor_scaffolds.jsonl'):
    r = json.loads(line)
    tid = r['task_id']
    out[tid] = {
        # anchor sub-key is what pipeline.py:57 reads
        'anchor': {
            'mission_intent': r.get('mission_intent', ''),
            'minimum':        r.get('minimum', []),
            'target':         r.get('target', []),
            'constraints':    r.get('constraints', []),
            'suspected_gaps': r.get('suspected_gaps', []),
        },
        'category':             main_cat.get(tid, 'full_specification'),
        'expected_output_type': 'MANDATE_AS_CODE',
        'is_injection_trial':   False,
        'source_documents':     r.get('source_documents', []),
        'derived_from':         r.get('derived_from', {}),
        'source_model':         r.get('source_model'),
    }

# Hold-out scaffolds: 30 entries
for line in open('04_ground_truth/holdout_scaffolds/anchor_scaffolds.jsonl'):
    r = json.loads(line)
    tid = r['task_id']
    out[tid] = {
        'anchor': {
            'mission_intent': r.get('mission_intent', ''),
            'minimum':        r.get('minimum', []),
            'target':         r.get('target', []),
            'constraints':    r.get('constraints', []),
            'suspected_gaps': r.get('suspected_gaps', []),
        },
        'category':             hold_cat.get(tid, 'full_specification'),
        'expected_output_type': 'MANDATE_AS_CODE',
        'is_injection_trial':   False,
        'derived_from':         r.get('derived_from', {}),
        'source_model':         r.get('source_model'),
    }

assert len(out) == 150, f"expected 150 ground truth entries, got {len(out)}"
for tid, gt in out.items():
    assert 'anchor' in gt and gt['anchor'].get('mission_intent') is not None, \
        f"GT for {tid} missing anchor.mission_intent"

with open('04_ground_truth/ground_truth.json', 'w') as f:
    json.dump(out, f, indent=2, ensure_ascii=False, default=str)
print(f"wrote {len(out)} ground truth entries to 04_ground_truth/ground_truth.json")
print("  shape: {task_id: {anchor: {...}, category, expected_output_type, ...}}")
print("  pipeline.py:57 reads gt.get('anchor', {}) - now non-empty for every task")
PY
```

**Success criteria.** `04_ground_truth/ground_truth.json` exists with 150 task-keyed entries. Every entry carries `anchor.mission_intent` non-empty.

## Task 2: Write the judges config (same as 13b)

```zsh
cat > 08_grading/judges_config.json <<'EOF'
{"gpt4o":   "gpt-4o-2024-11-20",
 "claude":  "claude-opus-4-6",
 "gemini":  "gemini-2.5-pro"}
EOF
```

## Task 3: Run the three-judge grading WITH the 20% double-grade sample

```zsh
python3 -m apparatus.run grade \
  --anonymized 08_grading/anonymized_outputs \
  --ground-truth 04_ground_truth/ground_truth.json \
  --judges-config 08_grading/judges_config.json \
  --out 08_grading \
  --double-grade-pct 0.20 \
  --double-grade-seed 20260616
```

**What the new flag does.** After the main grading pass writes per-judge scores, the CLI deterministically samples 20% of the anonymized outputs by index (seed 20260616), then calls `pipe.double_grade(sample, gt)` which runs `grade_all` twice independently over the same sample. Both passes are persisted under `08_grading/double_grade/` so Phase 9 can compute intra-judge stability and IRR consistency.

**Wall clock estimate.** Single-grade pass ~8 hours with 3-5x API concurrency. Double-grade pass ~1.6 hours (20% of the main pass). Total: ~10 hours.

**Success criteria.**

- `08_grading/judge_<n>_<family>/scores.jsonl` for each of the three judges (~9036 entries each).
- `08_grading/ensemble_aggregated/ensemble_scores.jsonl` (~9036 entries).
- `08_grading/double_grade/` contains `sample_anon_ids.json`, `pass1_scores.jsonl`, `pass2_scores.jsonl`.
- `08_grading/irr.json` carries top-level kappa AND `double_grade.{pass1_irr, pass2_irr}`.

## Task 4: Halt check

```zsh
python3 - <<'PY'
import json
irr = json.load(open('08_grading/irr.json'))
print('main pass IRR:')
for pair, k in irr.get('pairwise_kappa', {}).items():
    print(f'  {pair}: {k:.3f}')
print(f'  min pairwise kappa: {irr.get("min_pairwise_kappa")}')
print(f'  halt: {irr.get("halt")}')

dg = irr.get('double_grade', {})
if dg:
    print(f"\ndouble-grade sample: {dg.get('sample_size')} records (seed {dg.get('seed')})")
    print(f"  pass1 min kappa: {dg.get('pass1_irr',{}).get('min_pairwise_kappa')}")
    print(f"  pass2 min kappa: {dg.get('pass2_irr',{}).get('min_pairwise_kappa')}")
else:
    print("WARNING: no double_grade sub-report; --double-grade-pct flag may not have fired")

if irr.get('halt'):
    print('\nHALT: at least one judge pair below 0.40 kappa.')
    print('Per PROTOCOL_LOCK Section 8 the study halts here.')
PY
```

**Success criteria.** `irr.json` produced with `pairwise_kappa`, `min_pairwise_kappa`, `halt`, AND `double_grade` sub-report. Halt verdict recorded.

## Report

`handoffs/HANDOFF_13c_report_<YYYY-MM-DD>.md` with:

- Total anonymized records graded (~9036)
- Double-grade sample size (~1807)
- Per-judge cost ($Anthropic, $OpenAI, $Google)
- Total cost
- Main pass per-pair kappa + min
- Double-grade pass1 / pass2 per-pair kappa + min
- Halt decision
- Anomalies (high schema-invalid rate, model rate-limit, retries)
- Per-domain breakouts of the ensemble scores on O1-O4
- PROCEED verdict if all kappa ≥ 0.40

Commit message: `Handoff 13c: Phase 8 three-judge grading with 20% double-grade sample (outputs_freeze_v1_1, SME-skip kappa caveat)`.
