# Codex Handoff 13b: Phase 8 three-judge grading (corrected scope, outputs_freeze_v1_1)

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-15
**Estimated wall clock:** ~24 to 48 hours (three judges × 9000 outputs with API parallelism; rate-limited).
**Estimated API cost:** **$1,500 to $2,000** total. Most of the spend is Claude Opus (~$1,200 of the total at $0.135/call × 9000 single + 1800 double = $1,458). GPT-4o and Gemini are roughly $0.02 and $0.01 per call respectively.
**Blocked on:** `outputs_freeze_v1_1` present; ground_truth.json assembled (Task 1 builds it); all three API keys set with sufficient balance.

---

## Why this exists

The original HANDOFF_13 was drafted 2026-06-03 before Phase 6 ran. Six staleness items make it unsendable as-is:

1. References `outputs_freeze_v1` — contaminated MP hold-out leg; superseded by `outputs_freeze_v1_1` (HANDOFF_26).
2. Requires `ablation_freeze_v1` — that tag doesn't exist; ablations are deferred upstream MANDATE work (HANDOFF_05).
3. References non-existent `04_ground_truth/ground_truth.json` — under the SME-skip pivot the ground truth is three scaffold pools; this handoff assembles them.
4. Cost estimate "a few hundred dollars" is wrong by 10x.
5. Pilot smoke records (42 at `*_pilot/`) are not in the 9000 deposit-ready set and should not be graded here.
6. Kappa semantics under SME-skip need an inline note.

13b corrects all six.

## Scope

The 9000 anonymized RunRecords at `08_grading/anonymized_outputs/` correspond to:

```
1200  MANDATE-primary on 120 main tasks × 10 runs
1206  Baseline 1 on 120 main tasks × 10 runs   (6 extra over-budget records; per Codex's 11b-ii)
1206  Baseline 2 on 120 main tasks × 10 runs
1206  Baseline 3 on 120 main tasks × 10 runs
1206  Baseline 4 on 120 main tasks × 10 runs
1206  Baseline 5 on 120 main tasks × 10 runs
1206  Baseline 6 on 120 main tasks × 10 runs
 300  MANDATE-primary on 30 hold-out tasks × 10 runs (regenerated under HANDOFF_26)
 300  Baseline 1 on 30 hold-out tasks × 10 runs
─────
9036  total anonymized records (some baselines wrote 6 records over the 1200 target;
      grading is on every record present, not exactly 9000)
```

Plus a 20% randomly-sampled double-grading subset for IRR.

Ground truth: 120 `main_scaffolds` entries + 30 `holdout_scaffolds` entries = 150 task-keyed entries. Each anonymized record's `task_id` maps to one ground truth entry; the three judges score the record against that ground truth on the five pre-registered outcomes (O1 anchor completeness, O2 gap detection, O3 fabrication, O4 schema validity, O5 adversarial — though O5 requires perturbations which are deferred to HANDOFF_11c, so this handoff measures only O1-O4).

**Definition of done.**

1. `04_ground_truth/ground_truth.json` assembled (150 entries: 120 main + 30 hold-out).
2. Per-judge per-output `JudgeScore` JSONL under `08_grading/judge_<n>_<family>/scores.jsonl` (three judges × 9036 records ≈ 27,108 single-graded entries).
3. 20% double-grading subset graded for IRR (~5,420 additional grading calls).
4. Aggregated ensemble scores at `08_grading/ensemble_aggregated/ensemble_scores.jsonl`.
5. IRR report at `08_grading/irr.json` with per-pair Cohen's kappa and the halt-vs-proceed verdict.
6. Per-judge cost summary.
7. One handoff report.

## SME-skip note for kappa interpretation

PROTOCOL_LOCK §8 specifies a Cohen's kappa halt threshold of 0.40 between any pair of judges. Under the SME-skip deviation (`00_preregistration/DEVIATIONS.md` 2026-06-04), the ground truth in this run is Claude-Opus-4.6-generated scaffolds, not SME-accepted anchors. The kappa threshold still binds, but the semantic meaning shifts:

- **Original intent (SME-graded):** kappa measures how consistently three LLM judges recover the SME ground truth.
- **This study (SME-skipped):** kappa measures how consistently three LLM judges score outputs against a Claude-Opus-generated answer key.

A high kappa under the SME-skipped condition means the three judges agree on their answer key, not that the answer key is correct. The substantive interpretation in the writeup must reflect this. The halt rule is preserved unchanged: kappa < 0.40 = halt and report.

## Preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# 1. outputs_freeze_v1_1 is the canonical freeze
git tag --list | grep -E "^outputs_freeze_v1_1$" >/dev/null \
  || { echo "HALT: outputs_freeze_v1_1 missing"; exit 1; }
echo "outputs_freeze_v1_1 present"

# 2. Anonymized output tree carries 9000+ records
n_anon=$(ls 08_grading/anonymized_outputs/*.json 2>/dev/null | wc -l)
[ "$n_anon" -ge 9000 ] || { echo "HALT: anonymized count $n_anon < 9000"; exit 1; }
echo "anonymized outputs: $n_anon records"

# 3. All three API keys
python3 -c "
import os
from pathlib import Path
for line in Path('.env').read_text().splitlines():
    if '=' in line:
        k, v = line.split('=', 1); os.environ[k] = v
assert os.environ.get('ANTHROPIC_API_KEY','').startswith('sk-ant'), 'Anthropic missing'
assert os.environ.get('OPENAI_API_KEY','').startswith('sk-'), 'OpenAI missing'
assert os.environ.get('GOOGLE_API_KEY','').strip(), 'Google missing'
print('all three API keys set')
"

# 4. Real-call healthcheck for each judge (under $0.10 total)
START=$(date +%s)
python3 - <<'PY'
import os, json
from pathlib import Path
for line in Path('.env').read_text().splitlines():
    if '=' in line:
        k, v = line.split('=', 1); os.environ[k] = v

# Anthropic Opus
import anthropic
c = anthropic.Anthropic()
r = c.messages.create(model="claude-opus-4-6", max_tokens=16,
                       messages=[{"role":"user","content":"healthcheck"}])
print(f"  Claude Opus healthcheck OK: {r.content[0].text[:40]!r}")

# OpenAI GPT-4o
from openai import OpenAI
oc = OpenAI()
r = oc.chat.completions.create(model="gpt-4o-2024-11-20", max_tokens=16,
                                messages=[{"role":"user","content":"healthcheck"}])
print(f"  GPT-4o healthcheck OK: {r.choices[0].message.content[:40]!r}")

# Google Gemini
import google.generativeai as genai
genai.configure(api_key=os.environ['GOOGLE_API_KEY'])
m = genai.GenerativeModel('gemini-2.5-pro')
r = m.generate_content("healthcheck", generation_config={"max_output_tokens": 16})
print(f"  Gemini 2.5 Pro healthcheck OK: {r.text[:40]!r}")
PY
echo "all three judge APIs respond ($(($(date +%s) - START))s total)"
```

**Success criteria.** All four preconditions print confirmation lines.

## Decision boundary

You may decide:
- API concurrency per judge (recommended: 3-5 parallel streams per provider to manage rate limits).
- Commit incrementally per judge after each ~2000 grading calls.
- One retry per call on transient API errors with exponential backoff up to 60s.

You must escalate:
- A judge's per-call cost averaging >2x my estimate after 200 calls (signals prompt or model misconfiguration).
- Total cost above $2,500 (signals runaway tokens).
- A judge returning structured output that fails the JudgeScore schema on more than 5% of calls.
- Any kappa pair below 0.20 even partway through the double-grading sample (deep agreement failure; halt and report rather than continuing).

You may not:
- Modify ground truth.
- Modify anonymized outputs.
- Change the kappa halt threshold from 0.40.
- Skip the 20% double-grading sample (it's the only IRR signal).

---

## Task 1: Assemble ground_truth.json from the three scaffold pools

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

python3 - <<'PY'
import json
out = {}
# Main scaffolds: 120 entries
for line in open('04_ground_truth/main_scaffolds/anchor_scaffolds.jsonl'):
    r = json.loads(line)
    tid = r['task_id']
    out[tid] = {
        'mission_intent': r.get('mission_intent', ''),
        'minimum': r.get('minimum', []),
        'target': r.get('target', []),
        'constraints': r.get('constraints', []),
        'suspected_gaps': r.get('suspected_gaps', []),
        'source_model': r.get('source_model'),
        'source_documents': r.get('source_documents', []),
        'derived_from': r.get('derived_from', {}),
    }
# Hold-out scaffolds: 30 entries
for line in open('04_ground_truth/holdout_scaffolds/anchor_scaffolds.jsonl'):
    r = json.loads(line)
    tid = r['task_id']
    out[tid] = {
        'mission_intent': r.get('mission_intent', ''),
        'minimum': r.get('minimum', []),
        'target': r.get('target', []),
        'constraints': r.get('constraints', []),
        'suspected_gaps': r.get('suspected_gaps', []),
        'source_model': r.get('source_model'),
        'derived_from': r.get('derived_from', {}),
    }

assert len(out) == 150, f"expected 150 ground truth entries, got {len(out)}"
print(f"assembled {len(out)} ground truth entries:")
print(f"  main_scaffolds:    120")
print(f"  holdout_scaffolds:  30")

with open('04_ground_truth/ground_truth.json', 'w') as f:
    json.dump(out, f, indent=2, ensure_ascii=False, default=str)
print("\nwrote 04_ground_truth/ground_truth.json")
PY
```

**Success criteria.** `04_ground_truth/ground_truth.json` exists with 150 task-keyed entries.

## Task 2: Write the judges config

```zsh
cat > 08_grading/judges_config.json <<'EOF'
{"gpt4o":   "gpt-4o-2024-11-20",
 "claude":  "claude-opus-4-6",
 "gemini":  "gemini-2.5-pro"}
EOF
```

## Task 3: Run the three-judge grading

```zsh
python3 -m apparatus.run grade \
  --anonymized 08_grading/anonymized_outputs \
  --ground-truth 04_ground_truth/ground_truth.json \
  --judges-config 08_grading/judges_config.json \
  --out 08_grading
```

**Wall clock estimate.** With 3-5x concurrency per provider:
- Claude Opus: ~3 sec/call × 9036 / 5 parallel = ~90 min, plus rate-limit slowdowns. Allow 6-8 hours.
- GPT-4o: ~2 sec/call × 9036 / 5 = ~60 min. Allow 4 hours.
- Gemini 2.5 Pro: ~3 sec/call × 9036 / 3 = ~150 min. Allow 8 hours.

If the grader runs all three sequentially, total ~18-24 hours. If concurrently, ~8-10 hours.

**Success criteria.** Per-judge scores under `08_grading/judge_<n>_<family>/scores.jsonl`. Each file has roughly 9036 entries (or however many anonymized records exist).

## Task 4: Aggregate ensemble + IRR

This is what the grader CLI should produce automatically; if not, run the aggregation manually:

```zsh
# (Pseudo — the grader should write these. If it doesn't, the apparatus
# needs a small extension; report the gap and stop.)
test -f 08_grading/ensemble_aggregated/ensemble_scores.jsonl \
  || echo "ALERT: ensemble aggregation missing; check apparatus.run grade output"
test -f 08_grading/irr.json \
  || echo "ALERT: IRR report missing; check apparatus.run grade output"
```

## Task 5: Halt check

```zsh
python3 - <<'PY'
import json
irr = json.load(open('08_grading/irr.json'))
print('per-pair kappa:')
for pair, k in irr.get('pairwise_kappa', {}).items():
    print(f'  {pair}: {k:.3f}')
print(f'min pairwise kappa: {irr.get("min_pairwise_kappa")}')
print(f'halt: {irr.get("halt")}')
if irr.get('halt'):
    print('\nHALT: at least one judge pair below 0.40 kappa.')
    print('Per PROTOCOL_LOCK Section 8 the study halts here.')
PY
```

**Success criteria.** `irr.json` produced with per-pair kappa values. The halt verdict is recorded. If halt=True, the handoff report carries the failing pair and the protocol halt is binding.

## Report

`handoffs/HANDOFF_13b_report_<YYYY-MM-DD>.md` with:

- Total anonymized records graded
- Per-judge cost ($Anthropic, $OpenAI, $Google)
- Total cost
- Per-pair Cohen's kappa
- Min pairwise kappa
- Halt decision (PROCEED or HALT)
- Anomalies on any judge (high schema-invalid rate, model rate-limiting, retries)
- Per-domain breakouts of the ensemble scores on the 5 outcomes O1-O4 (O5 deferred to HANDOFF_11c)
- PROCEED verdict if kappa ≥ 0.40 across all pairs

Commit message: `Handoff 13b: Phase 8 three-judge grading (9036 records, outputs_freeze_v1_1, SME-skip kappa caveat)`.

## What 13b unblocks

After 13b PROCEED, the next handoffs are:

- **HANDOFF_14** (Phase 9 analysis): compute the five primary outcomes against ensemble grades, perform the cross-system comparisons, write the analysis section.
- **HANDOFF_15** (deposit): assemble the replication package for Zenodo deposit per PROTOCOL_LOCK Section 13.
- Optional **HANDOFF_11c** (perturbations, ~$1,200): if you want O5 (adversarial resistance) measured before the deposit.

If 13b HALTs on low kappa, the protocol halt is binding — the study cannot proceed without judge agreement. Diagnosis at that point will involve the per-judge prompt audit (is one judge's scoring radically different from the other two?) and likely a v2 grader candidate.
