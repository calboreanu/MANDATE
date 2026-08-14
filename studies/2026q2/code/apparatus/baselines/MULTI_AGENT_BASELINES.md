# Multi-agent Baselines B4, B5, and B6: Historical Design Note

**Publication status:** The evaluated B4-B6 systems are orchestration-pattern
shells implemented in `multi_agent.py`; they are not executions of the AutoGen,
CrewAI, or LangGraph products. This file preserves the design rationale that
preceded that implementation. Interpret the empirical comparisons accordingly.

## Why these are separate from B1-B3

B1-B3 call the Anthropic and OpenAI SDKs directly, which are stable and can be exercised with `MockLLMClient` offline. B4-B6 wrap multi-agent frameworks whose APIs have changed substantially across recent major versions, and multi-agent orchestration cannot be meaningfully validated against a mock: the behavior under test is how several model-backed agents interact. Writing these blind, with no ability to run them, risks coding against the wrong framework API.

They should be built either with a live API available (Computer use on the eval host, or a development key), or as the first activity of PLAYBOOK Phase 4 baseline calibration, which is exactly where the protocol expects baseline configurations to be iterated against live runs within a documented budget.

## The shared contract (already settled)

All three integrate identically to B1-B3, so the integration point is not open:

- Each is a `System` (most likely a `BaselineSystem` subclass from `base.py`).
- Each receives only the raw `request_text` (the harness same-input contract, PROTOCOL_LOCK Section 11).
- Each must produce the **baseline specification schema** (`schema.py`): `mission_intent`, `minimum`, `target`, `constraints`, `suspected_gaps`. Same schema as B1-B3, so grading is identical.
- Each emits a `RunRecord` with one `Step` (and one `RoleTiming`) per model call, so token usage and cost are captured per agent turn.
- B4-B6 use **one consistent model** so the orchestration pattern, rather than
  the model family, is the intended variable. The executed RunRecords are the
  source of truth for the frozen model identifiers.

So the work in B4-B6 is purely the framework-internal orchestration that produces the schema.

## B4: AutoGen

**Version situation, resolve first.** The eval-host venv has *both* AutoGen lines installed: `autogen-agentchat==0.7.5` / `autogen-core==0.7.5` (the redesigned 0.4+ architecture, import namespaces `autogen_agentchat` / `autogen_core`) and `pyautogen==0.10.0` (the continuation of the original `autogen` line, namespace `autogen`). These are different frameworks with different APIs. Pick one and pin it; `requirements.txt` currently names `pyautogen`. Recommendation: use `autogen-agentchat` (the actively developed line) and update `requirements.txt` accordingly, or deliberately pin `pyautogen` and remove the other. This is a pre-registration pinning decision.

**Approach.** A small team: a planner agent that drafts the specification and a reviewer agent that checks it for unsupported thresholds and missing fields, with a round-robin or two-turn conversation that terminates on an agreed final JSON. The final message is the specification.

## B5: CrewAI

**Version:** `crewai==1.14.5`.

**Approach.** A two-role crew: a "specification analyst" agent with a task to extract mission intent, minimum, target, and constraints; and a "gap reviewer" agent with a task to flag missing or ambiguous fields. The crew runs sequentially; the final task output is the specification JSON. CrewAI's `Task` supports an expected-output description and structured output, which should be pointed at the baseline schema.

## B6: LangGraph

**Version:** `langgraph==1.2.1`.

**Approach.** A small state graph: a `draft` node produces a first specification, a `review` node inspects it for fabrication and gaps, and a conditional edge loops once back to `draft` for one revision before an `END` node. State carries the working specification. The graph's terminal state holds the final JSON.

## Acceptance criteria for B4-B6 (each)

1. Implemented as a `System`; runs through `apparatus/harness/runner.run_matrix`.
2. Produces output validating against `baseline-specification-v1`.
3. Per-agent-turn token usage and cost captured in the `RunRecord`.
4. Runs end to end on the six calibration tasks with a live key.
5. Configuration (agent prompts, turn limits, model) frozen and pre-registered at the end of Phase 4 calibration.

## Open decisions

- AutoGen line: `autogen-agentchat` vs `pyautogen` (see B4 above).
- The single model used inside B4-B6, as frozen in the executed configuration.
- Per-baseline vs shared schema: this note assumes the shared `baseline-specification-v1`, consistent with B1-B3. PROTOCOL_LOCK Section 11 permits per-baseline schemas but shared is better for comparability.
