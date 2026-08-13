import json

from apparatus.baselines.llm_client import MockLLMClient
from apparatus.grading.judge import Judge
from apparatus.grading.rubric_v2 import (
    GRADER_PROMPT_V2,
    GRADER_SYSTEM_V2,
    render_grader_prompt_v2,
    render_schema_check_prompt,
)


def test_rubric_v2_names_free_form_object_shape():
    assert "FREE-FORM OBJECTS" in GRADER_SYSTEM_V2
    assert "not structural shape match" in GRADER_SYSTEM_V2


def test_rubric_v2_prompt_mentions_semantic_coverage():
    assert "SEMANTIC coverage" in GRADER_PROMPT_V2
    assert "description" in GRADER_PROMPT_V2


def test_render_grader_prompt_v2_substitutes_placeholders():
    prompt = render_grader_prompt_v2(
        ground_truth_json='{"anchor": true}',
        anonymized_output='{"output": true}',
        expected_output_type="MANDATE_AS_CODE",
        task_category="full_specification",
    )
    assert '{"anchor": true}' in prompt
    assert '{"output": true}' in prompt
    assert "MANDATE_AS_CODE" in prompt
    assert "full_specification" in prompt
    assert "{GROUND_TRUTH_JSON}" not in prompt


def test_v2_judge_can_use_v2_prompt_renderer():
    response = json.dumps({
        "mission_intent_match": 1,
        "mission_intent_rationale": "r",
        "minimum_coverage": 1.0,
        "minimum_coverage_rationale": "free-form object semantically covers it",
        "target_coverage": 0.5,
        "target_coverage_rationale": "r",
        "constraint_coverage": 0.0,
        "constraint_coverage_rationale": "r",
        "fabrication_count": 0,
        "fabrication_rationale": "r",
        "gap_classification": "TN",
        "gap_classification_rationale": "r",
        "trace_completeness": 2,
        "trace_completeness_rationale": "r",
        "adversarial_compliance": None,
        "adversarial_compliance_rationale": None,
    })
    client = MockLLMClient(default=response)
    judge = Judge(
        client,
        "mock",
        "judge_v2",
        grader_system=GRADER_SYSTEM_V2,
        render_grader_prompt_fn=render_grader_prompt_v2,
        render_schema_check_prompt_fn=render_schema_check_prompt,
    )
    score = judge.grade(
        anon_id="OUT-1",
        output_text='{"anchor":{"minimum":{"description":"x"}}}',
        ground_truth_json='{"minimum":[{"dimension":"x"}]}',
        expected_output_type="MANDATE_AS_CODE",
        task_category="full_specification",
    )
    assert score.parse_ok is True
    assert score.minimum_coverage == 1.0
    assert "FREE-FORM OBJECTS" in client.calls[0]["system"]
    assert "free-form object" in client.calls[0]["user"]


def test_schema_check_renderer_reused_from_v1_contract():
    prompt = render_schema_check_prompt(
        expected_schema_type="MANDATE_AS_CODE",
        schema_definition="{}",
        anonymized_output="{}",
    )
    assert "PARSEABLE" in prompt
    assert "MANDATE_AS_CODE" in prompt


def test_grade_v2_cli_flags_present():
    from apparatus.run import build_parser
    p = build_parser()
    ns = p.parse_args([
        "grade-v2",
        "--anonymized", "08_grading/anonymized_outputs",
        "--filter-system-id", "mandate_primary",
        "--sample-size", "100",
        "--ground-truth", "04_ground_truth/ground_truth.json",
        "--rubric", "v2",
        "--full-coverage",
        "--double-grade-pct", "0.10",
    ])
    assert ns.cmd == "grade-v2"
    assert ns.filter_system_id == "mandate_primary"
    assert ns.sample_size == 100
    assert ns.rubric == "v2"
    assert ns.full_coverage is True
    assert ns.double_grade_pct == 0.10
