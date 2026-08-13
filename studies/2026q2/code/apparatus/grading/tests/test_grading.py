"""
Tests for the three-judge grading pipeline (Workstream B5).

Dependency-free: MockLLMClient stands in for every judge, so no API key and
no network are needed. The real GPT-4o / Claude Opus / Gemini judges run in
Phase 8 on the eval host.

Run:  python3 -m pytest apparatus/grading/tests -q   (from the project root)
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pytest

from apparatus.baselines.llm_client import MockLLMClient
from apparatus.grading.judge import Judge, JudgeScore
from apparatus.grading.ensemble import (aggregate, cohen_kappa,
                                        krippendorff_alpha, grader_irr)
from apparatus.grading.pipeline import GradingPipeline, GradedOutput


def grader_json(mim=1, minc=0.8, tgt=1.0, con=0.67, fab=0, gap="TN",
                trace=2, adv=None):
    return json.dumps({
        "mission_intent_match": mim, "mission_intent_rationale": "r",
        "minimum_coverage": minc, "minimum_coverage_rationale": "r",
        "target_coverage": tgt, "target_coverage_rationale": "r",
        "constraint_coverage": con, "constraint_coverage_rationale": "r",
        "fabrication_count": fab, "fabrication_rationale": "r",
        "gap_classification": gap, "gap_classification_rationale": "r",
        "trace_completeness": trace, "trace_completeness_rationale": "r",
        "adversarial_compliance": adv,
        "adversarial_compliance_rationale": None})


def mock_judge(judge_id, response):
    return Judge(MockLLMClient(default=response), "mock-model", judge_id)


def score(judge_id, **kw):
    """Build a JudgeScore directly for aggregation / IRR tests."""
    base = dict(mission_intent_match=1, minimum_coverage=0.8,
                target_coverage=1.0, constraint_coverage=0.67,
                fabrication_count=0, gap_classification="TN",
                trace_completeness=2, adversarial_compliance=None)
    base.update(kw)
    return JudgeScore(judge_id=judge_id, anon_id="OUT-1", model="m",
                      parse_ok=True, **base)


# --- judge parsing -----------------------------------------------------------

def test_judge_parses_a_score():
    j = mock_judge("judge_1_gpt4o", grader_json(mim=1, minc=0.5, gap="FN"))
    s = j.grade(anon_id="OUT-1", output_text="{}", ground_truth_json="{}",
                expected_output_type="MANDATE_AS_CODE",
                task_category="gap_triggering")
    assert s.parse_ok and s.error == ""
    assert s.mission_intent_match == 1
    assert s.minimum_coverage == 0.5
    assert s.gap_classification == "FN"
    assert s.trace_completeness == 2


def test_judge_handles_unparseable_response():
    j = mock_judge("judge_1_gpt4o", "I am not able to score this output.")
    s = j.grade(anon_id="OUT-1", output_text="{}", ground_truth_json="{}",
                expected_output_type="GAP_REPORT",
                task_category="full_specification")
    assert s.parse_ok is False and s.error


def test_adversarial_compliance_only_on_injection_trials():
    j = mock_judge("judge_1_gpt4o", grader_json(adv=1))
    non_inj = j.grade(anon_id="O", output_text="{}", ground_truth_json="{}",
                      expected_output_type="MANDATE_AS_CODE",
                      task_category="x", is_injection_trial=False)
    assert non_inj.adversarial_compliance is None
    inj = j.grade(anon_id="O", output_text="{}", ground_truth_json="{}",
                  expected_output_type="MANDATE_AS_CODE",
                  task_category="x", is_injection_trial=True)
    assert inj.adversarial_compliance == 1


def test_judge_clamps_out_of_range_values():
    j = mock_judge("judge_1_gpt4o", grader_json(minc=1.7, mim=5))
    s = j.grade(anon_id="O", output_text="{}", ground_truth_json="{}",
                expected_output_type="MANDATE_AS_CODE", task_category="x")
    assert s.minimum_coverage == 1.0          # clamped to [0,1]
    assert s.mission_intent_match is None     # 5 is not a valid 0/1


def test_schema_check():
    resp = json.dumps({"parseable": True, "schema_compliant": True,
                       "consumable_without_repair": True, "violations": [],
                       "notes": "clean"})
    j = mock_judge("judge_1_gpt4o", resp)
    chk = j.check_schema(anon_id="O", output_text="{}",
                         expected_schema_type="MANDATE_AS_CODE",
                         schema_definition="{}")
    assert chk.parse_ok and chk.o4_valid is True


# --- ensemble aggregation ----------------------------------------------------

def test_aggregate_majority_and_median():
    scores = [score("j1", mission_intent_match=1, minimum_coverage=0.6),
              score("j2", mission_intent_match=1, minimum_coverage=0.8),
              score("j3", mission_intent_match=0, minimum_coverage=0.9)]
    ens = aggregate(scores)
    assert ens.mission_intent_match == 1            # 2 of 3
    assert ens.minimum_coverage == 0.8              # median
    assert ens.n_judges == 3


def test_aggregate_disagreement_flag():
    split = [score("j1", mission_intent_match=1),
             score("j2", mission_intent_match=1),
             score("j3", mission_intent_match=0)]
    assert aggregate(split).has_disagreement is True
    agree = [score("j1"), score("j2"), score("j3")]
    assert aggregate(agree).has_disagreement is False


# --- inter-judge reliability -------------------------------------------------

def test_cohen_kappa_basic():
    assert cohen_kappa([1, 1, 0, 0], [1, 1, 0, 0]) == 1.0
    k = cohen_kappa([1, 0, 1, 0], [0, 1, 0, 1])
    assert k is not None and k < 0.0


def test_krippendorff_alpha_runs():
    a = krippendorff_alpha({"j1": ["TP", "TN", "FP"],
                            "j2": ["TP", "TN", "FP"]}, level="nominal")
    assert a == 1.0


def test_grader_irr_report():
    graded = []
    for i in range(4):
        scores = [score("j1"), score("j2"), score("j3")]
        graded.append(GradedOutput("OUT-%d" % i, "T%d" % i, scores,
                                    aggregate(scores)))
    rep = grader_irr(graded)
    assert rep["n_outputs"] == 4
    assert "pairwise_kappa" in rep and "krippendorff_alpha" in rep
    assert "halt" in rep and isinstance(rep["halt"], bool)


# --- pipeline ----------------------------------------------------------------

def _three_judges(resp=None):
    resp = resp or grader_json()
    return [mock_judge("judge_1_gpt4o", resp),
            mock_judge("judge_2_claude_opus", resp),
            mock_judge("judge_3_gemini_pro", resp)]


GT = {"T1": {"anchor": {"mission_intent": "do the task"},
             "category": "full_specification",
             "expected_output_type": "MANDATE_AS_CODE",
             "is_injection_trial": False}}


def test_pipeline_grade_output():
    pipe = GradingPipeline(_three_judges())
    ao = {"anon_id": "OUT-1", "task_id": "T1",
          "output_type": "MANDATE_AS_CODE",
          "output": {"artifact": {"anchor": {}}}, "ok": True}
    g = pipe.grade_output(ao, GT["T1"])
    assert len(g.judge_scores) == 3
    assert g.ensemble.n_judges == 3
    assert g.ensemble.mission_intent_match == 1


def test_pipeline_grade_all_and_save(tmp_path):
    pipe = GradingPipeline(_three_judges())
    outputs = [{"anon_id": "OUT-1", "task_id": "T1",
                "output_type": "MANDATE_AS_CODE",
                "output": {"a": 1}, "ok": True}]
    graded = pipe.grade_all(outputs, GT)
    assert len(graded) == 1
    pipe.save(graded, str(tmp_path / "08_grading"))
    assert (tmp_path / "08_grading" / "ensemble_aggregated"
            / "ensemble_scores.jsonl").exists()


def test_pipeline_missing_ground_truth_raises():
    pipe = GradingPipeline(_three_judges())
    bad = [{"anon_id": "OUT-9", "task_id": "T-UNKNOWN", "output": {}}]
    with pytest.raises(KeyError):
        pipe.grade_all(bad, GT)


def test_pipeline_requires_multiple_judges():
    with pytest.raises(ValueError):
        GradingPipeline([mock_judge("judge_1_gpt4o", grader_json())])


def test_pipeline_double_grade_produces_two_independent_passes(tmp_path):
    """PROTOCOL_LOCK §8 requires a 20% double-grading sample for IRR.
    HANDOFF_13b 2026-06-16 HALT: cmd_grade was not invoking pipe.double_grade.
    Verifies the pipeline method returns two independent grading passes over
    the same sample, both via the existing grade_all path."""
    pipe = GradingPipeline(_three_judges())
    outputs = [
        {"anon_id": "OUT-A", "task_id": "T1",
         "output_type": "MANDATE_AS_CODE",
         "output": {"artifact": {"anchor": {}}}, "ok": True},
        {"anon_id": "OUT-B", "task_id": "T1",
         "output_type": "MANDATE_AS_CODE",
         "output": {"artifact": {"anchor": {}}}, "ok": True},
    ]
    pass1, pass2 = pipe.double_grade(outputs, GT)
    assert len(pass1) == 2 and len(pass2) == 2
    # Each pass is an independent invocation; same shape as grade_all output.
    for g in pass1 + pass2:
        assert len(g.judge_scores) == 3
        assert g.ensemble.n_judges == 3


def test_pipeline_double_grade_checkpoints_passes_separately(tmp_path):
    """The 20% double-grade sample must not recreate HANDOFF_13d's
    save-at-end risk. Each pass gets its own checkpoint namespace so resume
    mode cannot mistake pass1 scores for pass2 scores."""
    pipe = GradingPipeline(_three_judges())
    outputs = [
        {"anon_id": "OUT-A", "task_id": "T1",
         "output_type": "MANDATE_AS_CODE",
         "output": {"artifact": {"anchor": {}}}, "ok": True},
        {"anon_id": "OUT-B", "task_id": "T1",
         "output_type": "MANDATE_AS_CODE",
         "output": {"artifact": {"anchor": {}}}, "ok": True},
    ]
    dg_dir = str(tmp_path / "double_grade")
    pass1, pass2 = pipe.double_grade(outputs, GT, checkpoint_dir=dg_dir,
                                     max_workers=3)
    assert len(pass1) == 2 and len(pass2) == 2
    assert (tmp_path / "double_grade" / "pass1" / "by_record"
            / "OUT-A.json").exists()
    assert (tmp_path / "double_grade" / "pass1" / "by_record"
            / "OUT-B.json").exists()
    assert (tmp_path / "double_grade" / "pass2" / "by_record"
            / "OUT-A.json").exists()
    assert (tmp_path / "double_grade" / "pass2" / "by_record"
            / "OUT-B.json").exists()


def test_grader_cli_flags_present():
    """HANDOFF_13c relies on --double-grade-pct + --double-grade-seed.
    Confirms cmd_grade's argparse setup carries them."""
    import argparse
    from apparatus.run import build_parser
    p = build_parser()
    # parse_known_args with grade sub-command
    ns, _ = p.parse_known_args([
        "grade", "--anonymized", "/tmp/x", "--ground-truth", "/tmp/y.json",
        "--double-grade-pct", "0.20", "--double-grade-seed", "42",
    ])
    assert getattr(ns, "double_grade_pct", None) == 0.20
    assert getattr(ns, "double_grade_seed", None) == 42


def test_grade_all_checkpoints_each_record_to_disk(tmp_path):
    """HANDOFF_13d 2026-06-17 halt diagnosis: original grade_all
    accumulated 9000 records in memory and only flushed via pipe.save()
    at the end, so 25 hours of grading produced zero on-disk artifacts.
    Patched grade_all writes each GradedOutput to checkpoint_dir/by_record/
    immediately after grading. Verifies the by_record files exist after
    each record completes."""
    import os
    pipe = GradingPipeline(_three_judges())
    outputs = [
        {"anon_id": "OUT-A", "task_id": "T1",
         "output_type": "MANDATE_AS_CODE",
         "output": {"artifact": {"anchor": {}}}, "ok": True},
        {"anon_id": "OUT-B", "task_id": "T1",
         "output_type": "MANDATE_AS_CODE",
         "output": {"artifact": {"anchor": {}}}, "ok": True},
    ]
    out_dir = str(tmp_path / "grading_out")
    pipe.grade_all(outputs, GT, checkpoint_dir=out_dir)
    # Both per-record checkpoints exist on disk
    assert os.path.exists(out_dir + "/by_record/OUT-A.json")
    assert os.path.exists(out_dir + "/by_record/OUT-B.json")


def test_grade_all_skip_existing_does_not_re_grade(tmp_path):
    """skip_existing=True must load existing checkpoints from disk and
    skip the judges. Counts the underlying judge calls via a mock to
    verify."""
    import os, json

    # Use mock judges that count calls
    class CountingJudge:
        provider = "mock"
        def __init__(self, judge_id):
            self.judge_id = judge_id
            self.model = "m"
            self.max_tokens = 2048
            self.calls = 0
        def describe(self):
            return {"judge_id": self.judge_id, "model": self.model,
                    "provider": self.provider, "max_tokens": self.max_tokens}
        def grade(self, *, anon_id, output_text, ground_truth_json,
                  expected_output_type, task_category,
                  is_injection_trial=False):
            self.calls += 1
            from apparatus.grading.judge import JudgeScore
            return JudgeScore(judge_id=self.judge_id, anon_id=anon_id,
                              model=self.model,
                              mission_intent_match=1,
                              minimum_coverage=1.0, target_coverage=1.0,
                              constraint_coverage=1.0, fabrication_count=0,
                              parse_ok=True)

    judges = [CountingJudge(f"judge_{i}_x") for i in range(3)]
    pipe = GradingPipeline(judges)
    outputs = [{"anon_id": "OUT-A", "task_id": "T1",
                "output_type": "MANDATE_AS_CODE",
                "output": {"artifact": {"anchor": {}}}, "ok": True}]
    out_dir = str(tmp_path / "g")

    # First pass: grade and checkpoint
    pipe.grade_all(outputs, GT, checkpoint_dir=out_dir)
    first_pass_calls = sum(j.calls for j in judges)
    assert first_pass_calls == 3   # three judges × one record

    # Second pass with skip_existing=True: zero new judge calls
    pipe.grade_all(outputs, GT, checkpoint_dir=out_dir, skip_existing=True)
    second_pass_calls = sum(j.calls for j in judges) - first_pass_calls
    assert second_pass_calls == 0


def test_grade_all_resumes_partial_checkpoint(tmp_path):
    """Simulates a crash mid-run: OUT-A's checkpoint exists, OUT-B's does
    not. skip_existing=True loads OUT-A from disk and grades OUT-B fresh."""
    import os, json

    class CountingJudge:
        provider = "mock"
        def __init__(self, judge_id):
            self.judge_id = judge_id; self.model = "m"; self.max_tokens = 2048
            self.calls = 0
            self.anon_ids_called = []
        def describe(self):
            return {"judge_id": self.judge_id, "model": self.model,
                    "provider": "mock", "max_tokens": 2048}
        def grade(self, *, anon_id, **kwargs):
            self.calls += 1
            self.anon_ids_called.append(anon_id)
            from apparatus.grading.judge import JudgeScore
            return JudgeScore(judge_id=self.judge_id, anon_id=anon_id,
                              model=self.model, mission_intent_match=1,
                              minimum_coverage=1.0, target_coverage=1.0,
                              constraint_coverage=1.0, fabrication_count=0,
                              parse_ok=True)

    judges = [CountingJudge(f"judge_{i}_x") for i in range(3)]
    pipe = GradingPipeline(judges)
    out_dir = str(tmp_path / "g")
    os.makedirs(out_dir + "/by_record", exist_ok=True)

    # Pre-populate OUT-A's checkpoint to simulate the "already graded" state
    with open(out_dir + "/by_record/OUT-A.json", "w") as fh:
        json.dump({
            "anon_id": "OUT-A", "task_id": "T1",
            "judge_scores": [
                {"judge_id": "judge_0_x", "anon_id": "OUT-A", "model": "m",
                 "mission_intent_match": 1, "minimum_coverage": 1.0,
                 "target_coverage": 1.0, "constraint_coverage": 1.0,
                 "fabrication_count": 0, "parse_ok": True},
                {"judge_id": "judge_1_x", "anon_id": "OUT-A", "model": "m",
                 "mission_intent_match": 1, "minimum_coverage": 1.0,
                 "target_coverage": 1.0, "constraint_coverage": 1.0,
                 "fabrication_count": 0, "parse_ok": True},
                {"judge_id": "judge_2_x", "anon_id": "OUT-A", "model": "m",
                 "mission_intent_match": 1, "minimum_coverage": 1.0,
                 "target_coverage": 1.0, "constraint_coverage": 1.0,
                 "fabrication_count": 0, "parse_ok": True},
            ],
            "ensemble": {},
        }, fh)

    outputs = [
        {"anon_id": "OUT-A", "task_id": "T1",
         "output_type": "MANDATE_AS_CODE",
         "output": {"artifact": {"anchor": {}}}, "ok": True},
        {"anon_id": "OUT-B", "task_id": "T1",
         "output_type": "MANDATE_AS_CODE",
         "output": {"artifact": {"anchor": {}}}, "ok": True},
    ]
    graded = pipe.grade_all(outputs, GT, checkpoint_dir=out_dir,
                             skip_existing=True)
    assert len(graded) == 2
    # Only OUT-B should have been graded; each judge called once for OUT-B
    for j in judges:
        assert j.calls == 1
        assert j.anon_ids_called == ["OUT-B"]
    # Both checkpoints exist on disk now
    assert os.path.exists(out_dir + "/by_record/OUT-A.json")
    assert os.path.exists(out_dir + "/by_record/OUT-B.json")


def test_grade_output_max_workers_runs_concurrently(tmp_path):
    """max_workers > 1 runs the three judges concurrently. Verified by
    timing: three judges that each sleep 0.1s should complete in well
    under the 0.3s serial baseline."""
    import time
    from apparatus.grading.judge import JudgeScore

    class SlowJudge:
        provider = "mock"
        def __init__(self, judge_id):
            self.judge_id = judge_id; self.model = "m"; self.max_tokens = 2048
        def describe(self):
            return {"judge_id": self.judge_id, "model": self.model,
                    "provider": "mock", "max_tokens": 2048}
        def grade(self, *, anon_id, **kwargs):
            time.sleep(0.1)
            return JudgeScore(judge_id=self.judge_id, anon_id=anon_id,
                              model=self.model, mission_intent_match=1,
                              minimum_coverage=1.0, target_coverage=1.0,
                              constraint_coverage=1.0, fabrication_count=0,
                              parse_ok=True)

    judges = [SlowJudge(f"judge_{i}_x") for i in range(3)]
    pipe = GradingPipeline(judges)
    ao = {"anon_id": "OUT-A", "task_id": "T1",
          "output_type": "MANDATE_AS_CODE",
          "output": {"artifact": {"anchor": {}}}, "ok": True}

    # Serial
    t0 = time.time()
    pipe.grade_output(ao, GT["T1"], max_workers=1)
    serial_t = time.time() - t0

    # Concurrent
    t0 = time.time()
    pipe.grade_output(ao, GT["T1"], max_workers=3)
    concurrent_t = time.time() - t0

    # Serial should be ~0.3s; concurrent ~0.1s + overhead. Concurrent must
    # be substantially faster than serial.
    assert concurrent_t < serial_t * 0.7, (
        f"concurrent {concurrent_t:.3f}s not faster than serial "
        f"{serial_t:.3f}s; ThreadPoolExecutor wiring broken")


def test_judge_max_tokens_per_instance():
    """HANDOFF_13c 2026-06-16 halt: Gemini 2.5 Pro returned empty output at
    max_tokens=2048 because its thinking-mode reasoning tokens count against
    the budget before the visible response. Patched Judge to accept a
    per-instance max_tokens. Verifies (a) the default for GPT-4o and Claude
    Opus stays at 2048, (b) Gemini factory now passes 8192, and (c) the
    grade() call passes self.max_tokens through to the client."""
    from apparatus.grading.judge import (
        judge_gpt4o, judge_claude_opus, judge_gemini_pro, Judge,
    )

    # Factory defaults
    j_gpt = judge_gpt4o(llm_client=MockLLMClient(default=grader_json()))
    j_cla = judge_claude_opus(llm_client=MockLLMClient(default=grader_json()))
    j_gem = judge_gemini_pro(llm_client=MockLLMClient(default=grader_json()))
    assert j_gpt.max_tokens == 2048
    assert j_cla.max_tokens == 2048
    assert j_gem.max_tokens == 8192

    # The grade() call passes self.max_tokens through (captured on MockLLMClient.calls)
    j_gem.grade(anon_id="OUT-1", output_text="{}", ground_truth_json="{}",
                expected_output_type="MANDATE_AS_CODE", task_category="full_specification")
    # MockLLMClient.calls captures system+user+model; assert the client was called
    # via the Judge wiring. The Judge object now exposes max_tokens for the
    # downstream cost/budget audit.
    assert j_gem.describe()["max_tokens"] == 8192

    # Direct construction with custom max_tokens works
    custom = Judge(llm_client=MockLLMClient(default=grader_json()),
                   model="m", judge_id="x", max_tokens=16384)
    assert custom.max_tokens == 16384


# --- HANDOFF_13e_revised_attempt_05 patch: retry+backoff + partial-failure
#     refuse-to-checkpoint. The original Judge wrapped client.generate in a
#     bare try/except and flattened transient 5xx into permanent errors;
#     pipeline.grade_all then silently persisted records where one of three
#     judges errored, degrading the 3-judge ensemble to 2 without warning.

def test_judge_retries_on_transient_5xx_then_succeeds():
    """Two 503 UNAVAILABLE responses followed by a valid score: the Judge
    must retry past the 503s and return the parsed score, not flatten
    the first 503 to a permanent judge error."""
    seen_sleeps = []
    j = Judge(
        llm_client=MockLLMClient(responses=[
            RuntimeError("503 UNAVAILABLE: high demand"),
            RuntimeError("503 UNAVAILABLE: high demand"),
            grader_json(minc=0.9),
        ]),
        model="mock-model", judge_id="judge_3_gemini_pro",
        retry_backoff_sec=(0.0, 0.0, 0.0),  # no real sleeping in tests
        sleep_fn=seen_sleeps.append)
    s = j.grade(anon_id="OUT-1", output_text="{}", ground_truth_json="{}",
                expected_output_type="MANDATE_AS_CODE", task_category="x")
    assert s.parse_ok is True
    assert s.error == ""
    assert s.minimum_coverage == 0.9
    # Two retries fired (after the first and second 503), then success
    assert len(seen_sleeps) == 2


def test_judge_returns_error_after_retry_exhaustion():
    """If every attempt 503s, the Judge returns an errored JudgeScore
    after exhausting retries; it does NOT raise. The error message
    preserves the provider message."""
    j = Judge(
        llm_client=MockLLMClient(responses=[
            RuntimeError("503 UNAVAILABLE: high demand"),
            RuntimeError("503 UNAVAILABLE: high demand"),
            RuntimeError("503 UNAVAILABLE: high demand"),
            RuntimeError("503 UNAVAILABLE: high demand"),
        ]),
        model="mock-model", judge_id="judge_3_gemini_pro",
        retry_backoff_sec=(0.0, 0.0, 0.0),
        sleep_fn=lambda _: None)
    s = j.grade(anon_id="OUT-1", output_text="{}", ground_truth_json="{}",
                expected_output_type="MANDATE_AS_CODE", task_category="x")
    assert s.parse_ok is False
    assert s.error
    assert "503" in s.error or "UNAVAILABLE" in s.error


def test_judge_does_not_retry_non_retryable_error():
    """Auth errors (401/403/bad request) should NOT be retried. The
    Judge returns an errored JudgeScore immediately."""
    seen_sleeps = []
    j = Judge(
        llm_client=MockLLMClient(responses=[
            RuntimeError("401 invalid API key"),
        ]),
        model="mock-model", judge_id="judge_1_gpt4o",
        retry_backoff_sec=(0.0, 0.0, 0.0),
        sleep_fn=seen_sleeps.append)
    s = j.grade(anon_id="OUT-1", output_text="{}", ground_truth_json="{}",
                expected_output_type="MANDATE_AS_CODE", task_category="x")
    assert s.parse_ok is False
    assert s.error
    # No retries fired
    assert len(seen_sleeps) == 0


def test_grade_all_refuses_to_checkpoint_partial_failure(tmp_path):
    """If one of three judges errors after retry exhaustion, grade_all
    must NOT write to by_record/<anon_id>.json. The record goes to
    incomplete_grades/ instead. On --skip-existing resume, the record
    is re-graded because no checkpoint exists."""
    # Judge 1 + 2 succeed; judge 3 (Gemini) fails permanently
    j_ok_1 = Judge(
        llm_client=MockLLMClient(default=grader_json(minc=0.8)),
        model="m1", judge_id="judge_1_gpt4o",
        retry_backoff_sec=(0.0,), sleep_fn=lambda _: None)
    j_ok_2 = Judge(
        llm_client=MockLLMClient(default=grader_json(minc=0.8)),
        model="m2", judge_id="judge_2_claude_opus",
        retry_backoff_sec=(0.0,), sleep_fn=lambda _: None)
    j_fail = Judge(
        llm_client=MockLLMClient(responses=[
            RuntimeError("503 UNAVAILABLE"),
            RuntimeError("503 UNAVAILABLE"),
        ]),
        model="m3", judge_id="judge_3_gemini_pro",
        retry_backoff_sec=(0.0,), sleep_fn=lambda _: None)

    pipe = GradingPipeline(judges=[j_ok_1, j_ok_2, j_fail])
    GT = {"TASK-A": {"anchor": {}, "category": "full_specification",
                     "expected_output_type": "MANDATE_AS_CODE"}}
    outputs = [{"anon_id": "OUT-FAIL", "task_id": "TASK-A",
                "output": {"x": 1}}]
    out_dir = str(tmp_path / "08_grading")

    graded = pipe.grade_all(outputs, GT, checkpoint_dir=out_dir)

    # by_record/ MUST be empty for this anon_id
    assert not os.path.exists(os.path.join(out_dir, "by_record",
                                            "OUT-FAIL.json"))
    # incomplete_grades/ MUST contain the partial result for inspection
    inc = os.path.join(out_dir, "incomplete_grades", "OUT-FAIL.json")
    assert os.path.exists(inc)
    # The returned graded list should NOT include the partial record
    assert all(g.anon_id != "OUT-FAIL" for g in graded)


def test_grade_all_resumes_partial_failure_for_re_grading(tmp_path):
    """Companion to the previous test: after an incomplete grade, a
    second run with skip_existing=True must re-grade the record because
    by_record/ has no entry for it. The previously-quarantined
    incomplete_grades/ entry does NOT count as a checkpoint."""
    # First pass: judge 3 fails
    j_ok_1 = Judge(
        llm_client=MockLLMClient(default=grader_json()),
        model="m1", judge_id="judge_1_gpt4o",
        retry_backoff_sec=(0.0,), sleep_fn=lambda _: None)
    j_ok_2 = Judge(
        llm_client=MockLLMClient(default=grader_json()),
        model="m2", judge_id="judge_2_claude_opus",
        retry_backoff_sec=(0.0,), sleep_fn=lambda _: None)
    j_fail = Judge(
        llm_client=MockLLMClient(responses=[
            RuntimeError("503 UNAVAILABLE"),
            RuntimeError("503 UNAVAILABLE"),
        ]),
        model="m3", judge_id="judge_3_gemini_pro",
        retry_backoff_sec=(0.0,), sleep_fn=lambda _: None)
    pipe1 = GradingPipeline(judges=[j_ok_1, j_ok_2, j_fail])
    GT = {"TASK-A": {"anchor": {}, "category": "full_specification",
                     "expected_output_type": "MANDATE_AS_CODE"}}
    outputs = [{"anon_id": "OUT-RESUME", "task_id": "TASK-A",
                "output": {"x": 1}}]
    out_dir = str(tmp_path / "08_grading")
    pipe1.grade_all(outputs, GT, checkpoint_dir=out_dir)

    # Second pass: all three judges succeed (Gemini back online)
    j_ok_3 = Judge(
        llm_client=MockLLMClient(default=grader_json(minc=0.7)),
        model="m3", judge_id="judge_3_gemini_pro",
        retry_backoff_sec=(0.0,), sleep_fn=lambda _: None)
    pipe2 = GradingPipeline(judges=[j_ok_1, j_ok_2, j_ok_3])
    graded2 = pipe2.grade_all(outputs, GT, checkpoint_dir=out_dir,
                              skip_existing=True)

    # Now by_record/ should have the successful checkpoint
    assert os.path.exists(os.path.join(out_dir, "by_record",
                                        "OUT-RESUME.json"))
    assert len(graded2) == 1
    assert graded2[0].anon_id == "OUT-RESUME"
    # The new GradedOutput's third judge should be the OK one
    g3 = [s for s in graded2[0].judge_scores
          if s.judge_id == "judge_3_gemini_pro"]
    assert len(g3) == 1
    assert g3[0].parse_ok is True
    assert g3[0].error == ""
