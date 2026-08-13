"""Cond-A extractor: natural-language task text -> canonical MissionInput.

Cond-A is designed to separate planning quality from requirements extraction.
This module uses a strong extraction model to produce the canonical
``mlt.mandate.models.MissionInput`` object, then deterministic MLT MANDATE
does the planning work.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Optional

from apparatus.baselines.base import extract_json
from apparatus.baselines.llm_client import AnthropicClient, BudgetedLLMClient
from apparatus.llm_retry import DEFAULT_RETRY_BACKOFF_SEC, call_with_retry

import os
MLT_ROOT = Path(os.environ["MLT_ROOT"]) if os.environ.get("MLT_ROOT") else Path.home() / "Desktop" / "MLT-Governance-Stack"
MLT_SRC = MLT_ROOT / "src"
if str(MLT_SRC) not in sys.path:
    sys.path.insert(0, str(MLT_SRC))

from mlt.mandate.models import MissionInput, ToolSpec  # noqa: E402
from mlt.mandate.constraints import validate_constraint  # noqa: E402


EXTRACTION_PROMPT = """You are extracting a structured MissionInput from a natural-language operational task.

The output will be consumed by canonical MANDATE. Return JSON only, no
preamble. Use this schema:

{
  "mission_id": "short identifier",
  "intent": "1-3 sentence operational statement",
  "minimum_outcome": "multi-sentence minimum acceptable outcome; include every must/required/shall dimension",
  "target_outcome": "multi-sentence ideal outcome beyond the minimum",
  "constraints": ["valid MANDATE constraint grammar strings only"],
  "scope": ["scope item"],
  "assumptions": ["assumption"],
  "available_tools": [{"tool_id": "string", "tool_class": "RECON|SCAN|EXPLOIT|ANALYSIS|COLLECTION|COORDINATION|REPORTING", "description": "string"}],
  "risk_tolerance": "LOW|MEDIUM|HIGH"
}

Canonical MANDATE constraint grammar:
- constraints: array of strings in canonical MANDATE EBNF grammar. Each string
  must match one of these four shapes. MANDATE will reject any other string.

  1. FORBIDS <snake_case_identifier> - a hard prohibition.
     Examples:
       FORBIDS data_exfiltration
       FORBIDS unauthorized_system_shutdown
       FORBIDS production_modification

  2. REQUIRES <snake_case_identifier> - a hard requirement.
     Examples:
       REQUIRES ciso_approval
       REQUIRES nist_800_37_alignment
       REQUIRES interagency_coordination_cycle

  3. <field>.<subfield> IN ['item', 'item'] - scope or enumeration constraint.
     Field is one of: target.scope, target.systems, target.actors,
     target.timeline.
     Examples:
       target.scope IN ['10.0.1.0/24', 'acme.example.com']
       target.scope IN ['FIN-DC-EAST-01', 'FIN-DC-WEST-01']

  4. <field>.<subfield> <op> <literal> - comparison constraint. Op is one of:
     <=, >=, <, >, ==, !=. Literal is a duration (PT4H, PT30M, P30D), a
     quoted string, or a number.
     Examples:
       execution.duration <= PT4H
       execution.duration <= PT8H
       target.completion_deadline <= '2026Q4_end'

Rules:
- Convert natural-language constraints into one of these four shapes.
- Use snake_case identifiers, never spaces.
- Use ISO-8601 duration format for time (PT4H = 4 hours, P30D = 30 days).
- Use quoted strings inside IN lists, single-quoted.
- If you cannot map a natural-language constraint to one of the four shapes
  cleanly, omit it from constraints and mention it inside minimum_outcome
  instead. Do not emit invalid grammar.
- Use empty arrays for arrays with no extractable content.

TASK TEXT:
---
{task_text}
---

JSON OUTPUT:"""


def _coerce_tools(raw_tools: Any) -> list[ToolSpec]:
    tools: list[ToolSpec] = []
    if not isinstance(raw_tools, list):
        return tools
    for i, raw in enumerate(raw_tools):
        if not isinstance(raw, dict):
            continue
        tool_id = str(raw.get("tool_id") or f"tool_{i + 1}").strip()
        tool_class = str(raw.get("tool_class") or "ANALYSIS").strip().upper()
        if tool_class not in {
            "RECON", "SCAN", "EXPLOIT", "ANALYSIS",
            "COLLECTION", "COORDINATION", "REPORTING",
        }:
            tool_class = "ANALYSIS"
        tools.append(ToolSpec(
            tool_id=tool_id,
            tool_class=tool_class,
            description=str(raw.get("description") or ""),
            parameters=dict(raw.get("parameters") or {}),
        ))
    return tools


def _valid_constraints(raw_constraints: Any) -> list[str]:
    valid, _failed = _split_constraints(raw_constraints)
    return valid


def _split_constraints(raw_constraints: Any) -> tuple[list[str], list[dict[str, str]]]:
    valid: list[str] = []
    failed: list[dict[str, str]] = []
    if not isinstance(raw_constraints, list):
        return valid, failed
    for raw in raw_constraints:
        text = str(raw or "").strip()
        if not text:
            continue
        if validate_constraint(text):
            valid.append(text)
        else:
            failed.append({"text": text, "reason": "invalid_grammar"})
    return valid, failed


def _parse_response_text(text: str) -> dict:
    parsed, err = extract_json(text)
    if parsed is None:
        raise ValueError(err or "extractor returned no JSON object")
    if not isinstance(parsed, dict):
        raise ValueError("extractor JSON must be an object")
    return parsed


def extract(
    task_id: str,
    task_text: str,
    model: str = "claude-sonnet-4-6",
    client: Optional[Any] = None,
    retry_backoff_sec=DEFAULT_RETRY_BACKOFF_SEC,
    cost_ledger=None,
    run_id: str = "",
    run_number: int = 1,
) -> MissionInput:
    """Run the extraction model and return a canonical MLT MissionInput."""
    llm = client or AnthropicClient()
    if cost_ledger is not None and client is None:
        llm = BudgetedLLMClient(
            llm,
            cost_ledger=cost_ledger,
            run_id=run_id or f"cond_a__{task_id}__r{int(run_number):02d}",
            system_id="cond_a",
            task_id=task_id,
            run_number=run_number,
            role="PreExtractor",
        )
    prompt = EXTRACTION_PROMPT.replace("{task_text}", task_text)
    resp = call_with_retry(
        llm.generate,
        system=(
            "You are a senior systems analyst extracting structured "
            "specifications from operational tasks."
        ),
        user=prompt,
        model=model,
        temperature=0.0,
        max_tokens=4096,
        retry_backoff_sec=retry_backoff_sec,
    )
    parsed = _parse_response_text(resp.text)
    mission_id = str(parsed.get("mission_id") or task_id)
    intent = str(parsed.get("intent") or task_text[:500]).strip()
    if not intent:
        raise ValueError("extractor returned empty intent")
    risk_tolerance = str(parsed.get("risk_tolerance") or "").strip().upper() or None
    if risk_tolerance not in {"LOW", "MEDIUM", "HIGH", None}:
        risk_tolerance = None

    valid_constraints, failed_constraints = _split_constraints(parsed.get("constraints"))
    raw_response = dict(getattr(resp, "raw_response", {}) or {})
    retry_metadata = raw_response.get("retry") or {}
    response_cost = resp.cost_usd or 0.0
    budget_total_cost = raw_response.get("budget_total_cost_usd", response_cost)
    metadata = {
        "source_task_id": task_id,
        "extraction_model": model,
        "extraction_prompt_template_sha256": hashlib.sha256(EXTRACTION_PROMPT.encode("utf-8")).hexdigest(),
        "extraction_prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "extraction_cost_usd": budget_total_cost,
        "input_tokens": int(getattr(resp, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(resp, "output_tokens", 0) or 0),
        "raw_provider_response": {
            "provider": getattr(llm, "provider", ""),
            "model": model,
            "input_tokens": int(getattr(resp, "input_tokens", 0) or 0),
            "output_tokens": int(getattr(resp, "output_tokens", 0) or 0),
            "cost_usd": budget_total_cost,
            "response_cost_usd": response_cost,
            "budget_reservation_id": raw_response.get("budget_reservation_id"),
            "budget_attempts": list(raw_response.get("budget_attempts") or []),
            "budget_total_cost_usd": budget_total_cost,
            "budget_cost_accounting": raw_response.get("budget_cost_accounting", "exact"),
            "retry": retry_metadata,
            "text": resp.text,
        },
        "raw_extraction_json": json.dumps(parsed, default=str),
        "extraction_failed_constraints": failed_constraints,
        "constraints_extracted": len(valid_constraints),
        "constraints_failed_grammar": len(failed_constraints),
    }

    return MissionInput(
        mission_id=mission_id,
        intent=intent,
        scope=[str(x) for x in list(parsed.get("scope") or [])],
        constraints=valid_constraints,
        minimum_outcome=str(parsed.get("minimum_outcome") or ""),
        target_outcome=str(parsed.get("target_outcome") or ""),
        available_tools=_coerce_tools(parsed.get("available_tools")),
        risk_tolerance=risk_tolerance,
        metadata=metadata,
    )
