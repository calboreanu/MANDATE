# MLT-Governance-Stack — MANDATE Realness Audit

**Auditor:** Claude Opus 4.7 · **Date:** 2026-06-23
**Subject:** `/Users/ws01admin/Desktop/MLT-Governance-Stack` (`mlt-stack 1.0.0rc1`, generated 2026-06-13)
**Scope:** MANDATE plane only (`src/mlt/mandate/**`, `tests/mandate/**`)

## Verdict
**REAL** — with a meaningful caveat about the evaluation harness ground truth (see Risks).

## Confidence
**85%**

## Evidence for "real"

1. **The pipeline actually runs and produces a schema-validated artifact.** I ran a smoke test (`Pipeline(PipelineConfig(strict=True)).run(mi)`) on a constructed `MissionInput`: returned `ok=True`, all 6 roles executed, `trace.entry_count=6`, `mandate_id="SMOKE"`, no errors. Then ran the mandate test suite: **418 passed, 8 skipped, 3 xfailed** in 0.8s. The skips are all in `TestEvaluationHarness` (no corpus manifest ships) — not failures.

2. **The orchestrator is a real state machine, not a façade.** `pipeline.py` chains six `Role` subclasses with shared `PipelineState`, propagates `RoleResult`, builds Search-Select-Trace entries between roles, supports strict/lenient modes, cancellation, event sinks, metrics collection, LLM hybrid mode with deterministic fallback (`execute_with_fallback`), and per-role mlx-lm / Ollama adapter wiring with concrete env-var resolution paths. The control flow handles cancelled-mid-role, exceptions, and gap propagation distinctly — not boilerplate.

3. **Validation algorithm has actual content.** `validation.py` `_run_validation_algorithm` implements four paper-aligned checks with real per-COA scoring math:
   - `_check_minimum_satisfaction`: coverage ratio over `anchor.minimum` dimensions per COA, with token/lexical fallback (`_dimension_supported`).
   - `_check_target_feasibility`: weighted sum of `node_factor + procedure_factor + capability_factor + risk_factor + lexical_factor` clipped to ≤ 1, threshold 0.6.
   - `_check_constraint_compliance`: parses each constraint string into AST via `parse_constraint`, builds per-task state dict, runs `check_constraint_compliance` per (task × constraint), counts violations, computes `1.0 − violations/checks`.
   - `_check_risk_aggregation`: aggregates per-node risk scores via `max` or `weighted_average` mode (configurable via `risk_aggregation_mode`), classifies via `RiskModelConfig.classify(aggregated)`, compares to reported level.
   Each failure emits a typed `GapSpec` with severity (BLOCKING when *all* COAs fail, DEGRADING otherwise) — that distinction is the kind of thing AI-slop usually skips.

4. **Constraint parser is a real hand-written recursive-descent parser.** `constraints.py` has a hand-rolled lexer with prioritized regex token patterns, full precedence-climbing parser (`parse_or_expr → parse_and_expr → parse_not_expr → parse_primary → parse_field_predicate`), typed AST (`ComparisonPredicate`, `InPredicate`, `RequiresPredicate`, `ForbidsPredicate`, `NotExpr`, `AndExpr`, `OrExpr`), a separate `evaluate_constraint` (boolean truth) and `check_constraint_compliance` (planning-time compliance — distinct semantics for `FORBIDS`/`NOT FORBIDS` and tolerant of missing runtime fields), plus a **non-trivial ReDoS mitigation** with `_UNSAFE_REGEX_PATTERN` rejection + SIGALRM-based wall-clock timeout (`_safe_regex_match`). 250 lines of test coverage in `test_constraints.py`. Also two policy translators (`translators/rego.py` 313 LOC, `translators/cedar.py` 253 LOC) and 729 LOC of translator tests — that's a real backend, not a stub.

5. **Decomposition is templated, not random.** Two distinct generators: domain-profile-driven (`_generate_domain_coas` walks `profile.conservative_phases/moderate_phases/aggressive_phases`, binds available tools by class) and a legacy default (`_build_conservative_coa` RECON+SCAN, `_build_moderate_coa` adds targeted EXPLOIT, `_build_aggressive_coa` parallel multi-vector). Each builds a `TaskNodeSpec` DAG with explicit `depends_on`, edges, and `risk_factors`. `_validate_dag` runs an actual iterative topological sort with `visited`/`in_stack` cycle detection. The tool-class taxonomy (`RECON/SCAN/EXPLOIT/ANALYSIS`) is consistent throughout — this is a coherent, opinionated implementation.

6. **The artifact is hash-anchored.** `validation.py` `_build_trace` chains entries with parent-hashes, computes `compute_trace_entry_hash` (canonical JSON SHA-256) per entry, then `compute_chain_hash_from_strings` over the entry-hash list. `metadata` carries `input_hash` and `output_hash` over canonicalized payloads. The pipeline test `test_chain_hash_present` asserts 64-char hex; `test_trace_entries_are_valid_hashes` validates each is `int(entry, 16)`-parseable. The CHANGELOG and STACK_MANIFEST tie this back to `mlt.core` (RFC 8785 JCS) — the canonicalizer is shared across all three planes.

7. **Tests exercise the actual pipeline, not mocks.** `test_pipeline.py` (394 LOC, 27 passed + 1 xfailed) loads `tests/examples/normal_mission.json` (a fully-populated mission with 3 tools, 4 constraints, scope), runs `Pipeline.run()` end-to-end, then asserts: artifact validates via `validate_artifact()` against `mandate-as-code.schema.json` (real JSONSchema), all 6 role names in order, all trace hashes are 64-char hex, `recommendation` has `primary_coa`/`fallback_sequence`/`rationale`, `constraints` are preserved verbatim including `FORBIDS data_exfiltration`. There is no monkeypatching of the pipeline anywhere in this file. Same for `test_domain_pipeline.py` (643 LOC, also real-runs).

## Evidence for "not real"

1. **The evaluation corpus does not ship.** `benchmarks/corpus/manifest.json` is referenced everywhere in `test_evaluation.py` but does not exist in the repo. Eight `TestEvaluationHarness` tests `pytest.skip("Corpus manifest not found")` — the harness exists, but its expected-outcome ground truth does not. `benchmarks/` ships only `hscale.py` + `loadtest.py`. This is the single biggest gap.

2. **"Tool-class presence" check is weak.** In `evaluation.py` `_check_expectations`, the check for `required_tool_classes_in_coas` actually does this:
   ```python
   checks.append(CheckResult(
       "required_tool_classes_present",
       len(all_node_names) > 0 and (has_procedures or coa_count > 0),
       ...
   ))
   ```
   It checks "are there any nodes and any procedures or any COAs" — *not* whether the named tool classes appear. The variable `expected.required_tool_classes_in_coas` is read but its contents are unused. That's a smell: the assertion is decorative.

3. **Target-feasibility scoring is heuristic, not principled.** `_check_target_feasibility` adds 0.2 per arbitrary signal (`procedures`, `capabilities`, lexical hit, etc.) and thresholds at 0.6. This isn't AI-slop — it's an explicit "0.2 buckets" model — but it is hand-tuned, not learned or paper-derived. Don't treat the resulting `score` as a meaningful float; treat it as `passed/failed`.

4. **Risk-aggregation token list is keyword-matching.** `_task_risk_score` classifies tasks as HIGH if their text contains `exploit/payload/destructive/delete/exfil/lateral/privilege/contain/eradicate`, MEDIUM for `scan/enumerate/collect/active/modify/probe`. Works for the bundled examples (pentest, IR), but anything outside that vocabulary scores LOW by default. Brittle.

5. **Validation role swallows validator ImportError.** Lines 993–995 of `validation.py`:
   ```python
   except ImportError as e:
       return True, [f"Note: Validator unavailable ({e})"]
   ```
   If the JSONSchema validator can't import, the artifact is marked **valid**. Unlikely to fire in practice (validator is local), but it's a fail-open path.

6. **LLM "advisory" mutations are bolted on lightly.** `execute_with_llm` in every role calls `self.execute(state)` after collecting LLM output, with narrow `_LLM_MUTATION_BOUNDARY` (e.g. `validation.py` only mutates `artifact.metadata.validation_focus`). That's defensible — deterministic core + LLM advisory layer — but the LLM path is not what's being tested by the 418 mandate tests. It's instrumentation, not the spine.

## What the pipeline actually does

Six-role sequential transform of `MissionInput → mandate-as-code` JSON artifact:

1. **Intake** (121 LOC) — validates `mission_id`/`intent`, autogenerates `mission_id` if missing (uuid4 hex), validates constraint syntax with `validate_constraint()` early-fail, stores `MissionInput` on state.
2. **Interpreter** (276 LOC) — extracts `anchor_intent/minimum/target`, parses constraints into ASTs (catches `ForbidsPredicate` types), sets `risk_tolerance`, computes `anchor_hash` via `compute_anchor_hash`.
3. **Decomposition** (706 LOC) — detects MISSING_CAPABILITY / UNKNOWN_PATTERN gaps; generates 1–3 COAs (Conservative/Moderate/Aggressive) either from `DomainProfile` phase templates or default tool-class-driven templates; builds task DAG with edges.
4. **Procedure** (785 LOC) — attaches `procedures` and `capabilities` to each `COASpec` (by tool class / domain profile; optionally via RAG retriever).
5. **Binding** (317 LOC) — produces `Recommendation` (`primary_coa`, `fallback_sequence`, `rationale`).
6. **Validation** (997 LOC) — runs the 4-step algorithm, assembles trace chain, emits per-failure `GapSpec`s, builds final artifact with `anchor / courses_of_action / recommendation / trace / registry_reference / metadata{nist_rmf, input_hash, output_hash}`, then re-validates the assembled JSON against `mandate-as-code.schema.json`.

The artifact schema is real (in `mlt/schemas/mandate-as-code.schema.json`) and the assembly is faithful to it.

## What `evaluation.py` actually evaluates

A corpus-driven harness with declarative `ExpectedOutcome` per case. Checks performed (when corpus is provided):

- `pipeline_ok` (true/false), `expected_error_role` substring match in `result.errors`.
- `min_coas` / `max_coas` against `len(artifact["courses_of_action"])`.
- `recommendation_has_primary` / `recommendation_has_fallback`.
- `artifact_has_anchor_hash` (presence), `artifact_has_trace` (`chain_hash` presence).
- `constraints_count` (equality on `len(anchor.constraints)`).
- `gaps_expected` + `min_gaps` against `result.gap_reports`.
- Aggregate `BenchmarkStats` over `PipelineMetrics` (per-role latency, p50/p95, etc.).

**This is structural / counts-based scoring**, not semantic alignment to ground-truth mandates. There is no measurement of "did the artifact correctly represent the intent" beyond counts and presence. And, crucially, **no shipped corpus** to run it against in this snapshot — the harness compiles and the 16 unit tests for the harness classes pass, but the 8 end-to-end harness tests skip.

## Risks if Cal relies on this

1. **No ground-truth corpus shipped.** `benchmarks/corpus/manifest.json` is referenced but missing. The full evaluation pipeline is uncalibrated against any shared baseline. Cal will need to author the corpus + expected outcomes himself, or have the MLT team ship theirs.
2. **`required_tool_classes_in_coas` check is decorative** (see Evidence-against #2). Anyone using `EvaluationHarness` thinking it validates *which* tool classes appear is being misled. Easy fix, but flag-worthy.
3. **Validation is structural, not semantic.** Passing all four `ValidationResult` steps means "the artifact is well-formed and self-consistent," not "this mandate correctly captures the mission." For v2 work that needs to compare *mandate content* across runs/configs, Cal will need additional scoring on top.
4. **Risk taxonomy and tool taxonomy are pentest-flavored.** Default behavior assumes RECON/SCAN/EXPLOIT/ANALYSIS classes; outside pentest/IR a `DomainProfile` must be configured. There are domain profiles for incident response and intelligence ops (`tests/examples/incident_response_mission.json`, `defense_intel_mission.json`) — but the breadth beyond that is limited.
5. **LLM mode is real plumbing but lightly tested.** The 418 passing tests are predominantly the deterministic path. If Cal cares about the hybrid LLM mode, treat its production-readiness as "wired and unit-tested in pieces" rather than "battle-hardened."
6. **Validator fail-open on ImportError** — low probability, but if Cal vendors this and breaks an import, artifacts will silently be marked valid.
7. **`risk_aggregation_mode = "max"` default.** A single HIGH task ⇒ HIGH COA. If Cal wants more nuance, switch to `weighted_average` or override `RiskModelConfig`.

## Recommendation

**Yes — use this as the canonical MANDATE substrate for v2 work**, but with three guardrails:

1. **Ship your own evaluation corpus** at `benchmarks/corpus/manifest.json` (or point `EvaluationHarness.from_manifest` at a Cal-owned path). The harness itself is real; only the ground truth is missing. Use the 5 example missions in `tests/examples/` as seeds.
2. **Don't trust `EvaluationHarness` as a semantic evaluator.** It scores structure and counts. Layer your own semantic scorer (rubric / pairwise / LLM-as-judge) on top of the artifacts it produces. The artifacts themselves are the canonical thing — the harness just helps you run many of them.
3. **Patch the dead `required_tool_classes_in_coas` check** before you depend on it, or skip that field in your expected outcomes.

This is not vaporware. It is a coherent, opinionated, ~10.6K-LOC implementation with 418 real tests passing in under a second, a hand-written constraint grammar, hash-anchored traces, and a clear contract for what a MANDATE artifact contains. The author has clearly thought about edge cases (DAG cycle detection, ReDoS, fail-closed vs fail-open, strict vs lenient, deterministic-with-LLM-advisory). It deserves to be the canonical MANDATE for Cal's evaluation work — the gaps are around evaluation ground truth, not the implementation itself.

## Key file paths

- Orchestrator: `/Users/ws01admin/Desktop/MLT-Governance-Stack/src/mlt/mandate/pipeline.py`
- Models: `/Users/ws01admin/Desktop/MLT-Governance-Stack/src/mlt/mandate/models.py`
- Roles: `/Users/ws01admin/Desktop/MLT-Governance-Stack/src/mlt/mandate/roles/{intake,interpreter,decomposition,procedure,binding,validation}.py`
- Evaluation harness: `/Users/ws01admin/Desktop/MLT-Governance-Stack/src/mlt/mandate/evaluation.py`
- Constraint parser: `/Users/ws01admin/Desktop/MLT-Governance-Stack/src/mlt/mandate/constraints.py`
- Schema: `/Users/ws01admin/Desktop/MLT-Governance-Stack/src/mlt/schemas/mandate-as-code.schema.json`
- Test corpus (5 missions): `/Users/ws01admin/Desktop/MLT-Governance-Stack/tests/examples/*.json`
- **MISSING:** `/Users/ws01admin/Desktop/MLT-Governance-Stack/benchmarks/corpus/manifest.json`
- Stack manifest: `/Users/ws01admin/Desktop/MLT-Governance-Stack/STACK_MANIFEST.md`
