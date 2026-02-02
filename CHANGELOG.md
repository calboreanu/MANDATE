# Changelog

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
