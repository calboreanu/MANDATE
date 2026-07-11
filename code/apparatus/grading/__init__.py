"""
Three-judge ensemble grading for the MANDATE evaluation (Workstream B5).

PLAYBOOK Phase 8: three judges from three model families (GPT-4o, Claude
Opus 4, Gemini 2.5 Pro) score every anonymized output against ground truth
with the PROMPTS.md Section 4 rubric; results are aggregated and inter-judge
reliability is computed.
"""
from .rubric import (GRADER_PROMPT, SCHEMA_VALIDITY_PROMPT,
                     render_grader_prompt, render_schema_check_prompt)
from .judge import (Judge, JudgeScore, SchemaCheck, judge_gpt4o,
                    judge_claude_opus, judge_gemini_pro)
from .ensemble import (EnsembleScore, aggregate, cohen_kappa,
                       krippendorff_alpha, grader_irr, HALT_KAPPA)
from .pipeline import GradingPipeline, GradedOutput

__all__ = [
    "GRADER_PROMPT", "SCHEMA_VALIDITY_PROMPT", "render_grader_prompt",
    "render_schema_check_prompt",
    "Judge", "JudgeScore", "SchemaCheck", "judge_gpt4o", "judge_claude_opus",
    "judge_gemini_pro",
    "EnsembleScore", "aggregate", "cohen_kappa", "krippendorff_alpha",
    "grader_irr", "HALT_KAPPA",
    "GradingPipeline", "GradedOutput",
]
