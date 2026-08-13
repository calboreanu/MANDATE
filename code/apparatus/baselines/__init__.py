"""
Baseline systems for the MANDATE evaluation (Workstream B2).

Built and mock-tested: B1, B2 (single-prompt planners), B3 (ReAct), plus the
shared foundation (specification schema, LLM client, prompts, base class).

Pending: B4 (AutoGen), B5 (CrewAI), B6 (LangGraph). See MULTI_AGENT_BASELINES.md.
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
