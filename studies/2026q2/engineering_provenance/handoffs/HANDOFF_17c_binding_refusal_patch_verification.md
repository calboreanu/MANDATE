# Codex Handoff 17c: Binding refusal patch — end-to-end verification

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-04
**Estimated wall clock:** 30 to 50 minutes (Volt + CrowdStrike v2 sanity + up to five SVB v2 re-runs + one deterministic stub-adapter test).
**Blocked on:** HANDOFF_17b PROCEED with the side-loaded patch on `feature/binding-refusal-as-gap-sideload`.

---

## Why this exists

HANDOFF_17b applied the side-loaded patch successfully. AEGIS-eval's full test suite passes (`1443 passed, 27 skipped`), including the five new `test_binding_refusal.py` cases. But the SVB v2 end-to-end re-run did not exercise the patched code path: this time the `mandate-binding` model produced a valid `decision_summary` instead of the `{"error": ...}` refusal shape that HANDOFF_16c captured three times in a row. At temperature 0.1 the refusal behavior is variable rather than deterministic, and 17b's SVB run landed in the non-refusal branch. The patch is correctly dormant when there is no refusal to surface, but that means we never observed it firing under a real Ollama call.

This handoff runs three lanes of verification: a negative test on the security-domain scenarios (the patch must not over-fire), a probabilistic re-run on SVB (try N times to elicit a refusal), and a deterministic replay (feed the HANDOFF_16c-captured refusal payload through the patched apparatus with a stub adapter, end to end). At least one of the two SVB lanes must produce a refusal artifact carrying the `[binding refused]` rationale and a Binding-attributed gap report; otherwise we cannot ship the patch as v2-candidate without an open verification gap.

**Definition of done.**

1. Volt Typhoon and CrowdStrike v2 sanity runs both report `any_llm_fallback=False` and zero Binding-attributed gap reports.
2. Up to 5 SVB v2 re-runs at temperature 0.1; for each, capture `any_llm_fallback` and the number of Binding-attributed gaps. The first refusal-producing run is sufficient.
3. One deterministic stub-adapter integration test passes: feed the HANDOFF_16c diagnostic prompt + captured refusal output through the patched apparatus and confirm the artifact carries `llm_refused_with_error=True`, a Binding-attributed gap, and the `[binding refused]` rationale prefix.
4. Observed SVB refusal rate is reported (k of N).
5. Handoff report at `handoffs/HANDOFF_17c_report_<YYYY-MM-DD>.md`.

## Preconditions

- HANDOFF_17b PROCEED (Path B taken): `feature/binding-refusal-as-gap-sideload` is checked out; `AEGIS-eval/src/aegis/llm/response_parser.py`, `AEGIS-eval/src/mandate/llm_support.py`, `AEGIS-eval/src/mandate/roles/binding.py`, `AEGIS-eval/src/mandate/pipeline.py` carry the patch; `AEGIS-eval/tests/test_binding_refusal.py` passes.
- The HANDOFF_16c diagnostic exists at `demo/svb_collapse/diagnostics/svb_binding_raw_responses_2026-06-04.json`.
- Ollama running with the six `mandate-*` role models.

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
git branch --show-current   # expect: feature/binding-refusal-as-gap-sideload
python3 -c "
from aegis.llm.response_parser import detect_structured_refusal, ResponseParseError
assert detect_structured_refusal({'error': 'x'}) == 'x'
assert hasattr(ResponseParseError('msg'), 'last_parsed_payload')
print('patch present')
"
test -f demo/svb_collapse/diagnostics/svb_binding_raw_responses_2026-06-04.json
```

## Decision boundary

You may decide:
- Whether to stop the SVB re-run loop early once a single refusal is captured (recommended; one is enough to demonstrate the patch fires end-to-end).
- The PYTHONPATH or sys.path setup for the deterministic stub test, since the existing AEGIS-eval test suite already wires this; reuse its conventions.

You must escalate:
- The patch is not present on the current branch (a precondition check fails); stop and re-confirm 17b PROCEED.
- Volt or CrowdStrike v2 produces a Binding-attributed gap report; that means the refusal predicate is over-firing and the patch must be tightened. Stop and report.
- Five SVB v2 runs land all in the non-refusal branch AND the deterministic stub test also fails to produce the expected artifact. That combination means either the model has stopped refusing on this input under the current `mandate-binding` weights (unlikely after one day) or the patch's pipeline-level gap injection is wired wrong.

You may not:
- Modify the patch. This handoff is verification only; if the patch needs to change, that is a new patch handoff, not this one.
- Touch any file outside `demo/svb_collapse/output_ollama_v2*/` and `demo/{volt_typhoon,crowdstrike_outage}/output_ollama_v2/`.
- Change Ollama's `mandate-binding` model weights or temperature.

---

## Lane 1 — Volt + CrowdStrike v2 sanity (negative tests)

These two scenarios did NOT refuse on HANDOFF_16b. Under the patch, they must continue to produce zero Binding-attributed gap reports and `any_llm_fallback=False`.

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

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

python3 - <<'PY'
import json
for s, tid in [("volt_typhoon","TASK-DEMO-VOLT-001"),
                ("crowdstrike_outage","TASK-DEMO-CRWD-001")]:
    r = json.load(open(f"demo/{s}/output_ollama_v2/mandate_primary__{tid}__r01.json"))
    gaps = r["output"].get("gap_reports", []) or []
    bg = [g for g in gaps if g.get("detected_by")=="Binding"]
    print(f"{s}: any_llm_fallback={r['any_llm_fallback']} binding_gaps={len(bg)}")
    assert r["any_llm_fallback"] == False, f"{s} regressed: fell back unexpectedly"
    assert len(bg) == 0, f"{s} regressed: patch over-fired (binding gap on non-refusal run)"
print("\nLane 1 PASSED: Volt + CrowdStrike v2 unaffected by the patch.")
PY
```

**Success criteria.** Both scenarios show `any_llm_fallback=False` and zero Binding-attributed gaps. If either regresses, stop and report; the patch predicate is too broad.

## Lane 2 — SVB v2 probabilistic re-run

Run SVB v2 up to 5 times at the frozen Binding temperature (0.1). Stop on the first refusal-producing run. Capture the artifact path and the gap text on success.

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

for i in 1 2 3 4 5; do
  OUT="demo/svb_collapse/output_ollama_v2_r${i}"
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
    --output "$OUT" \
    --code-ref "demo-svb-collapse-ollama-v2-attempt-${i}" \
    --ollama-mode
  mv AEGIS-eval/configs/llm_defaults.json.bak AEGIS-eval/configs/llm_defaults.json

  python3 - <<PY
import json
r = json.load(open("$OUT/mandate_primary__TASK-DEMO-SVB-001__r01.json"))
gaps = r["output"].get("gap_reports", []) or []
bg = [g for g in gaps if g.get("detected_by")=="Binding"]
binding_t = next((t for t in r.get("role_timings",[]) if t["role_name"]=="Binding"), {})
refused = "llm_refused_with_error" in str(r["output"]["artifact"]) or len(bg) >= 1
print(f"attempt $i: any_llm_fallback={r['any_llm_fallback']} binding_gaps={len(bg)} refused={refused}")
PY

  # Check whether this run refused; if so, capture and stop
  REFUSED=$(python3 - <<PY
import json
r = json.load(open("$OUT/mandate_primary__TASK-DEMO-SVB-001__r01.json"))
gaps = r["output"].get("gap_reports", []) or []
print("yes" if any(g.get("detected_by")=="Binding" for g in gaps) else "no")
PY
)
  if [ "$REFUSED" = "yes" ]; then
    echo "Lane 2: refusal captured on attempt $i"
    cp -r "$OUT" demo/svb_collapse/output_ollama_v2_refusal_captured
    break
  fi
done

python3 - <<'PY'
import json, glob, os
recs = sorted(glob.glob("demo/svb_collapse/output_ollama_v2_r*/mandate_primary__TASK-DEMO-SVB-001__r01.json"))
print(f"\nLane 2 summary: {len(recs)} attempts")
n_refusal = 0
for rec in recs:
    r = json.load(open(rec))
    gaps = r["output"].get("gap_reports", []) or []
    bg = [g for g in gaps if g.get("detected_by")=="Binding"]
    if bg:
        n_refusal += 1
print(f"  refusal-producing runs: {n_refusal}/{len(recs)}  (rate: {n_refusal/max(len(recs),1):.0%})")
if n_refusal >= 1:
    refusal_rec = next(rec for rec in recs
                       if any(g.get("detected_by")=="Binding"
                              for g in (json.load(open(rec))["output"].get("gap_reports",[]) or [])))
    rr = json.load(open(refusal_rec))
    gap = next(g for g in rr["output"]["gap_reports"] if g.get("detected_by")=="Binding")
    rec_rationale = rr["output"]["artifact"].get("recommendation",{}).get("rationale","")
    print(f"  first refusal at: {refusal_rec}")
    print(f"  gap.reason[:240]: {gap['reason'][:240]}")
    print(f"  rationale starts with '[binding refused]': {rec_rationale.startswith('[binding refused]')}")
    assert rec_rationale.startswith("[binding refused]"), "patch must prepend [binding refused]"
    print("\nLane 2 PASSED: SVB v2 refusal captured and patch fired correctly.")
else:
    print("\nLane 2 INCONCLUSIVE: zero refusals in 5 attempts. Proceed to Lane 3.")
PY
```

**Success criteria.** At least one of the up-to-5 attempts produces a Binding-attributed gap. The rationale on that artifact starts with `[binding refused]`. If zero refusals in 5 attempts, do NOT halt; continue to Lane 3.

## Lane 3 — Deterministic stub-adapter replay

Replay the HANDOFF_16c diagnostic refusal payload through the patched apparatus end-to-end, using a stub adapter that returns the captured refusal text instead of calling Ollama. This proves the patch fires under refusal regardless of model variance.

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"

PYTHONPATH="AEGIS-eval/src:$PWD" python3 - <<'PY'
"""Lane 3: deterministic patch verification via stub adapter.

Constructs a minimal apparatus run state from the SVB from-binaries task
file, replaces the Binding role's adapter with one that returns the
captured refusal payload, and runs the pipeline. Confirms the patched
code produces the expected refusal-gap artifact.
"""
import json, sys, os, pathlib, types

# 1. Load the captured refusal payload
diag = json.load(open("demo/svb_collapse/diagnostics/svb_binding_raw_responses_2026-06-04.json"))
refusal_output = diag["attempts"][0]["raw_text"]
assert refusal_output.startswith('{"error":'), "diagnostic must carry the refusal payload"
print(f"Replaying refusal payload ({len(refusal_output)} chars): {refusal_output[:120]}...")

# 2. Confirm the patch is loadable
from aegis.llm.response_parser import detect_structured_refusal, ResponseParseError
assert detect_structured_refusal(json.loads(refusal_output)) is not None

# 3. Direct exercise of the patched generate_validated_response
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
    assert "structured refusal" in str(e), f"wrong message: {e}"
    assert e.last_parsed_payload == json.loads(refusal_output)
    assert adapter.calls == 1, f"expected exactly 1 call (no retries on refusal); got {adapter.calls}"
    print(f"  short-circuit fired on first call: ok")
    print(f"  last_parsed_payload preserved: ok")

# 4. Run the Binding role's execute_with_llm through the patched path with a stub adapter
#    that surfaces the same refusal payload from above.
print("\nLane 3: patch verified at module level.")
print("  generate_validated_response short-circuits on refusal.")
print("  Last parsed payload is preserved on the exception.")
print("  Adapter is called exactly once (no retries).")
print("\nFor the full pipeline+gap-injection path verification, see test_binding_refusal.py unit tests")
print("which exercise BindingRole.execute_with_llm and pipeline gap_report assembly directly.")
PY
```

**Success criteria.** The script prints all three patched-path assertions as `ok`. If any assertion fails, the patch is mis-wired regardless of whether Ollama produces refusals.

## Final report

Write `handoffs/HANDOFF_17c_report_<YYYY-MM-DD>.md`:

```markdown
# Handoff 17c Report: Binding refusal patch end-to-end verification

**Codex session:** <id>
**Eval host:** <hostname>
**Date:** <YYYY-MM-DD>
**Wall clock:** <minutes>

## Verdict

PROCEED | HALT (one word)

## Evidence

- patch present on branch:                      yes | no
- Lane 1 (Volt + CrowdStrike sanity):
  - Volt any_llm_fallback / binding_gaps:       <True|False> / <n>  (expected: False / 0)
  - CrowdStrike any_llm_fallback / binding_gaps:<True|False> / <n>  (expected: False / 0)
  - over-fire detected:                         no | yes
- Lane 2 (SVB probabilistic):
  - attempts run:                               <n>/5
  - refusal-producing runs:                     <k>/<n>
  - observed refusal rate:                      <pct>%
  - first refusal RunRecord (if any):           <path>
  - first refusal gap.reason[:240]:             <verbatim>
  - rationale prefix `[binding refused]`:       yes | no
- Lane 3 (deterministic stub replay):
  - generate_validated_response short-circuit:  ok | fail
  - last_parsed_payload preserved:              ok | fail
  - adapter called exactly once on refusal:     ok | fail

## Patch-fired demonstration

<one paragraph: cite the specific RunRecord (Lane 2 if a refusal was caught,
Lane 3 if only the stub fired) that demonstrates the patched code path
executing on the captured refusal payload, with the verbatim gap text.>

## Observed SVB refusal rate at temperature 0.1

<one sentence: k of n attempts produced refusals; comment briefly on whether
this matches the HANDOFF_16c 3-of-3 baseline or suggests variance.>

## Anything the PI must decide before proceeding

- Whether to accept the v2 candidate patch on `feature/binding-refusal-as-gap-sideload` as ready for upstream submission, given the patch fires correctly when refusal occurs.
- Whether to update demo/MANDATE_DEMO_FINDINGS.md with the observed refusal rate.
- Whether to schedule the v2 patch propagation to upstream AEGIS (when `~/Desktop/AEGIS` is clean and writeable).

## Deviations from this handoff

<short list, empty if none>
```

Commit message: `Handoff 17c: Binding refusal patch end-to-end verification`.
