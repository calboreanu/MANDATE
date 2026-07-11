"""
Task description generator (Workstream C2, PROMPTS Section 1).

PLAYBOOK Phase 2 runs PROMPTS Section 1 five times per (domain x category)
combination, yielding 75 candidates per domain (5 runs x 3 categories x 5
descriptions), and the Lead Analyst selects 40 per domain for the main
corpus. This module produces the candidate set; selection is a manual
review step that records each kept-or-dropped decision in the corpus log.

The generator wraps a single LLM call per run and parses the numbered
output into five `TaskCandidate` records. It records the model identity
and the run index so the corpus log can show full provenance.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from ..baselines.llm_client import LLMClient
from .prompts import (CATEGORIES, DOMAIN_GUIDANCE,
                      render_task_generation_prompt)

# Per PROMPTS Section 1 the model used to generate corpus tasks must not be
# from the Qwen3 family used inside MANDATE. The default is Claude Opus 4,
# expressed as the current Anthropic API identifier; the exact version
# string is pinned at the pre-registration deposit (TO_FILL_TRACKER D1).
DEFAULT_GENERATION_MODEL = "claude-opus-4-6"


@dataclass
class TaskCandidate:
    """One generated candidate task, before SME review."""
    text: str
    domain: str
    category: str
    run_idx: int                     # which of the 5 runs per domain x cat
    candidate_idx: int               # 1..5 within that run's output
    source_model: str
    candidate_id: str = ""           # filled at corpus freeze; empty for now
    accepted: Optional[bool] = None  # set during Lead-Analyst selection
    notes: str = ""

    def to_dict(self) -> dict:
        return {"candidate_id": self.candidate_id, "text": self.text,
                "domain": self.domain, "category": self.category,
                "run_idx": self.run_idx,
                "candidate_idx": self.candidate_idx,
                "source_model": self.source_model,
                "accepted": self.accepted, "notes": self.notes}


_NUM_RE = re.compile(r"^\s*(\d+)[\.\)]\s+(.*)", re.DOTALL)


def parse_numbered_tasks(raw_text: str) -> list:
    """Parse the model's "1. ... 2. ... 3. ..." output into a list of task
    text strings. Robust to extra blank lines, varied separators (period or
    paren after the number), and to lower-than-5 outputs (returns what is
    present rather than fabricating).
    """
    if not raw_text:
        return []
    # split on lines starting with `\nN. ` or `\nN) `; keep N for ordering
    parts = re.split(r"(?m)^\s*(\d+)[\.\)]\s+", "\n" + raw_text)
    # parts is like ['', 'leading'?, '1', 'text1', '2', 'text2', ...]
    if len(parts) < 3:
        return []
    items = []
    i = 1
    while i + 1 < len(parts):
        idx = parts[i].strip()
        body = parts[i + 1].strip()
        if idx.isdigit() and body:
            items.append((int(idx), body))
        i += 2
    items.sort(key=lambda p: p[0])
    return [b for _, b in items]


class TaskGenerator:
    """Run PROMPTS Section 1 against an LLM and collect TaskCandidates."""

    def __init__(self, client: LLMClient,
                 model: str = DEFAULT_GENERATION_MODEL,
                 temperature: float = 1.0, max_tokens: int = 2048):
        self.client = client
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def describe(self) -> dict:
        return {"model": self.model, "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "provider": getattr(self.client, "provider", "")}

    def generate_run(self, *, domain: str, category: str,
                     run_idx: int) -> list:
        """One PROMPTS Section 1 run; returns up to 5 TaskCandidates."""
        prompt = render_task_generation_prompt(domain=domain,
                                                category=category)
        resp = self.client.generate(system="", user=prompt, model=self.model,
                                    temperature=self.temperature,
                                    max_tokens=self.max_tokens)
        texts = parse_numbered_tasks(resp.text)
        out = []
        for k, text in enumerate(texts, start=1):
            if not text.strip():
                continue
            out.append(TaskCandidate(text=text, domain=domain,
                                     category=category, run_idx=run_idx,
                                     candidate_idx=k,
                                     source_model=self.model))
        return out

    def generate_batch(self, *, domain: str, n_runs: int = 5) -> list:
        """All categories x n_runs runs for one domain, per PLAYBOOK Phase 2.
        Returns the flat candidate list."""
        if domain not in DOMAIN_GUIDANCE:
            raise ValueError("unknown domain: %r" % domain)
        out = []
        for category in CATEGORIES:
            for run_idx in range(1, n_runs + 1):
                out.extend(self.generate_run(domain=domain,
                                              category=category,
                                              run_idx=run_idx))
        return out
