"""
Anchor scaffolder (Workstream C2, PROMPTS Section 2).

PLAYBOOK Phase 3 runs PROMPTS Section 2 once per main-corpus task to produce
a candidate anchor that the SME reviews, revises, or rejects. The SME forms
an independent judgement before reading the scaffold (FORMS Section 1); the
scaffolder must therefore be deterministic and conservative, exactly what
the Section 2 rubric tells the model to be: do not invent thresholds, set
absent values to null, and add anything genuinely missing to
suspected_gaps.

This module wraps the LLM call, parses the JSON, and returns a
`ScaffoldedAnchor`. It does not consume SME judgement; that is a manual
step recorded in `04_ground_truth/`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..baselines.base import extract_json
from ..baselines.llm_client import LLMClient
from .prompts import render_anchor_scaffold_prompt

DEFAULT_SCAFFOLD_MODEL = "claude-opus-4-6"


@dataclass
class ScaffoldedAnchor:
    """One AI scaffold for SME review."""
    task_id: str
    request_text: str
    mission_intent: str = ""
    minimum: list = field(default_factory=list)
    target: list = field(default_factory=list)
    constraints: list = field(default_factory=list)
    suspected_gaps: list = field(default_factory=list)
    source_model: str = ""
    parse_ok: bool = False
    error: str = ""
    raw_json: str = ""

    def to_dict(self) -> dict:
        return {"task_id": self.task_id, "request_text": self.request_text,
                "mission_intent": self.mission_intent,
                "minimum": self.minimum, "target": self.target,
                "constraints": self.constraints,
                "suspected_gaps": self.suspected_gaps,
                "source_model": self.source_model,
                "parse_ok": self.parse_ok, "error": self.error,
                "raw_json": self.raw_json}


class AnchorScaffolder:
    def __init__(self, client: LLMClient,
                 model: str = DEFAULT_SCAFFOLD_MODEL,
                 temperature: float = 0.0, max_tokens: int = 4096):
        # max_tokens default bumped 2048 -> 4096 on 2026-06-04 after
        # HANDOFF_06b halted with 0/6 parse_ok; the 2048 ceiling was
        # truncating Opus 4.6 mid-JSON on real source-grounded pilot
        # tasks. Callers may override via the CLI flag.
        self.client = client
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def describe(self) -> dict:
        return {"model": self.model, "temperature": self.temperature,
                "provider": getattr(self.client, "provider", "")}

    def scaffold(self, *, task_id: str, request_text: str
                 ) -> ScaffoldedAnchor:
        out = ScaffoldedAnchor(task_id=task_id, request_text=request_text,
                               source_model=self.model)
        prompt = render_anchor_scaffold_prompt(request_text=request_text)
        try:
            resp = self.client.generate(system="", user=prompt,
                                         model=self.model,
                                         temperature=self.temperature,
                                         max_tokens=self.max_tokens)
        except Exception as e:
            out.error = "scaffold LLM error: %r" % e
            return out
        out.raw_json = resp.text
        parsed, perr = extract_json(resp.text)
        if parsed is None:
            out.error = perr or "no JSON in scaffold response"
            return out
        out.mission_intent = str(parsed.get("mission_intent", ""))
        out.minimum = list(parsed.get("minimum", []) or [])
        out.target = list(parsed.get("target", []) or [])
        out.constraints = list(parsed.get("constraints", []) or [])
        out.suspected_gaps = list(parsed.get("suspected_gaps", []) or [])
        out.parse_ok = True
        return out
