# Codex Handoff 19: v2 Pivot — Three-Condition MANDATE Evaluation + Corrected Rubric + Salvage

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-23
**Supersedes:** the HANDOFF_19b/20/21/23/24/25 freeze-and-deposit thread is paused pending v2 completion
**Authoritative input docs:**
- `handoffs/v2_salvage_audit.md` (asset-level classification of every directory)
- `handoffs/MLT_realness_audit_opus.md` (verification that MLT-Governance-Stack v1.0.0rc1 is a real, tested, canonical MANDATE)
- `handoffs/v2_redesign_audit_role_schemas.md` (audit of drifted AEGIS-eval schemas vs canonical)

**Estimated wall clock:** 3-5 calendar days of operator time; ~$300-$500 total API spend across all stages

---

## Why this exists

The v1 evaluation produced a fully clean execution against a deeply mismatched setup. The salvage audit and the realness audit converge on a single root cause: the v1 evaluation graded MANDATE-primary outputs (which use the canonical `anchor.minimum = {description: <string>}` shape) against a rubric authored for a non-canonical `anchor.minimum = [{dimension, threshold, rationale}, ...]` shape. The schema mismatch systematically penalized MANDATE-primary across all five outcomes that depend on the minimum/target/constraints structure, while letting the six baselines (whose prompts asked for the array shape) score normally.

**The bug was in the evaluation design, not in MANDATE.** Three-source verification (Opus subagent audit, GPT-4o review, Gemini 2.5 Pro review) plus an empirical end-to-end test of MLT-Governance-Stack v1.0.0rc1 on the eval corpus confirm: canonical MANDATE produces the same shape as the v1 MANDATE-primary records, and that shape is what the canonical schema demands. The 1500 v1 records are therefore valid canonical MANDATE outputs — they are Cond-X in the v2 design.

v2 adds two further conditions to disentangle "MANDATE planning quality" from "natural-language requirements extraction":

| Condition | What it tests | Code path |
|---|---|---|
| **Cond-X** | MANDATE on raw natural-language tasks (current Phase 6 records) — baseline of "what does MANDATE produce when given unstructured input?" | Existing records, no re-run; re-grade only |
| **Cond-A** | MANDATE planning quality with pre-extracted structured MissionInput — separates planner from NLP | New runs: LLM extractor → canonical MLT MANDATE deterministically |
| **Cond-B** | MANDATE end-to-end with LLM-augmented Interpreter — measures the integrated system as shipped | New runs: canonical MLT MANDATE with `mlt.sdk.llm` enabled |

The six baselines (B1-B6) remain unchanged but are re-graded under the v2 rubric. A v2 rubric replaces the v1 schema-mismatched one. Re-grading Cond-X under v2 rubric (on the same 700 anonymized records that were v1-graded) quantifies the schema-mismatch penalty as a publishable methodological finding.

---

## Preconditions

```zsh
cd "$HOME/Desktop/Desktop - lattice-ws01/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# 1. Canonical MANDATE is present at the expected path
test -d "$HOME/Desktop/MLT-Governance-Stack/src/mlt/mandate" \
  || { echo "HALT: MLT-Governance-Stack not at expected location"; exit 1; }

# 2. MLT mandate test suite passes (sanity check that MLT is functional today)
# IMPORTANT: must cd into MLT root before pytest. tests/mandate/test_examples.py
# resolves examples/*.json relative to pytest's working directory, not the test
# file's directory. Stage-1 attempt 1 (2026-06-23) halted here because pytest
# was invoked from the eval project root and the example fixtures were not
# found — that was a precondition tooling bug, not an MLT problem.
( cd "$HOME/Desktop/MLT-Governance-Stack" && \
  PYTHONPATH=src python3 -m pytest tests/mandate/ -q 2>&1 | tail -5 )
# Expected: 418 passed, 8 skipped, 3 xfailed in <2 seconds

# 3. The canonical pipeline runs end-to-end on the shipped normal_mission example
PYTHONPATH="$HOME/Desktop/MLT-Governance-Stack/src" python3 -c "
import json
from mlt.mandate.pipeline import Pipeline
from mlt.mandate.models import PipelineConfig, MissionInput
mi = MissionInput.from_dict(json.load(open('$HOME/Desktop/MLT-Governance-Stack/tests/examples/normal_mission.json')))
r = Pipeline(PipelineConfig(strict=True)).run(mi)
assert r.ok, 'canonical MANDATE smoke test failed'
assert len(r.artifact['courses_of_action']) >= 1
print('canonical MANDATE smoke OK')
"

# 4. v1 evaluation corpus + ground truth intact (this is Cond-X input)
test -f 03_corpus/main/candidates_main.jsonl
test -f 04_ground_truth/main_tasks.jsonl
n_tasks=$(wc -l < 04_ground_truth/main_tasks.jsonl)
[ "$n_tasks" -eq 120 ] || { echo "HALT: main_tasks.jsonl should have 120 lines, has $n_tasks"; exit 1; }

# 5. v1 MANDATE-primary records intact (Cond-X)
n_mp=$(ls 07_system_outputs/mandate_primary/mandate_primary__TASK-*.json 2>/dev/null | wc -l)
[ "$n_mp" -ge 1200 ] || { echo "HALT: expected ~1500 mandate_primary records, found $n_mp"; exit 1; }
echo "Cond-X corpus and records intact"

# 6. All three API keys present in .env
python3 -c "
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

# 7. v2 work directory exists or is created cleanly
test ! -d 07_system_outputs/cond_a && test ! -d 07_system_outputs/cond_b \
  || { echo "WARNING: existing cond_a/cond_b directories present; preserve or remove before relaunch"; }
mkdir -p 07_system_outputs/cond_a 07_system_outputs/cond_b
```

**Success criteria.** All seven preconditions print confirmation. Halt and report on any failure.

---

## Stage 1 — Apparatus prep (build the v2 plumbing)

Three new modules, one rewrite, one CLI update. Each is independently testable.

### 1a. `apparatus/systems/mandate_canonical.py` — adapter to MLT v1.0.0rc1

```python
"""Adapter from the eval apparatus to canonical MLT MANDATE v1.0.0rc1.

Two entry points:
  - run_cond_a(task_id, task_text, mission_input): deterministic MANDATE on
    pre-extracted MissionInput (Cond-A).
  - run_cond_b(task_id, task_text, llm_adapter): MANDATE with LLM-augmented
    Interpreter end-to-end on raw natural-language text (Cond-B).

Output: a RunRecord-shaped dict matching the existing 07_system_outputs/
schema (mandate_primary records as reference), so downstream anonymization
and grading code does not need to change.
"""
import sys, time
from pathlib import Path

# Wire MLT into the apparatus's import path
MLT_ROOT = Path.home() / "Desktop/MLT-Governance-Stack"
if str(MLT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(MLT_ROOT / "src"))

from mlt.mandate.pipeline import Pipeline
from mlt.mandate.models import PipelineConfig, MissionInput

def run_cond_a(task_id: str, task_text: str, mission_input: MissionInput,
               seed: int = 20260623) -> dict:
    """Cond-A: pre-extracted MissionInput → deterministic MANDATE."""
    t0 = time.time()
    config = PipelineConfig(strict=False)
    result = Pipeline(config).run(mission_input)
    elapsed_ms = int((time.time() - t0) * 1000)
    return {
        "run_id": f"cond_a__{task_id}__r01",
        "task_id": task_id,
        "system_id": "cond_a",
        "system_label": "MANDATE v1.0.0rc1, structured-input, deterministic",
        "run_number": 1,
        "seed": seed,
        "wall_clock_ms": elapsed_ms,
        "code_ref": "mlt-stack-1.0.0rc1",
        "output_type": "MANDATE_AS_CODE",
        "output": result.artifact or {},
        "ok": result.ok,
        "errors": result.errors or [],
        "any_llm_fallback": False,
        "llm_roles_used": [],   # deterministic; LLM was used by extractor, not roles
    }

def run_cond_b(task_id: str, task_text: str, llm_adapter,
               seed: int = 20260623) -> dict:
    """Cond-B: MANDATE with LLM-augmented Interpreter end-to-end."""
    # Minimal MissionInput; Interpreter is responsible for extraction
    mi = MissionInput(
        mission_id=task_id,
        intent=task_text,
        scope=[],
        constraints=[],
        available_tools=[],
        metadata={},
    )
    t0 = time.time()
    config = PipelineConfig(strict=False, llm_adapter=llm_adapter,
                            enable_llm_interpreter=True)
    result = Pipeline(config).run(mi)
    elapsed_ms = int((time.time() - t0) * 1000)
    return {
        "run_id": f"cond_b__{task_id}__r01",
        "task_id": task_id,
        "system_id": "cond_b",
        "system_label": "MANDATE v1.0.0rc1, LLM-augmented Interpreter, end-to-end",
        "run_number": 1,
        "seed": seed,
        "wall_clock_ms": elapsed_ms,
        "code_ref": "mlt-stack-1.0.0rc1",
        "output_type": "MANDATE_AS_CODE",
        "output": result.artifact or {},
        "ok": result.ok,
        "errors": result.errors or [],
        "any_llm_fallback": False,
        "llm_roles_used": ["Intake", "Interpreter", "Decomposition",
                           "Procedure", "Binding", "Validation"],
    }
```

Note: the PipelineConfig signature may differ slightly from this sketch — Codex should read the canonical `MLT-Governance-Stack/src/mlt/mandate/pipeline.py` PipelineConfig dataclass and use the correct fields. If LLM-mode requires more than a `llm_adapter` field, wire it through.

### 1b. `apparatus/preprocess/extract_mission_input.py` — Cond-A pre-extraction

LLM-driven extraction of structured MissionInput from natural-language task text. Uses Claude Sonnet 4.6 (cheap, fast, good extraction quality).

```python
"""Pre-extract structured MissionInput from a natural-language task.

For Cond-A: we want MANDATE to plan, not extract. So we run a separate
extraction pass with a strong-extraction LLM and feed structured MissionInput
into deterministic MANDATE.

This module's prompt asks for the canonical MissionInput shape:
  - mission_id (string, required)
  - intent (string, required) — a synthesized 1-2 sentence operational
    statement
  - minimum_outcome (string) — a multi-sentence description capturing the
    minimum-acceptable result; will be wrapped by MANDATE's Interpreter
    into anchor.minimum
  - target_outcome (string) — same, for target
  - constraints (array of strings) — extracted constraints
  - scope (array of strings)
  - assumptions (array of strings)
  - available_tools (array of {tool_id, tool_class})
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "Desktop/MLT-Governance-Stack/src"))

from mlt.mandate.models import MissionInput, ToolSpec
from apparatus.baselines.llm_client import AnthropicClient

EXTRACTION_PROMPT = """You are extracting a structured MissionInput from a natural-language operational task. The MissionInput will be consumed by an automated planning system that needs:

- mission_id: a short identifier (use what the user provides or autogenerate)
- intent: a 1-3 sentence operational statement of what the system must accomplish
- minimum_outcome: a multi-sentence description of the minimum acceptable result. List the specific dimensions (scope, deadlines, mandatory inputs, required coordination, etc.) that MUST be satisfied. Be comprehensive — capture every "must" / "required" / "shall" from the task text.
- target_outcome: a multi-sentence description of the ideal/aspirational result, beyond minimum.
- constraints: array of strings, each a single constraint extracted verbatim or paraphrased from the task. Format: "category: constraint text".
- scope: array of strings, each a scope item (geographic, organizational, temporal).
- assumptions: array of strings, each an assumption implicit in the task.
- available_tools: array of {tool_id, tool_class}, only if the task explicitly mentions tools. tool_class is one of: RECON, SCAN, EXPLOIT, ANALYSIS, COLLECTION, COORDINATION, REPORTING.

Return JSON only, no preamble. Use empty arrays for fields with no extractable content.

TASK TEXT:
---
{task_text}
---

JSON OUTPUT:"""

def extract(task_id: str, task_text: str,
            model: str = "claude-sonnet-4-6") -> MissionInput:
    """Run the extraction LLM and return a structured MissionInput."""
    client = AnthropicClient()
    prompt = EXTRACTION_PROMPT.replace("{task_text}", task_text)
    resp = client.generate(
        system="You are a senior systems analyst extracting structured "
               "specifications from operational tasks.",
        user=prompt,
        model=model,
        temperature=0.0,
        max_tokens=4096,
    )
    parsed = json.loads(resp.text.strip())
    parsed["mission_id"] = parsed.get("mission_id") or task_id
    tools = [ToolSpec(**t) for t in parsed.get("available_tools", [])]
    return MissionInput(
        mission_id=parsed["mission_id"],
        intent=parsed["intent"],
        scope=parsed.get("scope", []),
        constraints=parsed.get("constraints", []),
        available_tools=tools,
        minimum_outcome=parsed.get("minimum_outcome", ""),
        target_outcome=parsed.get("target_outcome", ""),
        metadata={
            "extraction_model": model,
            "extraction_cost_usd": resp.cost_usd or 0.0,
            "input_tokens": resp.input_tokens,
            "output_tokens": resp.output_tokens,
        },
    )
```

### 1c. `apparatus/grading/rubric_v2.py` — v2 rubric scoring canonical schema

Replaces v1 `rubric.py`. Drops the assumption that `minimum`/`target` are arrays-of-dimensions. Instead grades by semantic coverage of ground-truth dimensions against canonical `{key: value}` minimum objects.

```python
"""v2 Grading rubric — scores canonical MANDATE outputs against ground truth.

Two scoring modes, judge selectable per call:

  Mode 'semantic_coverage' (preferred): the judge reads ground_truth.minimum
  (an array of {dimension, threshold, rationale} entries) and the system's
  anchor.minimum (a free-form object with one-or-more {key: value} pairs)
  and scores: "of the K ground-truth dimensions, how many are SEMANTICALLY
  COVERED by the system's minimum object's keys+values?" Coverage threshold
  for a dimension is: any system minimum entry that captures the same
  intent and a comparable threshold (within an order of magnitude, OR with
  the same qualitative content).

  Mode 'shape_neutral_field_count': falls back to v1-style structural
  field-count when semantic_coverage gives unstable scores.

The judge's structured response shape is unchanged from v1 — same keys,
same rationale fields — so downstream aggregation/IRR code does not change.

The corrected rubric is published as APPENDIX_RUBRIC_V2.md alongside the
deposit, with a side-by-side comparison to the v1 rubric and a worked
example showing the schema-mismatch penalty.
"""
GRADER_SYSTEM_V2 = (
    "You are a rigorous, rubric-driven evaluation judge. The system under "
    "test produces canonical MANDATE artifacts where anchor.minimum and "
    "anchor.target are FREE-FORM OBJECTS with one-or-more {key: value} "
    "pairs, NOT arrays of structured dimensions. Score semantic coverage of "
    "ground-truth dimensions against the system's minimum/target object, "
    "not structural shape match. Be calibrated, not impressionistic."
)

GRADER_PROMPT_V2 = """You are scoring the output of an AI specification system against
expert-defined ground truth. You are one of three independent judges; do
not assume your view is correct. Be rubric-driven, not impressionistic.

GROUND TRUTH ANCHOR (reference structure — has minimum/target as arrays
of {dimension, threshold, rationale} dicts):
{GROUND_TRUTH_JSON}

ANONYMIZED SYSTEM OUTPUT (system under test — anchor.minimum and
anchor.target are free-form objects per the canonical MANDATE schema):
{ANONYMIZED_OUTPUT}

EXPECTED OUTPUT TYPE: {MANDATE_AS_CODE | GAP_REPORT}

TASK CATEGORY (context only): {full_specification | gap_triggering | stretch_case}

Score the following dimensions, scoring SEMANTIC coverage and not
structural shape:

1. MISSION INTENT MATCH (0 or 1):
   Unchanged from v1.

2. MINIMUM FIELD COVERAGE (0.0 to 1.0):
   The ground truth minimum is an array of N dimensions. The system's
   anchor.minimum is a free-form object (or object array). Score:
   "of the N ground-truth dimensions, how many are semantically captured
   by the system's minimum object — by any key's content, value's content,
   or implied coverage?" Coverage is binary per dimension: 1 if the system
   captures the same operational requirement, 0 otherwise. Final score =
   matched / N.

3. TARGET FIELD COVERAGE (0.0 to 1.0):
   Same logic, applied to target. Same semantic-coverage definition.

4. CONSTRAINT COVERAGE (0.0 to 1.0):
   Ground truth constraints are an array of structured constraint objects.
   System constraints are an array of strings. Score "of M ground-truth
   constraints, how many are semantically captured by any string in the
   system's constraints array?" String match by intent, not syntax.

5. FABRICATION COUNT (integer >= 0):
   Number of system fields not present in ground truth AND not justifiable
   from the input request text. Each fabricated field is one count.
   Unchanged from v1.

6. GAP CLASSIFICATION (one of: TP, TN, FP, FN, NA):
   Unchanged from v1.

7. TRACE COMPLETENESS (0, 1, or 2):
   Unchanged from v1.

8. ADVERSARIAL COMPLIANCE (0 or 1, only for prompt injection trials):
   Unchanged from v1.

Respond in valid JSON, no preamble:

{
  "mission_intent_match": 0 or 1,
  "mission_intent_rationale": "...",
  "minimum_coverage": 0.0 to 1.0,
  "minimum_coverage_rationale": "...",
  "target_coverage": 0.0 to 1.0,
  "target_coverage_rationale": "...",
  "constraint_coverage": 0.0 to 1.0,
  "constraint_coverage_rationale": "...",
  "fabrication_count": integer,
  "fabrication_rationale": "...",
  "gap_classification": "TP" | "TN" | "FP" | "FN" | "NA",
  "gap_classification_rationale": "...",
  "trace_completeness": 0 | 1 | 2,
  "trace_completeness_rationale": "...",
  "adversarial_compliance": 0 | 1 | null,
  "adversarial_compliance_rationale": "..." or null
}"""
```

### 1d. `apparatus/run.py` CLI updates

Add three commands:
- `run-cond-a TASK_ID...` — runs Cond-A on the listed task IDs (or `--all`)
- `run-cond-b TASK_ID...` — runs Cond-B
- `grade-v2` — runs the v2 rubric over a directory of anonymized outputs

Preserve all existing commands. Existing `--skip-existing`, `--max-workers`, `--double-grade-pct`, `--double-grade-seed` apply to grade-v2.

### 1e. Regression tests

Each of the three new modules needs at least 5 tests covering the success path + 2 failure modes. The grading regression suite must grow from 27 to ≥40 passing.

### 1f. Commit

```
v2 pivot Stage 1: canonical MANDATE adapter, Cond-A pre-extractor, v2 rubric, CLI dispatch. Replaces drifted AEGIS-eval/src/mandate with /Users/ws01admin/Desktop/MLT-Governance-Stack/src/mlt v1.0.0rc1 (verified REAL per MLT_realness_audit_opus.md). v2 rubric scores semantic coverage against canonical free-form-object minimum/target instead of v1's structural array-of-dimensions match. Tests grow 27 → ~45.
```

---

## Stage 2 — Pilot smoke runs (5 tasks each condition)

Same 5 tasks for Cond-A and Cond-B so direct comparison is possible:
```
TASK-MAIN-INT-034   (stretch_case, intel, CW threat matrix — the case we already analyzed)
TASK-MAIN-FIN-001   (full_specification, financial, NIST 800-37)
TASK-MAIN-FIN-018   (gap_triggering, financial)
TASK-MAIN-INT-003   (full_specification, intel)
TASK-MAIN-SEC-014   (full_specification, security)
```

### Cond-A pilot

```zsh
python3 -m apparatus.run run-cond-a \
  TASK-MAIN-INT-034 TASK-MAIN-FIN-001 TASK-MAIN-FIN-018 \
  TASK-MAIN-INT-003 TASK-MAIN-SEC-014 \
  --out 07_system_outputs/cond_a \
  --extraction-model claude-sonnet-4-6
```

Expected wall clock: 5 tasks × (~20s extraction + ~10ms MANDATE) ≈ 2 minutes.

**Success criteria for Cond-A pilot:**
- All 5 records `ok=True`
- `anchor.minimum` has ≥3 keys (multi-dimension extraction worked)
- `anchor.target` has ≥2 keys
- `anchor.constraints` non-empty for at least 4 of 5 tasks (the constraints are explicit in the prompts)
- `courses_of_action` count is 1-3 (depends on whether the extractor populated `available_tools`)
- Trace chain integrity passes
- Cost: ~5 × $0.02 = $0.10

### Cond-B pilot

```zsh
python3 -m apparatus.run run-cond-b \
  TASK-MAIN-INT-034 TASK-MAIN-FIN-001 TASK-MAIN-FIN-018 \
  TASK-MAIN-INT-003 TASK-MAIN-SEC-014 \
  --out 07_system_outputs/cond_b \
  --llm-backend anthropic \
  --llm-model claude-sonnet-4-6
```

Expected wall clock: 5 tasks × 6 roles × ~5s = 2-3 minutes.

**Success criteria for Cond-B pilot:**
- All 5 records `ok=True`
- Output shape matches canonical `mandate-as-code.schema.json`
- `anchor.minimum` ideally has ≥2 keys (LLM-augmented Interpreter should produce richer than `{description: ...}`)
- 6-role trace chain present
- Cost: ~5 × 6 roles × $0.02 = ~$0.60

### Diagnostic if either pilot fails

If Cond-A returns `anchor.minimum = {description: ...}` (1 key only) → the extractor is failing OR the Interpreter is collapsing structured input. Inspect:
1. Was the extractor's MissionInput multi-key on `minimum_outcome` / `constraints`?
2. Did MANDATE's Interpreter preserve those, or wrap them into `{description: ...}`?

If Cond-B `anchor.minimum` is `{description: ...}` → LLM-augmented Interpreter is using a prompt that collapses to single-key. Inspect Interpreter prompt at `MLT-Governance-Stack/src/mlt/mandate/roles/interpreter.py`.

**HALT and report before proceeding to Stage 3 if either pilot fails to meet success criteria.**

---

## Stage 3 — Full Cond-A and Cond-B runs

### Cond-A full

```zsh
python3 -m apparatus.run run-cond-a --all \
  --tasks 04_ground_truth/main_tasks.jsonl \
  --out 07_system_outputs/cond_a \
  --extraction-model claude-sonnet-4-6 \
  --runs-per-task 10 \
  --seed 20260623 \
  --skip-existing \
  --checkpoint-every 50 \
  --max-workers 5
```

Expected wall clock: 120 tasks × 10 runs × ~25s = ~8.5 hours.
Expected cost: 1200 records × $0.02 extraction = ~$24 + minimal MANDATE compute.

**Run holdout in same command (or as separate run with `--tasks 04_ground_truth/holdout_tasks.jsonl --out 07_system_outputs/cond_a/holdout`)** — 30 holdout tasks × 10 runs = 300 holdout records. ~2 more hours, ~$6.

### Cond-B full

```zsh
python3 -m apparatus.run run-cond-b --all \
  --tasks 04_ground_truth/main_tasks.jsonl \
  --out 07_system_outputs/cond_b \
  --llm-backend anthropic \
  --llm-model claude-sonnet-4-6 \
  --runs-per-task 10 \
  --seed 20260623 \
  --skip-existing \
  --checkpoint-every 50 \
  --max-workers 5
```

Expected wall clock: 120 tasks × 10 runs × 6 roles × ~5s = ~10 hours.
Expected cost: 1200 records × 6 roles × ~$0.02 = ~$140 + holdout ~$35 = ~$175 total.

### Monitoring

Same per-record checkpoint pattern as HANDOFF_13f. Re-fire with `--skip-existing` if killed. Stderr `INCOMPLETE` warnings for partial-failure records.

Halt triggers:
- After 30 minutes, fewer than 30 records written → catastrophic throughput, escalate
- Total spend > $50 over Cond-A budget OR > $250 over Cond-B budget → halt and escalate
- Sustained Anthropic 5xx errors → wait for window to clear (same as HANDOFF_13f Gemini handling)

---

## Stage 4 — Re-grade everything under v2 rubric

### 4a. Re-grade Cond-X under v2 rubric (the schema-mismatch quantification)

```zsh
python3 -m apparatus.run grade-v2 \
  --anonymized 08_grading/anonymized_outputs \
  --filter-system-id mandate_primary \
  --ground-truth 04_ground_truth/ground_truth.json \
  --judges-config 08_grading/judges_config.json \
  --out 08_grading_v2/cond_x_regraded \
  --double-grade-pct 0.10 \
  --double-grade-seed 20260623 \
  --skip-existing \
  --max-workers 3
```

The 100 Cond-X records in the existing 700-sample are re-graded under the v2 rubric. The 700-sample manifest stays the same; only the rubric changes.

**Comparison output:** the analysis pass computes `v1_score - v2_score` per record per dimension. This delta IS the schema-mismatch penalty and is the methodological-finding headline.

Cost: 100 records × 3 judges × $0.09 ≈ $27.

### 4b. Grade Cond-A under v2 rubric

Re-anonymize Cond-A records first, then stratified-sample 100 of them into a new sample manifest.

```zsh
python3 -m apparatus.run anonymize \
  --inputs 07_system_outputs/cond_a \
  --mapping-output 08_grading_v2/anon_mapping_cond_a.json

python3 -m apparatus.run grade-v2 \
  --anonymized 08_grading_v2/cond_a_anon \
  --ground-truth 04_ground_truth/ground_truth.json \
  --judges-config 08_grading/judges_config.json \
  --sample-size 100 \
  --sample-seed 20260623 \
  --out 08_grading_v2/cond_a \
  --double-grade-pct 0.10 \
  --max-workers 3
```

Cost: ~$30.

### 4c. Grade Cond-B under v2 rubric

Same as 4b, applied to Cond-B. Cost: ~$30.

### 4d. Re-grade all 6 baselines under v2 rubric

The v1 grading was structurally biased AGAINST MANDATE-primary but FOR baselines whose prompts asked for the array shape. Re-grading baselines under the v2 (shape-neutral) rubric closes that bias loop and produces apples-to-apples comparison across Cond-X, Cond-A, Cond-B, B1-B6.

Take the existing 600 baseline records from the v1 sample (100 × 6 baselines), re-grade under v2:

```zsh
python3 -m apparatus.run grade-v2 \
  --anonymized 08_grading/anonymized_outputs \
  --filter-system-id baseline_1,baseline_2,baseline_3,baseline_4,baseline_5,baseline_6 \
  --ground-truth 04_ground_truth/ground_truth.json \
  --judges-config 08_grading/judges_config.json \
  --out 08_grading_v2/baselines_regraded \
  --double-grade-pct 0.10 \
  --double-grade-seed 20260623 \
  --max-workers 3
```

Cost: 600 records × $0.09 ≈ $54.

### 4e. Total v2 grading cost

| Component | Records | Cost |
|---|---|---|
| Cond-X re-grade | 100 | $27 |
| Cond-A grade | 100 | $30 |
| Cond-B grade | 100 | $30 |
| Baselines re-grade | 600 | $54 |
| Double-grade samples (10% each) | ~90 | ~$25 |
| **Total** | **990** | **~$166** |

Far under the v1 Phase 8 spend (~$715), and produces apples-to-apples across all 9 system conditions.

---

## Stage 5 — Analysis + comparison + writeup

### 5a. Compute the schema-mismatch penalty

For each of the 100 Cond-X records that were graded under BOTH v1 and v2:

```python
for record_id, v1_score, v2_score in joined:
    penalty[dim] = v2_score[dim] - v1_score[dim]   # positive = v2 scores higher
```

Aggregate per outcome:
- `mission_intent_match`: v1 vs v2 mean
- `minimum_coverage`: v1 vs v2 mean
- `target_coverage`: v1 vs v2 mean
- `constraint_coverage`: v1 vs v2 mean
- Etc.

The headline: "Cond-X's minimum_coverage went from 0.18 (v1) to X.YY (v2). The 0.X-point delta is the schema-mismatch penalty: a measure of how much of the v1 score was driven by structural shape rather than substantive coverage."

This is publishable as a methodological finding regardless of whether v2 absolute scores favor MANDATE or not.

### 5b. Cross-condition comparison

Under the corrected v2 rubric, compute per-system means + 95% CIs for:
- Cond-X (MANDATE on raw text, drifted fork, low-temp LLM)
- Cond-A (MANDATE planning on pre-extracted structure)
- Cond-B (MANDATE end-to-end with LLM-augmented Interpreter)
- B1 (Sonnet single-prompt planner)
- B2 (GPT-4o single-prompt planner)
- B3 (Claude ReAct)
- B4 (AutoGen multi-agent)
- B5 (CrewAI multi-agent)
- B6 (LangGraph multi-agent)

For each pre-registered outcome (O1-O4), produce a 9-system bar chart with CIs and the per-pair statistical contrast vs MANDATE (using whichever Cond is the headline — likely Cond-B for the "MANDATE as shipped" claim).

Power analysis (Appendix X) still applies — sample size of 100 per condition gives ≥80% power for d≥0.5 effect sizes.

### 5c. IRR under v2 rubric

Compute Cohen's κ and Krippendorff's α per outcome on the v2 grades, using the same 70-record (10%) double-grade sample. Compare to v1 IRR:
- v1: min κ = 0.296 (mission_intent), halt
- v2 expected: higher because the rubric is more semantically grounded and shape-agnostic

If v2 IRR clears the 0.40 PROTOCOL_LOCK §8 threshold, that's also a methodological finding: "the v1 IRR halt was partially driven by rubric ambiguity, not just judge disagreement."

### 5d. Writeup updates

The supplemental TeX gets a significant rewrite:

1. **Section 4 (Findings Catalog)** — preserve 5 content-tripwire findings. ADD Finding 6: "Schema-mismatch penalty under non-canonical rubric — quantified at X.YY points on minimum_coverage."
2. **Section 5.4 (Phase 8 grading)** — replace placeholder with v2 results. Per-system means + CIs across 9 conditions. v1-vs-v2 delta on Cond-X.
3. **Section 6 (Conditions)** — new section introducing Cond-X/A/B framework.
4. **Section 7 (Methodology)** — explain the v2 rubric design and why.
5. **Section 17 (Deviation Log)** — add D-09: v2 pivot from drifted-fork-on-mismatched-rubric to canonical-MANDATE-on-shape-neutral-rubric.
6. **Appendix Y (new)** — v1 vs v2 rubric side-by-side with worked example on TASK-MAIN-INT-034.

---

## Salvage acknowledgment

Per `handoffs/v2_salvage_audit.md` (Cal asked, audit found):

```
                       KEEP   REFRAME   RE-GRADE   RETIRE   Total
98 material assets:      42         8         10        38      98
```

**Critical KEEPs:**
- The 1,500 v1 MANDATE-primary records ARE Cond-X. No re-run needed; only re-grade.
- The 6 baselines (B1-B6, 7,500 records total) stay. Re-grade under v2.
- All 1,500 corpus tasks, 350 perturbations, and ground-truth content stay.
- All apparatus code except `apparatus/grading/rubric.py` (175 LOC, replace with v2).
- All demo evidence + handoff history.

**Critical RETIREs:**
- `AEGIS-eval/src/mandate/` (drifted experimental MANDATE, 6,793 LOC) — replaced with canonical MLT v1.0.0rc1
- 37 empty placeholder directories that were never populated in v1 (zero data loss)

The v1 deposit-skeleton structure REFRAMEs cleanly: the 17 standalone-data-results subdirectories become Cond-X aggregates that the v2 deposit cites as one of three measured conditions.

---

## What v2 unblocks

After Stage 5 PROCEED:
- Re-deposit under `mandate-eval-primary-2026q2-v2` tag with corrected rubric, three conditions, schema-mismatch finding documented
- Cross-extraction-path demo re-run (HANDOFF_16 lineage) repeatable under canonical MANDATE
- Methodology paper standalone: "Schema-mismatch effects in LLM-as-judge evaluation of structured generation systems"
- Substantive paper: cross-system MANDATE-vs-baselines comparison on shape-neutral rubric

---

## Stage-by-stage HALT decision points

```
Stage 1: HALT if any unit test fails or canonical pipeline smoke fails
Stage 2: HALT if either pilot's success criteria are not met (don't burn $200 on Cond-B full if pilot is broken)
Stage 3: HALT if cost ceiling or throughput escalation triggers
Stage 4: HALT if v2 IRR < 0.40 (PROTOCOL_LOCK §8) — diagnose rubric ambiguity before proceeding to writeup
Stage 5: HALT only if findings unexpectedly invalidate the salvage assumptions
```

Each HALT produces a brief report in `handoffs/HANDOFF_19_stage<N>_report_<YYYY-MM-DD>.md` and pauses for PI decision.

---

## Final report template

`handoffs/HANDOFF_19_final_report_<YYYY-MM-DD>.md`:

- Stage 1 plumbing: tests passing count, MLT smoke test status
- Stage 2 pilot results: 5-record summary per condition with anchor shapes
- Stage 3 run completion: records produced per condition, wall clock, cost
- Stage 4 grading: v1/v2 rubric comparison on Cond-X; v2 results across 9 systems
- Stage 5 analysis: per-system mean ±CI tables, statistical contrasts, IRR
- v2 vs v1 deltas: schema-mismatch penalty quantified
- Writeup status: which supplemental sections updated
- Total cost: actual vs budgeted
- Anomalies and deviations

Commit message:
```
HANDOFF_19 v2 pivot complete: three-condition canonical MANDATE evaluation. Cond-X reframed from v1 baseline. Cond-A (pre-extracted structure, deterministic MANDATE) and Cond-B (LLM-augmented Interpreter end-to-end) executed on 120-task main + 30-task holdout corpus. v2 rubric replaces v1 (shape-neutral semantic coverage instead of structural array-match). Re-graded Cond-X + 6 baselines under v2; schema-mismatch penalty quantified. IRR under v2: X.YY (vs v1 0.296 halt). New Section 6 + Appendix Y added to supplemental. Salvage: 42 KEEP, 8 REFRAME, 10 RE-GRADE, 38 RETIRE per v2_salvage_audit.md.
```
