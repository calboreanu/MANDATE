# Roadmap

## Completed (v1.0.0) — Paper v1.0 Release

- [x] JSON Schemas for mandate-as-code, trace-entry, gap-report
- [x] Hash computation and verification (anchor, trace entry, chain, entry_count)
- [x] CLI validation tool
- [x] Example artifacts with passing tests
- [x] Constraint grammar parser and validator
- [x] Constraint syntax integrated into `mandate validate`
- [x] Off-nominal trigger validation using constraint grammar
- [x] Package schemas with importlib.resources (wheel-safe)
- [x] Type-aware constraint evaluation with clear error messages
- [x] Security documentation for MATCHES patterns
- [x] FORBIDS/REQUIRES semantics documentation
- [x] CI schema sync check
- [x] Copyright registration filed (Case 1-15096549088, status: Complete)

## Completed (v1.1.0) — Pipeline & AEGIS Integration

- [x] 1+6 Pipeline Reference Implementation (all 6 roles)
  - IntakeRole: input parsing, constraint validation, mission_id generation
  - InterpreterRole: anchor extraction, min/target derivation, risk tolerance
  - DecompositionRole: rule-based COA generation (1-3 COAs)
  - ProcedureRole: task DAG sorting, procedure + trigger generation
  - BindingRole: risk assessment, COA recommendation, fallback sequences
  - ValidationRole: artifact assembly, final validation gate, trace generation
- [x] Pipeline orchestrator with strict/lenient modes
- [x] Data models (MissionInput, PipelineState, RoleResult, etc.)
- [x] `mandate pipeline` CLI command with `-o`, `-v`, `--lenient` flags
- [x] `normal_mission.json` example (pentest scenario)
- [x] AEGIS runner integration (MANDATE → LATTICE → TRACE end-to-end)

## Next Steps

### Phase 1 — Test Coverage & Commit Hygiene (v1.1.1) ✅ COMPLETE

1. **Commit uncommitted pipeline work**
   - [x] `cli.py` pipeline subcommand
   - [x] `normal_mission.json` example
   - [x] Bump version to 1.1.0 in `__init__.py`, `pyproject.toml`, `CITATION.cff`

2. **Pipeline integration tests** (`tests/test_pipeline.py`) — 28 tests
   - [x] End-to-end: MissionInput → PipelineResult with valid artifact
   - [x] Strict mode: verify pipeline halts on role failure
   - [x] Lenient mode: verify pipeline continues past role failure
   - [x] Artifact schema compliance: validate output passes `mandate validate`
   - [x] Trace integrity: verify chain_hash and entry_count in output
   - [x] Malformed input: verify graceful error handling

3. **CLI tests** (`tests/test_cli.py`) — 20 tests
   - [x] `mandate pipeline <path>` success path
   - [x] `mandate pipeline <path> -o <out>` writes file
   - [x] `mandate pipeline` with invalid input returns exit code 2
   - [x] `mandate validate` / `hash-anchor` / `hash-trace` / `check-constraint`

4. **Update CHANGELOG.md** for v1.1.0
   - [x] Changelog updated with all new features, tests, and infrastructure changes

### Phase 2 — Gap Report Generation (v1.2.0) ✅ COMPLETE

5. **Gap report pipeline output** — 34 tests
   - [x] Detect incomplete specification in Interpreter/Decomposition roles
     - Interpreter: UNDEFINED_MINIMUM, UNDEFINED_TARGET, UNASSESSABLE_RISK
     - Decomposition: MISSING_CAPABILITY (no tools, no RECON), UNKNOWN_PATTERN (no scope)
   - [x] Generate gap-report artifact conforming to `gap-report.schema.json`
     - `src/mandate/gap_report.py`: GapSpec → artifact conversion, save, validate
     - GapSpec model added to `models.py` with all 6 gap types
   - [x] CLI flag: `mandate pipeline --emit-gaps` to output gap report alongside mandate
   - [x] Tests: verify gap reports generated for underspecified missions (34 tests)
   - [x] Example: `underspecified_mission.json` → 4 gap reports output

### Phase 3 — Policy Translation (v1.2.0) ✅ COMPLETE

6. **OPA/Rego constraint translator** — 78 tests
   - [x] `src/mandate/translators/rego.py` — constraint AST → Rego v1 rules
     - OR → helper rule pairs, NOT → `not <rule_ref>`, AND → implicit body lines
     - Complete policy generation with package, imports, default rule, comments
   - [x] Example `.rego` policies: `examples/policies/normal_mission.rego`, `complex_mission.rego`
   - [x] Tests: all predicates, logical operators, full policy generation, round-trip paper examples

7. **Cedar policy translator**
   - [x] `src/mandate/translators/cedar.py` — constraint AST → Cedar permit/forbid policies
     - Inline `&&`/`||`/`!`, `decimal()` for floats, `like` for MATCHES
     - Configurable namespace, action type, policy effect
   - [x] Example `.cedar` policies: `examples/policies/normal_mission.cedar`, `complex_mission.cedar`
   - [x] Tests: all predicates, logical operators, full policy generation, round-trip, CLI integration

8. **`mandate translate` CLI subcommand**
   - [x] `-f rego|cedar` format selection
   - [x] `-o <path>` file output
   - [x] `--package`, `--rule`, `--namespace` customization
   - [x] Accepts mission inputs and mandate-as-code artifacts

### Phase 4 — Hashing & Integrity Hardening (v1.3.0) ✅ COMPLETE

9. **Strict RFC 8785 (JCS) canonicalization** — 63 tests
   - [x] Replace `canonical_json()` with JCS via `rfc8785` library (Trail of Bits)
     - IEEE 754 number serialization, UTF-16 key sorting, spec-compliant escaping
     - Byte-identical output for MANDATE-typical data (no hash changes)
   - [x] Evaluated `canonicaljson` (NOT RFC 8785 compliant), `jcs`, `rfc8785` — chose `rfc8785` (most recent, pure Python, zero deps)
   - [x] `legacy_canonical_json()` preserves v1.0–v1.2 behaviour for offline verification
   - [x] Migration path documented in `docs/hashing.md` with edge-case notes
   - [x] Tests: 63 tests covering RFC 8785 vectors, number serialization, key sorting,
     string escaping, legacy compatibility, hash computation, artifact integration

### Phase 5 — Additional Examples & Domain Customization (v1.4.0) ✅ COMPLETE

10. **Domain-specific examples** — 3 new mission scenarios + full pipeline integration
    - [x] `examples/defense_intel_mission.json` — SIGINT collection with COLLECT/PROCESS/ANALYZE/DISSEMINATE tools, redacted fields, classification constraints
    - [x] `examples/incident_response_mission.json` — Ransomware IR with DETECT/CONTAIN/ERADICATE/RECOVER tools, NIST SP 800-61 alignment
    - [x] `examples/multi_coa_mission.json` — Multi-cloud security assessment (AWS/GCP/Azure) with 6 tools, recommendation tracing

11. **Configurable COA generation** — 85 tests
    - [x] `src/mandate/domain.py` — `DomainProfile` with phase templates, `PhaseTemplate`, `RiskModelConfig`, 3 built-in profiles (pentest, IR, defense/intel), profile registry
    - [x] `src/mandate/registry.py` — `ToolRegistry` with 3-tier resolution (explicit → class → fallback), `ToolRegistryEntry`, `from_tools()` factory, 12 tool class defaults across 3 domains
    - [x] Domain-pluggable `DecompositionRole` — template-driven COA generation with tool binding, domain-aware gap detection, full backward compatibility
    - [x] Registry-aware `ProcedureRole` — uses `ToolRegistry` for capability determination when available
    - [x] Configurable `BindingRole` — uses `RiskModelConfig` thresholds and `ToolRegistry` risk weights for scoring
    - [x] `PipelineConfig` extensions — `domain_profile`, `risk_model`, `tool_registry` fields

### Phase 6 — Evaluation Harness (v2.0.0) ✅ COMPLETE

12. **Test datasets and benchmarks** — 77 tests
    - [x] `src/mandate/metrics.py` — `RoleMetric`, `PipelineMetrics`, `MetricsCollector`, `BenchmarkStats` with nanosecond timing, per-role breakdowns, aggregate statistics
    - [x] `src/mandate/evaluation.py` — `EvaluationHarness` with manifest-driven corpus loading, per-case expected outcome checks (pipeline_ok, COA count, tool classes, recommendation, anchor hash, trace, constraints, gaps), tag filtering, repetitions
    - [x] `benchmarks/corpus/manifest.json` — 8 evaluation cases: standard pentest, IR, defense intel, multi-COA, underspecified, minimal, max-complexity, invalid input
    - [x] Pipeline.run() now returns `PipelineMetrics` by default (opt-out via `collect_metrics=False`)
    - [x] `mandate benchmark <manifest>` CLI command with `--tags`, `--repetitions`, `-o` report output

13. **Success Registry interface** — included in 77 tests above
    - [x] `src/mandate/success_registry.py` — `SuccessRegistry`, `SuccessRecord`, `SimilarityMatch`
    - [x] Weighted Jaccard similarity matching: intent (0.5), constraints (0.3), tool classes (0.2)
    - [x] `find_similar()` with domain filter, top-k, min-score, custom weights
    - [x] JSON file persistence, registry merge, statistics
    - [x] `mandate registry stats|query|ingest` CLI commands

### Long-term

14. **Integration examples**
    - [ ] AutoGen integration pattern
    - [ ] LangChain integration pattern
    - [ ] Standalone agent framework example

14. **Formal verification pathway**
    - [ ] Temporal logic translation for constraints
    - [ ] Model checking integration
    - [ ] Assume-guarantee contract generation
