# Codex Handoff 17b: Binding structured-refusal patch — corrected architecture

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-04
**Estimated wall clock:** 90 to 120 minutes (patch in upstream AEGIS + AEGIS test suite + tag + re-extract + SVB v2 verification + sanity v2 runs).
**Blocked on:** HANDOFF_16c PROCEED. HANDOFF_17 HALT acknowledged. Read/write access to the upstream AEGIS repo (default `~/Desktop/AEGIS`).

---

## What HANDOFF_17 got wrong, and what 17b fixes

HANDOFF_17 instructed Codex to `cd AEGIS-eval && git checkout mandate-eval-primary-2026q2-v1 && git checkout -b feature/binding-refusal-as-gap`. Codex correctly halted because `AEGIS-eval/` in this project is not a git checkout — it is a flat `git archive` extract of the frozen upstream tag, as documented in `AEGIS-eval/_AEGIS_EVAL_README.txt` and `setup/recreate_aegis_eval.sh`. The frozen tag `mandate-eval-primary-2026q2-v1` lives in the upstream AEGIS repository at `$AEGIS_PATH` (default `~/Desktop/AEGIS`), not in this project. There is no branch to create inside `AEGIS-eval/`.

The correct architecture for proposing a MANDATE-primary v2 patch is:

1. Patch goes on a feature branch in the **upstream AEGIS repo** at `$AEGIS_PATH`.
2. AEGIS's own test suite runs on the branch.
3. A candidate tag is cut: `mandate-eval-primary-2026q2-v2-candidate-binding-refusal`.
4. The candidate tag is materialized into a sister directory `AEGIS-eval-v2/` via `setup/recreate_aegis_eval.sh --tag <candidate-tag>`.
5. The SVB from-binaries demo is re-run with `--aegis ./AEGIS-eval-v2` (not `./AEGIS-eval`).
6. The frozen `AEGIS-eval/` tree is unchanged. The formal Phase 6 study still imports from it. PROTOCOL_LOCK §13 holds.

If the upstream AEGIS repo is not writeable in your environment, fall back to Path B in Task 9.

## Mission (unchanged from 17 in intent)

Surface the Binding role's `{"error": <text>}` structured refusals as gap reports instead of parse failures, so the model's reasoning lands in `output.gap_reports` instead of being discarded. The patch is a candidate for MANDATE-primary v2 evaluation; the formal Phase 6 study is unaffected.

**Definition of done.**

1. Path A executed: a feature branch in upstream AEGIS carries the four-file patch + new unit tests; AEGIS's test suite passes on the branch; a candidate tag is cut; `AEGIS-eval-v2/` materializes that tag.
2. SVB from-binaries re-run against `AEGIS-eval-v2/` produces `any_llm_fallback=False`, one Binding-attributed gap report carrying the verbatim model refusal text, and `roles[4].artifacts.llm_refused_with_error=True`.
3. Volt Typhoon and CrowdStrike v2 sanity runs produce `any_llm_fallback=False` and zero Binding-attributed gap reports (negative tests confirming the predicate is not too broad).
4. `AEGIS-eval/` (v1) directory is unchanged. `AEGIS-eval/_AEGIS_EVAL_README.txt` is unchanged. The project's `main` branch is unchanged.
5. One handoff report at `handoffs/HANDOFF_17b_report_<YYYY-MM-DD>.md`.

## Preconditions

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

# 1. Confirm AEGIS-eval/ is a git archive extract, not a checkout
[ ! -d AEGIS-eval/.git ] || { echo "unexpected: AEGIS-eval/ is a git repo"; exit 1; }
[ -f AEGIS-eval/_AEGIS_EVAL_README.txt ] && cat AEGIS-eval/_AEGIS_EVAL_README.txt

# 2. Confirm upstream AEGIS is reachable and has the v1 tag
: "${AEGIS_PATH:=$HOME/Desktop/AEGIS}"
[ -d "$AEGIS_PATH/.git" ] || { echo "AEGIS_PATH is not a git repo: $AEGIS_PATH"; exit 1; }
git -C "$AEGIS_PATH" rev-parse --verify mandate-eval-primary-2026q2-v1^{commit} >/dev/null || {
  echo "v1 tag missing in upstream AEGIS at $AEGIS_PATH"; exit 1
}
git -C "$AEGIS_PATH" status --porcelain | head -5  # confirm clean
```

**Success criteria.** `AEGIS-eval/` has no `.git`. Upstream AEGIS at `$AEGIS_PATH` is a clean git repo carrying the v1 tag.

**On failure of any precondition.** If `$AEGIS_PATH` is not a writeable AEGIS git repo on this host, skip Tasks 1 through 6 and go directly to Task 9 (Path B side-load).

## Decision boundary

You may decide:
- The artifact field name conventions, as in HANDOFF_17.
- Whether the candidate tag carries the date or just the descriptor; the default is `mandate-eval-primary-2026q2-v2-candidate-binding-refusal`.

You must escalate:
- Upstream AEGIS is read-only or has uncommitted changes you would otherwise need to overwrite. Stop and report.
- AEGIS's own test suite has a pre-existing failure on the v1 tag that the patch did not introduce. Stop and report; do not paper over it.
- Any change required to `AEGIS-eval/` (the v1 tree). The freeze is preserved under Path A; if you find yourself editing `AEGIS-eval/`, you have drifted into Path B and should stop and follow Task 9 explicitly instead.

You may not:
- Move the `mandate-eval-primary-2026q2-v1` tag in upstream AEGIS.
- Modify `main` in upstream AEGIS (the candidate branch is independent).
- Modify `AEGIS-eval/` under Path A. If Path A is unavailable, follow Task 9 with explicit freeze-deviation documentation; do not silently edit the v1 tree.

---

## Path A — preferred

### Task 1: Set up the feature branch in upstream AEGIS

```zsh
cd "${AEGIS_PATH:-$HOME/Desktop/AEGIS}"
git fetch --tags
git checkout mandate-eval-primary-2026q2-v1
git checkout -b feature/binding-refusal-as-gap
git log --oneline -1
```

**Success criteria.** A new branch in upstream AEGIS pointing at the same commit as the v1 tag. Worktree clean.

### Task 2: Apply the four-file patch in upstream AEGIS

Files to edit are paths inside the AEGIS repo (no `AEGIS-eval/` prefix), since you are editing upstream now. The contracts are identical to HANDOFF_17's Task 2 (reproduced below for self-contained use). All paths in this section are relative to `$AEGIS_PATH`.

**2a — `src/aegis/llm/response_parser.py`** (add helper + extend exception):

```python
class ResponseParseError(ValueError):
    """Raised when an LLM response cannot be parsed or schema-validated."""

    def __init__(self, message: str, *,
                 last_raw_response: Optional[str] = None,
                 last_parsed_payload: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.last_raw_response = last_raw_response
        self.last_parsed_payload = last_parsed_payload


def detect_structured_refusal(parsed: Any) -> Optional[str]:
    """Return refusal text if `parsed` is a clean `{"error": <non-empty str>}`
    payload with no other keys. Otherwise return None. MANDATE role fine-tunes
    have been observed to emit this shape when upstream pipeline state is
    contradictory (HANDOFF_16c diagnostic, 2026-06-04)."""
    if not isinstance(parsed, dict):
        return None
    if list(parsed.keys()) != ["error"]:
        return None
    text = parsed.get("error")
    if not isinstance(text, str) or not text.strip():
        return None
    return text.strip()
```

**2b — `src/mandate/llm_support.py`** (short-circuit `generate_validated_response` on refusal):

```python
from aegis.llm.response_parser import (
    ResponseParser, ResponseParseError, detect_structured_refusal,
)

# Inside generate_validated_response, replacing the existing loop body:
last_error = "unknown parse failure"
last_raw = ""
last_parsed_for_diag = None

for attempt in range(1, max_attempts + 1):
    response = adapter.generate(prompt, dict(schema))
    last_raw = response.output
    parsed = parser.parse_output(response.output, schema)
    if parsed.ok and parsed.parsed is not None:
        return response, parsed.parsed, attempt

    try:
        raw_obj = json.loads(response.output)
    except Exception:
        raw_obj = None
    refusal_text = detect_structured_refusal(raw_obj)
    if refusal_text is not None:
        raise ResponseParseError(
            f"structured refusal from model: {refusal_text}",
            last_raw_response=response.output,
            last_parsed_payload=raw_obj,
        )

    last_error = parsed.error or "unknown parse failure"
    last_parsed_for_diag = raw_obj

raise ResponseParseError(
    f"LLM response parsing failed after {max_attempts} attempt(s): {last_error}",
    last_raw_response=last_raw,
    last_parsed_payload=last_parsed_for_diag,
)
```

**2c — `src/mandate/roles/binding.py`** (catch refusal, annotate, run deterministic):

```python
from aegis.llm.response_parser import ResponseParseError

# Replace the existing generate_validated_response call site with:
refusal_text: Optional[str] = None
try:
    llm_response, parsed_payload, attempts = generate_validated_response(
        adapter=adapter,
        prompt=prompt,
        schema=self._LLM_STAGE_OUTPUT_SCHEMA,
    )
except ResponseParseError as e:
    parsed = getattr(e, "last_parsed_payload", None)
    if isinstance(parsed, dict) and list(parsed.keys()) == ["error"]:
        refusal_text = str(parsed["error"]).strip()
    if refusal_text is None:
        raise

if refusal_text is not None:
    result = self.execute(state)
    if state.recommendation:
        state.recommendation.rationale = (
            f"[binding refused] {refusal_text} "
            f"Deterministic fallback recommendation: "
            f"{state.recommendation.rationale}"
        )
        result.artifacts["recommendation_rationale"] = state.recommendation.rationale
    result.artifacts["llm_used"] = True
    result.artifacts["llm_fallback"] = False
    result.artifacts["llm_refused_with_error"] = True
    result.artifacts["llm_refusal_text"] = refusal_text
    result.artifacts["llm_mutation_boundary"] = list(self._LLM_MUTATION_BOUNDARY)
    result.artifacts["llm_state_mutations_applied"] = []
    return result

# (... existing mutation-override code, unchanged ...)
```

**2d — `src/mandate/pipeline.py`** (inject Binding-refusal gap when present):

```python
GapSpec(
    gap_type=GapType.UNASSESSABLE_RISK,
    detected_by="Binding",
    pipeline_stage=4,
    field_or_task="recommendation.decision_summary",
    reason=refusal_text,
    action_required=(
        "Re-decompose the mission to satisfy the anchor minimum cardinality, "
        "or relax the anchor minimum. The Binding role refused to bind the "
        "inputs because the anchor's minimum requirement is not satisfiable "
        "by the upstream Decomposition output."
    ),
    severity=GapSeverity.DEGRADING,
    location=GapLocation.RISK,
    gap_source=GapSource.SPECIFICATION_GAP,
    responsible_party="Mission Author",
    complexity="MEDIUM",
    blocking=False,
    partial_spec_available=True,
)
```

Find the existing gap_reports assembly site (search for `build_gap_reports` or `gap_spec_to_artifact`) and append the gap there when the Binding role's `RoleResult.artifacts.llm_refused_with_error` is True.

**Success criteria for Task 2.** All four files edited cleanly. `python3 -c "from aegis.llm.response_parser import detect_structured_refusal, ResponseParseError; print('ok')"` succeeds inside the upstream AEGIS venv.

### Task 3: Unit tests in upstream AEGIS

Create `tests/test_binding_refusal.py` in the upstream AEGIS repo with the five-case test file specified in HANDOFF_17 Task 3 (reproduced below). Use the existing AEGIS test conventions you find in the rest of `tests/`.

```python
# tests/test_binding_refusal.py
import json
import pytest
from unittest.mock import MagicMock
from aegis.llm.response_parser import (
    detect_structured_refusal, ResponseParseError,
)

def test_detect_structured_refusal_returns_text():
    assert detect_structured_refusal({"error": "cannot bind"}) == "cannot bind"

def test_detect_structured_refusal_rejects_extra_keys():
    for bad in [{"error": "x", "decision_summary": "y"},
                {"decision_summary": "y"},
                {"error": ""},
                {"error": 42},
                [{"error": "x"}],
                "error",
                None]:
        assert detect_structured_refusal(bad) is None

def test_generate_validated_response_short_circuits_on_refusal():
    from mandate.llm_support import generate_validated_response
    adapter = MagicMock()
    adapter.generate = MagicMock(return_value=MagicMock(
        output=json.dumps({"error": "refused"}), tokens_used=10, latency_ms=5))
    adapter.retry_count = 3
    with pytest.raises(ResponseParseError) as ei:
        generate_validated_response(
            adapter=adapter, prompt="x",
            schema={"type":"object","required":["decision_summary"]})
    assert adapter.generate.call_count == 1
    assert "structured refusal" in str(ei.value)
    assert ei.value.last_parsed_payload == {"error": "refused"}

def test_binding_role_handles_structured_refusal():
    pass  # implement against existing pipeline test fixtures

def test_binding_role_falls_back_on_malformed_json():
    pass  # implement against existing pipeline test fixtures
```

Fill the two `pass` stubs using AEGIS's existing pipeline test harness; the diagnostic at `demo/svb_collapse/diagnostics/svb_binding_raw_responses_2026-06-04.json` (in this project, not in upstream AEGIS) is the source of truth for the fixture inputs.

**Success criteria.** `pytest tests/test_binding_refusal.py -v` passes five tests.

### Task 4: AEGIS suite regression

```zsh
cd "${AEGIS_PATH}"
# Run AEGIS's own test runner; the command shape will be in AEGIS's docs.
# Common patterns to try, in order:
python3 -m pytest -x -q 2>&1 | tail -30
# or
make test 2>&1 | tail -30
# or
bash scripts/run_tests.sh 2>&1 | tail -30
```

**Success criteria.** AEGIS's full test suite passes on the feature branch. No new failures attributable to the patch.

### Task 5: Commit and tag the candidate

```zsh
cd "${AEGIS_PATH}"
git add -A
git commit -m "Binding role: surface structured {error: ...} refusals as gap reports

Detect mandate-binding emitting a clean JSON {error: <text>} payload
when the upstream pipeline state is internally contradictory (anchor
demands N options, Decomposition emitted one). Treat the refusal as a
structured signal: short-circuit the parse retry loop, attach the
verbatim model text to the role artifact, run the deterministic
recommendation as a fallback summary, and append a
GapSpec(UNASSESSABLE_RISK, detected_by='Binding') to gap_reports.

Companion to HANDOFF_16c diagnostic (SVB from-binaries run, 2026-06-04).
The model is not malfunctioning; it is honestly refusing to bind, and
its reasoning belongs in gap_reports rather than the parse-failure
fallback path.

Candidate for MANDATE-primary v2. Tag mandate-eval-primary-2026q2-v1
is unchanged."

git tag -a mandate-eval-primary-2026q2-v2-candidate-binding-refusal \
       -m "MANDATE-primary v2 candidate: Binding structured-refusal as gap_report"
git log --oneline -3
git tag --list "mandate-eval-primary*"
```

**Success criteria.** Exactly one new commit on `feature/binding-refusal-as-gap`. A new tag `mandate-eval-primary-2026q2-v2-candidate-binding-refusal`. The v1 tag is unchanged (`git rev-parse mandate-eval-primary-2026q2-v1` returns the same commit it did at the start of this handoff).

### Task 6: Materialize the candidate tag into `AEGIS-eval-v2/`

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
# Re-use the existing recreate script with the new tag and a sibling output dir
TAG=mandate-eval-primary-2026q2-v2-candidate-binding-refusal
COMMIT="$(git -C "${AEGIS_PATH:-$HOME/Desktop/AEGIS}" rev-parse "$TAG^{commit}")"

mkdir -p AEGIS-eval-v2
git -C "${AEGIS_PATH:-$HOME/Desktop/AEGIS}" archive --format=tar "$TAG" | tar -x -C AEGIS-eval-v2

cat > AEGIS-eval-v2/_AEGIS_EVAL_README.txt <<EOF
This directory is a candidate-v2 extraction of upstream AEGIS at:
  tag    = $TAG
  commit = $COMMIT

It is NOT the formal study system under test. The formal Phase 6 study
imports from ./AEGIS-eval/ (the frozen v1 tag). This sister directory
holds the candidate v2 patch (HANDOFF_17b) for evaluation only.
EOF

ls AEGIS-eval-v2/src/aegis/llm/response_parser.py
ls AEGIS-eval-v2/src/mandate/roles/binding.py
```

**Success criteria.** `AEGIS-eval-v2/` populated; its `response_parser.py` and `binding.py` files reflect the patch.

### Task 7: SVB from-binaries re-run against `AEGIS-eval-v2/`

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

cp AEGIS-eval-v2/configs/llm_defaults.json AEGIS-eval-v2/configs/llm_defaults.json.bak
python3 -c "
import json, pathlib
p = pathlib.Path('AEGIS-eval-v2/configs/llm_defaults.json')
cfg = json.loads(p.read_text())
cfg['llm_rag_index'] = '$PWD/demo/svb_collapse/rag/svb_collapse__from_binaries.jsonl'
p.write_text(json.dumps(cfg, indent=2))
"

python3 -m apparatus.run run-system \
  --system mandate_primary \
  --aegis ./AEGIS-eval-v2 \
  --tasks demo/svb_collapse/tasks/tasks.jsonl \
  --runs 1 \
  --output demo/svb_collapse/output_ollama_v2 \
  --code-ref demo-svb-collapse-ollama-v2-refusal-gap \
  --ollama-mode

mv AEGIS-eval-v2/configs/llm_defaults.json.bak AEGIS-eval-v2/configs/llm_defaults.json

python3 - <<'PY'
import json
r = json.load(open("demo/svb_collapse/output_ollama_v2/mandate_primary__TASK-DEMO-SVB-001__r01.json"))
binding_t = next((t for t in r.get("role_timings",[]) if t["role_name"]=="Binding"), {})
gaps = r["output"].get("gap_reports", []) or []
binding_gaps = [g for g in gaps if g.get("detected_by")=="Binding"]
print("any_llm_fallback:", r["any_llm_fallback"])
print("Binding llm_used:", binding_t.get("llm_used"))
print("Binding llm_fallback:", binding_t.get("llm_fallback"))
print("n binding-attributed gap_reports:", len(binding_gaps))
print("first binding gap reason[:200]:", binding_gaps[0]["reason"][:200] if binding_gaps else "(none)")
print("recommendation.rationale[:300]:", r["output"]["artifact"].get("recommendation",{}).get("rationale","")[:300])
assert r["any_llm_fallback"] == False, "fallback expected to be False after patch"
assert len(binding_gaps) == 1, "expected exactly one Binding-attributed gap"
print("\nSVB v2 verification PASSED.")
PY
```

**Success criteria.** `any_llm_fallback=False`, exactly one Binding-attributed gap with the verbatim model refusal text in `reason`, rationale prefixed `[binding refused]`. If any assertion fires, do NOT proceed; debug, re-patch, re-verify.

### Task 8: Sanity — Volt Typhoon and CrowdStrike v2 negative tests

```zsh
for S in volt_typhoon crowdstrike_outage; do
  cp AEGIS-eval-v2/configs/llm_defaults.json AEGIS-eval-v2/configs/llm_defaults.json.bak
  python3 -c "
import json, pathlib
p = pathlib.Path('AEGIS-eval-v2/configs/llm_defaults.json')
cfg = json.loads(p.read_text())
cfg['llm_rag_index'] = '$PWD/demo/$S/rag/${S}__from_binaries.jsonl'
p.write_text(json.dumps(cfg, indent=2))
"
  python3 -m apparatus.run run-system \
    --system mandate_primary \
    --aegis ./AEGIS-eval-v2 \
    --tasks demo/$S/tasks/tasks.jsonl \
    --runs 1 \
    --output demo/$S/output_ollama_v2 \
    --code-ref demo-$S-ollama-v2-refusal-gap-sanity \
    --ollama-mode
  mv AEGIS-eval-v2/configs/llm_defaults.json.bak AEGIS-eval-v2/configs/llm_defaults.json
done

python3 - <<'PY'
import json
for s, tid in [("volt_typhoon","TASK-DEMO-VOLT-001"),
                ("crowdstrike_outage","TASK-DEMO-CRWD-001")]:
    r = json.load(open(f"demo/{s}/output_ollama_v2/mandate_primary__{tid}__r01.json"))
    gaps = r["output"].get("gap_reports", []) or []
    bg = [g for g in gaps if g.get("detected_by")=="Binding"]
    print(f"{s}: any_llm_fallback={r['any_llm_fallback']} binding_gaps={len(bg)}")
    assert r["any_llm_fallback"] == False
    assert len(bg) == 0, f"unexpected Binding gap in {s}; predicate too broad"
print("\nVolt + CrowdStrike v2 sanity PASSED.")
PY
```

**Success criteria.** Both scenarios show `any_llm_fallback=False` and zero Binding-attributed gaps. If either fails, the patch's refusal predicate is over-firing on non-refusal outputs; revert and tighten.

---

## Path B — fallback if upstream AEGIS is not writeable

Use this path only if Task 1's precondition check fails because `$AEGIS_PATH` is not a writeable AEGIS git repository on this host. Document explicitly in the report which precondition failed.

### Task 9 (Path B): Side-load the patch into AEGIS-eval/ on a project feature branch

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
git checkout -b feature/binding-refusal-as-gap-sideload

# Apply the same four edits directly to AEGIS-eval/src/aegis/llm/response_parser.py,
# AEGIS-eval/src/mandate/llm_support.py, AEGIS-eval/src/mandate/roles/binding.py,
# AEGIS-eval/src/mandate/pipeline.py — using the patch contracts from Task 2 above.
# These paths are the same as Task 2's but with the AEGIS-eval/ prefix.

# Update the marker file to record the deviation explicitly
cat > AEGIS-eval/_AEGIS_EVAL_README.txt <<EOF
This directory is a side-loaded variant of upstream AEGIS at:
  base tag = mandate-eval-primary-2026q2-v1
  base commit = 4f8af83d12ef1ffdedcf7c5f53a0f9a2c062b06f
  applied   = candidate v2 patch (Binding structured-refusal as gap_report)
  patch ref = handoffs/HANDOFF_17b_binding_refusal_as_gap_corrected.md
  branch    = feature/binding-refusal-as-gap-sideload

This is NOT the formal study system under test. The formal Phase 6 study
must run from the v1 tag, recreated by setup/recreate_aegis_eval.sh on the
project main branch. To rollback this side-load:
    git checkout main -- AEGIS-eval/
    bash setup/recreate_aegis_eval.sh --force
EOF

# Add new unit tests under AEGIS-eval/tests/test_binding_refusal.py mirroring Task 3
```

Then run Tasks 7 and 8 above with `--aegis ./AEGIS-eval` (since under Path B the patched tree IS the local AEGIS-eval).

**Path B success criteria.** Same as Path A's Tasks 7 and 8. Plus: the project's `main` branch has zero diff against the v1 baseline; the side-load lives only on `feature/binding-refusal-as-gap-sideload`; rolling back via the documented commands cleanly restores v1.

---

## Final report

Write `handoffs/HANDOFF_17b_report_<YYYY-MM-DD>.md`:

```markdown
# Handoff 17b Report: Binding structured-refusal patch (corrected architecture)

**Codex session:** <id>
**Eval host:** <hostname>
**Date:** <YYYY-MM-DD>
**Wall clock:** <minutes>

## Verdict

PROCEED | HALT (one word)

## Path taken

A (upstream AEGIS patched + candidate tag + AEGIS-eval-v2/ materialized)
B (side-loaded into AEGIS-eval/ on project feature branch)

## Evidence

- preconditions confirmed (AEGIS-eval/ has no .git, upstream AEGIS clean, v1 tag present): yes | no
- patch applied in: <upstream AEGIS @ feature/binding-refusal-as-gap | project @ feature/binding-refusal-as-gap-sideload>
- unit tests passing:                       <n>/<n>
- AEGIS suite still passes:                 yes | no
- candidate tag (Path A only):              mandate-eval-primary-2026q2-v2-candidate-binding-refusal @ <hash>
- AEGIS-eval-v2/ materialized (Path A):     yes | no
- v1 tag unchanged:                         yes | no
- AEGIS-eval/ (v1 tree) diff on project main: empty | non-empty
- SVB v2 run:
  - any_llm_fallback:                       <True|False>
  - Binding-attributed gap reports:         <n>           (expected: 1)
  - first 200 chars of recommendation.rationale:
    <verbatim>
- Volt v2 sanity:
  - any_llm_fallback:                       <True|False>  (expected: False)
  - Binding-attributed gap reports:         <n>           (expected: 0)
- CrowdStrike v2 sanity:
  - any_llm_fallback:                       <True|False>  (expected: False)
  - Binding-attributed gap reports:         <n>           (expected: 0)

## What changes for the formal study

Nothing. ./AEGIS-eval/ is unchanged on the project main branch; the formal Phase 6 study still imports from the v1 tag. PROTOCOL_LOCK §13 holds.

## What changes for the demo

The SVB from-binaries scenario now surfaces the Binding model's reasoning as a gap report under the v2 candidate tree. Volt Typhoon and CrowdStrike are structurally identical to their pre-patch v2 sanity runs (no Binding-attributed gaps, no fallbacks).

## Anything the PI must decide before proceeding

- Whether to take the v2 candidate tag to upstream AEGIS for merge into main.
- Whether to add a v1-vs-v2 row to demo/MANDATE_DEMO_FINDINGS.md once the v2 SVB artifact is in.
- Whether to schedule a fuller v2 calibration on the main corpus once Phase 6 v1 grading is complete.

## Deviations from this handoff

<short list, empty if none>
```

Commit message at the project / handoff level: `Handoff 17b: Binding structured-refusal as gap_report (corrected architecture)`.
