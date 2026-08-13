"""
B3: ReAct baseline (Workstream B2).

A Reason-and-Act loop on a Claude model. At each step the model emits a
THOUGHT and an ACTION; the action is either `reflect(<aspect>)`, which
continues the loop, or `finalize`, which ends it. After the loop a final call
asks for the JSON specification. The specification task has no meaningful
external tools, so the "acting" steps are bounded self-directed reflection,
consistent with PROTOCOL_LOCK Section 11.

`max_steps` (the reflection budget) is an INITIAL value; PLAYBOOK Phase 4
calibration tunes and then freezes it.
"""
from __future__ import annotations

import time

from .base import BaselineSystem, ProduceResult, Step
from .llm_client import AnthropicClient
from .prompts import (REACT_SYSTEM, REACT_TASK_HEADER, REACT_STEP_PROMPT,
                      REACT_FINALIZE_PROMPT)
from .single_prompt import DEFAULT_CLAUDE_MODEL


def _parse_action(text: str) -> str:
    """Return the action verb from a ReAct step: 'finalize' or 'reflect'.
    Defaults to 'reflect' if no ACTION line is found (the loop is bounded by
    max_steps regardless)."""
    for line in text.splitlines():
        line = line.strip()
        if line.upper().startswith("ACTION:"):
            action = line.split(":", 1)[1].strip().lower()
            if action.startswith("finalize"):
                return "finalize"
            return "reflect"
    return "reflect"


class ReactBaseline(BaselineSystem):
    def __init__(self, llm_client, model, system_id, system_label,
                 max_steps: int = 4):
        super().__init__(llm_client, model, system_id, system_label)
        self.max_steps = max_steps

    def describe(self) -> dict:
        d = super().describe()
        d["max_reflection_steps"] = self.max_steps
        return d

    def _call(self, user: str, name: str, steps: list):
        t0 = time.time()
        resp = self.client.generate(system=REACT_SYSTEM, user=user,
                                    model=self.model, temperature=0.0,
                                    max_tokens=4096)
        steps.append(Step(name=name, duration_ms=(time.time() - t0) * 1000.0,
                          input_tokens=resp.input_tokens,
                          output_tokens=resp.output_tokens,
                          cost_usd=resp.cost_usd))
        return resp.text

    def _produce(self, request_text: str) -> ProduceResult:
        steps: list = []
        transcript = REACT_TASK_HEADER + request_text
        remaining = self.max_steps

        for i in range(1, self.max_steps + 1):
            remaining = self.max_steps - i + 1
            prompt = ("%s\n\nYou have %d reflection step(s) left.%s"
                      % (transcript, remaining, REACT_STEP_PROMPT))
            out = self._call(prompt, "react_step_%d" % i, steps)
            transcript += "\n\n[step %d]\n%s" % (i, out.strip())
            if _parse_action(out) == "finalize":
                break

        final_text = self._call(transcript + REACT_FINALIZE_PROMPT,
                                 "finalize", steps)
        return ProduceResult(text=final_text, steps=steps)


def baseline_b3(model: str = DEFAULT_CLAUDE_MODEL, api_key=None,
                llm_client=None, max_steps: int = 4) -> ReactBaseline:
    """B3: ReAct baseline on Claude."""
    client = llm_client or AnthropicClient(api_key)
    return ReactBaseline(client, model, "baseline_3", "B3 ReAct (Claude)",
                         max_steps=max_steps)
