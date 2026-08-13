"""
Source-conditioned candidate generator (Workstream C2, PROMPTS Section 1
post-reconciliation).

For each (domain, category) the generator samples N chunks from the
per-domain AEGIS-format Jaccard index, calls Claude Opus 4 with the
source-conditioned PROMPTS Section 1 prompt for each chunk, and returns
TaskCandidate records whose `derived_from` field carries the chunk's
reference_id (canonical) plus the source name. Every candidate is
verifiably grounded in one real document.

Sampling is deterministic given a seed so the same `derived_from`
distribution can be reproduced for the replication package.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from typing import Optional

from ..baselines.llm_client import LLMClient
from .generator import TaskCandidate, DEFAULT_GENERATION_MODEL
from .prompts import CATEGORIES, DOMAIN_GUIDANCE


SOURCE_CONDITIONED_PROMPT = """You are generating one realistic operational task description for an
empirical evaluation of an AI agent specification framework. The task is a
natural-language request from a stakeholder to a team or system, similar
to what would appear in an email, ticket, or tasking memo. Every task
must be DERIVED FROM a real public source document, which is provided
to you below.

Domain: {DOMAIN}
Category: {CATEGORY}
Target length: 80 to 200 words

Source document (the canonical reference this task must derive from):
{SOURCE_TITLE}
{SOURCE_REFERENCE_ID}
---
{SOURCE_CONTENT_CHUNK}
---

Requirements:
- Write in the voice of the requesting stakeholder
- The task must be one that a competent practitioner in {DOMAIN} would
  naturally file BECAUSE the source above is the authoritative reference
  in scope; the source's subject matter is the reason for the request
- Include enough context that a competent team could attempt the task
- Use realistic terminology, system names, and operational constraints
  consistent with the source
- Do NOT quote the source verbatim; paraphrase as a stakeholder naturally
  would
- Do NOT include explicit machine-readable thresholds; phrase requirements
  as a stakeholder naturally would (for example: "by end of week" rather
  than "deadline: 2026-06-01T17:00:00Z")
- For full_specification: include all necessary thresholds, sources, and
  constraints stated naturally, consistent with the source
- For gap_triggering: leave one critical threshold, constraint, or
  capability the source defines unstated, where a competent SME would
  notice the gap
- For stretch_case: include a subtle contradiction (deadline conflicts
  with scope) or an unspecifiable requirement ("best efforts" with no
  quality bar), consistent with the source's domain

Output format: One task description as a single paragraph. No numbering,
no preamble, no commentary outside the paragraph."""


def render_source_conditioned_prompt(*, domain: str, category: str,
                                       source_title: str,
                                       source_reference_id: str,
                                       source_content: str) -> str:
    if domain not in DOMAIN_GUIDANCE:
        raise ValueError("unknown domain: %r" % domain)
    if category not in CATEGORIES:
        raise ValueError("unknown category: %r" % category)
    return (SOURCE_CONDITIONED_PROMPT
            .replace("{DOMAIN}", domain)
            .replace("{CATEGORY}", category)
            .replace("{SOURCE_TITLE}", source_title)
            .replace("{SOURCE_REFERENCE_ID}", source_reference_id)
            .replace("{SOURCE_CONTENT_CHUNK}", source_content))


def load_chunks(index_path: str) -> list:
    """Load an AEGIS-format Jaccard index as a list of dicts."""
    rows = []
    with open(index_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if isinstance(d, dict) and d.get("content"):
                rows.append(d)
    return rows


def sample_chunks(chunks: list, *, n: int, seed: int = 20260601) -> list:
    """Deterministic without-replacement sample of n chunks. If n exceeds
    the pool, returns the pool shuffled."""
    rng = random.Random(seed)
    pool = list(chunks)
    rng.shuffle(pool)
    return pool[:max(0, int(n))]


@dataclass
class SourceConditionedGenerator:
    client: LLMClient
    model: str = DEFAULT_GENERATION_MODEL
    temperature: float = 1.0
    max_tokens: int = 1024

    def describe(self) -> dict:
        return {"model": self.model, "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "provider": getattr(self.client, "provider", "")}

    def generate_one(self, *, domain: str, category: str,
                      chunk: dict, candidate_idx: int = 1
                      ) -> TaskCandidate:
        prompt = render_source_conditioned_prompt(
            domain=domain, category=category,
            source_title=str(chunk.get("name", "") or
                              chunk.get("source", "") or "source"),
            source_reference_id=str(chunk.get("reference_id", "")),
            source_content=str(chunk.get("content", "")))
        resp = self.client.generate(system="", user=prompt,
                                     model=self.model,
                                     temperature=self.temperature,
                                     max_tokens=self.max_tokens)
        text = (resp.text or "").strip()
        cand = TaskCandidate(
            text=text, domain=domain, category=category,
            run_idx=1, candidate_idx=candidate_idx,
            source_model=self.model)
        # carry the derivation explicitly
        cand.notes = ("derived_from=%s; source=%s"
                       % (chunk.get("reference_id", ""),
                          chunk.get("name", "")))
        return cand

    def generate_batch(self, *, domain: str, category: str,
                        chunks: list, start_idx: int = 1) -> list:
        out = []
        for i, ch in enumerate(chunks):
            out.append(self.generate_one(domain=domain, category=category,
                                          chunk=ch,
                                          candidate_idx=start_idx + i))
        return out


def candidate_to_record(cand: TaskCandidate, *, chunk: dict) -> dict:
    """A TaskCandidate plus its derivation, ready to write to JSONL.
    Carries the canonical `derived_from` field PROMPTS Section 1 post-
    reconciliation requires."""
    d = cand.to_dict()
    d["derived_from"] = {
        "reference_id": chunk.get("reference_id", ""),
        "source": chunk.get("source", ""),
        "name": chunk.get("name", ""),
        "content_preview": str(chunk.get("content", ""))[:240],
    }
    return d
