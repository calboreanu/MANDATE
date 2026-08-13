# Codex Handoff 19b: Stage 2 success-criteria revision + Cond-B constraint-gap wrapper + EBNF-aware extractor prompts

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-23 (afternoon)
**Supersedes for Stage 2 only:** the Stage 2 success criteria in `HANDOFF_19_v2_pivot_three_condition_eval.md` §2. Stages 1, 3, 4, 5 from HANDOFF_19 are unchanged in scope; only Stage 2 is re-run with revised criteria and a Cond-B apparatus wrapper.
**Authoritative input docs:**
- `handoffs/HANDOFF_19_stage2_report_2026-06-23.md` (the substantive Stage 2 findings — Cond-A anchor collapse and Cond-B constraint-grammar failure)
- `handoffs/MLT_realness_audit_opus.md` (canonical MLT verification — the constraint grammar is real and intentional, not a bug to work around)

**Estimated wall clock:** Stage 2 re-fire is ~10 minutes after the wrapper lands.
**Estimated API cost:** ~$1.50 for the revised pilots.

---

## Why this exists — and why we're not taking the shortcut

The Stage 2 pilots produced two empirical findings that change the v2 design but do NOT change the v2 goal:

1. **Canonical MANDATE Interpreter always emits single-key `{description: <string>}` for `anchor.minimum` and `anchor.target`**, regardless of input richness. This is the canonical Interpreter's documented job — compress the input description into a single anchor description string. Multi-key minimum/target objects are allowed by the schema but not produced by the canonical Interpreter. The v2 plan's original "≥3 keys in minimum, ≥2 in target" success criteria conflicted with canonical design.

2. **Canonical MANDATE Intake enforces an EBNF constraint grammar.** Constraints must take one of these forms: `FORBIDS <identifier>`, `REQUIRES <identifier>`, `<field> IN [<list>]`, or `<field> <op> <literal>` (with boolean composition via AND / OR / NOT). Natural-language constraints emitted by LLM Intake ("Must align with NIST SP 800-137 guidance") fail `validate_constraint` and halt the role early.

The shortcut path would be: (a) loosen the rubric to ignore anchor richness, (b) silently strip invalid constraints in Cond-B. This handoff explicitly does NOT take that path. Per PI directive (2026-06-23): "no shortcuts; goal is MANDATE-as-code done, period." Instead this handoff:

- Acknowledges canonical Interpreter's single-key design as canonical and measures Cond-A success on the things MANDATE actually controls (canonical-grammar constraint count, COA differentiation, COA semantic grounding in extractor structure).
- Treats Cond-B's natural-language constraint emissions as a measurable EXTRACTION_GAP and routes them into `output.gap_reports` per MANDATE's canonical GapSpec taxonomy, so the run completes AND the extraction-quality gap is quantified AND the Validator's existing gap-checking logic consumes the gaps. This is the same pattern as the v2 candidate Binding-refusal-as-gap patch already documented in Section~14 of the supplement.
- Teaches both extractors the canonical EBNF grammar explicitly so they emit valid constraints whenever the input supports them.
- Commits to multi-iteration discipline. If 2b still surfaces design-mismatch issues, we iterate to 2c, 2d, etc. The empirical process IS the work.

The canonical constraint grammar (from shipped example missions, verified 2026-06-23):

```
target.scope IN ['<id>', '<id>', ...]
execution.duration <= PT<hours>H
FORBIDS <snake_case_identifier>
REQUIRES <snake_case_identifier>
```

These are the shapes the canonical Intake validator accepts. The v2 extractors must emit these or nothing — natural-language must be routed to gaps, not into the constraints array.

---

## Stage 1 status (preserved)

Stage 1 plumbing is committed at `37477ae8` and verified:
- `apparatus/systems/mandate_canonical.py` — canonical adapter
- `apparatus/preprocess/extract_mission_input.py` — Cond-A pre-extractor
- `apparatus/grading/rubric_v2.py` — v2 rubric
- `apparatus/run.py` CLI: `run-cond-a`, `run-cond-b`, `grade-v2`
- Stage 1 suites: 53 passed; full apparatus suite: 278 passed, 1 skipped

Stage 1 does NOT need to be re-run. Stage 2 revision below is the only change.

---

## Preconditions for Stage 2 retry

```zsh
cd "$HOME/Desktop/Desktop - lattice-ws01/MANDATE Evaluation/mandate_eval_2026Q2"

# 1. Use the project venv directly. Do NOT rely on `source .venv/bin/activate`
#    — the activate script's VIRTUAL_ENV path is stale (pre-remap). The Stage 2
#    pilots used .venv/bin/python directly and that's the right pattern.
test -x .venv/bin/python || { echo "HALT: project venv broken"; exit 1; }

# 2. Stage 1 commit is in HEAD
git log --oneline -1 | grep -q "v2 pivot Stage 1" || \
  { echo "WARNING: Stage 1 plumbing commit not at HEAD; verify branch state"; }

# 3. Canonical MLT smoke (corrected pytest cwd)
( cd "$HOME/Desktop/MLT-Governance-Stack" && \
  PYTHONPATH=src .venv/bin/python -m pytest tests/mandate/ -q 2>&1 | tail -3 ) \
  || ( cd "$HOME/Desktop/MLT-Governance-Stack" && \
       PYTHONPATH=src python3 -m pytest tests/mandate/ -q 2>&1 | tail -3 )
# Expected: 418 passed, 8 skipped, 3 xfailed

# 4. Stage 2 pilot artifacts from the previous run are preserved (audit trail)
test -f 07_system_outputs/cond_a/ledger.jsonl && \
  echo "previous Cond-A pilot ledger preserved"
test -f 07_system_outputs/cond_b/ledger.jsonl && \
  echo "previous Cond-B pilot ledger preserved"
# Move them out of the way before the retry; do NOT delete
mkdir -p 07_system_outputs/cond_a/_stage2_attempt1
mkdir -p 07_system_outputs/cond_b/_stage2_attempt1
mv 07_system_outputs/cond_a/*.json 07_system_outputs/cond_a/_stage2_attempt1/ 2>/dev/null
mv 07_system_outputs/cond_a/ledger.jsonl 07_system_outputs/cond_a/_stage2_attempt1/ 2>/dev/null
mv 07_system_outputs/cond_b/*.json 07_system_outputs/cond_b/_stage2_attempt1/ 2>/dev/null
mv 07_system_outputs/cond_b/ledger.jsonl 07_system_outputs/cond_b/_stage2_attempt1/ 2>/dev/null
echo "Stage 2 attempt 1 artifacts quarantined"

# 5. API keys present
.venv/bin/python -c "
import os
from pathlib import Path
for line in Path('.env').read_text().splitlines():
    if '=' in line:
        k, v = line.split('=', 1); os.environ[k] = v.strip()
assert os.environ.get('ANTHROPIC_API_KEY','').startswith('sk-ant')
assert os.environ.get('OPENAI_API_KEY','').startswith('sk-')
assert os.environ.get('GOOGLE_API_KEY','').strip()
print('all three API keys set')
"
```

---

## Task 1: Patch the Cond-A extractor prompt to teach canonical EBNF grammar

File: `apparatus/preprocess/extract_mission_input.py`

The current extractor prompt asks for "constraints: array of strings, each a single constraint extracted verbatim or paraphrased from the task. Format: `category: constraint text`." That's natural-language; canonical MANDATE rejects it.

Replace the constraints block in `EXTRACTION_PROMPT` with explicit grammar teaching:

```python
EXTRACTION_PROMPT_CONSTRAINTS_SECTION = """
- constraints: array of strings in canonical MANDATE EBNF grammar. Each string
  must match one of these four shapes (MANDATE will reject any string that
  doesn't):

  1. `FORBIDS <snake_case_identifier>` — a hard prohibition.
     Examples:
       FORBIDS data_exfiltration
       FORBIDS unauthorized_system_shutdown
       FORBIDS production_modification

  2. `REQUIRES <snake_case_identifier>` — a hard requirement.
     Examples:
       REQUIRES ciso_approval
       REQUIRES nist_800_37_alignment
       REQUIRES interagency_coordination_cycle

  3. `<field>.<subfield> IN [<comma-separated quoted list>]` — scope or
     enumeration constraint. Field is one of: target.scope, target.systems,
     target.actors, target.timeline.
     Examples:
       target.scope IN ['10.0.1.0/24', 'acme.example.com']
       target.scope IN ['FIN-DC-EAST-01', 'FIN-DC-WEST-01']

  4. `<field>.<subfield> <op> <literal>` — comparison constraint. Op is one
     of: <=, >=, <, >, ==, !=. Literal is a duration (PT<N>H, PT<N>M, PT<N>D),
     a quoted string, or a number.
     Examples:
       execution.duration <= PT4H
       execution.duration <= PT8H
       target.completion_deadline <= 2026Q4_end

  RULES:
  - Convert natural-language constraints into one of these four shapes.
  - Use snake_case identifiers, never spaces.
  - Use ISO-8601 duration format for time (PT4H = 4 hours, P30D = 30 days).
  - Use quoted strings inside IN lists, single-quoted.
  - If you cannot map a natural-language constraint to one of the four shapes
    cleanly, OMIT IT FROM THIS ARRAY. Do NOT emit invalid grammar. Omitted
    constraints will be captured separately as extraction gaps by the
    apparatus.
"""
```

Then in `extract()`, after the LLM call, **validate every emitted constraint** with canonical `mlt.mandate.constraints.validate_constraint` before returning. Any constraint that fails validation is moved to the `MissionInput.metadata['extraction_failed_constraints']` list — preserving the verbatim text and the LLM's rationale — and removed from `MissionInput.constraints`. This guarantees what MANDATE sees is canonical-grammar-valid.

```python
def extract(task_id: str, task_text: str, model: str = "claude-sonnet-4-6") -> MissionInput:
    # ... LLM call as before ...
    parsed = json.loads(resp.text.strip())

    # Validate constraints against canonical grammar; route failures to metadata.
    from mlt.mandate.constraints import validate_constraint
    valid_constraints = []
    failed_constraints = []
    for c in parsed.get("constraints", []):
        if validate_constraint(c):
            valid_constraints.append(c)
        else:
            failed_constraints.append({"text": c, "reason": "invalid_grammar"})
    parsed["constraints"] = valid_constraints

    # ... build MissionInput as before, BUT add the failed list to metadata ...
    mi = MissionInput(
        # ... existing fields ...
        metadata={
            # ... existing extraction_model / cost / tokens ...
            "extraction_failed_constraints": failed_constraints,
            "constraints_extracted": len(valid_constraints),
            "constraints_failed_grammar": len(failed_constraints),
        },
    )
    return mi
```

The new tests to add:
- `test_extractor_validates_constraints_against_canonical_grammar` — feed a task; assert all returned `MissionInput.constraints` pass `validate_constraint`.
- `test_extractor_routes_invalid_constraints_to_metadata` — mock the LLM to return one valid + one invalid constraint; assert valid one in `.constraints`, invalid one in `.metadata['extraction_failed_constraints']`.

## Task 2: Build Cond-B apparatus wrapper that routes invalid constraints to gap_reports

File: `apparatus/systems/mandate_canonical.py`, the `run_cond_b` function.

Currently `run_cond_b` calls `Pipeline(config).run(mi)` with raw natural-language text in `mi.intent` and lets the canonical LLM Intake handle extraction. When LLM Intake emits invalid-grammar constraints, canonical Intake hard-fails. The wrapper change: do a post-LLM-Intake interception of invalid constraints, route them to `output.gap_reports` as canonical `GapSpec` entries, and let the rest of the pipeline complete.

The architectural shape (similar to the v2 candidate Binding-refusal-as-gap patch in supplement Section 14):

```python
def run_cond_b(task_id: str, task_text: str, llm_adapter, seed: int = 20260623) -> dict:
    """Cond-B with constraint-grammar gap-routing wrapper.

    Canonical MLT MANDATE LLM-augmented Intake hard-fails when emitted
    constraints don't match the EBNF grammar. For natural-language tasks
    this is the dominant failure mode (Stage 2 attempt 1: 5/5 records
    halted on this). Per HANDOFF_19b: invalid-grammar constraints get
    routed to GapSpec entries in output.gap_reports rather than failing
    the run. The Validator's existing gap-reporting machinery consumes
    them and they're visible to v2 grading.
    """
    from mlt.mandate.constraints import validate_constraint
    from mlt.mandate.models import (
        MissionInput, PipelineConfig, PipelineState,
        GapSpec, GapType, GapSeverity, GapLocation, GapSource,
    )

    # Minimal MissionInput as before
    mi = MissionInput(
        mission_id=task_id, intent=task_text,
        scope=[], constraints=[], available_tools=[],
        metadata={},
    )

    t0 = time.time()

    # === Phase 1: Run Intake + Interpreter ONLY, intercept the LLM-emitted
    # MissionInput before it propagates downstream. This requires
    # constructing the Pipeline manually instead of calling run() end-to-end.
    config = PipelineConfig(strict=False, llm_adapter=llm_adapter,
                            enable_llm_interpreter=True)
    pipe = Pipeline(config)

    # Run Intake (which calls the LLM and populates mi from the response)
    state = PipelineState()
    state.mission_input = mi
    intake_result = pipe.roles["Intake"].execute_with_llm(state, llm_adapter)

    # === Phase 2: Validate the LLM-emitted constraints; quarantine invalid.
    raw_constraints = list(state.mission_input.constraints)
    state.mission_input.constraints = []
    extraction_gaps = []
    for c in raw_constraints:
        if validate_constraint(c):
            state.mission_input.constraints.append(c)
        else:
            extraction_gaps.append(GapSpec(
                gap_type=GapType.UNKNOWN_PATTERN,
                severity=GapSeverity.DEGRADING,
                location=GapLocation.ANCHOR,
                source=GapSource.EXTRACTION_GAP,
                description=(
                    f"LLM Intake emitted a constraint that fails the canonical "
                    f"MANDATE constraint grammar: {c!r}"),
                detected_by="Intake (apparatus wrapper post-LLM)",
                recommended_action=(
                    "Operator review: refine the constraint into one of the "
                    "canonical predicate shapes (FORBIDS/REQUIRES/IN/comparison) "
                    "or accept it as out-of-scope for machine validation."),
            ))

    # === Phase 3: Continue the pipeline from Interpreter onward with the
    # cleaned MissionInput.
    for role_name in ["Interpreter", "Decomposition", "Procedure",
                      "Binding", "Validation"]:
        role_result = pipe.roles[role_name].execute_with_llm(state, llm_adapter)
        # ... (collect role_results as Pipeline.run() does; see canonical
        # pipeline.py for the exact RoleResult propagation)

    # === Phase 4: Inject the extraction gaps into the final artifact.
    artifact = pipe.assemble_artifact(state)
    artifact.setdefault("gap_reports", []).extend([g.to_dict() for g in extraction_gaps])
    artifact.setdefault("metadata", {})["extraction_failed_constraints"] = len(extraction_gaps)

    elapsed_ms = int((time.time() - t0) * 1000)
    return {
        # ... record metadata as before ...
        "output": artifact,
        "ok": True,   # pipeline reaches Validation with cleaned input + gaps
        "errors": [],
        "extraction_failed_constraints": len(extraction_gaps),
    }
```

Implementation note: the canonical `Pipeline.run()` already does the role chaining. The cleanest implementation may NOT reach into `pipe.roles` directly but instead patch `Pipeline.run()` to accept a `pre_validate_constraints=True` flag that does the same interception in-line. Codex should read `MLT-Governance-Stack/src/mlt/mandate/pipeline.py` and pick whichever approach is least invasive. The key invariant: invalid constraints become GapSpec entries in `output.gap_reports` rather than failing the run.

Add tests:
- `test_cond_b_wrapper_routes_invalid_constraints_to_gaps` — provide a fake LLM adapter that emits `["FORBIDS exfil", "Must align with NIST 800-37"]`; assert artifact has 1 valid constraint and 1 gap entry of type UNKNOWN_PATTERN.
- `test_cond_b_wrapper_passes_through_valid_constraints` — fake LLM emits all-valid; assert no gaps and all constraints preserved.
- `test_cond_b_wrapper_run_completes_on_all_invalid` — fake LLM emits all-invalid; assert `ok=True`, 0 constraints, 5 gaps.

## Task 3: Revise Stage 2 success criteria

The revised criteria measure things canonical MANDATE actually controls:

**Cond-A pilot success (5 tasks):**
1. `ok=True` in all 5 records.
2. Extractor produces ≥3 canonical-grammar-valid constraints in at least 4 of 5 records (allows 1 task with sparser explicit constraints, e.g., a short prompt).
3. `MissionInput.metadata['constraints_failed_grammar']` < 50% of total emitted constraints per record (the extractor's prompt update should reduce failures).
4. ≥1 COA generated per record.
5. **COA differentiation check** — for at least 3 of 5 records, the generated COA approach text is NOT the literal string `"Minimal manual assessment approach"`. This is the canonical fallback COA name; if the extractor's structured input is reaching Decomposition, we should see domain-specific approach names (per the canonical decomposition's domain-profile-driven paths).
6. Trace chain present (6 entries, valid chain_hash).
7. Canonical artifact validates against `mandate-as-code.schema.json` (use `mlt.mandate.schema.load_schema`).

**Cond-B pilot success (5 tasks):**
1. `ok=True` in all 5 records (the wrapper guarantees this).
2. `extraction_failed_constraints` is observed per-record but does not block the run.
3. Total `extraction_failed_constraints` across 5 records < 25 (the extractor-prompt update should make MOST constraints validate).
4. ≥1 COA generated per record.
5. Trace chain present.
6. Canonical artifact validates against the canonical schema.
7. `output.gap_reports` contains the extraction-gap entries for the failed constraints; canonical Validator consumed them without crashing.

If both pilots meet their criteria, proceed to Stage 3 per the original HANDOFF_19. If either fails — even on one of these revised criteria — HALT and write a Stage 2b report; we iterate again.

## Task 4: Run the revised Stage 2 pilots

```zsh
cd "$HOME/Desktop/Desktop - lattice-ws01/MANDATE Evaluation/mandate_eval_2026Q2"

# Cond-A revised pilot
.venv/bin/python -m apparatus.run run-cond-a \
  TASK-MAIN-INT-034 TASK-MAIN-FIN-001 TASK-MAIN-FIN-018 \
  TASK-MAIN-INT-003 TASK-MAIN-SEC-014 \
  --out 07_system_outputs/cond_a \
  --extraction-model claude-sonnet-4-6 \
  2> >(tee logs/HANDOFF_19b_cond_a_stage2.stderr >&2)

# Inspect Cond-A results
.venv/bin/python - <<'PY'
import json, glob
from pathlib import Path

records = sorted(glob.glob("07_system_outputs/cond_a/cond_a__TASK-MAIN-*.json"))
print(f"Cond-A pilot records: {len(records)}")
for f in records:
    d = json.load(open(f))
    art = d.get("output", {})
    anchor = art.get("anchor", {})
    coas = art.get("courses_of_action", [])
    mi_meta = d.get("mission_input_metadata", {})  # extractor stuffed metadata
    print(f"  {d.get('task_id')}")
    print(f"    ok: {d.get('ok')}")
    print(f"    constraints valid: {len(anchor.get('constraints',[]))}")
    print(f"    constraints failed grammar: {mi_meta.get('constraints_failed_grammar', '?')}")
    print(f"    COAs: {len(coas)}, first approach: {(coas[0].get('approach') if coas else '?')[:60]}")
    print(f"    artifact schema valid: ", end="")
    try:
        import jsonschema, sys
        sys.path.insert(0, str(Path.home() / 'Desktop/MLT-Governance-Stack/src'))
        from mlt.mandate.schema import load_schema
        jsonschema.validate(art, load_schema('mandate-as-code'))
        print("YES")
    except Exception as e:
        print(f"NO ({type(e).__name__}: {str(e)[:80]})")
PY

# Cond-B revised pilot
.venv/bin/python -m apparatus.run run-cond-b \
  TASK-MAIN-INT-034 TASK-MAIN-FIN-001 TASK-MAIN-FIN-018 \
  TASK-MAIN-INT-003 TASK-MAIN-SEC-014 \
  --out 07_system_outputs/cond_b \
  --llm-backend anthropic \
  --llm-model claude-sonnet-4-6 \
  2> >(tee logs/HANDOFF_19b_cond_b_stage2.stderr >&2)

# Inspect Cond-B results
.venv/bin/python - <<'PY'
import json, glob
records = sorted(glob.glob("07_system_outputs/cond_b/cond_b__TASK-MAIN-*.json"))
print(f"Cond-B pilot records: {len(records)}")
for f in records:
    d = json.load(open(f))
    art = d.get("output", {})
    gaps = art.get("gap_reports", [])
    extr_failed = art.get("metadata", {}).get("extraction_failed_constraints", 0)
    coas = art.get("courses_of_action", [])
    print(f"  {d.get('task_id')}")
    print(f"    ok: {d.get('ok')}")
    print(f"    constraints valid: {len(art.get('anchor',{}).get('constraints',[]))}")
    print(f"    extraction_failed_constraints: {extr_failed}")
    print(f"    extraction gap_reports: {sum(1 for g in gaps if g.get('source')=='EXTRACTION_GAP')}")
    print(f"    COAs: {len(coas)}")
PY
```

## Task 5: Stage 2b report

`handoffs/HANDOFF_19b_stage2_report_2026-06-23.md`:
- Stage 1 status: unchanged from `37477ae8`
- Patches landed: extractor EBNF teaching, Cond-B constraint-gap wrapper, ≥6 new tests
- Cond-A revised pilot: 5-record table with per-record success-criteria column
- Cond-B revised pilot: 5-record table with per-record success-criteria column
- Verdict: PROCEED (to Stage 3) or HALT (to Stage 2c with diagnosis)
- Anomalies / unexpected findings

Commit message:
```
HANDOFF_19b: Stage 2 success-criteria revision aligned with canonical MANDATE design. Cond-A criteria drop multi-key anchor (canonical Interpreter is single-key by design), add canonical-grammar constraint count + COA differentiation. Cond-B apparatus wrapper routes LLM-emitted invalid-grammar constraints to output.gap_reports as EXTRACTION_GAP UNKNOWN_PATTERN, matching the v2 candidate Binding-refusal-as-gap pattern; runs complete with quantified extraction-quality gaps. Both extractor prompts updated with explicit canonical EBNF teaching. Per PI directive: no shortcuts; iterate to 2c/2d/2e if Stage 2b surfaces further design mismatches.
```

---

## If Stage 2b still HALTs (commit to iteration discipline)

Per PI directive: no shortcuts. If Stage 2b fails any of the revised criteria, we go to 2c with a sharper diagnosis. The patterns likely to surface:

- **Extractor still emits some natural-language constraints.** Iterate the prompt with more explicit examples; possibly add a self-check step where the extractor validates its own output before returning. Stage 2c.
- **Decomposition still emits the canonical fallback COA approach name even when given rich `available_tools`.** This would mean the structured input isn't reaching the decomposition role's domain-profile-driven path. Diagnose by inspecting the canonical `decomposition.py` to find why the structured tools aren't being recognized. Stage 2c.
- **Wrapper introduces an artifact-validation failure** (e.g., the injected GapSpec doesn't pass schema validation). Patch the GapSpec construction. Stage 2c.
- **LLM Intake emits a different failure mode** (e.g., emits valid grammar but with hallucinated identifiers like `FORBIDS make_money`). Add a sanity-check layer or accept it. Stage 2c.

Each iteration ships its own report under `handoffs/HANDOFF_19b_stage2_report_attempt_<N>.md`, preserving the prior attempts in `07_system_outputs/cond_<a|b>/_stage2_attempt_<N>/`. We iterate until both conditions produce canonical-shape, schema-valid, completion-true artifacts on a 5-task pilot. The empirical work is the work.

---

## What Stage 2b unblocks

- Stage 3: full 1500-record Cond-A + Cond-B runs (HANDOFF_19 §3, unchanged).
- Stage 4: v2 grading per the existing plan (HANDOFF_19 §4).
- Stage 5: analysis + supplement updates (HANDOFF_19 §5).

The total HANDOFF_19 budget envelope (~$372) is unchanged; the Stage 2 retry cost (~$1.50) is well inside the contingency.

## Housekeeping note

The `.venv/bin/activate` script's `VIRTUAL_ENV` points at the old pre-remap Desktop path (`$HOME/Desktop/MANDATE Evaluation/...`). Sourcing it resolves `python3` to Homebrew Python 3.14, not the project venv. The Stage 2 attempt 1 workaround — use `.venv/bin/python` directly — is correct. To make `source` activation work properly before any Stage 3 long-running command, either (a) recreate the venv at the current path, or (b) edit the `VIRTUAL_ENV=...` line in `.venv/bin/activate`. This is operator housekeeping, not blocking; Stage 2b runs fine with the direct-binary pattern.
