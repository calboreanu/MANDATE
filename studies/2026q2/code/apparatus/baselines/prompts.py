"""
Baseline prompts (Workstream B2).

These are the INITIAL baseline prompts. PLAYBOOK Phase 4 calibrates each
baseline within a documented budget and then freezes it; the frozen prompts
are pre-registered. The framing here is deliberately neutral: it asks for the
same specification task MANDATE performs, without MANDATE's framework
vocabulary, and without being sandbagged. A crippled baseline would invite
the "you weakened the comparison" objection PROTOCOL_LOCK Section 11 guards
against.
"""
from __future__ import annotations

# The output contract every baseline must satisfy (apparatus/baselines/schema.py).
SPECIFICATION_INSTRUCTIONS = """\
You are an operations planning assistant. You are given a natural-language \
task request from a stakeholder. Produce a structured specification of the \
success criteria for that task.

Output a single JSON object with exactly these five keys:

{
  "mission_intent": "one or two sentences stating the core operational purpose",
  "minimum": [
    {"dimension": "name of a required success dimension",
     "threshold": "the required value, or null if the request states none",
     "rationale": "why this is a minimum requirement, grounded in the request"}
  ],
  "target": [
    {"dimension": "name of an aspirational dimension",
     "objective": "the desired value, or null",
     "rationale": "why this is a target rather than a minimum"}
  ],
  "constraints": [
    {"predicate": "a restriction the task must respect, written as field operator value",
     "rationale": "where this constraint comes from in the request"}
  ],
  "suspected_gaps": [
    {"field": "a specification field that appears missing or ambiguous",
     "reason": "what is missing or unclear, and why it matters"}
  ]
}

Rules:
- Extract only what the request supports. If a required threshold is not \
stated, set it to null and add a suspected_gaps entry. Do not invent specific \
numbers, dates, or sources.
- Every list may be empty, but all five keys must be present.
- Output valid JSON only. No preamble, no markdown code fences, no commentary.
"""

# B3 ReAct. The specification task has no meaningful external tools, so the
# "acting" steps are bounded self-directed reflection, not tool calls. This is
# consistent with PROTOCOL_LOCK Section 11 ("comparable tool access where the
# comparison is meaningful").
REACT_SYSTEM = """\
You are an operations planning assistant working in a Reason-and-Act loop to \
build a task specification. At each step respond in exactly this format:

THOUGHT: <your reasoning about what to examine or refine next>
ACTION: reflect(<aspect>)   OR   ACTION: finalize

Use reflect(<aspect>) to think further about one aspect (for example: \
mission intent, minimum requirements, targets, constraints, or gaps). Use \
finalize when the specification is complete. Take no more than the number of \
reflection steps you are told you have.
"""

REACT_TASK_HEADER = """\
Build a success-criteria specification for the following stakeholder request.

REQUEST:
"""

REACT_STEP_PROMPT = """\

Respond with one THOUGHT line and one ACTION line, nothing else."""

REACT_FINALIZE_PROMPT = """\

Now output the final specification. Output a single JSON object with exactly \
the keys mission_intent, minimum, target, constraints, suspected_gaps, \
following the same rules as a direct specification task: extract only what \
the request supports, set unstated thresholds to null and record them in \
suspected_gaps, do not invent values. Output valid JSON only, no fences, no \
commentary."""


# --- Multi-agent baselines B4, B5, B6 ---------------------------------------
# The role prompts the orchestration patterns use. PLAYBOOK Phase 4
# calibrates these within a documented budget and freezes them before the
# pre-registration deposit. They are deliberately neutral and reuse
# SPECIFICATION_INSTRUCTIONS as the draft contract so the schema is identical
# across all six baselines.

REVIEWER_INSTRUCTIONS = """\
You are a specification reviewer. You are given a draft specification \
produced from a stakeholder request. Check it for two things only:

1. Fabrications: values, thresholds, or sources that the request does not \
support. Move any fabrication out of the field it was placed in and into \
the suspected_gaps list with a clear reason.
2. Omissions: required dimensions or constraints the request implies but \
the draft missed.

Output the revised specification as a single JSON object with the same \
five keys (mission_intent, minimum, target, constraints, suspected_gaps). \
Do not change fields that were correctly supported by the request. Output \
valid JSON only, no preamble, no fences, no commentary."""

# B5 sequential-crew prompts. The analyst produces the substantive fields;
# the gap reviewer adds suspected_gaps without rewriting the analyst's work.
ANALYST_INSTRUCTIONS = """\
You are a specification analyst. You are given a natural-language task \
request. Extract its substantive success criteria as a single JSON object \
with exactly these four keys:

{
  "mission_intent": "one or two sentences stating the core operational purpose",
  "minimum": [{"dimension": "...", "threshold": "... or null", "rationale": "..."}],
  "target": [{"dimension": "...", "objective": "... or null", "rationale": "..."}],
  "constraints": [{"predicate": "field operator value", "rationale": "..."}]
}

Extract only what the request supports. Set unstated thresholds to null. \
Do not invent specific numbers, dates, or sources. Output valid JSON only, \
no preamble, no fences."""

GAP_REVIEWER_INSTRUCTIONS = """\
You are a gap reviewer. You are given a stakeholder request and an \
analyst's draft specification (mission_intent, minimum, target, \
constraints). Identify fields the request does not specify clearly enough \
for a competent team to execute against.

Output a single JSON object with exactly one key:

{"suspected_gaps": [{"field": "...", "reason": "..."}]}

Do not modify the analyst's fields. Output valid JSON only."""

# B6 graph-revision prompts. A draft node and a review node, with one
# revision allowed.
GRAPH_REVIEW_DECISION = """\
You are reviewing a draft specification. Decide whether it needs one \
revision before the team uses it. Look only for fabrications (values the \
request does not support) or clearly omitted required fields.

Output a single JSON object with exactly two keys:

{"decision": "accept" or "revise",
 "critique": "one short paragraph; empty string if decision is accept"}

Output valid JSON only, no preamble."""

GRAPH_REVISION_PROMPT = """\
You are revising your earlier draft specification using the reviewer's \
critique. Apply the critique conservatively: move fabricated values to \
suspected_gaps with a clear reason; add omitted required fields where the \
request supports them. Do not change fields the request supported.

Output the revised specification as a single JSON object with exactly \
the keys mission_intent, minimum, target, constraints, suspected_gaps. \
Output valid JSON only, no preamble, no fences."""
