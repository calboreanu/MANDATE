# MANDATE v2 Overview

MANDATE is a task-specification and evidence framework for autonomous agents.
It defines acceptable outcomes before execution, represents alternative
courses of action, records structured gaps, and routes incomplete results to
explicit non-executable states.

## Core concepts

- **Anchor:** minimum requirements, targets, constraints, and risk tolerance.
- **Courses of Action:** alternative approaches intended to satisfy the same
  Anchor.
- **Search→Select→Trace:** hash-linked evidence for retrieval, candidate
  selection, and role decisions.
- **Gap reporting:** structured descriptions of information or capability that
  is missing or insufficient for automation.
- **Execution state:** an explicit, fail-closed decision about whether a result
  may proceed.

## Output ontology

MANDATE separates the payload representation from the execution decision.

| Dimension | Values |
|---|---|
| Output representation | `MANDATE_AS_CODE`, `GAP_REPORT`, `NONE` |
| Execution state | `EXECUTABLE`, `NON_EXECUTABLE_GAPS`, `NON_EXECUTABLE_VALIDATION`, `FAILED` |

A partial mandate may remain represented as `MANDATE_AS_CODE` while its state
is `NON_EXECUTABLE_GAPS`. An executable result may retain nonblocking gap
reports. Schema validity, hash consistency, and executability are therefore
separate properties.

## This repository provides

- artifact and result-envelope JSON Schemas;
- RFC 8785 canonicalization and hash-integrity checks;
- constraint parsing, validation, and policy translators;
- a six-stage reference pipeline and command-line interface;
- evaluation and registry utilities; and
- the paper's deposited empirical evidence and verification tools.

## Relationship to adjacent systems

MANDATE operates upstream of tool execution. Agent orchestration frameworks may
consume a MANDATE result, while policy engines such as OPA/Rego or Cedar may
enforce translated constraints. Runtime execution, monitoring, and enforcement
are outside this repository's scope.

The public v2 implementation is a reference implementation. The exact campaign
engines used for the paper are versioned separately and are described in the
study's replication documentation.
