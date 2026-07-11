# Codex Handoff 13f: Judge retry+backoff for transient provider errors + relaunch D-08 sampled grading

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-18
**Supersedes:** `HANDOFF_13e_revised_D08_sampled_sonnet.md` (attempt 05 halted on Gemini 503 high-demand; patch needed before relaunch is safe)
**Patches applied on project main, pending stage+commit by Codex.**
**Deviation reference:** D-08 (Section 17) and a brief D-08 amendment paragraph (Section 17, new) noting the attempt 05 halt + retry patch.
**Estimated wall clock:** 90 minutes to 3 hours (+ up to 65s per retried record for backoff)
**Estimated API cost:** ~$215 projected (same as 13e revised; retry does not add records, only re-attempts)

---

## Why this exists

HANDOFF_13e revised attempt 05 launched cleanly after the GOOGLE_API_KEY
blocker was resolved, but was manually halted after 6 of 6 records hit
the canonical checkpoint directory and **4 of those 6 had Gemini 503
UNAVAILABLE errors** that the original Judge implementation flattened
into permanent judge errors with no retry. Cal halted the run before
the contamination spread; the 6 partial checkpoints were quarantined to
`08_grading/failed_attempts/HANDOFF_13e_revised_attempt_05_20260618_gemini_503/`
and the canonical `08_grading/by_record/` was restored to 0.

Two architecture bugs surfaced, both the same class as the
HANDOFF_13d failure mode (silent persistence of incomplete state):

1. **No retry on transient 5xx/429 errors.** The old `Judge.grade()`
   wrapped `client.generate()` in a single try/except and flattened
   ANY exception into a permanent `JudgeScore.error`. Gemini high-demand
   503s are exactly the case retry+backoff exists for; the original
   code did not retry.

2. **Silent persistence of partial-failure ensembles.** When one judge
   errored, `pipeline.grade_all` still wrote the GradedOutput (with 2
   valid + 1 errored judge_scores) to `08_grading/by_record/<anon_id>.json`,
   silently degrading the 3-judge ensemble to 2 for those records. On
   `--skip-existing` resume, those records would be reloaded as if they
   were complete and never re-graded.

## What changed on project main

### `apparatus/grading/judge.py`

- Added retry+backoff layer: `Judge._call_with_retry(...)` wraps the
  LLM client call. Default backoff schedule: `(5.0, 15.0, 45.0)`
  seconds — 4 total attempts, ~65s worst-case before giving up on one
  call. Tests pass `(0.0, 0.0, 0.0)` to skip real sleeping.
- Retryable patterns (regex against `"%r %s" % (exc, exc)`):
  `\b503\b`, `\b502\b`, `\b504\b`, `\b429\b`, `UNAVAILABLE`,
  `high demand`, `overloaded`, `rate.?limit`, `too many requests`,
  `timeout`, `timed out`, `connection reset`, `temporarily`.
  Pattern-matching on exception text is intentional: the provider
  SDKs each raise their own hierarchy (google.genai.errors.ServerError,
  anthropic.APIStatusError, openai.RateLimitError, etc.); coupling to
  specific exception types here would force the apparatus to import
  optional provider dependencies.
- `Judge.__init__` gained `retry_backoff_sec` and `sleep_fn` parameters
  for test injection; defaults preserve production behavior.
- `Judge.grade()` and `Judge.check_schema()` now call
  `_call_with_retry()` instead of `client.generate()` directly.
- `Judge.describe()` now reports the retry schedule.

### `apparatus/grading/pipeline.py`

- `grade_all()` checks every judge in the per-record ensemble for
  `parse_ok AND not error`. If ALL three judges succeeded, the
  GradedOutput is written to `08_grading/by_record/<anon_id>.json` as
  before. If ANY judge errored after retries, the partial GradedOutput
  goes to `08_grading/incomplete_grades/<anon_id>.json` instead, and a
  stderr warning is emitted in real time. The record is NOT in the
  returned `graded` list.
- On `--skip-existing` resume, records with no `by_record/<anon_id>.json`
  are naturally re-graded. The `incomplete_grades/` entries are for
  operator inspection only and do not count as checkpoints.
- New summary print includes `incomplete N` count.

### `apparatus/baselines/llm_client.py`

- `MockLLMClient` extended: a queued response that is a `BaseException`
  instance is RAISED instead of returned. Lets tests script transient
  provider errors (e.g. `RuntimeError("503 UNAVAILABLE: high demand")`)
  and exercise the retry path.

### `apparatus/grading/tests/test_grading.py`

- Five new regression tests covering the patch:
  - `test_judge_retries_on_transient_5xx_then_succeeds` — two 503s
    followed by a valid score; assert parse_ok=True, error="", 2 retries.
  - `test_judge_returns_error_after_retry_exhaustion` — four 503s in
    a row; assert errored JudgeScore preserves "503"/"UNAVAILABLE" in
    the error message.
  - `test_judge_does_not_retry_non_retryable_error` — 401 auth error;
    assert no sleeps fired and JudgeScore is errored immediately.
  - `test_grade_all_refuses_to_checkpoint_partial_failure` — judge 3
    fails permanently; assert `by_record/OUT-FAIL.json` does NOT exist,
    `incomplete_grades/OUT-FAIL.json` DOES exist, returned graded list
    excludes the record.
  - `test_grade_all_resumes_partial_failure_for_re_grading` — after
    incomplete first pass, second pass with `--skip-existing` and a
    healthy judge 3 re-grades the record and writes the successful
    checkpoint to `by_record/`.

Total test count: was 22, is now **27**.

## Stage and commit message

```
Handoff 13f: Judge retry+backoff for transient provider errors + refuse-to-checkpoint partial failures (HANDOFF_13e_revised_attempt_05 2026-06-18 halt: 4 of 6 records hit Gemini 503 UNAVAILABLE high-demand and were flattened to permanent judge errors with no retry, silently degrading the 3-judge ensemble to 2). Retry layer: 4 attempts with 5s/15s/45s exponential backoff on 5xx/429/timeout patterns. Pipeline: incomplete grades go to incomplete_grades/ not by_record/, so --skip-existing re-grades on resume. Five new regression tests; 22 -> 27 total.
```

---

## Preconditions

```zsh
cd "$HOME/Desktop/Desktop - lattice-ws01/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# 1. CLI flags still present
python3 -m apparatus.run grade --help 2>&1 | grep -q "skip-existing" \
  || { echo "HALT: --skip-existing missing"; exit 1; }
python3 -m apparatus.run grade --help 2>&1 | grep -q "max-workers" \
  || { echo "HALT: --max-workers missing"; exit 1; }
echo "CLI flags present"

# 2. Grading regression tests pass (must be 27, up from 22)
TEST_OUT=$(python3 -m pytest apparatus/grading/tests/test_grading.py -q 2>&1)
echo "$TEST_OUT" | tail -3
echo "$TEST_OUT" | grep -q "27 passed" \
  || { echo "HALT: expected 27 tests passing, got otherwise"; exit 1; }
echo "27/27 tests passed"

# 3. Patch presence smoke
python3 -c "
from apparatus.grading.judge import Judge, _is_retryable_error, _DEFAULT_RETRY_BACKOFF_SEC
assert _is_retryable_error(RuntimeError('503 UNAVAILABLE: high demand'))
assert not _is_retryable_error(RuntimeError('401 invalid API key'))
assert _DEFAULT_RETRY_BACKOFF_SEC == (5.0, 15.0, 45.0)
print('retry+backoff layer present')
"

# 4. judges_config.json under D-08 Sonnet
grep -q "claude-sonnet-4-6" 08_grading/judges_config.json \
  || { echo "HALT: judges_config.json missing Sonnet"; exit 1; }
echo "judges_config under D-08"

# 5. Sample manifest unchanged
test -f 08_grading/sample_manifest.jsonl
n_sample=$(wc -l < 08_grading/sample_manifest.jsonl)
[ "$n_sample" -eq 700 ] || { echo "HALT: sample_manifest.jsonl has $n_sample lines"; exit 1; }
echo "sample manifest: 700"

# 6. by_record/ is empty (Cal reset after attempt 05 halt)
n_by_rec=$(ls 08_grading/by_record/*.json 2>/dev/null | wc -l)
[ "$n_by_rec" -eq 0 ] || { echo "HALT: by_record/ has $n_by_rec entries; expected 0"; exit 1; }
echo "by_record/: clean"

# 7. incomplete_grades/ does not exist or is empty
if [ -d 08_grading/incomplete_grades ]; then
  n_inc=$(ls 08_grading/incomplete_grades/*.json 2>/dev/null | wc -l)
  [ "$n_inc" -eq 0 ] || { echo "HALT: incomplete_grades/ has $n_inc stale entries; remove them first"; exit 1; }
fi
echo "incomplete_grades/: clean"

# 8. attempt 05 quarantine is preserved (not removed)
QUAR=08_grading/failed_attempts/HANDOFF_13e_revised_attempt_05_20260618_gemini_503
test -d "$QUAR" \
  || { echo "HALT: attempt 05 quarantine missing — it must be preserved as evidence"; exit 1; }
echo "attempt 05 quarantine preserved"

# 9. Stale grade process check
pgrep -fl "apparatus.run grade" 2>/dev/null | grep -v grep && {
  echo "HALT: stale grade process running; kill it first"; exit 1; }
echo "no stale grade processes"

# 10. API keys (all three; attempt 05 confirmed all three working in production)
python3 -c "
import os
from pathlib import Path
for line in Path('.env').read_text().splitlines():
    if '=' in line:
        k, v = line.split('=', 1); os.environ[k] = v.strip()
assert os.environ.get('ANTHROPIC_API_KEY','').startswith('sk-ant'), 'ANTHROPIC_API_KEY missing'
assert os.environ.get('OPENAI_API_KEY','').startswith('sk-'), 'OPENAI_API_KEY missing'
assert os.environ.get('GOOGLE_API_KEY','').strip(), 'GOOGLE_API_KEY missing'
print('all three API keys set')
"
```

**Success criteria.** All 10 preconditions print confirmation. If any
fails, halt and report which one.

---

## Task 1: Re-stage the sample symlink directory (idempotent)

Same as HANDOFF_13e revised Task 1. The staging directory may already
exist from attempt 05; recreating it is safe.

```zsh
cd "$HOME/Desktop/Desktop - lattice-ws01/MANDATE Evaluation/mandate_eval_2026Q2"

SAMPLE_DIR=08_grading/sample_anonymized_outputs
rm -rf "$SAMPLE_DIR"
mkdir -p "$SAMPLE_DIR"

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

ls "$SAMPLE_DIR"/*.json | wc -l   # must print 700
```

---

## Task 2: Run the patched sampled grading

Same command as HANDOFF_13e revised:

```zsh
cd "$HOME/Desktop/Desktop - lattice-ws01/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

python3 -m apparatus.run grade \
  --anonymized 08_grading/sample_anonymized_outputs \
  --ground-truth 04_ground_truth/ground_truth.json \
  --judges-config 08_grading/judges_config.json \
  --out 08_grading \
  --double-grade-pct 0.10 \
  --double-grade-seed 20260618 \
  --skip-existing \
  --max-workers 3 \
  2> >(tee -a "logs/HANDOFF_13f_grade_$(date +%Y%m%d_%H%M%S).stderr" >&2)
```

The `2> >(tee ...)` redirection captures every stderr `INCOMPLETE`
warning to a log file in `logs/` for the report. Stdout goes to the
terminal as before.

**Expected throughput.**
- 700 records × ~3 seconds (max of three parallel calls) ≈ 35 minutes
  of judge calls.
- Plus 10% IRR double-grade (70 records): +5 minutes.
- Plus retry backoff for transient errors (worst case +65s per
  retried record; in practice well under that).
- Total wall clock: 90 min to 3 hours.

**Resume convention.** If killed, re-fire the same command. The
`--skip-existing` flag loads `08_grading/by_record/<anon_id>.json`
files; records that landed in `incomplete_grades/` are naturally
re-graded because there's no `by_record/` entry for them.

---

## Task 3: Real-time monitoring (run every ~10 minutes)

```zsh
python3 - <<'PY'
import os, glob, json, time
TARGET = 700
n_ok = len(glob.glob("08_grading/by_record/*.json"))
n_inc = len(glob.glob("08_grading/incomplete_grades/*.json"))
print(f"by_record (successful): {n_ok}/{TARGET} ({n_ok/TARGET*100:.1f}%)")
print(f"incomplete_grades (will re-grade): {n_inc}")

if n_inc > 0:
    # Per-judge incomplete count: how many incomplete records had judge X fail?
    from collections import Counter
    bad_judges = Counter()
    for f in glob.glob("08_grading/incomplete_grades/*.json"):
        d = json.load(open(f))
        for s in d.get("judge_scores", []):
            if s.get("error"):
                bad_judges[s.get("judge_id","?")] += 1
    print("\nincomplete-grade attribution:")
    for j, c in bad_judges.most_common():
        print(f"  {j}: {c}")

files = sorted(glob.glob("08_grading/by_record/*.json"),
               key=lambda f: -os.path.getmtime(f))
if files:
    age_s = time.time() - os.path.getmtime(files[0])
    print(f"\nmost recent successful checkpoint: {os.path.basename(files[0])} ({age_s:.0f}s ago)")
PY
```

**Success criteria.** `by_record/` count grows monotonically. Most
recent checkpoint < 5 minutes old while the process is alive.

**Escalation triggers (halt and report; do not silently continue):**
- After 30 minutes, `by_record/` count is < 30 → **catastrophic**
  throughput (judges not responding at all); escalate. Healthy-but-slow
  is ~60-90 records in 30 min, NOT a halt condition: max(3 parallel
  judges) is realistically ~25-30s per record because Sonnet generates
  ~800 tokens at ~50 tok/s and Gemini's thinking budget adds latency.
  The original 100-in-30-min threshold was over-tight; recalibrated
  2026-06-18 after the second retry halted at 65/30min on clean output.
- `incomplete_grades/` count exceeds 50 (> 7% of the sample) → the
  retry layer is not catching the provider errors; escalate. The patch
  is designed to make per-record incomplete rate << 1% under normal
  provider conditions; high-demand windows can push it up, but >7% is
  unsustainable.
- One judge dominates `incomplete_grades` (e.g., judge_3_gemini_pro >
  90% of the incompletes) → that provider is in sustained outage;
  escalate to pause/resume the run.
- Total API cost above $400 (sanity ceiling; actual projection
  recalibrated to ~$53 total based on 65-record empirical cost of
  $0.069/record observed in the 2026-06-18 retry) → halt and escalate.

---

## Task 4: After the main pass — second pass to clean up incompletes

If `incomplete_grades/` accumulated entries, re-fire the same Task 2
command. `--skip-existing` will preserve the records that already
landed in `by_record/` and only re-grade the incomplete ones (since
they have no checkpoint). This is the natural cleanup path; no manual
intervention needed.

```zsh
# Re-fire after waiting ~30 minutes for provider conditions to improve
sleep 1800
python3 -m apparatus.run grade \
  --anonymized 08_grading/sample_anonymized_outputs \
  --ground-truth 04_ground_truth/ground_truth.json \
  --judges-config 08_grading/judges_config.json \
  --out 08_grading \
  --double-grade-pct 0.10 \
  --double-grade-seed 20260618 \
  --skip-existing \
  --max-workers 3 \
  2> >(tee -a "logs/HANDOFF_13f_grade_resume_$(date +%Y%m%d_%H%M%S).stderr" >&2)
```

**Stop criterion.** Stop re-firing when either:
- (a) `by_record/` has 700 entries AND `incomplete_grades/` is empty
  or hasn't grown — full success.
- (b) Three consecutive re-fires fail to reduce `incomplete_grades/`
  → the provider issue is sustained; escalate to PI for scope decision
  (the affected records can be either dropped from the sample with a
  documented sample-shrinkage deviation, or the run can wait days
  for the provider).

Before each re-fire: delete the `incomplete_grades/<anon_id>.json`
entries for records that ARE now in `by_record/` (paranoia cleanup):

```zsh
python3 - <<'PY'
import os, glob
ok = set(os.path.basename(f) for f in glob.glob("08_grading/by_record/*.json"))
for f in glob.glob("08_grading/incomplete_grades/*.json"):
    if os.path.basename(f) in ok:
        os.remove(f)
        print(f"cleaned stale incomplete: {f}")
PY
```

---

## Task 5: Halt-or-PROCEED check after the sample is complete

Same as HANDOFF_13e revised Task 4 (Cohen's κ ≥ 0.40 under
PROTOCOL_LOCK §8) and the Sonnet-self-grading B1 inspection.

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
    print(f"\ndouble-grade sample: {dg.get('sample_size')} (seed {dg.get('seed')})")
    print(f"  pass1 min kappa: {dg.get('pass1_irr',{}).get('min_pairwise_kappa')}")
    print(f"  pass2 min kappa: {dg.get('pass2_irr',{}).get('min_pairwise_kappa')}")

print()
if min_k is None:
    print("DECISION: HALT — irr.json malformed")
elif min_k >= 0.40:
    print(f"DECISION: PROCEED (min kappa {min_k:.3f} >= 0.40)")
else:
    print(f"DECISION: HALT (min kappa {min_k:.3f} < 0.40); diagnose")
PY
```

---

## Report

`handoffs/HANDOFF_13f_report_<YYYY-MM-DD>.md`:

- Patch presence confirmation: `_call_with_retry` in judge.py,
  incomplete_grades branch in pipeline.py, MockLLMClient exception
  raising, 27 regression tests passing.
- D-08 component status (same as 13e revised report).
- Re-fire log: how many passes were needed; per-pass `incomplete_grades`
  counts; total retries observed in the stderr logs.
- Final `by_record/` count (target 700) and `incomplete_grades/` count
  (target 0).
- Per-judge call count, token usage, cost (sample period + retry
  amplification).
- Wall clock for 13f specifically.
- Main pass pairwise κ + double-grade pass pairwise κ.
- Halt decision (PROCEED or HALT) under PROTOCOL_LOCK §8.
- B1-column κ inspection (Sonnet self-grading bias check from D-08).
- Anomalies and provider weather notes.

Commit message: see the "Stage and commit message" block above.

---

## What 13f unblocks

- **HANDOFF_14 Phase 9 analysis** computes O1-O4 outcomes against the
  ensemble grades from the now-clean 700-record sample.
- **Section 5.4 of `Mandate Data/Empirical Evidence Supplemental.tex`**
  gets populated with the numerical results.
- **Section 17 deviation log** gets a brief amendment paragraph noting
  the attempt 05 halt and the 13f retry-layer patch (the lead analyst
  drafts that in the same pass as Section 5.4 population).

## If the patch surfaces a different failure class

If incomplete_grades/ accumulates rapidly even on a known-quiet
provider window, the failure class is not transient 5xx — it could be:
- Gemini thinking-budget exhaustion (the 8192-token safety margin from
  HANDOFF_13c may be insufficient for some prompts).
- Anthropic returning empty/malformed JSON under load (parse failure,
  not network failure; the retry pattern catches 5xx, not parse errors).
- Schema-violation prompts (the grader returns text that doesn't have
  the expected keys).

Inspect a few `incomplete_grades/*.json` files: which judge errored,
what does `raw_text` look like for the failed judge, what does the
`error` string say. Report the failure-class breakdown before
escalating.
