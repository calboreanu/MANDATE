"""
Corpus authoring tooling (Workstream C2).

PLAYBOOK Phase 2 and PROTOCOL_LOCK Section 6 require a frozen 120-task main
corpus (40 per domain across three domains), 6 pilot tasks, 30 hold-out
tasks, and a 6-task dev set, with:

  - AI-generated candidates following PROMPTS Section 1 verbatim, then
    Lead-Analyst selected at 40 per domain;
  - deduplication at cosine 0.85 against itself, with the package-specified
    "20 distinct / 20 paraphrase threshold" sanity check;
  - a leakage audit at cosine 0.85 against the MANDATE training corpus,
    Success Registry seed examples, and the PROMPTS scaffolding examples
    (PROTOCOL_LOCK Section 13);
  - SME realism audit and signoff;
  - candidate anchor scaffolding for SME review per PROMPTS Section 2.

This package holds the code that turns those steps into a repeatable
pipeline. Everything that can run without live API keys (parsing, dedup,
leakage) is unit-tested here; the LLM-call steps are mock-tested with the
shared `apparatus/baselines/llm_client.MockLLMClient` and run against
Anthropic / OpenAI on the eval host with keys.

Per PROTOCOL_LOCK Section 13 no main data is generated before the
pre-registration deposit. *Authoring* the corpus is the content-prep step
that produces the frozen artifact the pre-registration references; it is
not "data generation" in the gated sense. Running systems on the corpus is
the gated step.
"""
from .prompts import (TASK_GENERATION_PROMPT, ANCHOR_SCAFFOLD_PROMPT,
                      DOMAIN_GUIDANCE, CATEGORIES,
                      render_task_generation_prompt,
                      render_anchor_scaffold_prompt)
from .generator import TaskCandidate, TaskGenerator, parse_numbered_tasks
from .scaffolder import ScaffoldedAnchor, AnchorScaffolder
from .embeddings import (Embedder, HashEmbedder, SentenceTransformerEmbedder,
                         cosine_similarity_matrix, cosine_dedup,
                         leakage_audit)

__all__ = [
    "TASK_GENERATION_PROMPT", "ANCHOR_SCAFFOLD_PROMPT", "DOMAIN_GUIDANCE",
    "CATEGORIES", "render_task_generation_prompt",
    "render_anchor_scaffold_prompt",
    "TaskCandidate", "TaskGenerator", "parse_numbered_tasks",
    "ScaffoldedAnchor", "AnchorScaffolder",
    "Embedder", "HashEmbedder", "SentenceTransformerEmbedder",
    "cosine_similarity_matrix", "cosine_dedup", "leakage_audit",
]
