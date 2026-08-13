"""
Tests for the baseline systems B1-B3 (Workstream B2).

Dependency-free: every test uses MockLLMClient, so no API key and no network
are needed. The real Anthropic / OpenAI paths are exercised during Phase 4
baseline calibration on the eval host.

Run:  python3 -m pytest apparatus/baselines/tests -q   (from the project root)
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from apparatus.baselines.schema import validate_specification
from apparatus.baselines.base import extract_json
from apparatus.baselines.llm_client import MockLLMClient, estimate_cost
from apparatus.baselines.single_prompt import SinglePromptBaseline
from apparatus.baselines.react import ReactBaseline
from apparatus.harness.ledger import RunLedger
from apparatus.harness.runner import Task, run_matrix

VALID_SPEC = json.dumps({
    "mission_intent": "Provide the CIO with a weekly vulnerability report.",
    "minimum": [
        {"dimension": "deadline", "threshold": "Friday 1700",
         "rationale": "stated explicitly in the request"},
    ],
    "target": [],
    "constraints": [
        {"predicate": "classification == 'UNCLASSIFIED'",
         "rationale": "stated explicitly"},
    ],
    "suspected_gaps": [],
})


def _spb(responses):
    """A single-prompt baseline wired to a scripted mock client."""
    return SinglePromptBaseline(MockLLMClient(responses=responses),
                                "claude-test", "baseline_1", "B1 test")


# --- JSON extraction ---------------------------------------------------------

def test_extract_json_plain():
    obj, err = extract_json(VALID_SPEC)
    assert err is None and obj["mission_intent"].startswith("Provide")


def test_extract_json_fenced():
    obj, err = extract_json("```json\n" + VALID_SPEC + "\n```")
    assert err is None and obj is not None


def test_extract_json_prose_wrapped():
    obj, err = extract_json("Here is the spec:\n" + VALID_SPEC + "\nDone.")
    assert err is None and obj is not None


def test_extract_json_none():
    obj, err = extract_json("I cannot help with that request.")
    assert obj is None and err


# --- schema validation -------------------------------------------------------

def test_validate_specification_ok():
    valid, errs = validate_specification(json.loads(VALID_SPEC))
    assert valid and errs == []


def test_validate_specification_missing_key():
    bad = json.loads(VALID_SPEC)
    del bad["constraints"]
    valid, errs = validate_specification(bad)
    assert not valid and errs


# --- single-prompt baseline --------------------------------------------------

def test_single_prompt_valid_output():
    sys = _spb([VALID_SPEC])
    rec = sys.run("Generate the weekly report.", run_id="r1",
                  task_id="T1", run_number=1, seed=1)
    assert rec.ok is True
    assert rec.output["schema_valid"] is True
    assert rec.output["specification"]["mission_intent"]
    assert len(rec.role_timings) == 1
    assert rec.role_timings[0].llm_used is True
    assert rec.api_cost_usd is not None and rec.api_cost_usd > 0


def test_single_prompt_fenced_output():
    sys = _spb(["```json\n" + VALID_SPEC + "\n```"])
    rec = sys.run("x", run_id="r1", task_id="T1", run_number=1)
    assert rec.output["schema_valid"] is True


def test_single_prompt_prose_is_o4_failure_not_run_failure():
    sys = _spb(["I cannot produce that."])
    rec = sys.run("x", run_id="r1", task_id="T1", run_number=1)
    assert rec.ok is True                       # the system ran
    assert rec.output["schema_valid"] is False  # but failed O4
    assert rec.output["specification"] is None


def test_single_prompt_missing_key_is_schema_invalid():
    bad = json.loads(VALID_SPEC)
    del bad["target"]
    sys = _spb([json.dumps(bad)])
    rec = sys.run("x", run_id="r1", task_id="T1", run_number=1)
    assert rec.ok is True
    assert rec.output["schema_valid"] is False
    assert rec.output["schema_errors"]


# --- ReAct baseline ----------------------------------------------------------

def test_react_finalizes_early():
    responses = [
        "THOUGHT: consider the minimum requirements\nACTION: reflect(minimums)",
        "THOUGHT: the specification is complete\nACTION: finalize",
        VALID_SPEC,
    ]
    sys = ReactBaseline(MockLLMClient(responses=responses), "claude-test",
                        "baseline_3", "B3 test", max_steps=4)
    rec = sys.run("Generate the report.", run_id="r1", task_id="T1",
                  run_number=1)
    assert rec.ok is True
    assert rec.output["schema_valid"] is True
    # two reflection steps then a finalize call
    assert [s.role_name for s in rec.role_timings] == [
        "react_step_1", "react_step_2", "finalize"]


def test_react_respects_max_steps():
    reflect = "THOUGHT: keep thinking\nACTION: reflect(constraints)"
    sys = ReactBaseline(MockLLMClient(responses=[reflect] * 4 + [VALID_SPEC]),
                        "claude-test", "baseline_3", "B3 test", max_steps=4)
    rec = sys.run("x", run_id="r1", task_id="T1", run_number=1)
    # 4 reflection steps (never finalized) + 1 finalize call
    assert len(rec.role_timings) == 5
    assert rec.output["schema_valid"] is True


# --- harness integration -----------------------------------------------------

def test_baseline_runs_through_run_matrix(tmp_path):
    sys = _spb([VALID_SPEC, VALID_SPEC])
    ledger = RunLedger(str(tmp_path / "l.jsonl"))
    recs = run_matrix(sys, [Task("T1", "first task"), Task("T2", "second")],
                      n_runs=1, ledger=ledger, output_dir=str(tmp_path / "o"),
                      verbose=False)
    assert len(recs) == 2 and all(r.ok for r in recs)
    assert ledger.count() == 2
    assert recs[0].system_id == "baseline_1"
    assert recs[0].output_type == "BASELINE_SCHEMA:specification"


def test_cost_estimate():
    assert estimate_cost("claude-sonnet-4-6", 1_000_000, 1_000_000) == 18.0
    assert estimate_cost("unknown-model", 1000, 1000) is None
