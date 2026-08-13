# Codex Handoff 13e: Resume Phase 8 grading with per-record checkpoints + 3x concurrency

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-17
**Estimated wall clock:** 8 to 14 hours (3-way per-record concurrency + skip-existing resume from zero).
**Estimated API cost:** Whatever has not already been spent on the killed HANDOFF_13d in-memory work. If 13d burned ~$500 before kill, expect another ~$1,500 to complete the 9036 records under 13e. If 13d burned more, the remaining cost scales down proportionally only by however many records had partial scores written to disk (currently zero, so the full $1,500-$2,000 estimate stands).
**Blocked on:** HANDOFF_13d process killed cleanly; grader patches committed; the 8_grading by_record/ directory is fresh.

---

## Why this exists

HANDOFF_13d ran for 25+ hours with zero on-disk artifacts. Root cause:
the original grading pipeline accumulated 9000 records in memory and only
flushed via `pipe.save()` after the full main pass completed. A crash or
kill mid-run discarded all in-progress work. Cal opted to stop the run
intentionally and patch the grader before resuming, rather than gamble
more days against the same crash risk.

Two patches landed on project main:

1. **Per-record checkpointing in `grade_all`.** Each `GradedOutput` is
   written to `<out_dir>/by_record/<anon_id>.json` IMMEDIATELY as the
   record completes. Crash recovery loses only the most-recent in-flight
   record, not the entire pass.

2. **Per-record judge concurrency in `grade_output`.** The three judges
   per record run in a bounded `ThreadPoolExecutor` (default 3 workers).
   The judges are I/O-bound (each is an LLM API call); threads achieve
   roughly 3x throughput compared to serial.

Stage and commit with: `Patch grader for resumable per-record checkpointing + 3x judge concurrency (HANDOFF_13d 2026-06-17 halt: 25 hours with zero on-disk artifacts because original grader only flushed at end). Four regression tests covering checkpoint persistence, skip-existing resume, partial-checkpoint resume, and concurrent vs serial timing.`

The CLI gains two flags:
- `--skip-existing` (default off): load existing checkpoints and skip
  re-grading.
- `--max-workers N` (default 3): per-record judge concurrency.

The frozen MANDATE-primary v1 tag and the existing freeze tag chain are unaffected.

## Preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# 1. The patches are on project main
python3 -m apparatus.run grade --help 2>&1 | grep -q "skip-existing" \
  || { echo "HALT: --skip-existing flag missing"; exit 1; }
python3 -m apparatus.run grade --help 2>&1 | grep -q "max-workers" \
  || { echo "HALT: --max-workers flag missing"; exit 1; }
echo "both new CLI flags present"

# 2. Grading tests pass (regression guard) - 21 tests total
python3 -m pytest apparatus/grading/tests/test_grading.py -q 2>&1 | tail -3

# 3. Previous HANDOFF_13d process is fully terminated
pgrep -fl "apparatus.run grade" 2>/dev/null | grep -v grep && {
  echo "HALT: stale grade process still running; kill it first"; exit 1; }
echo "no stale grade processes"

# 4. The canonical 08_grading output tree is still clean (verifies the
#    13d kill did not partially write anything)
test -f 08_grading/irr.json && { echo "HALT: irr.json from prior run present; remove or rename first"; exit 1; }
test -d 08_grading/by_record && {
  n=$(ls 08_grading/by_record/*.json 2>/dev/null | wc -l)
  if [ "$n" -gt 0 ]; then
    echo "WARNING: by_record/ has $n existing checkpoints from a previous attempt; --skip-existing will preserve them"
  fi
}

# 5. Ground truth + judges config + anonymized outputs all present
test -f 04_ground_truth/ground_truth.json || { echo "HALT: ground_truth.json missing"; exit 1; }
test -f 08_grading/judges_config.json || { echo "HALT: judges_config.json missing"; exit 1; }
n_anon=$(ls 08_grading/anonymized_outputs/*.json 2>/dev/null | wc -l)
[ "$n_anon" -ge 9000 ] || { echo "HALT: anonymized outputs missing"; exit 1; }
echo "anonymized: $n_anon records"

# 6. All three API keys
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
```

**Success criteria.** All six preconditions print confirmation.

## Decision boundary

You may decide:
- Whether to write a brief 13d throughput report before launching 13e
  (recommended: capture API spend visible in the dashboards, elapsed time,
  process state from `ps` for the deposit's evidence trail).
- Commit incrementally after every ~1000 records committed.
- One retry on transient API rate-limit errors per judge per record.

You must escalate:
- If after 1 hour of 13e execution, the `08_grading/by_record/` directory
  has fewer than 100 checkpoints (signals throughput far below the
  3x-concurrent expectation; investigate per-call latency).
- Any judge returning HTTP 5xx persistently beyond exponential backoff up
  to 120 seconds.
- Total API cost above $2,500 (sanity ceiling).

You may not:
- Start a second concurrent grading process. The patched `--skip-existing`
  is the resume path; do not parallelize at the CLI invocation level.
- Modify ground truth or anonymized outputs.
- Lower `--max-workers` below 1 (would be no-op).

---

## Task 1: Capture the 13d throughput evidence (optional but recommended)

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

cat > handoffs/HANDOFF_13d_throughput_report_$(date +%Y-%m-%d).md <<'EOF'
# HANDOFF_13d Throughput Report

The HANDOFF_13d grading process was killed intentionally at <ELAPSED_HHMM>
after the diagnosis that the original grader only flushes outputs at the
end of the full 9000-record main pass. With zero on-disk artifacts after
25+ hours of execution, the crash/kill exposure for continuing the run
was higher than the cost of stopping and patching.

## Process state at kill time
- PID: <PID>
- Elapsed: <HH:MM:SS>
- CPU: <pcpu>
- RSS: <rss>
- VSZ: <vsz>

## API spend (visible at provider dashboards)
- Anthropic (Claude Opus): $<...>
- OpenAI (GPT-4o): $<...>
- Google (Gemini 2.5 Pro): $<...>
- Total estimated 13d burn: $<...>

## What was preserved
- ground_truth.json on disk
- judges_config.json on disk
- the Gemini max_tokens patch (HANDOFF_13d)
- the double_grade patch (HANDOFF_13c)

## What was lost
- ~25 hours of wall clock
- API spend listed above
- ~N records of in-memory partial grading

## Lesson captured for the apparatus
The grader pipeline now writes per-record checkpoints (HANDOFF_13e patches)
so the same failure mode cannot recur. The next grading run resumes from
zero with the patched concurrent + checkpointing implementation.
EOF
```

Edit the placeholders with the actual numbers from the running state
snapshot Codex captured before kill.

## Task 2: Run the resumable concurrent grading

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

python3 -m apparatus.run grade \
  --anonymized 08_grading/anonymized_outputs \
  --ground-truth 04_ground_truth/ground_truth.json \
  --judges-config 08_grading/judges_config.json \
  --out 08_grading \
  --double-grade-pct 0.20 \
  --double-grade-seed 20260616 \
  --skip-existing \
  --max-workers 3
```

**What the new flags do.**
- `--skip-existing`: if `08_grading/by_record/<anon_id>.json` exists for a
  given anon_id, load it and skip re-grading. Resume support.
- `--max-workers 3`: run the three judges per record in parallel
  (`ThreadPoolExecutor`). Each judge call is an independent API call to a
  different provider; threading achieves ~3x throughput.

**Expected throughput.**
- Serial (max_workers=1): ~3 seconds per call × 3 judges × 9036 records
  = ~22 hours minimum, more with rate limits and Gemini's 8192-token
  thinking budget. This is what 13d was doing.
- Concurrent (max_workers=3): ~3 seconds per record (max of three
  parallel calls, not sum) × 9036 records = ~7.5 hours. Plus retries and
  rate-limit backoff: ~8 to 14 hours wall clock.

**Resume convention.** If the process is killed or crashes, re-fire the
same command. The `--skip-existing` flag loads every
`08_grading/by_record/<anon_id>.json` that already exists; only the
remaining records get re-graded. No API spend is wasted on already-graded
records.

## Task 3: Verify checkpoints accumulating

Run this periodically (every ~30 minutes) while Task 2 is in flight to
confirm the grader is actually flushing to disk:

```zsh
python3 - <<'PY'
import os, glob, json, time
n = len(glob.glob("08_grading/by_record/*.json"))
print(f"by_record checkpoints: {n}/9036 ({n/9036*100:.1f}%)")
# Spot-check the most recent checkpoint
files = sorted(glob.glob("08_grading/by_record/*.json"),
               key=lambda f: -os.path.getmtime(f))
if files:
    most_recent = files[0]
    age_s = time.time() - os.path.getmtime(most_recent)
    print(f"most recent: {most_recent.split('/')[-1]} ({age_s:.0f}s ago)")
    d = json.load(open(most_recent))
    print(f"  judges scored: {len(d.get('judge_scores', []))}")
    print(f"  ensemble: {d.get('ensemble') is not None}")
PY
```

**Success criteria.** Checkpoint count grows monotonically. The most
recent checkpoint is fresh (< 5 minutes old) while the process is alive.

## Task 4: Halt check after the main pass completes

Same as the original HANDOFF_13c Task 4:

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
PY
```

## Report

`handoffs/HANDOFF_13e_report_<YYYY-MM-DD>.md` with:
- 13d throughput report linked
- Total records graded
- Per-judge cost (separated from any 13d residual)
- Wall clock for 13e specifically (separate from 13d sunk cost)
- Main pass kappa + double-grade pass kappa
- Halt decision (PROCEED or HALT)
- Anomalies (rate limits, retries, judge timeouts)

Commit message: `Handoff 13e: Phase 8 grading resume with per-record checkpoints + 3x concurrency`.

## What 13e unblocks

After 13e PROCEED:
- HANDOFF_14 Phase 9 analysis (computes O1-O4 outcomes against the
  ensemble grades).
- HANDOFF_15 deposit packaging.

If 13e produces a low kappa under the SME-skip caveat, the protocol halt
is binding. Diagnosis at that point: which judge pair has the lowest kappa,
which outcome they disagree most on, whether the disagreement correlates
with output structure (MANDATE_AS_CODE vs baseline_specification) or
domain.
