"""
Tests for the B4 / B5 / B6 multi-agent baseline shells (Workstream B2).

Dependency-free: MockLLMClient scripts the per-agent responses so the
orchestration patterns are exercised deterministically. The framework
integrations (AutoGen, CrewAI, LangGraph) are wired in during Phase 4
baseline calibration on the eval host with a live key; that step replaces
the shells' direct LLMClient calls with the framework's own orchestration.

Run:  python3 -m pytest apparatus/baselines/tests/test_multi_agent.py -q
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from apparatus.baselines.llm_client import MockLLMClient
from apparatus.baselines.multi_agent import (
    baseline_b4, baseline_b5, baseline_b6,
    PlannerReviewerBaseline, SequentialCrewBaseline, GraphRevisionBaseline)
from apparatus.harness.runner import Task, run_matrix
from apparatus.harness.ledger import RunLedger


DRAFT_JSON = json.dumps({
    "mission_intent": "Brief the CISO on patch compliance for Q2.",
    "minimum": [{"dimension": "delivery_date", "threshold": "by Friday",
                  "rationale": "explicit deadline in request"}],
    "target": [], "constraints": [], "suspected_gaps": []
})

REVISED_JSON = json.dumps({
    "mission_intent": "Brief the CISO on patch compliance for Q2.",
    "minimum": [{"dimension": "delivery_date", "threshold": "by Friday",
                  "rationale": "explicit deadline in request"}],
    "target": [{"dimension": "format", "objective": None,
                 "rationale": "format not specified"}],
    "constraints": [],
    "suspected_gaps": [{"field": "minimum.coverage_scope",
                         "reason": "scope of patch domains not stated"}]
})

ANALYST_JSON = json.dumps({
    "mission_intent": "Brief the CFO on Q2 budget variance.",
    "minimum": [{"dimension": "delivery_date", "threshold": "by board meeting",
                  "rationale": "deadline in request"}],
    "target": [],
    "constraints": [{"predicate": "audience == 'audit_committee'",
                      "rationale": "stated recipient"}]
})

GAP_JSON = json.dumps({
    "suspected_gaps": [{"field": "minimum.variance_threshold",
                         "reason": "no concrete variance bar stated"}]
})

ACCEPT_REVIEW = json.dumps({"decision": "accept", "critique": ""})
REVISE_REVIEW = json.dumps({"decision": "revise",
                             "critique": ("the threshold 99.5% is invented; "
                                          "move it to suspected_gaps")})


# --- B4 ---------------------------------------------------------------------

def test_b4_runs_planner_then_reviewer_and_uses_reviewer_output():
    mock = MockLLMClient(responses=[DRAFT_JSON, REVISED_JSON],
                         default="{}")
    b4 = baseline_b4(llm_client=mock, model="mock-model")
    rec = b4.run("Brief the CISO on patch compliance for Q2.",
                 run_id="b4-1", task_id="T1", run_number=1)
    assert rec.ok is True
    assert rec.system_id == "baseline_4"
    # two LLM calls, named planner and reviewer
    assert [rt.role_name for rt in rec.role_timings] == ["planner", "reviewer"]
    # final output is the revised spec (the reviewer's response)
    assert rec.output["schema_valid"] is True
    assert (rec.output["specification"]["suspected_gaps"][0]["field"]
            == "minimum.coverage_scope")


def test_b4_handles_review_returning_invalid_schema_gracefully():
    mock = MockLLMClient(responses=[DRAFT_JSON, "not json at all"],
                         default="{}")
    b4 = baseline_b4(llm_client=mock, model="mock-model")
    rec = b4.run("x", run_id="b4-2", task_id="T1", run_number=1)
    # the system ran (ok=True); the schema check failed (O4=False)
    assert rec.ok is True
    assert rec.output["schema_valid"] is False


# --- B5 ---------------------------------------------------------------------

def test_b5_merges_analyst_fields_and_gap_reviewer_suspected_gaps():
    mock = MockLLMClient(responses=[ANALYST_JSON, GAP_JSON],
                         default="{}")
    b5 = baseline_b5(llm_client=mock, model="mock-model")
    rec = b5.run("Brief the CFO on Q2 budget variance.",
                 run_id="b5-1", task_id="T2", run_number=1)
    assert rec.ok is True
    assert rec.system_id == "baseline_5"
    assert ([rt.role_name for rt in rec.role_timings]
            == ["analyst", "gap_reviewer"])
    spec = rec.output["specification"]
    assert spec["mission_intent"].startswith("Brief the CFO")
    # analyst's constraint is preserved
    assert spec["constraints"][0]["predicate"].startswith("audience")
    # gap reviewer's gap is attached
    assert (spec["suspected_gaps"][0]["field"]
            == "minimum.variance_threshold")
    assert rec.output["schema_valid"] is True


def test_b5_attaches_empty_gap_list_when_gap_reviewer_fails_to_parse():
    mock = MockLLMClient(responses=[ANALYST_JSON, "junk"], default="{}")
    b5 = baseline_b5(llm_client=mock, model="mock-model")
    rec = b5.run("x", run_id="b5-2", task_id="T2", run_number=1)
    spec = rec.output["specification"]
    assert spec["suspected_gaps"] == []


# --- B6 ---------------------------------------------------------------------

def test_b6_accepts_first_draft_when_review_says_accept():
    mock = MockLLMClient(responses=[DRAFT_JSON, ACCEPT_REVIEW],
                         default="{}")
    b6 = baseline_b6(llm_client=mock, model="mock-model")
    rec = b6.run("x", run_id="b6-1", task_id="T3", run_number=1)
    # only the draft and review nodes ran; no revision call
    assert [rt.role_name for rt in rec.role_timings] == ["draft", "review"]
    assert rec.output["schema_valid"] is True


def test_b6_runs_one_revision_when_review_says_revise():
    mock = MockLLMClient(responses=[DRAFT_JSON, REVISE_REVIEW, REVISED_JSON],
                         default="{}")
    b6 = baseline_b6(llm_client=mock, model="mock-model")
    rec = b6.run("x", run_id="b6-2", task_id="T3", run_number=1)
    assert ([rt.role_name for rt in rec.role_timings]
            == ["draft", "review", "revise"])
    # the final output is the revised draft
    assert rec.output["schema_valid"] is True
    assert (rec.output["specification"]["suspected_gaps"][0]["field"]
            == "minimum.coverage_scope")


def test_b6_caps_at_one_revision():
    """Even if the review says 'revise' twice, only one revision step runs:
    the cap is part of the pre-registered configuration."""
    b6 = baseline_b6(llm_client=MockLLMClient(default="{}"),
                     model="mock-model")
    assert b6.max_revisions == 1


# --- harness integration ----------------------------------------------------

def test_b4_b5_b6_all_flow_through_run_matrix(tmp_path):
    """The three shells produce uniform RunRecords the ledger can append."""
    systems = [
        baseline_b4(llm_client=MockLLMClient(
            responses=[DRAFT_JSON, REVISED_JSON], default="{}"),
                    model="m"),
        baseline_b5(llm_client=MockLLMClient(
            responses=[ANALYST_JSON, GAP_JSON], default="{}"), model="m"),
        baseline_b6(llm_client=MockLLMClient(
            responses=[DRAFT_JSON, ACCEPT_REVIEW], default="{}"),
                    model="m"),
    ]
    tasks = [Task(task_id="T1", request_text="some request")]
    ledger = RunLedger(str(tmp_path / "ledger.jsonl"))
    records = []
    for sys_ in systems:
        records.extend(run_matrix(sys_, tasks, n_runs=1, ledger=ledger,
                                   output_dir=str(tmp_path / sys_.system_id),
                                   verbose=False))
    assert len(records) == 3
    assert {r.system_id for r in records} == {"baseline_4", "baseline_5",
                                               "baseline_6"}
    for r in records:
        assert r.ok is True
        assert r.output["schema_valid"] is True


def test_b4_b5_b6_factories_default_to_a_single_consistent_model():
    """Per Decisions memo Section 4: B4-B6 share a model so the framework
    is the variable. The factory defaults reflect that."""
    b4 = baseline_b4(llm_client=MockLLMClient(default="{}"))
    b5 = baseline_b5(llm_client=MockLLMClient(default="{}"))
    b6 = baseline_b6(llm_client=MockLLMClient(default="{}"))
    assert b4.model == b5.model == b6.model
