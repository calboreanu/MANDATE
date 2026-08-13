# Codex Handoff 17: Apparatus patch — surface Binding role structured refusals as gap reports

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-04
**Estimated wall clock:** 60 to 90 minutes (patch implementation + unit tests + SVB re-run on the feature branch).
**Blocked on:** Handoff 16c PROCEED (the diagnostic that surfaced the refusal-not-defect finding). HANDOFF_01 PROCEED. `mandate-binding` Ollama model loaded.

---

## Mission

HANDOFF_16c established that the SVB Binding model is not malfunctioning — it is emitting clean JSON with a single `error` field explaining, in natural language, that it cannot bind one COA to a three-option anchor minimum. The apparatus currently treats those payloads as `'decision_summary' is a required property` parse failures, retries three times, falls back to the deterministic Binding path, and discards the model's `error` text entirely. The model's structured refusal carries information that belongs in `output.gap_reports`, not in the dropped-on-the-floor fallback path.

This handoff implements the corresponding apparatus patch. Surface the Binding model's structured refusal as a `GapSpec` in `output.gap_reports`, do not count it as an `llm_fallback`, and preserve the model's verbatim error text on the artifact. The patch lives on a feature branch; the frozen `mandate-eval-primary-2026q2-v1` tag and the `main` commit it points to are NOT touched. The patch is a candidate for evaluation as "MANDATE-primary v2"; the formal Phase 6 study still runs the frozen v1 tag.

**Definition of done.**

1. A new branch `feature/binding-refusal-as-gap` off the frozen tag, with the patch committed.
2. Three Python unit tests passing (`pytest AEGIS-eval/tests/test_binding_refusal.py`).
3. The full apparatus suite still passes (`bash scripts/run_apparatus_suite.sh` or equivalent project-conventional command).
4. A re-run of the SVB from-binaries scenario on the feature branch produces a RunRecord with `any_llm_fallback=False`, exactly one `gap_report` whose `detected_by="Binding"`, and `roles[4].artifacts.llm_refused_with_error=True` carrying the verbatim model error text.
5. One handoff report at `handoffs/HANDOFF_17_report_<YYYY-MM-DD>.md`.
6. The frozen tag `mandate-eval-primary-2026q2-v1` and the `main` branch in AEGIS-eval are unchanged. PROTOCOL_LOCK §13 holds for the formal study.

## Preconditions

- HANDOFF_16c PROCEED with the diagnostic at `demo/svb_collapse/diagnostics/svb_binding_raw_responses_2026-06-04.json` present.
- AEGIS-eval's `mandate-eval-primary-2026q2-v1` tag exists locally. Confirm with `cd AEGIS-eval && git tag --list "mandate-eval-primary*"`.
- Ollama running with the six `mandate-*` role models loaded.
- The apparatus suite passes on the current `main` (sanity baseline).

## Decision boundary

You may decide:
- The exact field name on `RoleResult.artifacts` for the refusal text; the handoff defaults to `llm_refused_with_error: bool` and `llm_refusal_text: str` but you may use clearer names if they match neighboring conventions you find in the role code.
- The GapType assignment for the refusal gap. The handoff defaults to `UNASSESSABLE_RISK` because it is the closest existing enum value to "the binder cannot bind these inputs"; if you find a cleaner fit reading the rest of `gap_report.py`, pick that and note the choice in the report.
- Whether to also propagate the refusal text into `Recommendation.rationale` for the deterministic fallback case (the handoff says yes; you may prefer to keep it artifact-side only and note the choice).

You must escalate:
- Any patch line that requires modifying `AEGIS-eval/configs/llm_defaults.json` or any frozen prompt under `AEGIS-eval/config/system-prompts/`. Those are part of the freeze.
- A unit test that cannot pass because the existing AEGIS-eval public API does not expose what the patch needs. In that case, stop, describe the missing surface, and ask the PI whether to extend the API or shrink the patch.
- The apparatus suite regressing on any other test. The patch is supposed to be additive; existing behavior on non-refusal responses must be identical.

You may not:
- Modify the `main` branch in AEGIS-eval. All commits go on the feature branch.
- Move or update the `mandate-eval-primary-2026q2-v1` tag.
- Re-run the formal corpus generation, the main study, or any non-demo pipeline. This handoff is purely the patch + unit tests + the SVB demo re-run as functional verification.
- Run the patch against Volt Typhoon or CrowdStrike on the feature branch unless you also document that those scenarios should produce zero refusal gaps (they did not refuse on HANDOFF_16b).

---

## Task 1: Set up the feature branch

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2/AEGIS-eval"
git status
git rev-parse HEAD
git tag --list "mandate-eval-primary*"

# Confirm we are at the frozen tag and the worktree is clean
git checkout mandate-eval-primary-2026q2-v1
git checkout -b feature/binding-refusal-as-gap
git log --oneline -1
```

**Success criteria.** A new branch `feature/binding-refusal-as-gap` exists, pointing at the same commit as `mandate-eval-primary-2026q2-v1`. Worktree clean.

## Task 2: Implement the patch

The patch touches three files. Concrete change list with file paths, function names, and the behavior contract for each. Implement in this order; the order matters because Binding depends on the response parser and the pipeline depends on Binding.

### 2a — `AEGIS-eval/src/aegis/llm/response_parser.py`

Add a new helper and extend `ResponseParseError`:

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
    """Return the refusal text if `parsed` is a clean structured refusal of
    the shape `{"error": <non-empty string>}` with no other keys. Otherwise
    return None.

    The MANDATE role fine-tunes have been observed to emit this shape when
    upstream pipeline state is internally contradictory (e.g. a Binding role
    handed an anchor that demands N options and a Decomposition output with
    one COA). Treat the refusal as a structured signal, not a parse failure.
    """
    if not isinstance(parsed, dict):
        return None
    if list(parsed.keys()) != ["error"]:
        return None
    text = parsed.get("error")
    if not isinstance(text, str) or not text.strip():
        return None
    return text.strip()
```

**Success criteria.** `detect_structured_refusal({"error": "x"})` returns `"x"`. `detect_structured_refusal({"error": "x", "decision_summary": "y"})` returns `None`. `detect_structured_refusal({"decision_summary": "y"})` returns `None`. Add three direct asserts to the unit test file in Task 3.

### 2b — `AEGIS-eval/src/mandate/llm_support.py`

Modify `generate_validated_response` so that on each attempt, after `parser.parse_output(...)` succeeds-as-JSON but fails-as-schema, the function checks for the structured-refusal shape and short-circuits without consuming the retry budget. The refusal is raised with the parsed payload attached so the caller can recover it.

Current code path (HANDOFF_16c trace, line 47-55):

```python
for attempt in range(1, max_attempts + 1):
    response = adapter.generate(prompt, dict(schema))
    parsed = parser.parse_output(response.output, schema)
    if parsed.ok and parsed.parsed is not None:
        return response, parsed.parsed, attempt
    last_error = parsed.error or "unknown parse failure"

raise ResponseParseError(
    f"LLM response parsing failed after {max_attempts} attempt(s): {last_error}"
)
```

Patched code path:

```python
from aegis.llm.response_parser import (
    ResponseParser, ResponseParseError, detect_structured_refusal,
)

# ...

last_error = "unknown parse failure"
last_raw = ""
last_parsed_for_diag = None

for attempt in range(1, max_attempts + 1):
    response = adapter.generate(prompt, dict(schema))
    last_raw = response.output
    parsed = parser.parse_output(response.output, schema)
    if parsed.ok and parsed.parsed is not None:
        return response, parsed.parsed, attempt

    # Structured refusal detection. We parse the raw output independent of
    # the schema so we can distinguish `{"error": "..."}` (deliberate
    # model refusal, valuable signal) from other parse failures.
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

**Success criteria.** A structured refusal is raised on attempt 1 without further retries. A non-refusal parse failure still consumes the full retry budget and raises with the original message.

### 2c — `AEGIS-eval/src/mandate/roles/binding.py`

Wrap the `generate_validated_response` call so that a structured refusal does not bubble up as a fallback. Instead, run the deterministic recommendation and annotate the result.

Current code path (lines 96-100 in the existing `execute_with_llm`):

```python
llm_response, parsed_payload, attempts = generate_validated_response(
    adapter=adapter,
    prompt=prompt,
    schema=self._LLM_STAGE_OUTPUT_SCHEMA,
)
```

Patched code path:

```python
from aegis.llm.response_parser import ResponseParseError

# ...

refusal_text: Optional[str] = None
try:
    llm_response, parsed_payload, attempts = generate_validated_response(
        adapter=adapter,
        prompt=prompt,
        schema=self._LLM_STAGE_OUTPUT_SCHEMA,
    )
except ResponseParseError as e:
    # If the model emitted a structured refusal, surface it as a signal.
    parsed = getattr(e, "last_parsed_payload", None)
    if isinstance(parsed, dict) and list(parsed.keys()) == ["error"]:
        refusal_text = str(parsed["error"]).strip()
    if refusal_text is None:
        raise  # not a refusal — let the normal fallback path handle it

if refusal_text is not None:
    # Run the deterministic recommendation. The LLM said "I can't bind
    # this" and gave us its reasoning; we keep the model's text and
    # produce a deterministic recommendation alongside.
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

# (... existing post-call mutation-override code, unchanged ...)
```

**Success criteria.** When the model emits a clean structured refusal, the role returns successfully with `llm_used=True`, `llm_fallback=False`, `llm_refused_with_error=True`, `llm_refusal_text=<verbatim model text>`. When the model emits malformed JSON or a non-refusal parse failure, the role re-raises and the existing pipeline-level fallback (`execute_with_fallback`) takes over exactly as today.

### 2d — `AEGIS-eval/src/mandate/pipeline.py`

After the pipeline builds the artifact, if any role's artifacts carry `llm_refused_with_error=True`, append a `GapSpec` to the run's gap reports. Find the `gap_reports` assembly site (search `build_gap_reports` or `gap_spec_to_artifact`) and add the new gap there.

Suggested GapSpec for a Binding refusal:

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

**Success criteria.** When `roles[4].artifacts.llm_refused_with_error=True`, the final RunRecord's `output.gap_reports` carries exactly one new gap with `detected_by="Binding"` and the refusal text in the `reason` field. The Volt Typhoon and CrowdStrike scenarios are unaffected (their Binding roles did not refuse, so no new gap is added).

## Task 3: Unit tests

Create `AEGIS-eval/tests/test_binding_refusal.py` with three cases. Use the existing AEGIS-eval test conventions (look at `tests/python_api/` for the harness shape).

```python
# AEGIS-eval/tests/test_binding_refusal.py
import json
import pytest
from unittest.mock import MagicMock

from aegis.llm.response_parser import (
    detect_structured_refusal, ResponseParseError,
)


def test_detect_structured_refusal_returns_text():
    assert detect_structured_refusal({"error": "cannot bind one COA to three-option anchor"}) \
        == "cannot bind one COA to three-option anchor"


def test_detect_structured_refusal_rejects_extra_keys():
    assert detect_structured_refusal({"error": "x", "decision_summary": "y"}) is None
    assert detect_structured_refusal({"decision_summary": "y"}) is None
    assert detect_structured_refusal({"error": ""}) is None
    assert detect_structured_refusal({"error": 42}) is None
    assert detect_structured_refusal([{"error": "x"}]) is None
    assert detect_structured_refusal("error") is None


def test_generate_validated_response_short_circuits_on_refusal():
    """When the adapter returns a structured refusal, the parse loop
    should NOT consume the retry budget."""
    from mandate.llm_support import generate_validated_response
    adapter = MagicMock()
    adapter.generate = MagicMock(return_value=MagicMock(
        output=json.dumps({"error": "model refused: input contradictory"}),
        tokens_used=42, latency_ms=10,
    ))
    # The 4-arg adapter retry_count fixture; pull a sensible default
    adapter.retry_count = 3
    with pytest.raises(ResponseParseError) as excinfo:
        generate_validated_response(
            adapter=adapter, prompt="ignored",
            schema={"type": "object", "required": ["decision_summary"]},
        )
    # The adapter should have been called exactly once (no retries on refusal)
    assert adapter.generate.call_count == 1
    err = excinfo.value
    assert "structured refusal" in str(err)
    assert err.last_parsed_payload == {"error": "model refused: input contradictory"}


def test_binding_role_handles_structured_refusal():
    """When generate_validated_response raises a structured refusal,
    BindingRole.execute_with_llm should NOT fall back; it should return
    a deterministic-recommendation result annotated with the refusal."""
    # Construct a minimal PipelineState with one COA and a recommendation-ready
    # set of anchors / constraints, then call execute_with_llm with a mock
    # adapter that emits the refusal shape.
    # ... fixture construction matches the test helpers in tests/ ...
    pass  # implement using the existing pipeline test fixtures


def test_binding_role_falls_back_on_malformed_json():
    """When the adapter emits malformed JSON (not a structured refusal),
    BindingRole.execute_with_llm should let the exception propagate so the
    pipeline-level execute_with_fallback runs the deterministic path. The
    existing llm_fallback=True semantics are preserved."""
    pass  # implement using the existing pipeline test fixtures
```

Fill in the two `pass`-stubbed tests using the test fixtures already present in the AEGIS-eval test tree. The shape is taken from the diagnostic captured in 16c: a fixture that constructs a `PipelineState` with one COA, anchor minimum demanding multiple options, and a mock adapter that emits the refusal payload.

**Success criteria.** `pytest AEGIS-eval/tests/test_binding_refusal.py -v` reports five passing tests.

## Task 4: Apparatus suite regression check

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
# Run the project's apparatus suite as Handoff 01 runs it
bash scripts/apparatus_suite.sh
# Or if the script name differs in your tree
# python3 -m pytest apparatus/ AEGIS-eval/tests/ -x -q
```

**Success criteria.** All previously-passing tests still pass. No new failures introduced by the patch.

## Task 5: Functional verification via SVB re-run on the feature branch

The SVB from-binaries scenario is the one that exercises the patched code path. Re-run it and confirm the RunRecord changes shape correctly.

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

cp AEGIS-eval/configs/llm_defaults.json AEGIS-eval/configs/llm_defaults.json.bak
python3 -c "
import json, pathlib
p = pathlib.Path('AEGIS-eval/configs/llm_defaults.json')
cfg = json.loads(p.read_text())
cfg['llm_rag_index'] = '$PWD/demo/svb_collapse/rag/svb_collapse__from_binaries.jsonl'
p.write_text(json.dumps(cfg, indent=2))
"

python3 -m apparatus.run run-system \
  --system mandate_primary \
  --aegis ./AEGIS-eval \
  --tasks demo/svb_collapse/tasks/tasks.jsonl \
  --runs 1 \
  --output demo/svb_collapse/output_ollama_v2 \
  --code-ref demo-svb-collapse-ollama-v2-refusal-gap \
  --ollama-mode

mv AEGIS-eval/configs/llm_defaults.json.bak AEGIS-eval/configs/llm_defaults.json
```

Then check the artifact:

```zsh
python3 - <<'PY'
import json
r = json.load(open("demo/svb_collapse/output_ollama_v2/mandate_primary__TASK-DEMO-SVB-001__r01.json"))
print("ok:", r["ok"])
print("any_llm_fallback:", r["any_llm_fallback"])
print("fallback_roles:", r["fallback_roles"])
binding_t = next((t for t in r.get("role_timings",[]) if t["role_name"]=="Binding"), {})
print("Binding llm_used:", binding_t.get("llm_used"))
print("Binding llm_fallback:", binding_t.get("llm_fallback"))
print("Binding llm_fallback_reason:", binding_t.get("llm_fallback_reason"))
art = r["output"]["artifact"]
gaps = r["output"].get("gap_reports", []) or []
print("n_gap_reports:", len(gaps))
for g in gaps:
    print("  gap:", g.get("detected_by"), "|", g.get("gap_type"), "|", g.get("reason")[:200])
print("recommendation.rationale[:300]:", art.get("recommendation",{}).get("rationale","")[:300])
PY
```

**Success criteria.**
- `any_llm_fallback=False`
- `fallback_roles=[]`
- `Binding` role timing shows `llm_used=True, llm_fallback=False`
- `output.gap_reports` carries exactly one gap with `detected_by="Binding"` and the verbatim model refusal text in `reason`
- `recommendation.rationale` begins with `[binding refused]` followed by the model's text and then the deterministic fallback rationale.

If any of these fail, do not commit the patch; debug, fix, and re-verify. If the patch produces an apparently-correct artifact but a different shape than the success criteria, stop and describe the actual artifact shape in the report.

## Task 6: Sanity — Volt Typhoon and CrowdStrike are unaffected

The patch must not change the behavior of non-refusal Binding runs. Re-run the two security-domain demos on the feature branch and confirm zero refusal gaps:

```zsh
for S in volt_typhoon crowdstrike_outage; do
  cp AEGIS-eval/configs/llm_defaults.json AEGIS-eval/configs/llm_defaults.json.bak
  python3 -c "
import json, pathlib
p = pathlib.Path('AEGIS-eval/configs/llm_defaults.json')
cfg = json.loads(p.read_text())
cfg['llm_rag_index'] = '$PWD/demo/$S/rag/${S}__from_binaries.jsonl'
p.write_text(json.dumps(cfg, indent=2))
"
  python3 -m apparatus.run run-system \
    --system mandate_primary \
    --aegis ./AEGIS-eval \
    --tasks demo/$S/tasks/tasks.jsonl \
    --runs 1 \
    --output demo/$S/output_ollama_v2 \
    --code-ref demo-$S-ollama-v2-refusal-gap-sanity \
    --ollama-mode
  mv AEGIS-eval/configs/llm_defaults.json.bak AEGIS-eval/configs/llm_defaults.json
done

# Verify zero refusal gaps on both
python3 - <<'PY'
import json
for s, tid in [("volt_typhoon","TASK-DEMO-VOLT-001"),("crowdstrike_outage","TASK-DEMO-CRWD-001")]:
    r = json.load(open(f"demo/{s}/output_ollama_v2/mandate_primary__{tid}__r01.json"))
    binding_t = next((t for t in r.get("role_timings",[]) if t["role_name"]=="Binding"), {})
    refused = binding_t.get("llm_fallback_reason","").startswith("structured refusal") or False
    gaps = r["output"].get("gap_reports", []) or []
    binding_gaps = [g for g in gaps if g.get("detected_by")=="Binding"]
    print(f"{s}: any_llm_fallback={r['any_llm_fallback']}  binding_refused={refused}  binding_gaps={len(binding_gaps)}")
    assert r["any_llm_fallback"] == False
    assert not refused
    assert len(binding_gaps) == 0
print("Volt and CrowdStrike sanity passed: no new gaps, no new fallbacks.")
PY
```

**Success criteria.** Both scenarios run with `any_llm_fallback=False`, no Binding-attributed gap reports, and identical-to-prior recommendation structure. If either scenario regresses, the patch is too broad; revert and tighten the refusal-detection predicate.

## Task 7: Commit and document

```zsh
cd AEGIS-eval
git add -A
git commit -m "Binding role: surface structured {error: ...} refusals as gap reports

Detect mandate-binding emitting a clean JSON {error: <text>} payload
when the upstream pipeline state is internally contradictory (e.g.
anchor demands N options, Decomposition emitted one). Treat the
refusal as a structured signal: short-circuit the parse retry loop,
attach the model's verbatim error text to the role artifact, run the
deterministic recommendation as a fallback summary, and append a
GapSpec(UNASSESSABLE_RISK, detected_by='Binding') to the run's
gap_reports.

Companion to HANDOFF_16c diagnostic finding (SVB from-binaries run).
The model is not malfunctioning; it is honestly refusing to bind, and
its reasoning belongs in gap_reports rather than the parse-failure
fallback path.

Candidate for MANDATE-primary v2. Frozen tag
mandate-eval-primary-2026q2-v1 is unchanged. PROTOCOL_LOCK §13 holds
for the formal Phase 6 study, which still runs the v1 tag."
git log --oneline -3
cd ..
```

**Success criteria.** Exactly one new commit on `feature/binding-refusal-as-gap` in AEGIS-eval. `main` and the frozen tag are unchanged. The commit message names the diagnostic that motivated the patch.

## Final report

Write `handoffs/HANDOFF_17_report_<YYYY-MM-DD>.md`:

```markdown
# Handoff 17 Report: Binding structured-refusal apparatus patch

**Codex session:** <id>
**Eval host:** <hostname>
**Date:** <YYYY-MM-DD>
**Wall clock:** <minutes>

## Verdict

PROCEED | HALT (one word)

## Evidence

- branch created off frozen tag:           feature/binding-refusal-as-gap @ <hash>
- frozen tag unchanged:                    yes | no
- response_parser.py patch applied:        yes | no
- llm_support.py patch applied:            yes | no
- binding.py patch applied:                yes | no
- pipeline.py gap injection applied:       yes | no
- unit tests created:                      AEGIS-eval/tests/test_binding_refusal.py (<n> tests)
- unit tests passing:                      <n>/<n>
- apparatus suite still passes:            yes | no  (which test failed, if any)
- SVB v2 run:
  - any_llm_fallback:                      <True|False>
  - Binding llm_used:                      <True|False>
  - Binding llm_fallback:                  <True|False>
  - n_gap_reports:                         <n>
  - binding-attributed gap_reports:        <n>  (expected: 1)
  - first 200 chars of recommendation.rationale:
    <verbatim>
- Volt Typhoon v2 sanity:
  - any_llm_fallback:                      <True|False>  (expected: False)
  - binding-attributed gap_reports:        <n>           (expected: 0)
- CrowdStrike v2 sanity:
  - any_llm_fallback:                      <True|False>  (expected: False)
  - binding-attributed gap_reports:        <n>           (expected: 0)

## What the patch changes for the formal study

Nothing. The frozen `mandate-eval-primary-2026q2-v1` tag is unchanged and the formal Phase 6 study still runs that exact code. The patch lives on `feature/binding-refusal-as-gap` as a candidate for MANDATE-primary v2 evaluation.

## What the patch changes for the demo

The SVB from-binaries scenario now produces an artifact that surfaces the Binding model's reasoning as a structured gap report instead of discarding it as a parse failure. The deterministic recommendation is still produced as a fallback summary, prefixed with `[binding refused]` and the verbatim model text.

## Anything the PI must decide before proceeding

- Whether to schedule a v2 calibration handoff that re-runs the full demo trio against the feature branch and confirms the apparatus-suite + demo evidence holds.
- Whether to include the patch on the deposit branch as "v2 candidate, not graded" or to keep it strictly post-deposit.
- Whether to merge the patch into `main` after the v2 calibration completes.

## Deviations from this handoff

<short list, empty if none>
```

Commit message at the apparatus / handoff level: `Handoff 17: Binding structured-refusal as gap_report (candidate v2 patch)`.
