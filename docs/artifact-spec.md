# Artifact Specification

The authoritative structure is captured in the JSON Schemas under `schemas/`.

## Input Documents

MANDATE synthesizes requirements from operational documents and organizational context sources. In complex operational environments (defense, intelligence, critical infrastructure), inputs may include:

**Operational Documents:**
- **FRAGOs** (Fragmentary Orders) — mission changes and updates
- **ROE** (Rules of Engagement) — authorization boundaries
- **CONOPS / SECONOPS** — operational and security concepts of operations
- **Technical Manuals** — system employment guidelines
- **Mission Orders** — specific task directives

**Organizational Context Sources:**
- **SOPs** (Standard Operating Procedures)
- **TTPs** (Tactics, Techniques, Procedures)
- **Capability Inventories** — available tools and resources
- **Organizational Policies** — risk tolerances, approval workflows
- **Success Registry** — precedent mandates for similar tasks

This multi-source synthesis is why explicit tolerance specification matters: implicit thresholds buried across dozens of source documents must be surfaced and reconciled into a coherent anchor.

---

## mandate-as-code (top level)

Key fields:
- `mandate_id` (string)
- `version` (string)
- `generated` (ISO-8601 datetime)
- `anchor` (object)
- `courses_of_action` (array)
- `recommendation` (object)
- `trace` (object)
- `registry_reference` (object; optional)
- `metadata` (object; optional)

## anchor

- `mission_intent`: string — natural language statement of purpose
- `minimum`: map of dimension→value — **required** thresholds for acceptable completion
- `target`: map of dimension→value — **aspirational** thresholds (optional)
- `constraints`: list of constraint strings following the constraint grammar
- `risk_tolerance`: autonomous operation limits (optional)
- `anchor_hash`: SHA-256 of canonicalized anchor object (excluding `anchor_hash`)

### Constraint Grammar

Constraints follow a formal grammar for verifiability:

```ebnf
constraint      ::= predicate | constraint AND constraint | constraint OR constraint | NOT constraint
predicate       ::= field comparator value | field IN set | REQUIRES capability | FORBIDS action
field           ::= identifier ('.' identifier)*
comparator      ::= '==' | '!=' | '<' | '<=' | '>' | '>=' | 'CONTAINS' | 'MATCHES'
value           ::= string | number | boolean | timestamp | duration
set             ::= '[' value (',' value)* ']'
capability      ::= identifier
action          ::= identifier
```

**Examples:**
- `execution.duration <= PT4H` (ISO 8601 duration: max 4 hours)
- `data.classification IN ['UNCLASSIFIED', 'CUI']`
- `REQUIRES network_access AND NOT FORBIDS external_api`
- `outcome.confidence >= 0.8 AND risk.score != 'HIGH'`

**Satisfaction:** A constraint C is satisfied by state S iff `eval(C, S) = true`.

See `src/mandate/constraints.py` for the parser implementation.

## courses_of_action

Each COA contains:
- `coa_id`: unique identifier
- `approach`: description of the strategy
- `task_dag`: nodes and edges representing the task graph
- `procedures`: referenced SOPs
- `capabilities`: required tools/resources
- `risk_assessment`: score, confidence levels, primary factor
- `off_nominal_triggers`: conditions that indicate deviation from expected execution

## trace-entry

Each recorded decision is a trace entry with:
- `hash`: SHA-256 of canonicalized entry (excluding `hash`)
- `role`: one of Intake, Interpreter, Decomposition, Procedure, Binding, Validation
- `decision_type`: free string (e.g., `anchor_extraction`, `procedure_assignment`)
- `timestamp`: ISO-8601 datetime
- `parent_hashes`: list of predecessor hashes

Optional fields include:
- `search`: query, source, k, total_results, ranker_version
- `results`: candidate items with scores
- `selected`: chosen item (or null)
- `confidence`: LOW | MEDIUM | HIGH
- `rationale`: explanation of decision
- `risk`: assessment at this step

## gap-report

Produced when the system cannot complete the specification. Gap reports are diagnostic artifacts, not failures—they tell the organization what information is missing.

Gap types:
- `UNDEFINED_MINIMUM` — cannot determine required threshold
- `UNDEFINED_TARGET` — cannot determine aspirational threshold
- `UNKNOWN_PATTERN` — no matching task pattern found
- `MISSING_TTP` — required procedure not available
- `MISSING_CAPABILITY` — required tool/resource not available
- `UNASSESSABLE_RISK` — cannot determine risk score

Each gap includes:
- Location in input documents
- Remediation action required
- Responsible party
- Complexity estimate
- Readiness score (percentage complete)
