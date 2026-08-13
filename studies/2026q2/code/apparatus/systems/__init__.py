"""System adapters for the MANDATE evaluation harness.

Built (B1): ReferenceSystem, MandatePrimarySystem.
Pending: baselines B1-B6 (Workstream B2), the five alternative backends,
and the seven ablations A1-A7.
"""
from .reference import ReferenceSystem
from .mandate_primary import MandatePrimarySystem, load_ollama_config
from .mandate_canonical import (
    AnthropicMLTAdapter,
    CondASystem,
    CondBSystem,
    run_cond_a,
    run_cond_b,
)

__all__ = [
    "ReferenceSystem",
    "MandatePrimarySystem",
    "load_ollama_config",
    "AnthropicMLTAdapter",
    "CondASystem",
    "CondBSystem",
    "run_cond_a",
    "run_cond_b",
]
