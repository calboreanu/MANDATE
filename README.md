# MANDATE

**MANDATE (Multi-Agent Nominal Decomposition for Autonomous Task Execution)** is a tolerance-based task specification framework for autonomous agent systems.

It produces governance-ready specification artifacts that separate:

- **What constitutes acceptable success** (the *Anchor*: minimum / target / constraints), from
- **How to achieve it** (multiple **Courses of Action**, COAs),
- With **Search→Select→Trace** provenance and optional **Gap Analysis** output when intent cannot be fully specified.

> This repository is the public reference implementation for the MANDATE artifact,
> provenance, gap-reporting, and fail-closed execution-state contracts. It is not the
> proprietary model-serving stack used to regenerate the paper's campaign records.

## What’s in here

- `schemas/` — JSON Schemas for:
  - `mandate-as-code.schema.json`
  - `trace-entry.schema.json`
  - `gap-report.schema.json`
- `src/mandate/` — Python utilities and a CLI:
  - `mandate validate examples/quarterly_report_mandate.json`
- `examples/` — example artifacts (mandate + gap report) and trace entries
- `docs/` — short specs and implementation notes

Pipeline results expose both an artifact representation and an execution state.
`ok=true` is reserved for `EXECUTABLE`; any blocking or
insufficient-for-automation signal routes to `NON_EXECUTABLE_GAPS` and `ok=false`,
even when a mandate-shaped partial artifact is retained for review.

## Quickstart (local)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

mandate validate examples/quarterly_report_mandate.json
```

## CLI

```bash
# Validate artifact schema and hashes
mandate validate <path/to/mandate.json>
mandate validate <path/to/gap.json>

# Compute hashes
mandate hash-anchor <path/to/mandate.json>
mandate hash-trace <path/to/trace_entry.json>

# Constraint grammar validation
mandate check-constraint "status == 'active' AND priority > 5"
mandate validate-constraints <path/to/mandate.json>
```

The `pipeline` command exits `0` for `EXECUTABLE`, `3` for a retained partial
artifact routed to `NON_EXECUTABLE_GAPS`, and `2` for a hard pipeline failure.

## Status / non-goals

- This is **not** an execution runtime. It does **not** run tools, enforce policy, or monitor runtime behavior.
- Constraint predicates follow a formal grammar (see `docs/artifact-spec.md`). The `constraints.py` module provides parsing and validation. Translation to enforcement engines (OPA/Rego, Cedar) is a downstream responsibility.

## Repository conventions

- `version` fields are semantic and should be bumped when schemas change.
- Hashes are SHA-256 over a deterministic JSON representation (see `docs/hashing.md`).

## License

Apache 2.0. See [LICENSE](LICENSE) for details.
