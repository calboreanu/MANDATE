# Overview

MANDATE is a specification framework for autonomous agent tasks.

## Core Concepts

- **Anchor** = immutable success criteria (minimum / target / constraints)
- **COAs** = alternative approaches that all satisfy the anchor
- **Search-Trace** = record search → candidate results → selection → rationale, chained by hashes
- **Dual output**:
  - `mandate-as-code` (complete), or
  - `gap-report` (incomplete; tells you what is missing)

## This Repository Provides

- JSON Schemas for the artifacts
- Hashing + integrity checks (anchor hash, trace entry hash, simple chain hash)
- Constraint grammar parser and validator
- A validation CLI

## Related Work

MANDATE builds on and differs from several established approaches:

- **BDI Architecture** [Bratman 1987, Rao & Georgeff 1995]: MANDATE extends BDI's binary goal satisfaction with tolerance-based thresholds (minimum/target).

- **Multi-Agent Orchestration (AutoGen, LangChain)**: These frameworks focus on conversation patterns and tool execution. MANDATE operates upstream, specifying *what* constitutes success before execution begins.

- **Reflexion** [Shinn et al. 2023]: Introduces episodic memory for agent self-improvement. MANDATE's Success Registry applies similar principles to specification precedents rather than execution improvement.

- **Agent Evaluation (AgentBench)**: Benchmarks assess task completion but don't address the upstream problem of *defining* acceptable completion. MANDATE provides that specification layer.

- **Policy-as-Code (OPA/Rego, Cedar)**: These enforce constraints at runtime. MANDATE specifies constraints declaratively; enforcement is a downstream responsibility with translation pathways to OPA and Cedar.

## Paper Reference

See the MANDATE paper (v1.0) for complete framework description, formal definitions, and architectural details.
