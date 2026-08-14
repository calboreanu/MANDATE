# Changelog

## 2.0.1 (2026-08-13)

### Publication release
- Published one canonical v2 release surface for the framework and its 2026Q2
  evidence package.
- Replaced internal planning language with publication-facing documentation.
- Clarified the two-axis result ontology, the verification boundary, and the
  relationship between the public reference implementation and proprietary
  campaign engines.

### Correctness and reproducibility
- Added an explicit fail-closed `execution_state` and result-envelope contract.
- Blocking or insufficient-for-automation signals now force `ok=false` and
  `NON_EXECUTABLE_GAPS`, even when the partial mandate representation is schema-valid.
- Added a Draft 2020-12 envelope schema plus semantic reconciliation against raw gaps.
- Added regression coverage for the state-routing defect reported by the MANDATE audit.
- Published RFC 8785 canonicalization through the `rfc8785` dependency and test suite.

## 2.0.0 (2026-02-11)

### New Features
- **Pipeline Metrics Collection** (`src/mandate/metrics.py`)
  - `RoleMetric` dataclass with nanosecond timing, success status, error capture
  - `PipelineMetrics` aggregation with total duration, slowest/fastest role,
    per-role percentage breakdown, and serializable summary
  - `MetricsCollector` class for accumulating metrics during pipeline execution
  - `BenchmarkStats` for aggregate statistics across multiple pipeline runs
    (min/max/avg duration, pass rate, per-role averages)
  - Pipeline.run() now returns `PipelineMetrics` on every invocation by default
    (opt-out via `collect_metrics=False`)
- **Evaluation Harness** (`src/mandate/evaluation.py`)
  - `EvaluationHarness` class that runs a corpus of mission inputs against the
    pipeline and evaluates results against expected outcomes
  - `ExpectedOutcome` dataclass for declaring expected pipeline behavior:
    pipeline_ok, COA count ranges, tool class presence, recommendation structure,
    anchor hash, trace integrity, constraint count, gap detection
  - `EvaluationCase` and `EvaluationReport` with per-check pass/fail detail
  - `EvaluationHarness.from_manifest()` factory for loading corpus from JSON manifest
  - Tag-based filtering and configurable repetitions for benchmark stability
  - Automatic domain profile / tool registry configuration for domain-specific cases
- **Success Registry** (`src/mandate/success_registry.py`)
  - `SuccessRegistry` class for precedent storage of successful mandate executions
  - `SuccessRecord` dataclass with intent, scope, constraints, tool classes,
    domain, risk level, metrics, and pre-computed token sets
  - `SuccessRecord.from_artifact()` factory for creating records from pipeline output
  - **Similarity matching** via weighted Jaccard similarity across 3 dimensions:
    intent tokens (default 0.5), constraint tokens (0.3), tool class overlap (0.2)
  - `find_similar()` query with domain filtering, top-k, min-score threshold,
    and custom weight overrides
  - `find_by_domain()` and `find_by_tool_class()` convenience queries
  - JSON file persistence (`save()`/`load()`), registry merge, and statistics
- **`mandate benchmark` CLI command**
  - Run evaluation corpus against the pipeline: `mandate benchmark <manifest>`
  - `-o <path>`: Save full evaluation report as JSON
  - `--tags`: Comma-separated tag filter (e.g., `--tags pentest,standard`)
  - `--repetitions N`: Run each case N times for benchmark stability
  - Prints per-case PASS/FAIL with timing, aggregate stats, per-role averages
- **`mandate registry` CLI command**
  - `mandate registry stats`: Show record count, domain distribution, tool class usage
  - `mandate registry query --intent "..." --domain "..." --top-k N`: Find similar
    past mandates by intent/constraint/tool class similarity
  - `mandate registry ingest <artifact> --domain "..."`: Ingest a mandate artifact
    into the registry

### Benchmark Corpus
- `benchmarks/corpus/manifest.json` — 8 evaluation cases with expected outcomes
- `benchmarks/corpus/minimal_valid.json` — Bare minimum input (1 tool, 1 scope)
- `benchmarks/corpus/max_complexity.json` — 5 tools, 8 constraints, 6 scope items
- `benchmarks/corpus/invalid_missing_fields.json` — Missing required fields (negative test)
- Existing examples reused: normal, IR, defense intel, multi-COA, underspecified missions

### Tests
- 77 new tests across 3 test files:
  - `tests/test_metrics.py` (22 tests): RoleMetric, PipelineMetrics, MetricsCollector,
    BenchmarkStats, real timing verification
  - `tests/test_evaluation.py` (23 tests): ExpectedOutcome, CheckResult, CaseResult,
    EvaluationReport, EvaluationHarness corpus runs, tag filtering, repetitions,
    metrics collection, invalid input, gap detection, pipeline metrics integration
  - `tests/test_success_registry.py` (32 tests): tokenization, Jaccard similarity,
    SuccessRecord creation/serialization, SuccessRegistry CRUD, similarity queries
    (intent, domain, tool class, constraints, custom weights), persistence
    (save/load/merge), statistics, SimilarityMatch

### Infrastructure
- New modules: `src/mandate/metrics.py`, `src/mandate/evaluation.py`,
  `src/mandate/success_registry.py`
- New directory: `benchmarks/corpus/` with manifest and test mission files
- Updated `__all__` exports to include `metrics`, `evaluation`, `success_registry`
- `PipelineResult` now includes optional `PipelineMetrics` field
- `PipelineResult.summary()` includes `total_duration_ms` when metrics available
- Version bumped to 2.0.0

## 1.4.0 (2026-02-11)

### New Features
- **Domain Profiles** (`src/mandate/domain.py`)
  - `DomainProfile` dataclass with phase templates for conservative, moderate, and
    aggressive COA generation — enables domain-specific pipeline behavior
  - `PhaseTemplate` dataclass for describing individual COA phases with tool class
    bindings, risk factors, and dependency configuration
  - Built-in profiles: `PENTEST_PROFILE`, `INCIDENT_RESPONSE_PROFILE`, `DEFENSE_INTEL_PROFILE`
  - Profile registry with `get_domain_profile()` and `list_domain_profiles()` lookup functions
- **Tool Capability Registry** (`src/mandate/registry.py`)
  - `ToolRegistry` class with 3-tier resolution: explicit entry → class defaults → fallback
  - `ToolRegistryEntry` dataclass with tool_id, tool_class, capabilities, and risk_weight
  - `ToolRegistry.from_tools()` factory for building registries from `ToolSpec` lists
  - Default capability and risk weight mappings for 12 tool classes across 3 domains
    (pentest, incident response, defense/intelligence)
  - ProcedureRole now uses registry for capability determination when available
  - BindingRole now uses registry risk weights for scoring when available
- **Configurable Risk Model** (`mandate.domain.RiskModelConfig`)
  - `RiskModelConfig` dataclass replacing hardcoded thresholds in BindingRole
  - Configurable `low_ceiling`, `medium_ceiling`, DAG complexity thresholds,
    and risk factor weights
  - Domain profiles carry their own risk model (e.g., IR has tighter thresholds,
    defense/intel weights risk factors more heavily)
  - Resolution priority: domain_profile.risk_model > config.risk_model > defaults
- **Domain-Pluggable DecompositionRole**
  - When `PipelineConfig.domain_profile` is set, DecompositionRole generates COAs
    from phase templates instead of hardcoded pentest heuristics
  - Template-driven tool binding matches available_tools to phase required_tool_classes
  - Scope and tool lists are interpolated into description templates
  - Domain-aware gap detection (checks for domain's primary tool class, not just RECON)
  - Full backward compatibility when no domain_profile is configured
- **PipelineConfig extensions**
  - New optional fields: `domain_profile`, `risk_model`, `tool_registry`
  - All existing code continues to work unchanged (None defaults)

### Examples
- `examples/incident_response_mission.json` — Ransomware IR scenario (DETECT/CONTAIN/ERADICATE/RECOVER tools, NIST SP 800-61)
- `examples/defense_intel_mission.json` — SIGINT collection scenario (COLLECT/PROCESS/ANALYZE/DISSEMINATE tools, redacted fields)
- `examples/multi_coa_mission.json` — Multi-cloud security assessment with 6 tools across 4 providers

### Tests
- 85 new tests across 3 test files:
  - `tests/test_registry.py` (28 tests): entry creation, registration, resolution tiers,
    from_tools factory, serialization, default mappings
  - `tests/test_domain.py` (30 tests): RiskModelConfig classification, PhaseTemplate,
    DomainProfile, all 3 built-in profiles, profile registry
  - `tests/test_domain_pipeline.py` (27 tests): decomposition with profiles, procedure
    with registry, binding with risk model, full E2E for IR/intel/multi-COA missions,
    example file loading, edge cases (empty profile, partial tools, custom profiles)

### Infrastructure
- New modules: `src/mandate/registry.py`, `src/mandate/domain.py`
- Updated `__all__` exports to include `registry` and `domain` modules
- Version bumped to 1.4.0

## 1.3.0 (2026-02-11)

### Breaking Changes (nominal)
- **`canonical_json()` now uses RFC 8785 (JCS)** via the `rfc8785` library.
  For MANDATE's typical string/integer data, output is byte-identical to
  the v1.0–v1.2 pragmatic encoding — existing artifact hashes remain valid.
  The only behavioural difference is `-0.0` → `0` (per ECMA-262).

### New Features
- **Strict RFC 8785 (JCS) canonicalization** (`src/mandate/hashing.py`)
  - `canonical_json()` delegates to `rfc8785.dumps()` for IEEE 754 number
    serialization, UTF-16 lexicographic key sorting, and spec-compliant
    string escaping
  - `legacy_canonical_json()` preserves the v1.0–v1.2 `json.dumps(sort_keys=True)`
    behaviour for offline verification of pre-v1.3.0 artifacts
  - `sha256_bytes_hex()` accepts raw bytes to avoid redundant encode/decode
    round-trips when hashing JCS output
- **Migration documentation** (`docs/hashing.md`)
  - Full migration guide (v1.2 → v1.3) with edge-case notes
  - Updated all formulas to reference `jcs()` instead of `canonical_json()`

### Tests
- 63 JCS/hashing tests (`tests/test_jcs_hashing.py`) covering:
  - RFC 8785 number serialization (negative zero, exponents, precision, MAX_SAFE_INTEGER)
  - UTF-16 key sorting (numeric strings, mixed case, empty keys, recursion)
  - String escaping (control chars, unicode preservation)
  - Legacy compatibility (parametrized parity check for MANDATE-typical data)
  - Hash computation (anchor, trace entry, chain, determinism, immutability)
  - RFC 8785 test vectors from the specification
  - MANDATE artifact hash integration (full anchor cycle, trace chain integrity)

### Infrastructure
- New dependency: `rfc8785>=0.1.4` (pure Python, zero transitive deps)
- Version bumped to 1.3.0

## 1.2.0 (2026-02-11)

### New Features
- **OPA/Rego Policy Translator** (`src/mandate/translators/rego.py`)
  - Translates MANDATE constraint AST → idiomatic Rego v1 policy rules
  - Handles OR via helper rule pairs, NOT via `not <rule_ref>`
  - Generates complete policies with `package`, `import rego.v1`, `default allow := false`
  - Preserves original constraint strings as inline comments
- **Cedar Policy Translator** (`src/mandate/translators/cedar.py`)
  - Translates MANDATE constraint AST → Cedar `permit`/`forbid` policies
  - Inline `&&`, `||`, `!` operators (no helper rules needed)
  - Cedar `decimal()` for floating-point values, `like` for MATCHES
  - Configurable namespace, action type, and policy effect
- **`mandate translate` CLI command**
  - `-f rego|cedar`: Choose target policy language
  - `-o <path>`: Write policy to file
  - `--package`: Custom Rego package name
  - `--rule`: Custom Rego rule name
  - `--namespace`: Custom Cedar namespace
  - Accepts both mission inputs and mandate-as-code artifacts as source

### Examples
- `examples/policies/normal_mission.rego` — Rego policy for pentest scenario (FORBIDS, scope IN, duration ≤)
- `examples/policies/normal_mission.cedar` — Cedar equivalent
- `examples/policies/complex_mission.rego` — REQUIRES + NOT FORBIDS patterns
- `examples/policies/complex_mission.cedar` — Cedar equivalent

### Tests
- 78 translator tests covering:
  - Individual predicate translation (comparison, IN, REQUIRES, FORBIDS) for both Rego and Cedar
  - Logical operators (AND, OR, NOT) with helper rule generation
  - Full policy generation with headers, helpers, and structural validation
  - CLI translate subcommand integration (file I/O, error handling, custom options)
  - Round-trip verification of all paper examples
  - Edge cases (deep nesting, negative numbers, precedence, unique helper names)

### Infrastructure
- New `src/mandate/translators/` package with `__init__.py`, `rego.py`, `cedar.py`
- `TranslationError` exception for unsupported node types
- Version bumped to 1.2.0
- Updated `__all__` exports to include translators module

## 1.1.0 (2026-02-11)

### New Features
- **1+6 Pipeline Reference Implementation**: Full pipeline from mission input to validated mandate-as-code artifact
  - 6 roles: Intake, Interpreter, Decomposition, Procedure, Binding, Validation
  - Pipeline orchestrator with strict/lenient modes and verbose output
  - Data models: `MissionInput`, `PipelineState`, `PipelineConfig`, `RoleResult`, etc.
- **`mandate pipeline` CLI command**: Run the full pipeline from command line
  - `-o <path>`: Save artifact to file
  - `-v`: Verbose role-by-role output
  - `--lenient`: Continue past role failures
  - `--version`: Set artifact version string
- **Normal mission example**: `examples/normal_mission.json` — pentest scenario with 3 tools (nmap, nuclei, metasploit)
- **AEGIS runner integration**: MANDATE phase module for end-to-end MANDATE → LATTICE → TRACE execution

### Tests
- Pipeline integration tests (end-to-end, strict/lenient modes, malformed input)
- CLI tests (pipeline, validate, hash commands)

### Infrastructure
- Version bumped to 1.1.0
- Updated `__all__` exports to include pipeline, models, and roles modules
- Updated roadmap to reflect completed pipeline work and phased next steps

## 1.0.0 (2026-02-02)

### Breaking Changes
- Schema version updated to `1.0` (artifacts should use `"version": "1.0"`)

### New Features
- **Off-nominal trigger validation**: `mandate validate` now validates `off_nominal_triggers[]` in COAs using the same constraint grammar parser
- **Paper v1.0 alignment**: Repository now aligned with MANDATE paper v1.0

### Fixes
- **Example trigger format**: Updated example triggers to use ISO 8601 duration format (`PT1H` instead of `1h`)

### Infrastructure
- Added `validate_triggers()` function to validator
- New `kind="trigger"` for validation issues

## 0.2.2 (2026-02-02)

### P0 Fixes (Critical)
- **Empty trace chain hash**: Now verifies `trace.chain_hash` even when `entries: []` (expected hash is `sha256("[]")`)
- **Entry count validation**: Now verifies `trace.entry_count == len(trace.entries)`

### P1 Fixes (Important)
- **CLI non-string handling**: `mandate validate-constraints` now gracefully handles non-string constraint values
- **CONTAINS type safety**: `CONTAINS` comparator now raises `EvaluationError` with clear message if left operand is not iterable

### P2 Fixes (Polish)
- **CI schema sync check**: Added workflow step to verify root `schemas/` and `src/mandate/schemas/` stay in sync

## 0.2.1 (2026-02-02)

### P0 Fixes (Critical)
- **Constraint validation integrated**: `mandate validate` now checks constraint syntax automatically
- **Chain hash verification fixed**: Now verifies `trace.chain_hash` for both embedded objects AND hash-string references
- **Package-safe schema loading**: Schemas now packaged with module and loaded via `importlib.resources` (works with wheel/sdist installs, not just editable)

### P1 Fixes (Important)
- **Type-aware constraint evaluation**: Clear error messages when comparing incompatible types (e.g., numeric vs duration string)
- **Security documentation**: Added ReDoS warning for MATCHES patterns in module docstring
- **FORBIDS semantics documented**: Clarified state model for REQUIRES/FORBIDS predicates

### P2 Fixes (Polish)
- **Roadmap consistency**: Fixed version references (v0.1.0 → v0.2.0 for constraint grammar)
- **Schema $id namespace**: Changed from `https://example.org/schemas/` to `urn:mandate:schema:` for proper URN-based identifiers

### Infrastructure
- Added `importlib_resources` as conditional dependency for Python < 3.11
- Added `EvaluationError` exception class for runtime evaluation failures

## 0.2.0 (2026-02-02)
- **Constraint Grammar Parser**: Added `src/mandate/constraints.py` with full EBNF grammar support
  - Parses constraints into AST
  - Validates constraint syntax
  - Evaluates constraints against state dictionaries
  - Supports: comparisons, IN predicates, REQUIRES, FORBIDS, AND, OR, NOT
- **New CLI Commands**:
  - `mandate check-constraint "<constraint>"` - Validate a single constraint
  - `mandate validate-constraints <path>` - Validate all constraints in a mandate
- **Updated Documentation**:
  - `docs/artifact-spec.md` - Added operational document types (FRAGOs, ROE, CONOPS, etc.)
  - `docs/overview.md` - Added related work section (AutoGen, Reflexion, AgentBench)
  - `docs/roadmap.md` - Updated with completed items and future milestones
- **Updated Examples**: Constraint strings now follow formal grammar syntax
- **Version Alignment**: Updated all version references to v0.64

## 0.1.0 (2026-02-02)
- Initial repository scaffold
- JSON Schemas for mandate-as-code, trace-entry, gap-report
- Python CLI: schema validation + hash checks
- Examples + unit tests
