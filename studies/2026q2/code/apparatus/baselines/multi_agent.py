"""
B4 / B5 / B6 multi-agent baselines (Workstream B2).

PROTOCOL_LOCK Section 2.2 fixes six baselines: B1, B2 (single-prompt), B3
(ReAct), and B4 (AutoGen), B5 (CrewAI), B6 (LangGraph). The three frameworks
have unstable APIs across recent major versions, and the design note
`MULTI_AGENT_BASELINES.md` calls for the framework integration itself to be
the final step of Phase 4 baseline calibration on the eval host with a live
key.

This module is the apparatus-side shell each framework will integrate
against. Each baseline runs the orchestration *pattern* the framework
implements, using direct LLMClient calls so it is deterministically
mock-testable today:

  B4  PlannerReviewerBaseline      planner + reviewer, one revision pass
  B5  SequentialCrewBaseline       analyst + gap reviewer, sequential
  B6  GraphRevisionBaseline        draft -> review decision, one revision

Per the Decisions memo Section 4, B4-B6 should run a single consistent
model so the framework, not the model, is the variable; the default is
the same Claude model B1 and B3 use. The pre-registration freezes both
the model and the prompts at the end of Phase 4 calibration.

All three subclass `BaselineSystem`, so the harness, anonymization,
grading and scoring path treat them exactly like B1-B3, and the same
baseline-specification-v1 schema validates the output.
"""
from __future__ import annotations

import json
import time
from typing import Optional

from .base import BaselineSystem, ProduceResult, Step, extract_json
from .llm_client import AnthropicClient
from .prompts import (SPECIFICATION_INSTRUCTIONS, REVIEWER_INSTRUCTIONS,
                      ANALYST_INSTRUCTIONS, GAP_REVIEWER_INSTRUCTIONS,
                      GRAPH_REVIEW_DECISION, GRAPH_REVISION_PROMPT)

# Default model: per Decisions memo Section 4, one model across B4-B6. The
# placeholder is the pinned Claude family used by B1 and B3; the version
# string is finalized at deposit (TO_FILL_TRACKER row D7 / D8).
DEFAULT_MULTI_AGENT_MODEL = "claude-sonnet-4-6"


def _call(client, *, system, user, model, name, temperature=0.0,
          max_tokens=4096):
    """One model call captured as a Step (for the RunRecord)."""
    t0 = time.time()
    resp = client.generate(system=system, user=user, model=model,
                            temperature=temperature, max_tokens=max_tokens)
    dur = (time.time() - t0) * 1000.0
    step = Step(name=name, duration_ms=dur,
                input_tokens=resp.input_tokens,
                output_tokens=resp.output_tokens,
                cost_usd=resp.cost_usd)
    return resp.text, step


# --- B4: AutoGen-shape ------------------------------------------------------

class PlannerReviewerBaseline(BaselineSystem):
    """B4 shell. A planner agent drafts the specification; a reviewer agent
    critiques and revises. The reviewer's output is the final.

    The framework's actual orchestration (turn-taking, message routing,
    termination) is delegated to AutoGen on the eval host; this shell uses
    the same prompts and the same single-revision turn budget so the
    framework's contribution is what changes when it is wired in."""

    framework = "autogen"

    def _produce(self, request_text: str) -> ProduceResult:
        steps = []
        draft_text, s1 = _call(self.client,
                               system=SPECIFICATION_INSTRUCTIONS,
                               user=request_text, model=self.model,
                               name="planner")
        steps.append(s1)
        reviewer_user = ("STAKEHOLDER REQUEST:\n%s\n\nDRAFT SPECIFICATION:\n"
                          "%s" % (request_text, draft_text))
        final_text, s2 = _call(self.client,
                                system=REVIEWER_INSTRUCTIONS,
                                user=reviewer_user, model=self.model,
                                name="reviewer")
        steps.append(s2)
        return ProduceResult(text=final_text, steps=steps)


# --- B5: CrewAI-shape -------------------------------------------------------

class SequentialCrewBaseline(BaselineSystem):
    """B5 shell. A specification analyst produces the substantive fields;
    a gap reviewer adds the suspected_gaps. Outputs are merged: the
    analyst's fields stand, the gap reviewer's list is attached."""

    framework = "crewai"

    def _produce(self, request_text: str) -> ProduceResult:
        steps = []
        analyst_text, s1 = _call(self.client,
                                  system=ANALYST_INSTRUCTIONS,
                                  user=request_text, model=self.model,
                                  name="analyst")
        steps.append(s1)
        gap_user = ("STAKEHOLDER REQUEST:\n%s\n\nANALYST DRAFT:\n%s"
                     % (request_text, analyst_text))
        gap_text, s2 = _call(self.client,
                              system=GAP_REVIEWER_INSTRUCTIONS,
                              user=gap_user, model=self.model,
                              name="gap_reviewer")
        steps.append(s2)

        # Merge: keep the analyst's four substantive fields, attach the
        # gap reviewer's suspected_gaps. If either fails to parse, we still
        # emit the available pieces so schema validation can decide.
        analyst, analyst_err = extract_json(analyst_text)
        gaps, gap_err = extract_json(gap_text)
        merged = dict(analyst or {})
        if gaps and isinstance(gaps.get("suspected_gaps"), list):
            merged["suspected_gaps"] = gaps["suspected_gaps"]
        else:
            merged.setdefault("suspected_gaps", [])
        final_text = json.dumps(merged, indent=2)
        return ProduceResult(text=final_text, steps=steps)


# --- B6: LangGraph-shape ----------------------------------------------------

class GraphRevisionBaseline(BaselineSystem):
    """B6 shell. A draft node produces a first specification; a review node
    decides accept or revise; on revise a single revision node produces the
    final draft. The state is the working specification text. The graph is
    capped at one revision; that cap is part of the pre-registered config."""

    framework = "langgraph"
    max_revisions = 1

    def _produce(self, request_text: str) -> ProduceResult:
        steps = []
        draft_text, s1 = _call(self.client,
                                system=SPECIFICATION_INSTRUCTIONS,
                                user=request_text, model=self.model,
                                name="draft")
        steps.append(s1)
        review_user = ("STAKEHOLDER REQUEST:\n%s\n\nDRAFT SPECIFICATION:\n%s"
                        % (request_text, draft_text))
        review_text, s2 = _call(self.client,
                                 system=GRAPH_REVIEW_DECISION,
                                 user=review_user, model=self.model,
                                 name="review")
        steps.append(s2)

        decision_obj, _ = extract_json(review_text)
        decision = (decision_obj or {}).get("decision", "accept")
        critique = (decision_obj or {}).get("critique", "")
        if decision == "revise" and self.max_revisions > 0:
            revise_user = (
                "STAKEHOLDER REQUEST:\n%s\n\nEARLIER DRAFT:\n%s\n\n"
                "REVIEWER CRITIQUE:\n%s" %
                (request_text, draft_text, critique))
            final_text, s3 = _call(self.client,
                                    system=GRAPH_REVISION_PROMPT,
                                    user=revise_user, model=self.model,
                                    name="revise")
            steps.append(s3)
        else:
            final_text = draft_text
        return ProduceResult(text=final_text, steps=steps)


# --- factories --------------------------------------------------------------

def baseline_b4(model: str = DEFAULT_MULTI_AGENT_MODEL, api_key=None,
                llm_client=None) -> PlannerReviewerBaseline:
    """B4: AutoGen-shape planner+reviewer on a single Claude model."""
    client = llm_client or AnthropicClient(api_key)
    return PlannerReviewerBaseline(client, model, "baseline_4",
                                    "B4 AutoGen (planner+reviewer)")


def baseline_b5(model: str = DEFAULT_MULTI_AGENT_MODEL, api_key=None,
                llm_client=None) -> SequentialCrewBaseline:
    """B5: CrewAI-shape sequential analyst+gap-reviewer."""
    client = llm_client or AnthropicClient(api_key)
    return SequentialCrewBaseline(client, model, "baseline_5",
                                   "B5 CrewAI (sequential crew)")


def baseline_b6(model: str = DEFAULT_MULTI_AGENT_MODEL, api_key=None,
                llm_client=None) -> GraphRevisionBaseline:
    """B6: LangGraph-shape draft -> review -> one revision."""
    client = llm_client or AnthropicClient(api_key)
    return GraphRevisionBaseline(client, model, "baseline_6",
                                  "B6 LangGraph (draft / review / revise)")
