import json

import pytest

from apparatus.baselines.llm_client import MockLLMClient
from apparatus.preprocess.extract_mission_input import (
    _parse_response_text,
    _valid_constraints,
    extract,
)


def extraction_json(**overrides):
    base = {
        "mission_id": "M-1",
        "intent": "Assess reporting controls for the mission.",
        "minimum_outcome": "Minimum: enumerate control gaps and deadlines.",
        "target_outcome": "Target: produce prioritized remediation options.",
        "constraints": ["FORBIDS data_exfiltration", "execution.duration <= PT4H"],
        "scope": ["financial reporting"],
        "assumptions": ["Records are available"],
        "available_tools": [
            {"tool_id": "analysis_workbench", "tool_class": "ANALYSIS"}
        ],
        "risk_tolerance": "LOW",
    }
    base.update(overrides)
    return json.dumps(base)


def test_extract_builds_mission_input():
    mi = extract("TASK-1", "task text",
                 client=MockLLMClient(default=extraction_json()))
    assert mi.mission_id == "M-1"
    assert mi.intent.startswith("Assess reporting controls")
    assert mi.minimum_outcome
    assert mi.target_outcome
    assert mi.constraints == ["FORBIDS data_exfiltration",
                              "execution.duration <= PT4H"]
    assert mi.available_tools[0].tool_class == "ANALYSIS"
    assert mi.metadata["source_task_id"] == "TASK-1"


def test_extract_defaults_missing_mission_id_to_task_id():
    mi = extract("TASK-2", "fallback task",
                 client=MockLLMClient(default=extraction_json(mission_id="")))
    assert mi.mission_id == "TASK-2"


def test_extract_filters_invalid_constraint_strings():
    constraints = ["nonsense: not mandate grammar", "FORBIDS destructive_action"]
    mi = extract("TASK-3", "task",
                 client=MockLLMClient(default=extraction_json(constraints=constraints)))
    assert mi.constraints == ["FORBIDS destructive_action"]
    assert mi.metadata["constraints_extracted"] == 1
    assert mi.metadata["constraints_failed_grammar"] == 1
    assert mi.metadata["extraction_failed_constraints"] == [
        {"text": "nonsense: not mandate grammar", "reason": "invalid_grammar"}
    ]


def test_extractor_validates_constraints_against_canonical_grammar():
    from mlt.mandate.constraints import validate_constraint

    mi = extract("TASK-3B", "task",
                 client=MockLLMClient(default=extraction_json(
                     constraints=[
                         "FORBIDS destructive_action",
                         "target.scope IN ['system_a', 'system_b']",
                         "execution.duration <= PT4H",
                     ]
                 )))
    assert mi.constraints
    assert all(validate_constraint(c) for c in mi.constraints)


def test_extractor_routes_invalid_constraints_to_metadata():
    mi = extract("TASK-3C", "task",
                 client=MockLLMClient(default=extraction_json(
                     constraints=[
                         "FORBIDS destructive_action",
                         "Must align with NIST 800-37",
                     ]
                 )))
    assert mi.constraints == ["FORBIDS destructive_action"]
    assert mi.metadata["extraction_failed_constraints"] == [
        {"text": "Must align with NIST 800-37", "reason": "invalid_grammar"}
    ]


def test_extractor_retries_on_anthropic_overload():
    client = MockLLMClient(
        responses=[
            RuntimeError("529 overloaded_error"),
            RuntimeError("500 api_error"),
            extraction_json(),
        ]
    )
    mi = extract(
        "TASK-3D",
        "task",
        client=client,
        retry_backoff_sec=(0.0, 0.0, 0.0),
    )
    assert mi.mission_id == "M-1"
    assert len(client.calls) == 3
    retry = mi.metadata["raw_provider_response"]["retry"]
    assert retry["attempts"] == 3
    assert retry["final_status"] == "success"
    assert len(retry["errors"]) == 2


def test_extract_normalizes_unknown_tool_class_to_analysis():
    tools = [{"tool_id": "weird", "tool_class": "spreadsheet"}]
    mi = extract("TASK-4", "task",
                 client=MockLLMClient(default=extraction_json(available_tools=tools)))
    assert mi.available_tools[0].tool_class == "ANALYSIS"


def test_extract_rejects_empty_intent():
    with pytest.raises(ValueError, match="empty intent"):
        extract("TASK-5", "",
                client=MockLLMClient(default=extraction_json(intent="")))


def test_parse_response_text_accepts_fenced_json():
    parsed = _parse_response_text("```json\n{\"intent\":\"x\"}\n```")
    assert parsed == {"intent": "x"}


def test_valid_constraints_keeps_only_mlt_grammar():
    assert _valid_constraints(["FORBIDS data_exfiltration", "bad: value"]) == [
        "FORBIDS data_exfiltration"
    ]
