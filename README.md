# MANDATE v2

**MANDATE (Multi-Agent Nominal Decomposition for Autonomous Task Execution)**
is a tolerance-based task-specification framework for autonomous agent systems.
This repository is the publication release of MANDATE v2. The current software
version is **2.0.8**.

MANDATE separates:

- what constitutes acceptable success: minimum requirements, targets, and
  constraints in an **Anchor**;
- how an agent may pursue that success: multiple **Courses of Action**; and
- whether the result may proceed: an explicit, fail-closed execution state.

It also records hash-linked Search→Select→Trace provenance and structured gap
reports when the available information is insufficient for automation.

> This is the public reference implementation of the MANDATE artifact,
> provenance, gap-reporting, and execution-state contracts. It is not the
> proprietary model-serving stack that generated the paper's campaign records.

## Publication release

- **Software:** MANDATE 2.0.8
- **Release tag:** `v2.0.8`
- **Empirical evidence:** [`studies/2026q2/`](studies/2026q2/)
- **Citation metadata:** [`CITATION.cff`](CITATION.cff)
- **License:** Apache-2.0 for framework code; the study directory documents its
  separate data and registration licenses.

The study evidence is included in this repository as one component of the v2
publication release. Historical study tags remain available as immutable
provenance anchors; they are not separate current releases.

## Repository contents

- [`schemas/`](schemas/) — JSON Schemas for mandate-as-code, trace entries, gap
  reports, and result envelopes.
- [`src/mandate/`](src/mandate/) — reference Python implementation and CLI.
- [`examples/`](examples/) — example inputs, artifacts, gap reports, and traces.
- [`docs/`](docs/) — artifact, hashing, and
  [release-status](docs/release-status.md) documentation.
- [`studies/2026q2/`](studies/2026q2/) — the paper's deposited evidence,
  retained grading records, analysis code, and verification apparatus.

## Install and verify

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Validate an example artifact:

```bash
mandate validate examples/quarterly_report_mandate.json
```

Verify the deposited study evidence from a full checkout:

```bash
python3 studies/2026q2/code/scripts/verify_study_release.py
cd studies/2026q2 && shasum -a 256 -c EVIDENCE_SHA256SUMS.txt
```

## Result contract

A pipeline result has two separate dimensions:

1. an output representation (`MANDATE_AS_CODE`, `GAP_REPORT`, or `NONE`); and
2. an execution state (`EXECUTABLE`, `NON_EXECUTABLE_GAPS`,
   `NON_EXECUTABLE_VALIDATION`, or `FAILED`).

`ok=true` is reserved for `EXECUTABLE`. Any blocking or
insufficient-for-automation signal routes to `NON_EXECUTABLE_GAPS` and
`ok=false`, even when a mandate-shaped partial artifact is retained for review.

## CLI

```bash
# Validate schemas and hashes
mandate validate <path/to/artifact.json>

# Compute hashes
mandate hash-anchor <path/to/mandate.json>
mandate hash-trace <path/to/trace_entry.json>

# Validate constraint grammar
mandate check-constraint "status == 'active' AND priority > 5"
mandate validate-constraints <path/to/mandate.json>
```

The `pipeline` command exits `0` for `EXECUTABLE`, `3` for a retained partial
artifact routed to `NON_EXECUTABLE_GAPS`, and `2` for a hard pipeline failure.

## Scope

MANDATE is a specification and evidence layer. It does not execute tools,
enforce downstream policy, or monitor runtime behavior. Constraint predicates
follow the grammar in [`docs/artifact-spec.md`](docs/artifact-spec.md);
translation to enforcement engines such as OPA/Rego or Cedar remains a
downstream integration responsibility.

Hash consistency establishes integrity relative to a trusted released digest.
It is not a substitute for signatures, an external transparency log, or runtime
authentication.

## License

Framework code is licensed under Apache License 2.0. See [`LICENSE`](LICENSE).
Study data and registration materials have separate licenses documented under
[`studies/2026q2/`](studies/2026q2/).
