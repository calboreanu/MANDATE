# Codex Handoff 17d: Migrate the Binding-refusal patch to upstream AEGIS

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-04
**Estimated wall clock:** 20 to 40 minutes (upstream branch + 1443-test AEGIS suite + tag + re-extract + stub verify).
**Blocked on:** `~/Desktop/AEGIS` (or `$AEGIS_PATH`) is a clean git working tree. HANDOFF_17c PROCEED (the side-load patch is verified and committed in this project on `feature/binding-refusal-as-gap-sideload`).

---

## Why this exists

HANDOFF_17b applied the Binding structured-refusal patch via Path B (side-load into this project's `AEGIS-eval/` on a project feature branch) because the upstream AEGIS repository at `~/Desktop/AEGIS` was dirty. HANDOFF_17c verified the patch fires correctly end to end (Lane 3 deterministic stub-adapter replay) and does not over-fire on non-refusal scenarios (Lane 1 Volt + CrowdStrike sanity). 17d migrates the verified patch off the side-load and onto a proper upstream-AEGIS feature branch, cuts the candidate v2 tag, and re-extracts into a sister `AEGIS-eval-v2/` so the formal Phase 6 study (which still imports from `./AEGIS-eval/` at the v1 tag) is structurally unchanged.

The side-load branch `feature/binding-refusal-as-gap-sideload` in this project stays as the in-project verification snapshot; project `main` already points at the v1 baseline; the formal Phase 6 study is unaffected.

**Definition of done.**

1. Upstream AEGIS at `$AEGIS_PATH` carries a new branch `feature/binding-refusal-as-gap` off the v1 tag, with one commit containing the four-file patch + the `tests/test_binding_refusal.py` unit-test file.
2. AEGIS's own test suite passes on the branch (target: same `1443 passed, 27 skipped` baseline HANDOFF_17b observed; one new test file should add the five refusal cases, target 1448 passed).
3. A new annotated tag `mandate-eval-primary-2026q2-v2-candidate-binding-refusal` points at the feature-branch commit.
4. `AEGIS-eval-v2/` directory in this project materializes the candidate tag via `setup/recreate_aegis_eval.sh --tag <candidate-tag>`.
5. The HANDOFF_17c Lane 3 deterministic stub-adapter test passes against `AEGIS-eval-v2/`.
6. The v1 tag is unchanged (`git rev-parse mandate-eval-primary-2026q2-v1` returns the same commit it did at the start of this handoff).
7. Project `main` branch in this project is unchanged.
8. The side-load branch `feature/binding-refusal-as-gap-sideload` is left intact as the verification snapshot.
9. Handoff report at `handoffs/HANDOFF_17d_report_<YYYY-MM-DD>.md`.

## Preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

# 1. Confirm side-load patch is present in this project
git rev-parse --verify feature/binding-refusal-as-gap-sideload >/dev/null \
  && echo "side-load branch present" || { echo "side-load branch MISSING"; exit 1; }

# 2. Confirm upstream AEGIS is clean and has the v1 tag
: "${AEGIS_PATH:=$HOME/Desktop/AEGIS}"
[ -d "$AEGIS_PATH/.git" ] || { echo "AEGIS_PATH not a git repo: $AEGIS_PATH"; exit 1; }
DIRTY="$(git -C "$AEGIS_PATH" status --porcelain | head -1)"
if [ -n "$DIRTY" ]; then
  echo "HALT: upstream AEGIS at $AEGIS_PATH has uncommitted changes:"
  git -C "$AEGIS_PATH" status --short
  exit 1
fi
git -C "$AEGIS_PATH" rev-parse --verify mandate-eval-primary-2026q2-v1^{commit} >/dev/null \
  || { echo "HALT: v1 tag missing in upstream AEGIS"; exit 1; }

V1_COMMIT="$(git -C "$AEGIS_PATH" rev-parse mandate-eval-primary-2026q2-v1^{commit})"
echo "v1 tag at upstream commit: $V1_COMMIT"

# 3. Confirm the 5 patched files exist on the side-load branch
git show feature/binding-refusal-as-gap-sideload:AEGIS-eval/src/aegis/llm/response_parser.py | head -1 >/dev/null \
  && echo "response_parser.py present on side-load" || { echo "missing"; exit 1; }
git show feature/binding-refusal-as-gap-sideload:AEGIS-eval/src/mandate/llm_support.py | head -1 >/dev/null \
  && echo "llm_support.py present on side-load" || { echo "missing"; exit 1; }
git show feature/binding-refusal-as-gap-sideload:AEGIS-eval/src/mandate/roles/binding.py | head -1 >/dev/null \
  && echo "binding.py present on side-load" || { echo "missing"; exit 1; }
git show feature/binding-refusal-as-gap-sideload:AEGIS-eval/src/mandate/pipeline.py | head -1 >/dev/null \
  && echo "pipeline.py present on side-load" || { echo "missing"; exit 1; }
git show feature/binding-refusal-as-gap-sideload:AEGIS-eval/tests/test_binding_refusal.py | head -1 >/dev/null \
  && echo "test_binding_refusal.py present on side-load" || { echo "missing"; exit 1; }
```

**Success criteria.** Side-load branch present in this project, upstream AEGIS clean, v1 tag present in upstream AEGIS, all five patched files retrievable from the side-load branch.

**On HALT here.** If upstream AEGIS is dirty, stop and write the report. Do not stash, do not auto-commit upstream changes; that is a PI-only decision.

## Decision boundary

You may decide:
- Whether to use git-cherry-pick or file-copy to bring the patch over (file-copy is fine since the side-load and v1 share the same baseline; cherry-pick across repositories isn't trivial in git).
- The annotated-tag commit message text, as long as it names the diagnostic motivation.

You must escalate:
- The AEGIS test suite drops a previously-passing test on the feature branch. The patch is supposed to be additive; existing tests should not regress.
- The candidate tag already exists in upstream AEGIS from a prior attempt; in that case, run `git tag -d` only if PI confirms it should be replaced.
- A diff between the v1 baseline files and the side-load patched files unexpectedly touches files outside the four patched + one new test file.

You may not:
- Move or recreate the `mandate-eval-primary-2026q2-v1` tag in upstream AEGIS.
- Modify `main` in upstream AEGIS.
- Modify the side-load branch in this project (leave it as the verification snapshot).
- Modify the project's `main` branch.

---

## Task 1: Branch + patch in upstream AEGIS

```zsh
: "${AEGIS_PATH:=$HOME/Desktop/AEGIS}"
PROJECT_ROOT="$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

cd "$AEGIS_PATH"
git checkout mandate-eval-primary-2026q2-v1
git checkout -b feature/binding-refusal-as-gap
git log --oneline -1

# Pull the five files verbatim from the side-load branch via the project
cd "$PROJECT_ROOT"
git show feature/binding-refusal-as-gap-sideload:AEGIS-eval/src/aegis/llm/response_parser.py \
  > "$AEGIS_PATH/src/aegis/llm/response_parser.py"
git show feature/binding-refusal-as-gap-sideload:AEGIS-eval/src/mandate/llm_support.py \
  > "$AEGIS_PATH/src/mandate/llm_support.py"
git show feature/binding-refusal-as-gap-sideload:AEGIS-eval/src/mandate/roles/binding.py \
  > "$AEGIS_PATH/src/mandate/roles/binding.py"
git show feature/binding-refusal-as-gap-sideload:AEGIS-eval/src/mandate/pipeline.py \
  > "$AEGIS_PATH/src/mandate/pipeline.py"

mkdir -p "$AEGIS_PATH/tests"
git show feature/binding-refusal-as-gap-sideload:AEGIS-eval/tests/test_binding_refusal.py \
  > "$AEGIS_PATH/tests/test_binding_refusal.py"

# Verify the diff against v1 is the expected five files only
cd "$AEGIS_PATH"
git status
git diff --stat
```

**Success criteria.** Exactly five files differ from the v1 baseline: `src/aegis/llm/response_parser.py`, `src/mandate/llm_support.py`, `src/mandate/roles/binding.py`, `src/mandate/pipeline.py`, `tests/test_binding_refusal.py`. No other files touched. If any other file shows in the diff, stop and report.

## Task 2: AEGIS test suite on the feature branch

```zsh
cd "$AEGIS_PATH"
# AEGIS's own test runner; try the conventional patterns in order
python3 -m pytest -q 2>&1 | tail -15
```

**Success criteria.** All previously-passing AEGIS tests still pass. The new `tests/test_binding_refusal.py` adds five passing cases. Target line: `1448 passed, 27 skipped` (or whatever the v1 baseline reported + 5). If any pre-existing test fails on this branch, the patch has introduced a regression — stop, do not commit, report.

## Task 3: Commit and tag the candidate

```zsh
cd "$AEGIS_PATH"
git add -A
git status --short
git commit -m "Binding role: surface structured {error: ...} refusals as gap reports

Detect mandate-binding emitting a clean JSON {error: <text>} payload
when the upstream pipeline state is internally contradictory (anchor
demands N options, Decomposition emitted one). Treat the refusal as a
structured signal: short-circuit the parse retry loop, attach the
verbatim model text to the role artifact, run the deterministic
recommendation as a fallback summary, and append a
GapSpec(UNASSESSABLE_RISK, detected_by='Binding') to gap_reports.

Companion to MANDATE-eval HANDOFF_16c diagnostic (SVB from-binaries
run, 2026-06-04) and HANDOFF_17c verification. The model is not
malfunctioning; it is honestly refusing to bind, and its reasoning
belongs in gap_reports rather than the parse-failure fallback path.

Candidate for MANDATE-primary v2. Tag mandate-eval-primary-2026q2-v1
is unchanged."

git tag -a mandate-eval-primary-2026q2-v2-candidate-binding-refusal \
       -m "MANDATE-primary v2 candidate: Binding structured-refusal as gap_report

Verified at unit level (1448 AEGIS tests passing including 5 new
refusal cases) and at deterministic-replay level (HANDOFF_17c Lane 3
stub-adapter replay of the HANDOFF_16c captured refusal payload).
Does not over-fire on non-refusal scenarios (Lane 1: Volt + CrowdStrike
v2 clean). See MANDATE-eval handoffs 17b, 17c, 17d for the full chain."

git log --oneline -3
git tag --list "mandate-eval-primary*"
git rev-parse mandate-eval-primary-2026q2-v1
git rev-parse mandate-eval-primary-2026q2-v2-candidate-binding-refusal
```

**Success criteria.** Exactly one new commit on `feature/binding-refusal-as-gap`. New annotated tag points at that commit. The v1 tag's commit hash is unchanged from the start of Task 1. `main` in upstream AEGIS is unchanged.

## Task 4: Materialize the candidate tag into `AEGIS-eval-v2/`

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

# Use the existing recreate script with --tag pointing at the candidate
FORCE=1 bash setup/recreate_aegis_eval.sh \
  --aegis "${AEGIS_PATH:-$HOME/Desktop/AEGIS}" \
  --tag mandate-eval-primary-2026q2-v2-candidate-binding-refusal

# The script writes into AEGIS-eval/ by default; we want a sister dir
# instead, so the v1 baseline at ./AEGIS-eval/ stays put.
# If the script doesn't take an output-dir flag, do it manually:
if [ ! -d AEGIS-eval-v2 ]; then
  TAG=mandate-eval-primary-2026q2-v2-candidate-binding-refusal
  mkdir -p AEGIS-eval-v2
  git -C "${AEGIS_PATH:-$HOME/Desktop/AEGIS}" archive --format=tar "$TAG" | tar -x -C AEGIS-eval-v2
  COMMIT="$(git -C "${AEGIS_PATH:-$HOME/Desktop/AEGIS}" rev-parse "$TAG^{commit}")"
  cat > AEGIS-eval-v2/_AEGIS_EVAL_README.txt <<EOF
This directory is a candidate-v2 extraction of upstream AEGIS at:
  tag    = $TAG
  commit = $COMMIT

It is NOT the formal study system under test. The formal Phase 6 study
imports from ./AEGIS-eval/ (the frozen v1 tag). This sister directory
holds the candidate v2 patch (HANDOFF_17d migration) for evaluation only.
EOF
fi

# Sanity: ./AEGIS-eval/ (v1) is unchanged
git status --short AEGIS-eval/
# Should produce no output (the v1 tree is untouched on this branch)

# Sanity: ./AEGIS-eval-v2/ exists and carries the patched files
ls AEGIS-eval-v2/src/aegis/llm/response_parser.py >/dev/null && echo "v2 response_parser.py present"
ls AEGIS-eval-v2/src/mandate/roles/binding.py >/dev/null && echo "v2 binding.py present"
ls AEGIS-eval-v2/tests/test_binding_refusal.py >/dev/null && echo "v2 test_binding_refusal.py present"
```

**Success criteria.** `AEGIS-eval-v2/` exists. The five patched files are present. `./AEGIS-eval/` (v1) is untouched.

**On script-incompatibility.** If `setup/recreate_aegis_eval.sh` does not accept a separate output directory and would overwrite `./AEGIS-eval/`, follow the manual `git archive | tar -x` branch above instead.

## Task 5: Deterministic stub-adapter verification against `AEGIS-eval-v2/`

This is HANDOFF_17c Lane 3 re-run against the new v2 tree to confirm the patch behaves identically post-migration.

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

PYTHONPATH="AEGIS-eval-v2/src:$PWD" python3 - <<'PY'
"""Lane 3 verification against AEGIS-eval-v2/ post-migration."""
import json
diag = json.load(open("demo/svb_collapse/diagnostics/svb_binding_raw_responses_2026-06-04.json"))
refusal_output = diag["attempts"][0]["raw_text"]
assert refusal_output.startswith('{"error":'), "diagnostic must carry refusal payload"

from aegis.llm.response_parser import detect_structured_refusal, ResponseParseError
assert detect_structured_refusal(json.loads(refusal_output)) is not None

from mandate.llm_support import generate_validated_response
class StubResponse:
    def __init__(self, output): self.output = output; self.tokens_used=0; self.latency_ms=0
class StubAdapter:
    retry_count = 3
    def __init__(self, output): self.output = output; self.calls = 0
    def generate(self, prompt, schema):
        self.calls += 1
        return StubResponse(self.output)

adapter = StubAdapter(refusal_output)
try:
    generate_validated_response(
        adapter=adapter, prompt="x",
        schema={"type":"object","required":["decision_summary"]},
    )
    raise AssertionError("expected ResponseParseError for structured refusal")
except ResponseParseError as e:
    assert "structured refusal" in str(e)
    assert e.last_parsed_payload == json.loads(refusal_output)
    assert adapter.calls == 1
    print("AEGIS-eval-v2 verification: short-circuit fired, payload preserved, 1-call adapter.")
PY
```

**Success criteria.** The script prints the success line. The patched behavior in `AEGIS-eval-v2/` matches the side-load behavior verified in HANDOFF_17c.

## Task 6: Commit the materialization at the project level

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

# Stage the new AEGIS-eval-v2/ directory and any project-side notes
git add AEGIS-eval-v2/
git status --short

# Confirm AEGIS-eval/ is unchanged
git diff --stat AEGIS-eval/  # expect: empty
# Confirm project main is the active branch in this project for the commit
git branch --show-current
# Expect: any branch except feature/binding-refusal-as-gap-sideload (which stays as verification snapshot)
# If you are on the side-load branch, switch to main first:
# git checkout main

git commit -m "Materialize MANDATE-primary v2 candidate at AEGIS-eval-v2/

Re-extracts upstream AEGIS at tag
mandate-eval-primary-2026q2-v2-candidate-binding-refusal into a sister
directory alongside the frozen ./AEGIS-eval/ (v1) tree. The formal
Phase 6 study still imports from AEGIS-eval/ (v1); AEGIS-eval-v2/
holds the candidate patch for evaluation only.

HANDOFF_17d migration of the side-load patch verified in HANDOFF_17c."
```

**Success criteria.** Project main has one new commit adding `AEGIS-eval-v2/`. `./AEGIS-eval/` has zero diff against the pre-migration state. The side-load branch is unchanged.

## Final report

Write `handoffs/HANDOFF_17d_report_<YYYY-MM-DD>.md`:

```markdown
# Handoff 17d Report: Upstream-AEGIS migration of Binding-refusal patch

**Codex session:** <id>
**Eval host:** <hostname>
**Date:** <YYYY-MM-DD>
**Wall clock:** <minutes>

## Verdict

PROCEED | HALT (one word)

## Evidence

- preconditions: upstream AEGIS clean / v1 tag present:    yes | no
- upstream AEGIS branch created off v1:                    feature/binding-refusal-as-gap @ <hash>
- five patched files brought over from side-load:          yes | no
- diff stat against v1 (expected: 5 files):                <n> files / <ins>+ <del>- lines
- AEGIS test suite on feature branch:
  - total passed / skipped / failed:                       <n> / <n> / <n>
  - new tests added in test_binding_refusal.py:            5
  - expected baseline (1443 passed + 5 new = 1448):        yes | no
- annotated tag created:                                   mandate-eval-primary-2026q2-v2-candidate-binding-refusal @ <hash>
- v1 tag unchanged:                                        yes | no
- upstream main branch unchanged:                          yes | no
- AEGIS-eval-v2/ materialized in project:                  yes | no
- AEGIS-eval/ (v1) tree diff on project main:              empty | non-empty
- Lane 3 verification against AEGIS-eval-v2/:              ok | fail
- side-load branch left intact:                            yes | no

## Anything the PI must decide before proceeding

- Whether to schedule an upstream-AEGIS PR/merge of the candidate patch into upstream main (after wider review).
- Whether to retire the side-load branch (`feature/binding-refusal-as-gap-sideload`) once the upstream migration is committed.
- Whether to run a full v2 calibration on the main corpus (would be a separate handoff).

## Deviations from this handoff

<short list, empty if none>
```

Commit message for the handoff report at the project level: `Handoff 17d: upstream-AEGIS migration of Binding-refusal patch`.
