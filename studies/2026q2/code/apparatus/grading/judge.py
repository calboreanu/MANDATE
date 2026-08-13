"""
Judges for the three-judge ensemble (Workstream B5).

A Judge wraps one LLM (from one model family) and applies the PROMPTS.md
Section 4 rubric to an anonymized output, and the Section 4a check for schema
validity. PLAYBOOK Section 8 fixes the three families: GPT-4o (OpenAI),
Claude Opus 4 (Anthropic), Gemini 2.5 Pro (Google). None is the Qwen3 family
used inside MANDATE.

Exact judge model versions are pinned at the deposit (TO_FILL_TRACKER D9).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional, Sequence

from ..baselines.base import extract_json
from ..baselines.llm_client import (AnthropicClient, OpenAIClient,
                                    GeminiClient)
from ..llm_retry import (
    DEFAULT_RETRY_BACKOFF_SEC as _DEFAULT_RETRY_BACKOFF_SEC,
    call_with_retry as _call_with_retry_shared,
    is_retryable_error as _is_retryable_error,
)
from .rubric import (GRADER_SYSTEM, RATIONALE_KEYS, render_grader_prompt,
                     render_schema_check_prompt)

GAP_CLASSES = ("TP", "TN", "FP", "FN", "NA")

__all__ = [
    "Judge",
    "JudgeScore",
    "SchemaCheck",
    "judge_gpt4o",
    "judge_claude_opus",
    "judge_gemini_pro",
    "_is_retryable_error",
    "_DEFAULT_RETRY_BACKOFF_SEC",
]


def _as_binary(v):
    try:
        i = int(v)
    except (TypeError, ValueError):
        return None
    return i if i in (0, 1) else None


def _as_unit(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return min(1.0, max(0.0, f))


def _as_count(v):
    try:
        i = int(v)
    except (TypeError, ValueError):
        return None
    return max(0, i)


def _as_trace(v):
    try:
        i = int(v)
    except (TypeError, ValueError):
        return None
    return i if i in (0, 1, 2) else None


@dataclass
class JudgeScore:
    """One judge's rubric scoring of one anonymized output."""
    judge_id: str
    anon_id: str
    model: str
    mission_intent_match: Optional[int] = None     # 0 / 1
    minimum_coverage: Optional[float] = None        # 0.0 - 1.0
    target_coverage: Optional[float] = None         # 0.0 - 1.0
    constraint_coverage: Optional[float] = None     # 0.0 - 1.0
    fabrication_count: Optional[int] = None         # >= 0
    gap_classification: Optional[str] = None        # TP/TN/FP/FN/NA
    trace_completeness: Optional[int] = None        # 0 / 1 / 2
    adversarial_compliance: Optional[int] = None    # 0 / 1 / None
    rationales: dict = field(default_factory=dict)
    parse_ok: bool = False
    error: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: Optional[float] = None
    raw_text: str = ""

    def to_dict(self) -> dict:
        return {
            "judge_id": self.judge_id, "anon_id": self.anon_id,
            "model": self.model,
            "mission_intent_match": self.mission_intent_match,
            "minimum_coverage": self.minimum_coverage,
            "target_coverage": self.target_coverage,
            "constraint_coverage": self.constraint_coverage,
            "fabrication_count": self.fabrication_count,
            "gap_classification": self.gap_classification,
            "trace_completeness": self.trace_completeness,
            "adversarial_compliance": self.adversarial_compliance,
            "rationales": self.rationales,
            "parse_ok": self.parse_ok, "error": self.error,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens, "cost_usd": self.cost_usd,
        }


@dataclass
class SchemaCheck:
    """One judge's Section 4a schema-validity check of one output."""
    judge_id: str
    anon_id: str
    parseable: Optional[bool] = None
    schema_compliant: Optional[bool] = None
    consumable_without_repair: Optional[bool] = None
    violations: list = field(default_factory=list)
    notes: str = ""
    parse_ok: bool = False
    error: str = ""

    @property
    def o4_valid(self) -> bool:
        """O4 = 1 only if all three checks are true (PROMPTS.md 4a)."""
        return bool(self.parseable and self.schema_compliant
                    and self.consumable_without_repair)


class Judge:
    def __init__(self, llm_client, model: str, judge_id: str,
                 max_tokens: int = 2048,
                 retry_backoff_sec: Sequence[float] = _DEFAULT_RETRY_BACKOFF_SEC,
                 sleep_fn=time.sleep,
                 grader_system: str = GRADER_SYSTEM,
                 render_grader_prompt_fn=render_grader_prompt,
                 render_schema_check_prompt_fn=render_schema_check_prompt):
        # max_tokens default 2048 covers GPT-4o and Claude Opus comfortably.
        # Gemini 2.5 Pro burns budget on thinking-mode tokens BEFORE emitting
        # visible output, so its factory passes 8192 to leave room for both
        # the reasoning trace and the structured score JSON. (HANDOFF_13c
        # 2026-06-16 halt: Gemini returned empty model output at 2048 because
        # the thinking-mode chain consumed the full budget; Codex verified
        # 4096 produced valid JSON; 8192 is the safety margin.)
        #
        # retry_backoff_sec is the sleep schedule for retryable provider
        # errors (5xx, 429, timeouts). The retry layer was added after the
        # HANDOFF_13e_revised_attempt_05 2026-06-18 halt where Gemini
        # high-demand 503s flattened to permanent errors with no retry.
        # Tests can pass (0, 0, 0) to skip real sleeps.
        self.client = llm_client
        self.model = model
        self.judge_id = judge_id
        self.max_tokens = max_tokens
        self.retry_backoff_sec = tuple(retry_backoff_sec)
        self._sleep = sleep_fn
        self.grader_system = grader_system
        self._render_grader_prompt = render_grader_prompt_fn
        self._render_schema_check_prompt = render_schema_check_prompt_fn

    def describe(self) -> dict:
        return {"judge_id": self.judge_id, "model": self.model,
                "provider": getattr(self.client, "provider", ""),
                "max_tokens": self.max_tokens,
                "retry_backoff_sec": list(self.retry_backoff_sec)}

    def _call_with_retry(self, *, system: str, user: str,
                         max_tokens: int):
        """Wrap client.generate() with retry+backoff on transient errors."""
        return _call_with_retry_shared(
            self.client.generate,
            system=system,
            user=user,
            model=self.model,
            temperature=0.0,
            max_tokens=max_tokens,
            retry_backoff_sec=self.retry_backoff_sec,
            sleep_fn=self._sleep,
        )

    def grade(self, *, anon_id: str, output_text: str,
              ground_truth_json: str, expected_output_type: str,
              task_category: str,
              is_injection_trial: bool = False) -> JudgeScore:
        prompt = self._render_grader_prompt(
            ground_truth_json=ground_truth_json,
            anonymized_output=output_text,
            expected_output_type=expected_output_type,
            task_category=task_category)
        score = JudgeScore(judge_id=self.judge_id, anon_id=anon_id,
                           model=self.model)
        try:
            resp = self._call_with_retry(system=self.grader_system, user=prompt,
                                         max_tokens=self.max_tokens)
        except Exception as e:
            score.error = "judge LLM error: %r" % e
            return score
        score.raw_text = resp.text
        score.input_tokens = resp.input_tokens
        score.output_tokens = resp.output_tokens
        score.cost_usd = resp.cost_usd

        parsed, perr = extract_json(resp.text)
        if parsed is None:
            score.error = perr or "no JSON in judge response"
            return score

        score.mission_intent_match = _as_binary(
            parsed.get("mission_intent_match"))
        score.minimum_coverage = _as_unit(parsed.get("minimum_coverage"))
        score.target_coverage = _as_unit(parsed.get("target_coverage"))
        score.constraint_coverage = _as_unit(parsed.get("constraint_coverage"))
        score.fabrication_count = _as_count(parsed.get("fabrication_count"))
        gc = parsed.get("gap_classification")
        score.gap_classification = gc if gc in GAP_CLASSES else None
        score.trace_completeness = _as_trace(parsed.get("trace_completeness"))
        # adversarial_compliance applies only to prompt-injection trials
        score.adversarial_compliance = (
            _as_binary(parsed.get("adversarial_compliance"))
            if is_injection_trial else None)
        score.rationales = {k: parsed.get(k) for k in RATIONALE_KEYS
                            if parsed.get(k) is not None}
        score.parse_ok = True
        return score

    def check_schema(self, *, anon_id: str, output_text: str,
                     expected_schema_type: str,
                     schema_definition: str) -> SchemaCheck:
        prompt = self._render_schema_check_prompt(
            expected_schema_type=expected_schema_type,
            schema_definition=schema_definition,
            anonymized_output=output_text)
        check = SchemaCheck(judge_id=self.judge_id, anon_id=anon_id)
        try:
            resp = self._call_with_retry(system=self.grader_system, user=prompt,
                                         max_tokens=1024)
        except Exception as e:
            check.error = "judge LLM error: %r" % e
            return check
        parsed, perr = extract_json(resp.text)
        if parsed is None:
            check.error = perr or "no JSON in judge response"
            return check
        check.parseable = parsed.get("parseable")
        check.schema_compliant = parsed.get("schema_compliant")
        check.consumable_without_repair = parsed.get(
            "consumable_without_repair")
        check.violations = list(parsed.get("violations", []) or [])
        check.notes = str(parsed.get("notes", ""))
        check.parse_ok = True
        return check


# Default judge model versions are placeholders, pinned at deposit (D9).
def judge_gpt4o(model: str = "gpt-4o", api_key=None, llm_client=None,
                **kwargs) -> Judge:
    return Judge(llm_client or OpenAIClient(api_key), model, "judge_1_gpt4o",
                 **kwargs)


def judge_claude_opus(model: str = "claude-opus-4-6", api_key=None,
                      llm_client=None, **kwargs) -> Judge:
    return Judge(llm_client or AnthropicClient(api_key), model,
                 "judge_2_claude_opus", **kwargs)


def judge_gemini_pro(model: str = "gemini-2.5-pro", api_key=None,
                     llm_client=None, **kwargs) -> Judge:
    # max_tokens=8192 not 2048: Gemini 2.5 Pro's thinking-mode reasoning
    # tokens count against the output budget BEFORE the visible response,
    # and 2048 was insufficient (HANDOFF_13c 2026-06-16 halt). 4096 worked
    # in the diagnostic; 8192 is the safety margin against tasks with
    # longer reasoning chains.
    return Judge(llm_client or GeminiClient(api_key), model,
                 "judge_3_gemini_pro", max_tokens=8192, **kwargs)
