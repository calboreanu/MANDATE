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

## Next Steps

### Short-term (v0.3.0)

1. **Policy Translation Examples**
   - OPA/Rego constraint translator
   - Cedar policy translator
   - Example policies for common constraint patterns

2. **Strict RFC 8785 Canonicalizer**
   - Replace pragmatic JSON encoding with full JCS compliance
   - Or adopt a mature library (e.g., `canonicaljson`)

3. **Additional Examples**
   - Defense/intelligence domain examples (redacted)
   - Gap report workflow example
   - Multi-COA selection scenario

### Medium-term (v0.4.0)

4. **1+6 Pipeline Reference Implementation**
   - Minimal Intake→Validation pipeline
   - LLM-based anchor extraction prototype
   - Registry query interface

5. **Evaluation Harness**
   - Test datasets for constraint validation
   - Benchmark suite for pipeline stages
   - Metrics collection framework

### Long-term

6. **Integration Examples**
   - AutoGen integration pattern
   - LangChain integration pattern
   - Standalone agent framework example

7. **Formal Verification Pathway**
   - Temporal logic translation for constraints
   - Model checking integration
   - Assume-guarantee contract generation
