# Codex Handoff 13d: Phase 8 three-judge grading with Gemini budget patched

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-16
**Estimated wall clock:** 8 to 24 hours (unchanged from 13c — Gemini's larger budget doesn't slow per-call latency materially).
**Estimated API cost:** ~$1,550 to $2,100 (unchanged from 13c; Gemini's per-call cost rises slightly with the larger output budget).
**Blocked on:** Judge max_tokens patch committed on project main; 13c smoke-test pattern (one-record per judge) passing with parse_ok=True on all three judges.

---

## Why this exists

HANDOFF_13c halted on a one-record smoke test: GPT-4o and Claude Opus parsed cleanly, but Gemini 2.5 Pro returned empty visible output. Codex diagnosed: Gemini 2.5 Pro's thinking-mode reasoning tokens count against the `max_output_tokens` budget BEFORE the visible response. The Judge's hardcoded `max_tokens=2048` was insufficient — Gemini burned the full budget on reasoning and hit `MAX_TOKENS` before emitting JSON. At 4096 Codex saw valid JSON; 8192 is the safety margin against tasks with longer reasoning chains.

Apparatus patch landed on project main:

```
apparatus/grading/judge.py        Judge.__init__ accepts max_tokens (default 2048).
                                  Judge.grade() uses self.max_tokens instead of hardcode.
                                  judge_gemini_pro factory passes max_tokens=8192.
                                  judge_gpt4o and judge_claude_opus factories unchanged
                                  (still 2048; their thinking modes don't burn the budget).
apparatus/grading/tests/test_grading.py
                                  New test_judge_max_tokens_per_instance verifies
                                  factory defaults and per-Judge override. 17/17 passing.
```

Stage and commit with: `Patch Judge to support per-instance max_tokens; bump Gemini 2.5 Pro to 8192 to accommodate thinking-mode reasoning budget (HANDOFF_13c 2026-06-16 halt). Regression test covers factory defaults and Judge() direct construction.`

The healthcheck in 13d also uses the real `GeminiClient` path from `apparatus.baselines.llm_client` so the precondition exercises the same code the judge will use during grading.

## Scope (unchanged from 13c)

9036 records + 20% double-grade sample. Same outputs_freeze_v1_1, same ground_truth.json contract, same judges config, same SME-skip kappa caveat.

## Preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# 1. The Judge max_tokens patch is on project main
python3 -c "
from apparatus.grading.judge import (
    judge_gpt4o, judge_claude_opus, judge_gemini_pro,
)
from apparatus.baselines.llm_client import MockLLMClient
mc = MockLLMClient(default='{}')
assert judge_gpt4o(llm_client=mc).max_tokens == 2048
assert judge_claude_opus(llm_client=mc).max_tokens == 2048
assert judge_gemini_pro(llm_client=mc).max_tokens == 8192
print('Judge max_tokens patch present (Gemini at 8192)')
"

# 2. Grading tests pass (regression guard)
python3 -m pytest apparatus/grading/tests/test_grading.py -q 2>&1 | tail -3

# 3. outputs_freeze_v1_1 present
git tag --list | grep -E "^outputs_freeze_v1_1$" >/dev/null \
  || { echo "HALT: outputs_freeze_v1_1 missing"; exit 1; }

# 4. ground_truth.json exists with 150 anchor-wrapped entries (from 13c Task 1)
test -f 04_ground_truth/ground_truth.json \
  || { echo "HALT: ground_truth.json missing; re-run 13c Task 1"; exit 1; }
python3 - <<'PY'
import json
gt = json.load(open('04_ground_truth/ground_truth.json'))
assert len(gt) == 150, f'expected 150, got {len(gt)}'
assert all('anchor' in v and v['anchor'].get('mission_intent') for v in gt.values()), \
    'GT entries missing anchor.mission_intent'
print(f'ground_truth.json: {len(gt)} anchor-wrapped entries')
PY

# 5. Anonymized output count
n_anon=$(ls 08_grading/anonymized_outputs/*.json 2>/dev/null | wc -l)
[ "$n_anon" -ge 9000 ] || { echo "HALT: anonymized count $n_anon < 9000"; exit 1; }
echo "anonymized outputs: $n_anon records"

# 6. Three API keys
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

# 7. Healthcheck via the actual production path (not the SDK directly).
#    Exercises the same GeminiClient code the Judge uses, with the new max_tokens=8192.
START=$(date +%s)
python3 - <<'PY'
import os
from pathlib import Path
for line in Path('.env').read_text().splitlines():
    if '=' in line:
        k, v = line.split('=', 1); os.environ[k] = v
from apparatus.baselines.llm_client import (
    AnthropicClient, OpenAIClient, GeminiClient,
)
# Anthropic
ac = AnthropicClient()
r = ac.generate(system="", user="healthcheck", model="claude-opus-4-6",
                temperature=0.0, max_tokens=16)
print(f"  AnthropicClient healthcheck OK: {r.text[:40]!r}")
# OpenAI
oc = OpenAIClient()
r = oc.generate(system="", user="healthcheck", model="gpt-4o-2024-11-20",
                temperature=0.0, max_tokens=16)
print(f"  OpenAIClient healthcheck OK: {r.text[:40]!r}")
# Gemini via the production GeminiClient path with the patched 8192 budget
gc = GeminiClient()
r = gc.generate(system="", user="healthcheck", model="gemini-2.5-pro",
                temperature=0.0, max_tokens=8192)
assert r.text and r.text.strip(), \
    f"Gemini returned empty text even at max_tokens=8192: {r!r}"
print(f"  GeminiClient healthcheck OK (max_tokens=8192): {r.text[:40]!r}")
PY
echo "all three judge clients respond ($(($(date +%s) - START))s total)"
```

**Success criteria.** All seven preconditions print confirmation. The Gemini healthcheck returns non-empty text at the patched budget.

**On HALT.** If the Gemini healthcheck still returns empty at 8192, the issue is not the budget — likely a model-version mismatch (`gemini-2.5-pro` vs `gemini-2.5-pro-002` or similar) or an account-level access issue. Stop and report.

## Task 1-4: Same as HANDOFF_13c

Tasks 1 (assemble ground_truth.json), 2 (write judges_config), 3 (run grade with --double-grade-pct 0.20), and 4 (halt check) are identical to HANDOFF_13c. The single change is the Judge max_tokens patch, which is precondition-verified above.

If ground_truth.json from 13c Task 1 is already on disk and validates the precondition, **skip Task 1** and proceed directly to Task 3:

```zsh
python3 -m apparatus.run grade \
  --anonymized 08_grading/anonymized_outputs \
  --ground-truth 04_ground_truth/ground_truth.json \
  --judges-config 08_grading/judges_config.json \
  --out 08_grading \
  --double-grade-pct 0.20 \
  --double-grade-seed 20260616
```

## Decision boundary

Carried from HANDOFF_13c. Add:

- If Gemini's per-call cost averages more than 3x the GPT-4o per-call cost after 200 calls, the 8192 budget is producing tokens you're paying for but not using. Pause and inspect a sample of Gemini scores; consider dropping to 4096 in a follow-up patch. (Codex verified 4096 works; 8192 is safety margin, not requirement.)
- The Gemini `MAX_TOKENS` failure mode is now actively monitored. Any judge_3_gemini_pro score with `error` matching `MAX_TOKENS` after the patch indicates the 8192 budget is also insufficient for that task — quarantine those records and report.

## Report

`handoffs/HANDOFF_13d_report_<YYYY-MM-DD>.md` with the same structure as HANDOFF_13c, plus:

- Gemini empty-output rate (target: 0/9036)
- Gemini per-call cost (sanity check vs the 8192 budget)
- Total Phase 8 cost vs estimate

Commit message: `Handoff 13d: Phase 8 three-judge grading (Gemini max_tokens patched to 8192; outputs_freeze_v1_1)`.

## What 13d unblocks

After 13d PROCEED:
- **HANDOFF_14** (Phase 9 analysis): compute O1-O4 outcomes against ensemble grades.
- **HANDOFF_15** (deposit): replication package assembly for Zenodo.
- Optional **HANDOFF_11c** (perturbations, ~$1,200) for O5.

If 13d HALTs again on Gemini-specific output emptiness despite the 8192 budget, the diagnostic at that point would be: switch to a non-thinking-mode Gemini variant (e.g. `gemini-1.5-pro` or `gemini-2.0-flash`), or replace the third judge with a different family entirely. Both are v2-grader candidate questions, not v1 modifications.
