"""
Corpus-authoring prompts (Workstream C2).

PROMPTS.md Section 1 (task generation) and Section 2 (anchor scaffolding),
reproduced here verbatim. PROTOCOL_LOCK requires the prompts be used as
written; any change is a documented deviation in the deviation log. The
render functions fill the substitution points with str.replace so the
literal JSON braces in the Section 2 body survive intact.
"""
from __future__ import annotations

CATEGORIES = ("full_specification", "gap_triggering", "stretch_case")

# Domain guidance as PROMPTS Section 1 specifies.
DOMAIN_GUIDANCE = {
    "security_operations_reporting": (
        "vulnerability reporting, patch compliance, incident summaries, "
        "threat briefings, security posture assessments. Stakeholders "
        "include CISOs, SOC managers, executive leadership."),
    "financial_reporting": (
        "quarterly reports, expense analyses, revenue summaries, budget "
        "variance reports, audit response packages. Stakeholders include "
        "CFOs, controllers, audit committees."),
    "intelligence_collection_tasking": (
        "OSINT collection, target package development, threat actor "
        "profiling, indicator extraction. Stakeholders include "
        "intelligence analysts, collection managers, operations leads."),
    "software_engineering_specification": (
        "software requirements specifications, architecture decision "
        "records, API contracts, secure software development plans, "
        "technical design documents. Stakeholders include engineering "
        "leads, system architects, principal engineers, technical "
        "program managers."),
}

# --- PROMPTS.md Section 1, verbatim body ------------------------------------
TASK_GENERATION_PROMPT = """You are generating realistic operational task descriptions for an empirical
evaluation of an AI agent specification framework. Each task description is
a natural-language request from a stakeholder to a team or system, similar
to what would appear in an email, ticket, or tasking memo.

Domain: {DOMAIN}
Category: {full_specification | gap_triggering | stretch_case}
Target length: 80 to 200 words

Requirements:
- Write in the voice of the requesting stakeholder
- Include enough context that a competent team could attempt the task
- Use realistic terminology, system names, and operational constraints
- Do not include explicit machine-readable thresholds; phrase requirements
  as a stakeholder naturally would (for example: "by end of week" rather
  than "deadline: 2026-06-01T17:00:00Z")
- For full_specification: include all necessary thresholds, sources, and
  constraints stated naturally
- For gap_triggering: leave one critical threshold, constraint, or
  capability unstated where a competent SME would notice the gap
- For stretch_case: include a subtle contradiction (deadline conflicts
  with scope) or an unspecifiable requirement ("best efforts" with no
  quality bar)

Produce 5 distinct task descriptions. Number them 1 through 5. Each should
be substantively different in scope, stakeholder, or sub-domain. Do not
repeat the same scenario in different phrasings.

Output format: Plain text, numbered 1 through 5, each task description as
a single paragraph."""


# --- PROMPTS.md Section 2, verbatim body ------------------------------------
ANCHOR_SCAFFOLD_PROMPT = """You are scaffolding a candidate anchor specification for SME review. The
SME will accept, revise, or reject your proposal. Be thorough but
conservative: it is better to flag a gap than to invent a threshold.

Task description:
{REQUEST_TEXT}

Produce a candidate anchor in the following JSON structure:

{
  "mission_intent": "1 to 2 sentence statement of the core operational purpose",
  "minimum": [
    {
      "dimension": "name of the success dimension",
      "threshold": "value, or null if not specified in the request",
      "rationale": "why this is a minimum requirement; cite the request text"
    }
  ],
  "target": [
    {
      "dimension": "name of the aspirational dimension",
      "objective": "value, or null",
      "rationale": "why this is a target rather than minimum"
    }
  ],
  "constraints": [
    {
      "predicate": "constraint expressed in MANDATE constraint grammar",
      "rationale": "where this constraint comes from in the request"
    }
  ],
  "suspected_gaps": [
    {
      "field": "anchor field where information appears missing",
      "reason": "what is missing or ambiguous, and why an SME might want to flag it"
    }
  ]
}

Rules:
- If a threshold cannot be reasonably inferred from the task description,
  set the value to null and add an entry to suspected_gaps
- Do not invent specific numbers (such as "95%" or "within 48 hours") that
  are not implied by the request
- Use the MANDATE constraint grammar for predicates: field operator value,
  with AND/OR connectives. Operators: ==, !=, <, <=, >, >=, IN, CONTAINS
- Output valid JSON only. No preamble or commentary outside the JSON."""


def render_task_generation_prompt(*, domain: str, category: str) -> str:
    """Fill the Section 1 task generation prompt. Domain is one of the keys
    of DOMAIN_GUIDANCE; category is one of CATEGORIES."""
    if domain not in DOMAIN_GUIDANCE:
        raise ValueError("unknown domain: %r (use one of %s)"
                         % (domain, ", ".join(DOMAIN_GUIDANCE)))
    if category not in CATEGORIES:
        raise ValueError("unknown category: %r (use one of %s)"
                         % (category, ", ".join(CATEGORIES)))
    return (TASK_GENERATION_PROMPT
            .replace("{DOMAIN}", domain)
            .replace("{full_specification | gap_triggering | stretch_case}",
                     category))


def render_anchor_scaffold_prompt(*, request_text: str) -> str:
    """Fill the Section 2 anchor scaffolding prompt. str.replace is used so
    the literal JSON braces in the prompt body survive intact."""
    return ANCHOR_SCAFFOLD_PROMPT.replace("{REQUEST_TEXT}",
                                          request_text or "")
