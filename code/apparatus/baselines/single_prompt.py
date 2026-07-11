"""
B1 and B2: single-prompt planner baselines (Workstream B2).

One LLM call: the request goes in, the specification JSON comes out. B1 runs
on a Claude model, B2 on a GPT model. Per PROTOCOL_LOCK Section 2.2 these are
the "LLM only" baselines and have no tools by design.
"""
from __future__ import annotations

import time

from .base import BaselineSystem, ProduceResult, Step
from .llm_client import AnthropicClient, OpenAIClient
from .prompts import SPECIFICATION_INSTRUCTIONS

# Placeholder default models. The exact version strings are pinned at the
# pre-registration deposit (TO_FILL_TRACKER row D7).
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-6"
DEFAULT_GPT_MODEL = "gpt-4o"


class SinglePromptBaseline(BaselineSystem):
    """One system prompt, one user message, one completion."""

    def _produce(self, request_text: str) -> ProduceResult:
        t0 = time.time()
        resp = self.client.generate(
            system=SPECIFICATION_INSTRUCTIONS, user=request_text,
            model=self.model, temperature=0.0, max_tokens=4096)
        dur = (time.time() - t0) * 1000.0
        step = Step(name="generate", duration_ms=dur,
                    input_tokens=resp.input_tokens,
                    output_tokens=resp.output_tokens,
                    cost_usd=resp.cost_usd)
        return ProduceResult(text=resp.text, steps=[step])


def baseline_b1(model: str = DEFAULT_CLAUDE_MODEL, api_key=None,
                llm_client=None) -> SinglePromptBaseline:
    """B1: single-prompt planner on Claude."""
    client = llm_client or AnthropicClient(api_key)
    return SinglePromptBaseline(client, model, "baseline_1",
                                "B1 single-prompt planner (Claude)")


def baseline_b2(model: str = DEFAULT_GPT_MODEL, api_key=None,
                llm_client=None) -> SinglePromptBaseline:
    """B2: single-prompt planner on GPT."""
    client = llm_client or OpenAIClient(api_key)
    return SinglePromptBaseline(client, model, "baseline_2",
                                "B2 single-prompt planner (GPT)")
