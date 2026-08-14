"""
Baseline systems for the MANDATE evaluation (Workstream B2).

This package exports B1, B2 (single-prompt planners), and B3 (ReAct), plus the
shared specification schema, model client, prompts, and base class. B4-B6 were
evaluated through orchestration-pattern shells in ``multi_agent.py`` rather
than the corresponding framework products; see ``MULTI_AGENT_BASELINES.md``.
"""
from .schema import (BASELINE_SPECIFICATION_SCHEMA, SCHEMA_ID,
                     validate_specification)
from .llm_client import (LLMClient, AnthropicClient, BudgetedLLMClient, OpenAIClient,
                         GeminiClient, MockLLMClient, LLMResponse,
                         estimate_cost)
from .base import BaselineSystem, Step, ProduceResult, extract_json
from .single_prompt import SinglePromptBaseline, baseline_b1, baseline_b2
from .react import ReactBaseline, baseline_b3

__all__ = [
    "BASELINE_SPECIFICATION_SCHEMA", "SCHEMA_ID", "validate_specification",
    "LLMClient", "AnthropicClient", "BudgetedLLMClient", "OpenAIClient", "GeminiClient",
    "MockLLMClient", "LLMResponse", "estimate_cost",
    "BaselineSystem", "Step", "ProduceResult", "extract_json",
    "SinglePromptBaseline", "baseline_b1", "baseline_b2",
    "ReactBaseline", "baseline_b3",
]
