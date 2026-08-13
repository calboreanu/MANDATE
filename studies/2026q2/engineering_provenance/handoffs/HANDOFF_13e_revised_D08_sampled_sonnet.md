# Codex Handoff 13e (REVISED, supersedes HANDOFF_13e_grading_resume_with_checkpoints.md)

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-18
**Supersedes:** `HANDOFF_13e_grading_resume_with_checkpoints.md` (full-coverage Opus plan; halted on missing GOOGLE_API_KEY)
**Deviation reference:** D-08 (see `Mandate Data/Empirical Evidence Supplemental.tex` Section 17 and Appendix X)
**Estimated wall clock:** 90 minutes to 3 hours (3-way per-record concurrency, 700 records, 10% double-grade adds 70 records)
**Estimated API cost:** ~$215 projected (vs $1,500-$2,000 under the original 13e plan)
**Blocked on:** GOOGLE_API_KEY populated in `.env`

---

## Why this revision exists

Cal pushed back on the projected ~$1,700–$2,200 cost of full-coverage
three-judge grading at the original judge mix. The original plan graded
all 9,000 anonymized RunRecords with Claude Opus 4.6, GPT-4o, and Gemini
2.5 Pro and a 20% IRR double-grade sample.

Cal's substantive point: the five content-tripwire findings are
evidenced at full coverage from on-disk RunRecord inspection (verbatim
quotes, structural counts) and do not depend on Phase 8 grading. Phase 8
provides cross-system numerical comparison on the four measured
outcomes (O1-O4); for that comparison, a stratified sample is adequate.

The deviation has three components, all documented in D-08:

1. **Stratified sample of N=700** (100 records per system across 7
   systems). Sample drawn deterministically with seed `20260618` and
   stored in `08_grading/sample_manifest.jsonl`. Sample-size
   justification (statistical power) is in Appendix X of the supplemental.
2. **Claude Sonnet 4.6 substituted for Claude Opus 4.6** as the
   Anthropic judge. Same generation, lower-cost tier.
   `08_grading/judges_config.json` updated.
3. **10% IRR double-grade sample** (70 records) instead of the
   pre-registered 20%.

The grader patches from the original HANDOFF_13e (per-record
checkpointing + bounded concurrency) remain in place and are required.

---

## Preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# 1. CLI patches present
python3 -m apparatus.run grade --help 2>&1 | grep -q "skip-existing" \
  || { echo "HALT: --skip-existing missing"; exit 1; }
python3 -m apparatus.run grade --help 2>&1 | grep -q "max-workers" \
  || { echo "HALT: --max-workers missing"; exit 1; }
echo "CLI flags present"

# 2. Grading regression tests pass (21 tests)
python3 -m pytest apparatus/grading/tests/test_grading.py -q 2>&1 | tail -3

# 3. Judges config is the Sonnet-substituted version (D-08 component b)
grep -q "claude-sonnet-4-6" 08_grading/judges_config.json \
  || { echo "HALT: judges_config.json still has Opus; expected Sonnet under D-08"; exit 1; }
echo "judges_config.json under D-08 (Sonnet)"

# 4. Sample manifest present (D-08 component a)
test -f 08_grading/sample_manifest.jsonl || { echo "HALT: sample_manifest.jsonl missing"; exit 1; }
n_sample=$(wc -l < 08_grading/sample_manifest.jsonl)
[ "$n_sample" -eq 700 ] || { echo "HALT: sample_manifest.jsonl has $n_sample lines, expected 700"; exit 1; }
test -f 08_grading/sample_manifest_meta.json || { echo "HALT: sample_manifest_meta.json missing"; exit 1; }
echo "sample manifest: $n_sample records"

# 5. Anonymized outputs (the population the sample draws from)
test -d 08_grading/anonymized_outputs || { echo "HALT: anonymized_outputs/ missing"; exit 1; }
n_anon=$(ls 08_grading/anonymized_outputs/*.json 2>/dev/null | wc -l)
[ "$n_anon" -ge 9000 ] || { echo "HALT: anonymized outputs missing (found $n_anon)"; exit 1; }
echo "anonymized population: $n_anon records"

# 6. Ground truth
test -f 04_ground_truth/ground_truth.json || { echo "HALT: ground_truth.json missing"; exit 1; }

# 7. No stale grade process
pgrep -fl "apparatus.run grade" 2>/dev/null | grep -v grep && {
  echo "HALT: stale grade process running; kill it first"; exit 1; }
echo "no stale grade processes"

# 8. Old irr.json from prior attempts is moved out of the way (do not delete)
if [ -f 08_grading/irr.json ]; then
  mv 08_grading/irr.json "08_grading/irr.json.pre_13e_revised_$(date +%Y%m%d_%H%M%S).bak"
  echo "moved prior irr.json to .bak"
fi

# 9. All three API keys (the original 13e blocker)
python3 -c "
import os
from pathlib import Path
for line in Path('.env').read_text().splitlines():
    if '=' in line:
        k, v = line.split('=', 1); os.environ[k] = v.strip()
assert os.environ.get('ANTHROPIC_API_KEY','').startswith('sk-ant'), 'ANTHROPIC_API_KEY missing'
assert os.environ.get('OPENAI_API_KEY','').startswith('sk-'), 'OPENAI_API_KEY missing'
g = os.environ.get('GOOGLE_API_KEY','').strip()
assert g, 'GOOGLE_API_KEY MISSING — this was the original 13e blocker; halt until Cal pastes one from https://aistudio.google.com/apikey'
print('all three API keys set')
"
```

**Success criteria.** All nine preconditions print confirmation. If any
fails, halt and report which one. The `GOOGLE_API_KEY` precondition is
the most common blocker — do not work around it; halt and ask Cal.

---

## Task 1: Stage the sampled-subset directory

The `apparatus.run grade` CLI grades every JSON in the `--anonymized`
directory. To drive a sampled run without patching the CLI, stage a
fresh directory containing only the 700 sampled records via symlinks.

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

# Fresh staging directory
SAMPLE_DIR=08_grading/sample_anonymized_outputs
rm -rf "$SAMPLE_DIR"
mkdir -p "$SAMPLE_DIR"

# Symlink the 700 sampled records
python3 - <<'PY'
import json, os
from pathlib import Path
manifest = Path("08_grading/sample_manifest.jsonl")
src_dir = Path("08_grading/anonymized_outputs").resolve()
dst_dir = Path("08_grading/sample_anonymized_outputs")
n = 0
for line in manifest.read_text().splitlines():
    rec = json.loads(line)
    anon_id = rec["anon_id"]
    src = src_dir / f"{anon_id}.json"
    dst = dst_dir / f"{anon_id}.json"
    assert src.exists(), f"missing source: {src}"
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    os.symlink(src, dst)
    n += 1
print(f"staged {n} symlinks in {dst_dir}/")
PY

# Sanity
ls "$SAMPLE_DIR"/*.json | wc -l   # must print 700
```

**Success criteria.** Staging directory contains exactly 700 symlinks
that all resolve to existing files in `08_grading/anonymized_outputs/`.

---

## Task 2: Run the sampled grading

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

python3 -m apparatus.run grade \
  --anonymized 08_grading/sample_anonymized_outputs \
  --ground-truth 04_ground_truth/ground_truth.json \
  --judges-config 08_grading/judges_config.json \
  --out 08_grading \
  --double-grade-pct 0.10 \
  --double-grade-seed 20260618 \
  --skip-existing \
  --max-workers 3
```

**Flag notes:**
- `--anonymized 08_grading/sample_anonymized_outputs`: points at the
  staged subset directory built in Task 1 (700 symlinks). Critical
  difference from prior runs which pointed at the full 9000-record
  directory.
- `--double-grade-pct 0.10`: D-08 component (c). Was 0.20.
- `--double-grade-seed 20260618`: matches the sample seed for
  reproducibility.
- `--skip-existing`: if Task 2 is killed mid-run, re-fire the same
  command to resume from `08_grading/by_record/`.
- `--max-workers 3`: per-record concurrency across the three judges.

**Expected throughput.**
- 700 records × ~3 seconds (max of three parallel calls) ≈ 35 minutes
  of judge calls.
- Plus the 70-record IRR double-grade pass: +5 minutes.
- Plus rate-limit backoff, Gemini thinking-budget latency, retries:
  total wall clock ~90 min to 3 hours.

**Resume convention.** If killed, re-fire the same command. The
`--skip-existing` flag loads existing `08_grading/by_record/<anon_id>.json`
files and skips re-grading them. No API spend is wasted.

---

## Task 3: Monitor checkpoints accumulating

Run this every ~10 minutes while Task 2 is in flight:

```zsh
python3 - <<'PY'
import os, glob, json, time
TARGET = 700
n = len(glob.glob("08_grading/by_record/*.json"))
print(f"by_record checkpoints: {n}/{TARGET} ({n/TARGET*100:.1f}%)")
files = sorted(glob.glob("08_grading/by_record/*.json"),
               key=lambda f: -os.path.getmtime(f))
if files:
    most_recent = files[0]
    age_s = time.time() - os.path.getmtime(most_recent)
    print(f"most recent: {os.path.basename(most_recent)} ({age_s:.0f}s ago)")
    d = json.load(open(most_recent))
    print(f"  judges scored: {len(d.get('judge_scores', []))}")
    print(f"  ensemble: {d.get('ensemble') is not None}")
PY
```

**Success criteria.** Checkpoint count grows monotonically. The most
recent checkpoint is < 5 minutes old while the process is alive.

**Escalation triggers (do not silently work around):**
- After 30 minutes of execution, fewer than 100 checkpoints written →
  throughput far below the 3x-concurrent expectation; capture provider
  rate-limit responses and escalate.
- Any judge returning HTTP 5xx persistently beyond 120-second
  exponential backoff → escalate per-judge.
- Total API cost above $400 (sanity ceiling; expected ~$215) →
  halt and escalate.
- The Gemini judge errors with `GOOGLE_API_KEY` problems → halt; the
  precondition check missed something.

---

## Task 4: Halt-or-PROCEED check after main pass

```zsh
python3 - <<'PY'
import json
irr = json.load(open('08_grading/irr.json'))
print('main pass IRR:')
for pair, k in irr.get('pairwise_kappa', {}).items():
    print(f'  {pair}: {k:.3f}')
min_k = irr.get("min_pairwise_kappa")
print(f'  min pairwise kappa: {min_k}')
print(f'  halt: {irr.get("halt")}')

dg = irr.get('double_grade', {})
if dg:
    print(f"\ndouble-grade sample: {dg.get('sample_size')} records (seed {dg.get('seed')})")
    print(f"  pass1 min kappa: {dg.get('pass1_irr',{}).get('min_pairwise_kappa')}")
    print(f"  pass2 min kappa: {dg.get('pass2_irr',{}).get('min_pairwise_kappa')}")

print()
if min_k is None:
    print("DECISION: HALT — irr.json malformed")
elif min_k >= 0.40:
    print(f"DECISION: PROCEED (min kappa {min_k:.3f} >= 0.40 PROTOCOL_LOCK §8 threshold)")
else:
    print(f"DECISION: HALT (min kappa {min_k:.3f} < 0.40); diagnose judge pair disagreement")
PY
```

**Sonnet-self-grading flag.** D-08 documents that the Anthropic judge
(Sonnet) and the B1 baseline (also Sonnet) share a generation family.
Inspect per-system kappa specifically for B1 records:

```zsh
python3 - <<'PY'
import json, glob
from collections import defaultdict
import statistics

# Map anon_id -> system_id
mapping = json.load(open('07_system_outputs/anonymization_mapping.json'))

# Per-system score spreads (rough proxy; ensemble_scores.jsonl would be canonical)
files = glob.glob("08_grading/by_record/*.json")
by_sys = defaultdict(list)
for f in files:
    d = json.load(open(f))
    anon_id = d.get('anon_id')
    sys_id = mapping.get(anon_id, {}).get('system_id', '?')
    ens = d.get('ensemble')
    if ens is not None:
        by_sys[sys_id].append(ens)

print("per-system ensemble score (rough mean - check for B1 inflation vs others):")
for s in sorted(by_sys.keys()):
    scores = by_sys[s]
    if scores:
        # Best-effort numeric extraction; depends on ensemble shape
        try:
            nums = [x if isinstance(x,(int,float)) else x.get('score', 0) for x in scores]
            print(f"  {s:30s} n={len(scores):3d} mean={statistics.mean(nums):.3f}")
        except Exception:
            print(f"  {s:30s} n={len(scores):3d} (ensemble shape varies)")
PY
```

If B1's per-system mean is anomalously high relative to other baselines,
flag this in the report — D-08 anticipates this direction of bias.

---

## Report

`handoffs/HANDOFF_13e_revised_report_<YYYY-MM-DD>.md` with:
- D-08 component status: sample staged, Sonnet judge active, 10% IRR
- Total records graded (must be 700) + double-grade sample (~70)
- Per-judge call count, token usage, and cost (separated from any
  HANDOFF_13d residual sunk cost)
- Wall clock for 13e revised specifically
- Main pass per-pair kappa + double-grade pass per-pair kappa
- Halt decision (PROCEED or HALT) under PROTOCOL_LOCK §8 (≥0.40 binding)
- B1-column kappa inspection (Sonnet-self-grading bias check from D-08)
- Anomalies (rate limits, retries, judge timeouts, Gemini thinking-budget hits)
- Per-outcome ensemble score breakdown by system (the Section 5.4 fill data)

Commit message:
```
Handoff 13e revised (D-08): Phase 8 grading on N=700 stratified sample with Sonnet ensemble and 10% IRR double-grade. Total Phase 8 cost ~$215 (vs $1,700-$2,200 original plan). Compute-budget sampling per D-08 with power-analysis justification in Appendix X of the supplemental.
```

---

## What 13e-revised unblocks

- **HANDOFF_14 Phase 9 analysis** computes O1-O4 outcomes against the
  ensemble grades from the 700-record sample. Confidence intervals on
  per-outcome scores will be wider than full-coverage grading would have
  produced; report 95% CIs explicitly.
- **HANDOFF_15 deposit packaging** finalizes the Zenodo bundle including
  the sample_manifest.jsonl, sample_manifest_meta.json, judges_config.json,
  by_record/ checkpoints, irr.json, and ensemble_aggregated/.
- **Section 5.4 of `Mandate Data/Empirical Evidence Supplemental.tex`**
  gets populated with the numerical results once 13e-revised completes.
  The methodological framing is already final in that section.

## If kappa < 0.40 (halt path)

Under PROTOCOL_LOCK §8, kappa below 0.40 is a binding halt. Diagnostic
order under D-08:
1. Identify the lowest-kappa judge pair (likely Sonnet-Gemini or
   GPT-4o-Gemini given vendor-family disagreement patterns).
2. Identify the highest-disagreement outcome (likely O2 gap detection
   under the SME-skip caveat — judge consensus on "what counts as a
   missing-information probe" varies).
3. Check the Sonnet-B1 self-grading hypothesis: is the Sonnet judge
   systematically scoring B1 records higher than the other judges?
4. Escalate to Cal with the pairwise kappa table and the
   highest-disagreement outcome before deciding whether to publish under
   halt (discovery paper framing, drop the cross-system scoring layer)
   or re-grade with a different judge mix.
