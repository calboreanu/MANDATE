# MANDATE v2.0 Redesign — Role Schema Audit

Source files audited (under `AEGIS-eval/src/mandate/`):

- `roles/intake.py`
- `roles/interpreter.py`
- `roles/decomposition.py`
- `roles/procedure.py`
- `roles/binding.py`
- `roles/validation.py`
- `models.py`

All schemas are JSON Schema dicts attached as class constants on each `Role` subclass. They govern what the LLM hybrid path may emit on the `execute_with_llm` branch. Deterministic `execute()` paths read/write the dataclass models in `models.py` directly and do not consult these schemas.

---

## Role 0 — Intake (`roles/intake.py`)

**Input schema.** `state.mission_input: MissionInput | None` on `PipelineState`. Hybrid `execute_with_llm` re-serializes via `mission_input_prompt_payload(...)` and feeds that JSON as `source_text` to the LLM.

**Output schema.** A `MissionInput` instance (rebuilt with `MissionInput.from_dict(merged_payload)`) plus mutation of `state.mission_id` and `state.timestamp`. The LLM-emitted shape it validates against is `_MISSION_INPUT_SCHEMA` (see direct quote below).

**LLM mutation boundary.**

```python
_LLM_MUTATION_BOUNDARY = (
    "mission_input",
)
```

The LLM may rewrite the entire `mission_input` payload (whole-record replacement) but every field is merged conservatively via `_merge_llm_payload` (existing values stay unless the LLM returns a non-empty replacement).

**Validation logic.**

- `mi.mission_id` auto-filled with `f"MANDATE-{uuid4().hex[:8].upper()}"` if missing.
- `mi.intent` required, else `_fail("MissionInput.intent is required")`.
- Each entry in `mi.constraints` run through `validate_constraint(c)`; any failure aborts with a concatenated error list.
- On success: `state.mission_id`, `state.timestamp` populated; `RoleResult` reports `mission_id`, `constraint_count`, `scope_count`.

**Direct schema quote.**

```python
_MISSION_INPUT_SCHEMA = {
    "type": "object",
    "required": ["mission_id", "intent"],
    "properties": {
        "mission_id": {"type": "string"},
        "intent": {"type": "string"},
        "time_limit": {"type": "string"},
        "minimum_outcome": {"type": "string"},
        "target_outcome": {"type": "string"},
        "constraints": {"type": "array", "items": {"type": "string"}},
        "scope": {"type": "array", "items": {"type": "string"}},
        "available_tools": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["tool_id"],
                "properties": {
                    "tool_id": {"type": "string"},
                    "tool_class": {"type": "string"},
                    "description": {"type": "string"},
                    "parameters": {"type": "object"},
                },
                "additionalProperties": True,
            },
        },
        "risk_tolerance": {
            "anyOf": [
                {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
                {"type": "string", "enum": [""]},
            ]
        },
        "metadata": {"type": "object"},
        "assumptions": {"type": "array", "items": {"type": "string"}},
    },
}
```

`minimum_outcome` and `target_outcome` are plain `string` types — no per-dimension structure.

---

## Role 1 — Interpreter (`roles/interpreter.py`)

**Input schema.** Reads `state.mission_input: MissionInput`. Hybrid path packs the same `mission_input_prompt_payload` as Intake into the prompt.

**Output schema.** Writes onto `PipelineState`:

- `state.anchor_intent: str` (= `mi.intent`)
- `state.anchor_minimum: Dict[str, Any]` — always set to `{"description": <string>}` (one key)
- `state.anchor_target: Dict[str, Any]` — same shape `{"description": <string>}`
- `state.constraints: List[str]`
- `state.risk_tolerance: Dict[str, Any] | None` of shape `{"max_autonomous_score": <LOW|MEDIUM|HIGH>, "escalate_above": <MEDIUM|HIGH>}`
- `state.anchor_hash: str` (via `compute_anchor_hash`)
- Appends to `state.gaps` (`UNDEFINED_MINIMUM`, `UNDEFINED_TARGET`, `UNASSESSABLE_RISK` as applicable).

**LLM mutation boundary.**

```python
_LLM_MUTATION_BOUNDARY = (
    "mission_input.minimum_outcome",
    "mission_input.target_outcome",
    "mission_input.risk_tolerance",
)
```

LLM may override the three plain-string fields on `mission_input` before deterministic execution runs.

**Validation logic.**

- `state.mission_input` required, else `_fail("No MissionInput in state")`.
- Missing `mi.minimum_outcome` → derive default + append `UNDEFINED_MINIMUM` gap.
- Missing `mi.target_outcome` → derive default + append `UNDEFINED_TARGET` gap.
- `_derive_risk_tolerance` returns `None` → append `UNASSESSABLE_RISK` gap.
- No hard fail beyond missing mission_input; gaps are informational unless escalated downstream.
- `RoleResult` artifacts: `anchor_hash`, `constraint_count`, `gaps_detected`.

**Direct schema quote (LLM stage advisory schema).**

```python
_LLM_STAGE_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["decision_summary"],
    "properties": {
        "decision_summary": {"type": "string"},
        "uncertainties": {"type": "array", "items": {"type": "string"}},
        "minimum_outcome": {
            "anyOf": [
                {"type": "string"},
                {"type": "null"},
            ]
        },
        "target_outcome": {
            "anyOf": [
                {"type": "string"},
                {"type": "null"},
            ]
        },
        "risk_tolerance": {
            "anyOf": [
                {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
                {"type": "string", "enum": [""]},
                {"type": "null"},
            ]
        },
    },
    "additionalProperties": False,
}
```

`minimum_outcome` and `target_outcome` are plain `string | null`. `anchor_minimum` / `anchor_target` are serialized only as `{"description": str}` dicts — there is no `dimension` / `threshold` / `rationale` structure.

---

## Role 2 — Decomposition (`roles/decomposition.py`)

**Input schema.** Reads `state.mission_input`, `state.anchor_intent`, `state.anchor_minimum`, `state.anchor_target`, `state.constraints`, `state.risk_tolerance`. Hybrid path builds an `anchor` dict and passes it to the LLM.

**Output schema.** Writes `state.coas: List[COASpec]`. May also rewrite `state.mission_input.scope` if the LLM emits `scope_override`. Appends `MISSING_CAPABILITY` and `UNKNOWN_PATTERN` gaps.

**LLM mutation boundary.**

```python
_LLM_MUTATION_BOUNDARY = (
    "mission_input.scope",
    "coas[:candidate_coa_count]",
)
```

LLM may rewrite `mission_input.scope` (advisory) and truncate the deterministic COA list to a candidate count.

**Validation logic.**

- `state.mission_input` required.
- `_generate_coas` must return at least one COA, else `_fail("Could not generate any courses of action")`.
- DAG validation helper `_validate_dag` exists (cycle + dangling-edge check) but is not invoked in `execute` itself; only built-by-construction edges are accepted.
- `RoleResult` artifacts: `coa_count`, `coa_ids`, `gaps_detected`, `nist_map`.

**Direct schema quote.**

```python
_LLM_STAGE_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["decision_summary"],
    "properties": {
        "decision_summary": {"type": "string"},
        "candidate_coa_count": {"type": "integer", "minimum": 0},
        "scope_override": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}
```

This is an advisory schema only — the deterministic generator produces COAs, the LLM cannot directly emit COA structures here. No `minimum` / `target` dimensions appear.

---

## Role 3 — Procedure (`roles/procedure.py`)

**Input schema.** Reads `state.coas`, `state.constraints`, `state.mission_input.metadata` (for `rag_context`, `rag_results`, `registry_entries`). Hybrid path also resolves `rag_context` via `self.config.llm_procedure_retriever` and registry entries via `self.config.success_registry`.

**Output schema.** Mutates each `COASpec` in place:

- `coa.procedures: List[str]` (step-N strings)
- `coa.capabilities: List[str]`
- `coa.off_nominal_triggers: List[str]` (validated EBNF constraints)

Appends `MISSING_TTP` / `MISSING_PROCEDURE` gaps with `evidence_trace_hashes` and `evidence_sources`.

**LLM mutation boundary.**

```python
_LLM_MUTATION_BOUNDARY = (
    "coas[*].off_nominal_triggers",
)
```

Only `off_nominal_triggers` may be replaced (when `trigger_strategy ∈ {LOW, MEDIUM, HIGH}`).

**Validation logic.**

- `state.coas` non-empty, else `_fail("No COAs in state — Decomposition must run first")`.
- Hybrid path: `selected_reference_ids` from the LLM must be a subset of `allowed_reference_ids` (the retrieved RAG/registry IDs). Otherwise `ValueError`.
- `_generate_triggers` only keeps triggers that pass `validate_constraint(trigger)`.
- `RoleResult` artifacts: `procedure_count`, `trigger_count`, `missing_ttp_gaps`, `missing_procedure_gaps`, `gaps_detected`.

**Direct schema quote.**

```python
_LLM_STAGE_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["decision_summary"],
    "properties": {
        "decision_summary": {"type": "string"},
        "trigger_strategy": {"type": "string"},
        "selected_reference_ids": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "additionalProperties": False,
}
```

No anchor / minimum / target dimensions appear.

---

## Role 4 — Binding (`roles/binding.py`)

**Input schema.** Reads `state.coas`, `state.constraints`, anchor fields, `state.risk_tolerance`. Hybrid path builds an `assessed_payload` containing per-COA assessments plus the deterministic recommendation as a `deterministic_recommendation` payload.

**Output schema.**

- Sets `coa.risk_assessment: RiskAssessment` on every COA.
- Sets `state.recommendation: Recommendation` (primary_coa, fallback_sequence, rationale).

**LLM mutation boundary.**

```python
_LLM_MUTATION_BOUNDARY = (
    "recommendation.primary_coa",
    "recommendation.fallback_sequence",
    "recommendation.rationale",
)
```

LLM may override the recommendation triad. `primary_override` must exist in the COA set; each `fallback_override` must be a valid COA id and not equal to primary.

**Validation logic.**

- `state.coas` non-empty, else `_fail("No COAs in state — Decomposition must run first")`.
- `_assess_risk` computes a score from tool invasiveness, DAG complexity, declared `risk_factors` (configurable via `RiskModelConfig`/`ToolRegistry`).
- Confidence levels assigned heuristically: `MEDIUM/HIGH` if all non-analysis nodes have tools, else `LOW/MEDIUM`.
- Primary factor selected from `{exploitation_risk, complexity_risk, execution_uncertainty}`.
- `RoleResult` artifacts: `primary_coa`, `risk_scores`.

**Direct schema quote.**

```python
_LLM_STAGE_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["decision_summary"],
    "properties": {
        "decision_summary": {"type": "string"},
        "risk_notes": {"type": "array", "items": {"type": "string"}},
        "primary_coa": {"type": "string"},
        "fallback_sequence": {"type": "array", "items": {"type": "string"}},
        "rationale_override": {"type": "string"},
    },
    "additionalProperties": False,
}
```

No anchor / minimum / target dimensions.

---

## Role 5 — Validation (`roles/validation.py`)

**Input schema.** Reads the full `PipelineState`: anchor fields, COAs (with `risk_assessment`, `procedures`, `capabilities`, `off_nominal_triggers`), constraints, `state.recommendation`, trace inputs.

**Output schema.**

- Runs the paper-aligned 4-step algorithm → `ValidationResult` with four `ValidationStepResult`s (`minimum_satisfaction`, `target_feasibility`, `constraint_compliance`, `risk_aggregation`).
- Builds `state.trace_entries`, `state.trace_entry_hashes`, `state.chain_hash`.
- Assembles the full mandate-as-code artifact dict (`mandate_id`, `version`, `generated`, `anchor`, `courses_of_action`, `recommendation`, `trace`, `registry_reference`, `metadata`).
- Runs `validator.validate_artifact(...)` (writes artifact to temp file, calls schema validator) as final gate.
- Appends additional gaps (`UNDEFINED_MINIMUM`, `UNDEFINED_TARGET`, `UNKNOWN_PATTERN`, `UNASSESSABLE_RISK`) for failing COAs.

**LLM mutation boundary.**

```python
_LLM_MUTATION_BOUNDARY = (
    "artifact.metadata.validation_focus",
)
```

LLM may add a `validation_focus: List[str]` into `artifact.metadata` — purely advisory; does not affect pass/fail.

**Validation logic (the 4-step algorithm).**

1. **`_check_minimum_satisfaction`** — iterates `for dimension, expected_value in minimum.items()`. Because `state.anchor_minimum` always has shape `{"description": <string>}` (see Interpreter), this is effectively a single-dimension lexical check via `_dimension_supported`. Coverage ratio = covered/total dims. `passed` iff ratio == 1.0 for every COA.
2. **`_check_target_feasibility`** — extracts tokens from `json.dumps(target)`, computes per-COA `feasibility_score` from `node_factor + procedure_factor + capability_factor + risk_factor + lexical_factor`. Threshold `>= 0.6`.
3. **`_check_constraint_compliance`** — parses each constraint, runs `check_constraint_compliance(ast, task_state, task_text)` against every task node; counts violations.
4. **`_check_risk_aggregation`** — aggregates per-task scores (`max` or `weighted_average`), compares classified level to `coa.risk_assessment.score`. Passes only if assessment exists.

A failed schema validation aborts with `_fail("Validation failed ...")`. Algorithm-step failures emit gaps but do not abort (warning surfaced in success message).

**Direct schema quote.**

```python
_LLM_STAGE_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["decision_summary"],
    "properties": {
        "decision_summary": {"type": "string"},
        "validation_focus": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}
```

The `minimum` / `target` dict structure is consumed (via `.items()`) — implying a multi-dimension schema is theoretically supported by the algorithm — but the upstream Interpreter only ever emits `{"description": str}`. So the multi-dimension path is dead code in current flow.

---

## Shared Models (`mandate/models.py`)

### `PipelineState` (the accumulator)

```python
@dataclass
class PipelineState:
    # From input
    mission_input: Optional[MissionInput] = None

    # Built by Intake
    mission_id: str = ""
    timestamp: str = ""

    # Built by Interpreter
    anchor_intent: str = ""
    anchor_minimum: Dict[str, Any] = field(default_factory=dict)
    anchor_target: Dict[str, Any] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    risk_tolerance: Optional[Dict[str, Any]] = None
    anchor_hash: str = ""

    # Built by Decomposition
    coas: List[COASpec] = field(default_factory=list)

    # Built by Procedure (mutates COASpec in place)

    # Built by Binding
    recommendation: Optional[Recommendation] = None

    # Built by Validation
    trace_entries: List[Dict[str, Any]] = field(default_factory=list)
    trace_entry_hashes: List[str] = field(default_factory=list)
    chain_hash: str = ""

    # Cross-role accumulators
    gaps: List[GapSpec] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
```

Critical: `anchor_minimum` and `anchor_target` are `Dict[str, Any]`. In current code, Interpreter populates them with shape `{"description": str}`. There is no `dimension` / `threshold` / `rationale` keying anywhere in the pipeline.

### Input dataclasses

```python
@dataclass
class ToolSpec:
    tool_id: str
    tool_class: str           # RECON, SCAN, EXPLOIT, ANALYSIS
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MissionInput:
    mission_id: str
    intent: str                          # Free-text mission intent
    scope: List[str] = field(default_factory=list)
    time_limit: str = ""                 # e.g. "PT4H"
    constraints: List[str] = field(default_factory=list)  # EBNF constraint strings
    minimum_outcome: str = ""            # plain string
    target_outcome: str = ""             # plain string
    available_tools: List[ToolSpec] = field(default_factory=list)
    risk_tolerance: Optional[str] = None  # "LOW", "MEDIUM", "HIGH"
    metadata: Dict[str, Any] = field(default_factory=dict)
```

`minimum_outcome` and `target_outcome` are plain strings — confirmed at the dataclass level, not just the JSON schema.

### Per-role output / intermediate dataclasses

```python
@dataclass
class TaskNodeSpec:
    node_id: str
    name: str
    description: str = ""
    depends_on: List[str] = field(default_factory=list)
    tool_ids: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)


@dataclass
class RiskAssessment:
    score: RiskLevel                     # LOW | MEDIUM | HIGH | UNASSESSABLE
    confidence_min: ConfidenceLevel      # LOW | MEDIUM | HIGH
    confidence_target: ConfidenceLevel
    primary_factor: str


@dataclass
class COASpec:
    coa_id: str
    approach: str
    task_nodes: List[TaskNodeSpec] = field(default_factory=list)
    edges: List[Dict[str, str]] = field(default_factory=list)
    risk_assessment: Optional[RiskAssessment] = None
    off_nominal_triggers: List[str] = field(default_factory=list)
    procedures: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)


@dataclass
class GapSpec:
    gap_type: GapType
    detected_by: str
    pipeline_stage: int
    field_or_task: str
    reason: str
    action_required: str
    severity: GapSeverity = GapSeverity.DEGRADING
    location: GapLocation = GapLocation.ANCHOR
    gap_source: GapSource = GapSource.SPECIFICATION_GAP
    responsible_party: str = "Mission Author"
    complexity: str = "LOW"
    completion_percentage: int = 0
    blocking: bool = False
    partial_spec_available: bool = False
    input_reference: str = "mission_input"
    evidence_trace_hashes: List[str] = field(default_factory=list)
    evidence_sources: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Recommendation:
    primary_coa: str
    fallback_sequence: List[str]
    rationale: str


@dataclass
class ValidationStepResult:
    passed: bool
    score: float = 1.0
    details: List[str] = field(default_factory=list)
    per_coa: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    minimum_satisfaction: ValidationStepResult
    target_feasibility: ValidationStepResult
    constraint_compliance: ValidationStepResult
    risk_aggregation: ValidationStepResult
```

### Role-result wrapper

```python
@dataclass
class RoleResult:
    role_name: str
    status: RoleStatus           # SUCCESS | FAILED | SKIPPED
    message: str = ""
    artifacts: Dict[str, Any] = field(default_factory=dict)
    trace_entry_hash: str = ""
```

### Trace dataclasses

`SearchDetail`, `SearchResultItem`, `SelectionDetail`, `SearchTraceEntry` (full S-S-T trace structure). Not directly schema-relevant to the Phase 8 minimum/target rubric.

---

## Cross-cutting findings vs. Phase 8 rubric

- **`minimum_outcome` / `target_outcome` are plain `str` everywhere** — in the `MissionInput` dataclass, in `_MISSION_INPUT_SCHEMA` (Intake), in `_LLM_STAGE_OUTPUT_SCHEMA` (Interpreter). No role declares them as arrays of `{dimension, threshold, rationale}` dicts.
- **`anchor_minimum` / `anchor_target` are `Dict[str, Any]`** but currently constructed solely as `{"description": <string>}` in `InterpreterRole.execute`. The Validation step iterates `for dimension, expected_value in minimum.items()`, which means it would tolerate a multi-key dict, but no upstream code emits one and no schema models per-dimension `threshold`/`rationale` structure.
- **No role schema (Intake, Interpreter, Decomposition, Procedure, Binding, Validation) references `dimension`, `threshold`, or `rationale` as keys.** The gap is uniform across the 1+6 pipeline, not isolated to Intake — it propagates through Interpreter's emission shape, through PipelineState dataclass typing, into Validation's per-dimension coverage loop.
- **Per-dimension grading (per Phase 8 rubric) has no representation** in the current schemas. A v2 redesign that wants `minimum: List[{dimension, threshold, rationale}]` and `target: List[{dimension, threshold, rationale}]` must touch (at minimum):
  - `MissionInput.minimum_outcome` / `target_outcome` types (`models.py`).
  - `IntakeRole._MISSION_INPUT_SCHEMA` properties block.
  - `InterpreterRole._LLM_STAGE_OUTPUT_SCHEMA` plus the `state.anchor_minimum` / `state.anchor_target` construction.
  - `PipelineState.anchor_minimum` / `anchor_target` types.
  - `ValidationRole._check_minimum_satisfaction` and `_check_target_feasibility` iteration shape and `_dimension_supported` semantics.
  - The artifact assembler `_assemble_artifact` `anchor` dict shape (currently passes the dict through as-is, so this may flow through if upstream changes).
