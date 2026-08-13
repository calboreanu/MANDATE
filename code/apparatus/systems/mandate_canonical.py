"""Adapter from the eval apparatus to canonical MLT MANDATE v1.0.0rc1.

Two conditions are exposed:

* Cond-A: Sonnet pre-extracts a structured ``MissionInput``; deterministic
  canonical MLT MANDATE performs the planning.
* Cond-B: canonical MLT MANDATE runs with its LLM advisory hooks enabled,
  using an Anthropic-backed ``mlt.sdk.llm.LLMAdapter`` bridge.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

from apparatus.baselines.base import extract_json
from apparatus.baselines.llm_client import AnthropicClient, BudgetedLLMClient
from apparatus.harness.records import (
    OUTPUT_GAP_REPORT,
    OUTPUT_MANDATE_AS_CODE,
    RoleTiming,
    RunRecord,
)
from apparatus.harness.system import System
from apparatus.llm_retry import DEFAULT_RETRY_BACKOFF_SEC, RetryingLLMClient

MLT_ROOT = Path(os.environ["MLT_ROOT"]) if os.environ.get("MLT_ROOT") else Path.home() / "Desktop" / "MLT-Governance-Stack"
MLT_SRC = MLT_ROOT / "src"
if str(MLT_SRC) not in sys.path:
    sys.path.insert(0, str(MLT_SRC))

from mlt import __version__ as MLT_VERSION  # noqa: E402
from mlt.mandate.execution_contract import (  # noqa: E402
    CONTRACT_SCHEMA_VERSION,
    build_result_envelope,
    validate_result_envelope,
)
from mlt.mandate.models import MissionInput, PipelineConfig  # noqa: E402
from mlt.mandate.constraints import validate_constraint  # noqa: E402
from mlt.mandate.domain import get_domain_profile  # noqa: E402
from mlt.mandate.gap_report import build_gap_reports  # noqa: E402
from mlt.mandate.models import (  # noqa: E402
    GapLocation,
    GapSeverity,
    GapSource,
    GapSpec,
    GapType,
)
from mlt.mandate.pipeline import Pipeline  # noqa: E402
from mlt.sdk.llm import LLMAdapter, LLMConfig, LLMResponse  # noqa: E402


APPARATUS_ROOT = Path(__file__).resolve().parents[3]


def _git_commit(path: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "UNKNOWN"


def _git_dirty(path: Path) -> bool:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(path), "status", "--porcelain", "--untracked-files=no"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return bool(out.strip())
    except Exception:
        return True


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _source_hashes(root: Path, rels: list[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for rel in rels:
        path = root / rel
        hashes[rel] = _sha256_file(path) if path.exists() else "MISSING"
    return hashes


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _budget_attempt_id(attempt: dict) -> str:
    return str(
        attempt.get("budget_reservation_id")
        or attempt.get("reservation_id")
        or ""
    )


def _budget_attempt_total(attempts: list[dict]) -> float:
    return round(sum(float(a.get("cost_usd") or 0.0) for a in attempts), 6)


def _budget_cost_accounting(attempts: list[dict]) -> str:
    if all(
        str(a.get("cost_basis") or "").startswith("authoritative")
        or str(a.get("cost_basis") or "") == "undispatched_zero"
        for a in attempts
    ):
        return "exact"
    return "conservative_upper_bound"


def _merge_budget_attempts(*groups: list[dict]) -> list[dict]:
    merged: list[dict] = []
    seen: set[str] = set()
    for group in groups:
        for attempt in group or []:
            if not isinstance(attempt, dict):
                continue
            row = dict(attempt)
            rid = _budget_attempt_id(row)
            if rid:
                row["budget_reservation_id"] = rid
                row.setdefault("reservation_id", rid)
                if rid in seen:
                    continue
                seen.add(rid)
            merged.append(row)
    return merged


MLT_GIT_COMMIT = _git_commit(MLT_ROOT)
APPARATUS_GIT_COMMIT = _git_commit(APPARATUS_ROOT)
MLT_GIT_DIRTY = _git_dirty(MLT_ROOT)
APPARATUS_GIT_DIRTY = _git_dirty(APPARATUS_ROOT)
CODE_REF = f"mlt-stack-{MLT_VERSION}+{CONTRACT_SCHEMA_VERSION}@{MLT_GIT_COMMIT}"
COND_A_LABEL = f"MANDATE v{MLT_VERSION}+{CONTRACT_SCHEMA_VERSION}, structured-input, deterministic"
COND_B_LABEL = f"MANDATE v{MLT_VERSION}+{CONTRACT_SCHEMA_VERSION}, LLM-augmented Interpreter, end-to-end"
_TASK_DOMAIN_TO_PROFILE_NAME = {
    "INT": "defense_intel",
    "SEC": "incident_response",
    "FIN": None,  # no canonical financial profile in MLT v1.0.0rc1
}
MLT_EXPERIMENT_SOURCE_HASHES = _source_hashes(MLT_ROOT, [
    "src/mlt/mandate/pipeline.py",
    "src/mlt/mandate/execution_contract.py",
    "src/mlt/schemas/mandate-result-envelope.schema.json",
    "src/mlt/sdk/llm/prompt_templates.py",
])
APPARATUS_EXPERIMENT_SOURCE_HASHES = _source_hashes(APPARATUS_ROOT, [
    "code/apparatus/consolidate_rerun.py",
    "code/apparatus/harness/ledger.py",
    "code/apparatus/harness/records.py",
    "code/apparatus/harness/runner.py",
    "code/apparatus/llm_retry.py",
    "code/apparatus/preflight.py",
    "code/apparatus/preprocess/extract_mission_input.py",
    "code/apparatus/run.py",
    "code/apparatus/systems/mandate_canonical.py",
    "code/apparatus/rerun_analysis.py",
])
CONSTRAINT_GRAMMAR_INSTRUCTION = """

Canonical MANDATE constraint grammar reminder:
- constraints must be strings matching one of these shapes:
  FORBIDS <snake_case_identifier>
  REQUIRES <snake_case_identifier>
  <field>.<subfield> IN ['item', 'item']
  <field>.<subfield> <op> <literal> where op is <=, >=, <, >, ==, or !=
- Convert natural-language constraints into those shapes.
- Omit any natural-language constraint that cannot be cleanly mapped. The
  apparatus will route omitted invalid grammar to extraction-gap reports.
"""


def _resolve_domain_profile(task_id: str, mode: str):
    """Resolve an opt-in canonical DomainProfile from a corpus task ID.

    ``default`` preserves pre-HANDOFF_19d behavior: no profile is passed to
    canonical MANDATE. ``auto`` maps INT/SEC to shipped MLT profiles; FIN has
    no canonical financial profile in v1.0.0rc1 and intentionally returns None.
    """
    if mode != "auto":
        return None
    parts = str(task_id or "").split("-")
    if len(parts) < 3:
        return None
    profile_name = _TASK_DOMAIN_TO_PROFILE_NAME.get(parts[2])
    if profile_name is None:
        return None
    return get_domain_profile(profile_name)


class AnthropicMLTAdapter(LLMAdapter):
    """Bridge the eval harness Anthropic client into MLT's adapter protocol."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        *,
        client: Optional[Any] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        retry_count: int = 2,
        cost_ledger=None,
    ):
        self.client = client or AnthropicClient()
        self.model = model
        self.config = LLMConfig(
            model_path=model,
            max_tokens=max_tokens,
            temperature=temperature,
            retry_count=retry_count,
        )
        self.cost_ledger = cost_ledger
        self._current_role = ""
        self._budget_context = {
            "run_id": "",
            "system_id": "cond_b",
            "task_id": "",
            "run_number": 1,
        }
        self._pending_budget_attempts: dict[tuple[str, str], list[dict]] = {}

    def set_current_role(self, role_name: Optional[str]) -> None:
        self._current_role = str(role_name or "")

    def set_budget_context(self, *, run_id: str, system_id: str, task_id: str, run_number: int) -> None:
        previous_run_id = self._budget_context.get("run_id")
        self._budget_context = {
            "run_id": run_id,
            "system_id": system_id,
            "task_id": task_id,
            "run_number": int(run_number),
        }
        if previous_run_id and previous_run_id != run_id:
            self._pending_budget_attempts = {
                key: attempts
                for key, attempts in self._pending_budget_attempts.items()
                if key[0] == run_id
            }

    def _budget_key(self) -> tuple[str, str]:
        return (
            str(self._budget_context.get("run_id") or ""),
            self._current_role or "UNKNOWN_ROLE",
        )

    def generate(self, prompt: str, schema: dict) -> LLMResponse:
        t0 = time.time()
        client = self.client
        budgeted_client = None
        if self.cost_ledger is not None:
            budgeted_client = BudgetedLLMClient(
                self.client,
                cost_ledger=self.cost_ledger,
                run_id=self._budget_context["run_id"],
                system_id=self._budget_context["system_id"],
                task_id=self._budget_context["task_id"],
                run_number=int(self._budget_context["run_number"]),
                role=self._current_role or "UNKNOWN_ROLE",
            )
            client = budgeted_client
        try:
            resp = client.generate(
                system=("You are a schema-constrained MANDATE role assistant. "
                        "Return JSON only."),
                user=prompt,
                model=self.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
        except Exception:
            if budgeted_client is not None and budgeted_client.attempts:
                key = self._budget_key()
                self._pending_budget_attempts.setdefault(key, [])
                self._pending_budget_attempts[key] = _merge_budget_attempts(
                    self._pending_budget_attempts[key],
                    budgeted_client.attempts,
                )
            raise

        parsed, _ = extract_json(resp.text)
        output: Any = parsed if parsed is not None else resp.text
        raw = getattr(resp, "raw_response", {})
        raw = dict(raw) if isinstance(raw, dict) else {}
        pending_attempts: list[dict] = []
        if budgeted_client is not None:
            pending_attempts = self._pending_budget_attempts.pop(self._budget_key(), [])
        current_attempts = list(raw.get("budget_attempts") or [])
        if not current_attempts and budgeted_client is not None:
            current_attempts = list(budgeted_client.attempts)
        budget_attempts = _merge_budget_attempts(pending_attempts, current_attempts)
        budget_total = (
            _budget_attempt_total(budget_attempts)
            if budget_attempts
            else raw.get("budget_total_cost_usd", resp.cost_usd)
        )
        budget_accounting = (
            _budget_cost_accounting(budget_attempts)
            if budget_attempts
            else raw.get("budget_cost_accounting")
        )
        raw_response = {
            "model": self.model,
            "input_tokens": resp.input_tokens,
            "output_tokens": resp.output_tokens,
            "cost_usd": resp.cost_usd,
            "budget_reservation_id": raw.get("budget_reservation_id"),
            "text": resp.text,
        }
        raw_response.update(raw)
        if budget_attempts:
            raw_response["budget_attempts"] = budget_attempts
            raw_response["budget_total_cost_usd"] = budget_total
            raw_response["budget_cost_accounting"] = budget_accounting
        return LLMResponse(
            output=output,
            tokens_used=int((resp.input_tokens or 0) + (resp.output_tokens or 0)),
            latency_ms=(time.time() - t0) * 1000.0,
            raw_response=raw_response,
        )

    def generate_with_trace(self, prompt: str, schema: dict):
        response = self.generate(prompt, schema)
        return response, {
            "provider": getattr(self.client, "provider", "anthropic"),
            "model": self.model,
            "tokens_used": response.tokens_used,
            "latency_ms": response.latency_ms,
        }


class OllamaMLTAdapter(LLMAdapter):
    """Bridge local Ollama JSON generation into MLT's adapter protocol."""

    provider = "ollama"

    def __init__(
        self,
        model: str,
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        retry_count: int = 2,
        timeout: int = 600,
        seed: Optional[int] = None,
        call_json=None,
    ):
        from apparatus.llm.ollama_client import call_ollama_json

        self.model = model
        self.seed = seed
        self.timeout = timeout
        self._call_json = call_json or call_ollama_json
        self.config = LLMConfig(
            model_path=model,
            max_tokens=max_tokens,
            temperature=temperature,
            retry_count=retry_count,
        )

    def set_seed(self, seed: Optional[int]) -> None:
        self.seed = seed

    def generate(self, prompt: str, schema: dict) -> LLMResponse:
        del schema
        t0 = time.time()
        options = {
            "temperature": self.config.temperature,
            "num_predict": self.config.max_tokens,
        }
        if self.seed is not None:
            options["seed"] = int(self.seed)
        output = self._call_json(
            model=self.model,
            prompt=prompt,
            format="json",
            options=options,
            timeout=self.timeout,
        )
        rendered = json.dumps(output, sort_keys=True)
        return LLMResponse(
            output=output,
            tokens_used=max(1, (len(prompt) + len(rendered)) // 4),
            latency_ms=(time.time() - t0) * 1000.0,
            raw_response={
                "provider": self.provider,
                "model": self.model,
                "options": options,
                "output": output,
            },
        )

    def generate_with_trace(self, prompt: str, schema: dict):
        response = self.generate(prompt, schema)
        return response, {
            "provider": self.provider,
            "model": self.model,
            "tokens_used": response.tokens_used,
            "latency_ms": response.latency_ms,
        }


def _sanitize_provider_payload(obj: Any) -> Any:
    if isinstance(obj, dict):
        clean = {}
        for key, value in obj.items():
            key_s = str(key)
            if any(token in key_s.lower() for token in ("api_key", "authorization", "secret", "x-api-key")):
                clean[key_s] = "[REDACTED]"
            else:
                clean[key_s] = _sanitize_provider_payload(value)
        return clean
    if isinstance(obj, list):
        return [_sanitize_provider_payload(item) for item in obj]
    if isinstance(obj, str):
        if "sk-ant-" in obj:
            return "[REDACTED_SECRET_STRING]"
        return obj
    return obj


def _prompt_evidence(prompt: str) -> dict[str, Any]:
    rendered_prompt = _sanitize_provider_payload(prompt)
    if not isinstance(rendered_prompt, str):
        rendered_prompt = str(rendered_prompt)
    return {
        "prompt_evidence_format": "rendered_prompt.v1",
        "rendered_prompt": rendered_prompt,
        "prompt_sha256": _sha256_text(rendered_prompt),
    }


class RecordingLLMAdapter(LLMAdapter):
    """Record sanitized provider calls without exposing request headers or keys."""

    def __init__(self, inner: LLMAdapter):
        self.inner = inner
        self.config = getattr(inner, "config", None)
        self.provider = (
            getattr(inner, "provider", "")
            or getattr(getattr(inner, "client", None), "provider", "")
        )
        self.model = getattr(inner, "model", getattr(self.config, "model_path", ""))
        self.current_role: Optional[str] = None
        self.calls: list[dict[str, Any]] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def set_current_role(self, role_name: Optional[str]) -> None:
        self.current_role = role_name
        if hasattr(self.inner, "set_current_role"):
            self.inner.set_current_role(role_name)

    def set_seed(self, seed: Optional[int]) -> None:
        if hasattr(self.inner, "set_seed"):
            self.inner.set_seed(seed)

    def generate(self, prompt: str, schema: dict) -> LLMResponse:
        t0 = time.time()
        prompt_evidence = _prompt_evidence(prompt)
        schema_sha256 = _sha256_text(json.dumps(schema, sort_keys=True, default=str))
        try:
            response = self.inner.generate(prompt, schema)
        except Exception as exc:
            self.calls.append({
                "role": self.current_role or "",
                "provider": self.provider,
                "model": self.model,
                "prompt_sha256": prompt_evidence["prompt_sha256"],
                "schema_sha256": schema_sha256,
                "prompt_evidence_format": prompt_evidence["prompt_evidence_format"],
                "rendered_prompt": prompt_evidence["rendered_prompt"],
                "ok": False,
                "error_type": type(exc).__name__,
                "error": str(exc)[:500],
                "latency_ms": round((time.time() - t0) * 1000.0, 4),
            })
            raise

        raw = _sanitize_provider_payload(dict(response.raw_response or {}))
        cost_usd = raw.get("budget_total_cost_usd", raw.get("cost_usd")) if isinstance(raw, dict) else None
        self.calls.append({
            "role": self.current_role or "",
            "provider": self.provider,
            "model": self.model,
            "prompt_sha256": prompt_evidence["prompt_sha256"],
            "schema_sha256": schema_sha256,
            "prompt_evidence_format": prompt_evidence["prompt_evidence_format"],
            "rendered_prompt": prompt_evidence["rendered_prompt"],
            "ok": True,
            "tokens_used": int(getattr(response, "tokens_used", 0) or 0),
            "latency_ms": float(getattr(response, "latency_ms", 0.0) or 0.0),
            "input_tokens": int(raw.get("input_tokens") or 0) if isinstance(raw, dict) else 0,
            "output_tokens": int(raw.get("output_tokens") or 0) if isinstance(raw, dict) else 0,
            "cost_usd": cost_usd,
            "response_cost_usd": raw.get("cost_usd") if isinstance(raw, dict) else None,
            "raw_response": raw,
        })
        return response

    def generate_with_trace(self, prompt: str, schema: dict):
        response = self.generate(prompt, schema)
        return response, {
            "provider": self.provider,
            "model": self.model,
            "tokens_used": response.tokens_used,
            "latency_ms": response.latency_ms,
        }


def _is_mission_input_schema(schema: dict) -> bool:
    props = schema.get("properties", {}) if isinstance(schema, dict) else {}
    required = set(schema.get("required", []) or [])
    return {"mission_id", "intent"}.issubset(required) and "constraints" in props


class ConstraintGapRoutingAdapter(LLMAdapter):
    """Sanitize Cond-B LLM Intake constraints and remember rejected grammar.

    Canonical MLT Intake intentionally rejects natural-language constraints.
    For Cond-B, invalid LLM-emitted constraints are an extraction-quality gap,
    not a reason to lose the rest of the run. This adapter intercepts only the
    MissionInput-shaped Intake response, removes invalid constraints before
    canonical Intake validation, and stores the verbatim rejected text so
    run_cond_b can publish it as EXTRACTION_GAP gap reports.
    """

    def __init__(self, inner: LLMAdapter):
        self.inner = inner
        self.config = getattr(inner, "config", None)
        self.provider = getattr(inner, "provider", "")
        self.constraint_gap_events: list[dict[str, str]] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def set_current_role(self, role_name: Optional[str]) -> None:
        if hasattr(self.inner, "set_current_role"):
            self.inner.set_current_role(role_name)

    def set_seed(self, seed: Optional[int]) -> None:
        if hasattr(self.inner, "set_seed"):
            self.inner.set_seed(seed)

    def generate(self, prompt: str, schema: dict) -> LLMResponse:
        is_intake = _is_mission_input_schema(schema)
        routed_prompt = (
            prompt + CONSTRAINT_GRAMMAR_INSTRUCTION
            if is_intake else prompt
        )
        response = self.inner.generate(routed_prompt, schema)
        if not is_intake or not isinstance(response.output, dict):
            return response

        payload = dict(response.output)
        valid_constraints: list[str] = []
        failed_constraints: list[dict[str, str]] = []
        for raw in list(payload.get("constraints", []) or []):
            text = str(raw or "").strip()
            if not text:
                continue
            if validate_constraint(text):
                valid_constraints.append(text)
            else:
                failed = {"text": text, "reason": "invalid_grammar"}
                failed_constraints.append(failed)
                self.constraint_gap_events.append(failed)

        payload["constraints"] = valid_constraints
        metadata = dict(payload.get("metadata") or {})
        metadata["extraction_failed_constraints"] = list(failed_constraints)
        metadata["constraints_extracted"] = len(valid_constraints)
        metadata["constraints_failed_grammar"] = len(failed_constraints)
        payload["metadata"] = metadata

        raw_response = dict(response.raw_response or {})
        raw_response["constraint_gap_wrapper"] = {
            "constraints_extracted": len(valid_constraints),
            "constraints_failed_grammar": len(failed_constraints),
            "failed_constraints": list(failed_constraints),
        }
        return LLMResponse(
            output=payload,
            tokens_used=response.tokens_used,
            latency_ms=response.latency_ms,
            raw_response=raw_response,
        )

    def generate_with_trace(self, prompt: str, schema: dict):
        response = self.generate(prompt, schema)
        trace = {}
        if hasattr(self.inner, "generate_with_trace"):
            trace = {
                "constraint_gap_wrapper": "generate_with_trace routed through generate()",
            }
        return response, trace


def _constraint_gap_specs(events: list[dict[str, str]]) -> list[GapSpec]:
    specs: list[GapSpec] = []
    for event in events:
        text = str(event.get("text", "")).strip()
        if not text:
            continue
        specs.append(GapSpec(
            gap_type=GapType.UNKNOWN_PATTERN,
            detected_by="Intake",
            pipeline_stage=1,
            field_or_task="constraints",
            reason=(
                "LLM Intake emitted a constraint that fails the canonical "
                f"MANDATE constraint grammar: {text!r}"
            ),
            action_required=(
                "Operator review: refine the constraint into a canonical "
                "predicate shape (FORBIDS, REQUIRES, IN, or comparison) or "
                "accept it as out-of-scope for machine validation."
            ),
            severity=GapSeverity.DEGRADING,
            location=GapLocation.ANCHOR,
            gap_source=GapSource.EXTRACTION_GAP,
            responsible_party="Mission Author",
            complexity="LOW",
            completion_percentage=0,
            blocking=False,
            partial_spec_available=True,
            input_reference="mission_input.constraints",
        ))
    return specs


def _role_timings(result: Any, *, extraction_timing: Optional[RoleTiming] = None) -> list[RoleTiming]:
    llm_flags = {}
    for rr in getattr(result, "role_results", []) or []:
        arts = getattr(rr, "artifacts", {}) or {}
        llm_flags[getattr(rr, "role_name", "")] = (
            bool(arts.get("llm_used", False)),
            bool(arts.get("llm_fallback", False)),
            str(arts.get("llm_fallback_reason", "")),
        )

    timings: list[RoleTiming] = []
    if extraction_timing is not None:
        timings.append(extraction_timing)

    metric_rows = []
    metrics = getattr(result, "metrics", None)
    if metrics is not None:
        try:
            metric_rows = metrics.to_dict().get("role_timings", []) or []
        except Exception:
            metric_rows = getattr(metrics, "role_timings", []) or []

    if metric_rows:
        for row in metric_rows:
            name = row.get("role_name", "")
            used, fell, reason = llm_flags.get(name, (False, False, ""))
            timings.append(RoleTiming(
                role_name=name,
                status="success" if row.get("success", True) else "failed",
                duration_ms=float(row.get("duration_ms", 0.0)),
                llm_used=used,
                llm_fallback=fell,
                llm_fallback_reason=reason,
            ))
    else:
        for rr in getattr(result, "role_results", []) or []:
            name = getattr(rr, "role_name", "")
            used, fell, reason = llm_flags.get(name, (False, False, ""))
            timings.append(RoleTiming(
                role_name=name,
                status=getattr(getattr(rr, "status", ""), "value", "success"),
                llm_used=used,
                llm_fallback=fell,
                llm_fallback_reason=reason,
            ))
    return timings


def _validation_from_result(result: Any) -> Optional[dict]:
    for role_result in reversed(getattr(result, "role_results", []) or []):
        artifacts = getattr(role_result, "artifacts", {}) or {}
        validation = artifacts.get("validation")
        if isinstance(validation, dict):
            return validation
    return None


def _refresh_result_contract(result: Any) -> None:
    envelope = build_result_envelope(
        ok=bool(getattr(result, "ok", False)),
        artifact=getattr(result, "artifact", None),
        gap_reports=list(getattr(result, "gap_reports", []) or []),
        schema_valid=getattr(result, "schema_valid", None),
        errors=list(getattr(result, "errors", []) or []),
        validation=_validation_from_result(result),
    )
    result.result_envelope = envelope
    result.execution_state = str(envelope["execution_state"])
    result.contract_schema_version = str(envelope["contract_schema_version"])


def _record_from_result(
    *,
    run_id: str,
    task_id: str,
    system_id: str,
    system_label: str,
    run_number: int,
    seed: Optional[int],
    started_at: str,
    elapsed_ms: float,
    result: Any,
    role_timings: list[RoleTiming],
    model_versions: dict,
    decoding_params: dict,
    api_cost_usd: Optional[float] = None,
) -> RunRecord:
    artifact = getattr(result, "artifact", None)
    gap_reports = list(getattr(result, "gap_reports", []) or [])
    execution_state = str(getattr(result, "execution_state", "") or "")
    contract_schema_version = str(
        getattr(result, "contract_schema_version", "") or CONTRACT_SCHEMA_VERSION
    )
    result_envelope = dict(getattr(result, "result_envelope", {}) or {})
    if not execution_state:
        raise ValueError("core result did not provide execution_state")
    if not result_envelope:
        raise ValueError("core result did not provide result_envelope")
    envelope_issues = validate_result_envelope(
        result_envelope,
        artifact=artifact,
        gap_reports=gap_reports,
        schema_valid=getattr(result, "schema_valid", None),
        errors=list(getattr(result, "errors", []) or []),
        validation=_validation_from_result(result),
    )
    if envelope_issues:
        raise ValueError("core result envelope failed validation: " + "; ".join(envelope_issues))
    model_versions = dict(model_versions or {})
    model_versions.update({
        "mlt_stack_version": MLT_VERSION,
        "mlt_git_commit": MLT_GIT_COMMIT,
        "apparatus_git_commit": APPARATUS_GIT_COMMIT,
        "mlt_git_dirty": MLT_GIT_DIRTY,
        "apparatus_git_dirty": APPARATUS_GIT_DIRTY,
        "mlt_source_hashes": dict(MLT_EXPERIMENT_SOURCE_HASHES),
        "apparatus_source_hashes": dict(APPARATUS_EXPERIMENT_SOURCE_HASHES),
        "contract_schema_version": contract_schema_version,
    })
    validation = _validation_from_result(result)
    rec = RunRecord(
        run_id=run_id,
        task_id=task_id,
        system_id=system_id,
        system_label=system_label,
        run_number=run_number,
        seed=seed,
        started_at=started_at,
        wall_clock_ms=elapsed_ms,
        local_compute_ms=elapsed_ms,
        api_cost_usd=api_cost_usd,
        model_versions=model_versions,
        decoding_params=decoding_params,
        code_ref=CODE_REF,
        role_timings=role_timings,
        output_type=str(result_envelope.get("output_representation") or (
            OUTPUT_MANDATE_AS_CODE if artifact else OUTPUT_GAP_REPORT
        )),
        output={
            "artifact": artifact,
            "gap_reports": gap_reports,
            "has_gaps": bool(gap_reports),
            "schema_valid": getattr(result, "schema_valid", None),
            "validation": validation,
            "execution_state": execution_state,
            "contract_schema_version": contract_schema_version,
            "result_envelope": result_envelope,
        },
        execution_state=execution_state,
        contract_schema_version=contract_schema_version,
        ok=bool(result_envelope.get("ok", False)),
        errors=list(getattr(result, "errors", []) or []),
    )
    return rec


def run_cond_a(
    task_id: str,
    task_text: str,
    mission_input: MissionInput,
    seed: int = 20260623,
    *,
    run_id: Optional[str] = None,
    run_number: int = 1,
    started_at: str = "",
    extraction_duration_ms: float = 0.0,
    domain_profile_mode: str = "default",
) -> dict:
    """Cond-A: pre-extracted MissionInput -> deterministic MLT MANDATE."""
    from apparatus.harness.records import utc_now_iso

    rid = run_id or f"cond_a__{task_id}__r{run_number:02d}"
    started = started_at or utc_now_iso()
    profile = _resolve_domain_profile(task_id, domain_profile_mode)
    profile_name = getattr(profile, "domain_id", None)
    t0 = time.time()
    result = Pipeline(PipelineConfig(
        strict=False,
        emit_gaps=True,
        domain_profile=profile,
    )).run(mission_input)
    _refresh_result_contract(result)
    elapsed_ms = (time.time() - t0) * 1000.0 + float(extraction_duration_ms or 0.0)
    extraction_cost = float(mission_input.metadata.get("extraction_cost_usd", 0.0) or 0.0)
    extraction_timing = RoleTiming(
        role_name="PreExtractor",
        status="success",
        duration_ms=float(extraction_duration_ms or 0.0),
        llm_used=True,
        llm_fallback=False,
    )
    rec = _record_from_result(
        run_id=rid,
        task_id=task_id,
        system_id="cond_a",
        system_label=COND_A_LABEL,
        run_number=run_number,
        seed=seed,
        started_at=started,
        elapsed_ms=elapsed_ms,
        result=result,
        role_timings=_role_timings(result, extraction_timing=extraction_timing),
        model_versions={
            "mlt": CODE_REF,
            "extraction_model": mission_input.metadata.get("extraction_model", ""),
            "total_input_tokens": mission_input.metadata.get("input_tokens", 0),
            "total_output_tokens": mission_input.metadata.get("output_tokens", 0),
        },
        decoding_params={
            "condition": "cond_a",
            "pipeline_strict": False,
            "emit_gaps": True,
            "domain_profile_mode": domain_profile_mode,
            "domain_profile_name": profile_name,
        },
        api_cost_usd=round(extraction_cost, 6),
    )
    if isinstance(rec.output, dict):
        rec.output["mission_input_metadata"] = dict(mission_input.metadata or {})
        rec.output["domain_profile_mode"] = domain_profile_mode
        rec.output["domain_profile_name"] = profile_name
    return rec.to_dict()


def run_cond_b(
    task_id: str,
    task_text: str,
    llm_adapter: LLMAdapter,
    seed: int = 20260623,
    *,
    run_id: Optional[str] = None,
    run_number: int = 1,
    started_at: str = "",
    retry_backoff_sec=DEFAULT_RETRY_BACKOFF_SEC,
    domain_profile_mode: str = "default",
) -> dict:
    """Cond-B: canonical MLT MANDATE with LLM advisory hooks enabled."""
    from apparatus.harness.records import utc_now_iso

    rid = run_id or f"cond_b__{task_id}__r{run_number:02d}"
    started = started_at or utc_now_iso()
    profile = _resolve_domain_profile(task_id, domain_profile_mode)
    profile_name = getattr(profile, "domain_id", None)
    mission_input = MissionInput(mission_id=task_id, intent=task_text)
    resilient_adapter = RetryingLLMClient(
        llm_adapter,
        retry_backoff_sec=retry_backoff_sec,
    )
    recording_adapter = RecordingLLMAdapter(resilient_adapter)
    routing_adapter = ConstraintGapRoutingAdapter(recording_adapter)
    cfg = PipelineConfig(
        strict=False,
        emit_gaps=True,
        llm_adapter=routing_adapter,
        llm_fallback_enabled=True,
        domain_profile=profile,
    )
    t0 = time.time()
    result = Pipeline(cfg).run(mission_input)
    elapsed_ms = (time.time() - t0) * 1000.0
    extraction_gap_specs = _constraint_gap_specs(routing_adapter.constraint_gap_events)
    if extraction_gap_specs:
        mission_id = (
            getattr(result, "artifact", {}) or {}
        ).get("mandate_id") or task_id
        extra_reports = build_gap_reports(extraction_gap_specs, mission_id)
        result.gap_reports = list(getattr(result, "gap_reports", []) or []) + extra_reports
    _refresh_result_contract(result)
    adapter_cfg = getattr(llm_adapter, "config", None)
    model = getattr(adapter_cfg, "model_path", getattr(llm_adapter, "model", ""))
    provider_calls = list(recording_adapter.calls)
    total_input_tokens = sum(int(call.get("input_tokens") or 0) for call in provider_calls)
    total_output_tokens = sum(int(call.get("output_tokens") or 0) for call in provider_calls)
    total_cost = round(
        sum(float(call.get("cost_usd") or 0.0) for call in provider_calls),
        6,
    )
    rec = _record_from_result(
        run_id=rid,
        task_id=task_id,
        system_id="cond_b",
        system_label=COND_B_LABEL,
        run_number=run_number,
        seed=seed,
        started_at=started,
        elapsed_ms=elapsed_ms,
        result=result,
        role_timings=_role_timings(result),
        model_versions={
            "mlt": CODE_REF,
            "llm_model": model,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
        },
        decoding_params={
            "condition": "cond_b",
            "pipeline_strict": False,
            "emit_gaps": True,
            "llm_fallback_enabled": True,
            "llm_backend": (
                getattr(llm_adapter, "provider", "")
                or getattr(getattr(llm_adapter, "client", None), "provider", "")
            ),
            "llm_max_tokens": getattr(adapter_cfg, "max_tokens", None),
            "llm_temperature": getattr(adapter_cfg, "temperature", None),
            "domain_profile_mode": domain_profile_mode,
            "domain_profile_name": profile_name,
        },
        api_cost_usd=total_cost,
    )
    if isinstance(rec.output, dict):
        failed_count = len(extraction_gap_specs)
        rec.output.setdefault("metadata", {})["extraction_failed_constraints"] = failed_count
        rec.output["extraction_failed_constraints"] = failed_count
        rec.output["domain_profile_mode"] = domain_profile_mode
        rec.output["domain_profile_name"] = profile_name
        rec.output["provider_responses"] = provider_calls
        rec.output["provider_response_count"] = len(provider_calls)
    return rec.to_dict()


class CondASystem(System):
    system_id = "cond_a"
    system_label = COND_A_LABEL
    output_type = OUTPUT_MANDATE_AS_CODE

    def __init__(self, extraction_model: str = "claude-sonnet-4-6",
                 extractor=None, domain_profile_mode: str = "default",
                 cost_ledger=None):
        self.extraction_model = extraction_model
        self.extractor = extractor
        self.domain_profile_mode = domain_profile_mode
        self.cost_ledger = cost_ledger

    def run(self, request_text: str, *, run_id: str, task_id: str,
            run_number: int, seed: Optional[int] = None) -> RunRecord:
        from apparatus.harness.records import utc_now_iso
        from apparatus.preprocess.extract_mission_input import extract

        started = utc_now_iso()
        t0 = time.time()
        if self.extractor is not None:
            mission_input = self.extractor(task_id, request_text, self.extraction_model)
        else:
            mission_input = extract(
                task_id,
                request_text,
                self.extraction_model,
                cost_ledger=self.cost_ledger,
                run_id=run_id,
                run_number=run_number,
            )
        extraction_ms = (time.time() - t0) * 1000.0
        d = run_cond_a(
            task_id,
            request_text,
            mission_input,
            seed=seed or 20260623,
            run_id=run_id,
            run_number=run_number,
            started_at=started,
            extraction_duration_ms=extraction_ms,
            domain_profile_mode=self.domain_profile_mode,
        )
        return RunRecord.from_dict(d)


class CondBSystem(System):
    system_id = "cond_b"
    system_label = COND_B_LABEL
    output_type = OUTPUT_MANDATE_AS_CODE

    def __init__(
        self,
        *,
        llm_backend: str = "anthropic",
        llm_model: str = "claude-sonnet-4-6",
        llm_adapter: Optional[LLMAdapter] = None,
        domain_profile_mode: str = "default",
        cost_ledger=None,
        retry_backoff_sec=DEFAULT_RETRY_BACKOFF_SEC,
    ):
        if llm_backend not in ("anthropic", "ollama") and llm_adapter is None:
            raise ValueError(
                "only --llm-backend anthropic or ollama is supported for Cond-B"
            )
        self.llm_backend = llm_backend
        self.llm_model = llm_model
        if llm_adapter is not None:
            self.llm_adapter = llm_adapter
        elif llm_backend == "ollama":
            self.llm_adapter = OllamaMLTAdapter(model=llm_model)
        else:
            try:
                self.llm_adapter = AnthropicMLTAdapter(model=llm_model, cost_ledger=cost_ledger)
            except TypeError:
                self.llm_adapter = AnthropicMLTAdapter(model=llm_model)
        self.domain_profile_mode = domain_profile_mode
        self.cost_ledger = cost_ledger
        self.retry_backoff_sec = retry_backoff_sec

    def run(self, request_text: str, *, run_id: str, task_id: str,
            run_number: int, seed: Optional[int] = None) -> RunRecord:
        if hasattr(self.llm_adapter, "set_seed"):
            self.llm_adapter.set_seed(seed or 20260623)
        if hasattr(self.llm_adapter, "set_budget_context"):
            self.llm_adapter.set_budget_context(
                run_id=run_id,
                system_id=self.system_id,
                task_id=task_id,
                run_number=run_number,
            )
        d = run_cond_b(
            task_id,
            request_text,
            self.llm_adapter,
            seed=seed or 20260623,
            run_id=run_id,
            run_number=run_number,
            domain_profile_mode=self.domain_profile_mode,
            retry_backoff_sec=self.retry_backoff_sec,
        )
        return RunRecord.from_dict(d)


# ── Canonical (MLT) ablations ──────────────────────────────────────────────
# The seven pre-registered ablations (PROTOCOL_LOCK §5) expressed as canonical
# MLT MANDATE PipelineConfig overrides. A1/A2/A4/A6/A7 were previously
# classified AEGIS-variants (source-level, unbuilt); MLT v1.0.0rc1 now exposes
# them as config switches (mlt.mandate.PipelineConfig.ablate_*), so every
# ablation runs against the SAME canonical engine that produces Cond-A/Cond-B —
# removing the apples-to-oranges seam where ablations ran on the AEGIS-eval
# engine while the comparative conditions ran on MLT. A3/A5 keep their original
# overrides. The frozen apparatus/ablations/manifest.py is left unchanged; this
# is the canonical execution path on top of it.
CANONICAL_ABLATION_OVERRIDES: dict[str, dict] = {
    "A1": {"ablate_role_separation": True},   # one combined call (needs adapter)
    "A2": {"ablate_tolerance_bands": True},   # collapse min/target bands
    "A3": {"emit_gaps": False},               # suppress gap-report artifact
    "A4": {"ablate_validation": True},        # drop Validation role checks/gate
    # A5 removes the precedent registry. NOTE (contrast caveat): the canonical
    # baseline path (run_ablation base cfg + Cond-A/Cond-B) already runs WITHOUT a
    # success_registry, so A5 == baseline and its measured marginal contribution is
    # zero *by construction*. This is an honest result (removing an unused
    # component has no effect), not evidence the registry is worthless: to measure
    # A5 the baseline must first be configured with a seeded success_registry.
    # Reported as N/A rather than a spurious null effect unless that is done.
    "A5": {"success_registry": None},         # no precedent registry (see note above)
    "A6": {"ablate_search_trace": True},      # suppress trace entries + chain
    "A7": {"ablate_nist_rmf": True},          # drop NIST AI RMF metadata
}


def run_ablation(
    task_id: str,
    task_text: str,
    mission_input: MissionInput,
    ablation_id: str,
    seed: int = 20260623,
    *,
    run_id: Optional[str] = None,
    run_number: int = 1,
    started_at: str = "",
    extraction_duration_ms: float = 0.0,
    domain_profile_mode: str = "default",
    llm_adapter: Optional[LLMAdapter] = None,
) -> dict:
    """Run one ablation against canonical MLT MANDATE on a pre-extracted
    ``MissionInput`` (the deterministic, Cond-A-style path), with the ablation's
    PipelineConfig override layered on. A1 (role separation) additionally
    requires an ``llm_adapter`` for its single combined call."""
    from apparatus.harness.records import utc_now_iso

    aid = str(ablation_id or "").upper().strip()
    overrides = CANONICAL_ABLATION_OVERRIDES.get(aid)
    if overrides is None:
        raise KeyError(
            "unknown canonical ablation id %r (the seven are: %s)"
            % (ablation_id, ", ".join(sorted(CANONICAL_ABLATION_OVERRIDES)))
        )

    rid = run_id or f"ablation_{aid.lower()}__{task_id}__r{run_number:02d}"
    started = started_at or utc_now_iso()
    profile = _resolve_domain_profile(task_id, domain_profile_mode)
    profile_name = getattr(profile, "domain_id", None)

    cfg_kwargs: dict[str, Any] = dict(strict=False, emit_gaps=True, domain_profile=profile)
    cfg_kwargs.update(overrides)
    if overrides.get("ablate_role_separation"):
        # A1: the single combined pass is an LLM ablation; never silently fall
        # back to the role-separated pipeline.
        cfg_kwargs["llm_adapter"] = llm_adapter
        cfg_kwargs["llm_fallback_enabled"] = False

    t0 = time.time()
    result = Pipeline(PipelineConfig(**cfg_kwargs)).run(mission_input)
    elapsed_ms = (time.time() - t0) * 1000.0 + float(extraction_duration_ms or 0.0)

    rec = _record_from_result(
        run_id=rid,
        task_id=task_id,
        system_id=f"ablation_{aid.lower()}",
        system_label=f"Ablation {aid} (canonical MLT v1.0.0rc1)",
        run_number=run_number,
        seed=seed,
        started_at=started,
        elapsed_ms=elapsed_ms,
        result=result,
        role_timings=_role_timings(result),
        model_versions={"mlt": CODE_REF, "ablation": aid},
        decoding_params={
            "condition": f"ablation_{aid.lower()}",
            "ablation_id": aid,
            "config_overrides": dict(overrides),
            "domain_profile_mode": domain_profile_mode,
            "domain_profile_name": profile_name,
        },
        api_cost_usd=None,
    )
    if isinstance(rec.output, dict):
        rec.output["ablation_id"] = aid
        # A5 internal-validity fix: the canonical baseline runs WITHOUT a
        # success_registry, so removing it (A5) is a null-by-construction control
        # with zero measurable contrast. Tag it explicitly so the analysis layer
        # excludes A5 from marginal-effect claims (reported N/A) rather than
        # surfacing a spurious ~0 effect that could be misread as "the registry
        # does nothing". A genuine measurement requires a registry-seeded
        # reference arm (see the CANONICAL_ABLATION_OVERRIDES['A5'] note).
        if aid == "A5":
            rec.output["contrast_applicable"] = False
            rec.output["contrast_na_reason"] = (
                "baseline has no success_registry; A5 removal has zero contrast "
                "by construction — measure only against a registry-seeded reference"
            )
    return rec.to_dict()


class CanonicalAblationSystem(System):
    """Run one ablation (A1-A7) against canonical MLT MANDATE through the same
    extract-then-run path as Cond-A, with the ablation override layered on.

    Deterministic ablations (A2/A4/A6/A7, plus A3/A5) need no model beyond the
    Cond-A pre-extraction; A1 requires ``llm_adapter`` for the combined call.
    """

    output_type = OUTPUT_MANDATE_AS_CODE

    def __init__(
        self,
        *,
        ablation_id: str,
        extraction_model: str = "claude-sonnet-4-6",
        extractor=None,
        domain_profile_mode: str = "default",
        llm_adapter: Optional[LLMAdapter] = None,
    ):
        aid = str(ablation_id or "").upper().strip()
        if aid not in CANONICAL_ABLATION_OVERRIDES:
            raise KeyError(
                "unknown canonical ablation id %r (the seven are: %s)"
                % (ablation_id, ", ".join(sorted(CANONICAL_ABLATION_OVERRIDES)))
            )
        self.ablation_id = aid
        self.system_id = f"ablation_{aid.lower()}"
        self.system_label = f"Ablation {aid} (canonical MLT v1.0.0rc1)"
        self.extraction_model = extraction_model
        self.extractor = extractor
        self.domain_profile_mode = domain_profile_mode
        self.llm_adapter = llm_adapter

    def run(self, request_text: str, *, run_id: str, task_id: str,
            run_number: int, seed: Optional[int] = None) -> RunRecord:
        from apparatus.harness.records import utc_now_iso
        from apparatus.preprocess.extract_mission_input import extract

        started = utc_now_iso()
        t0 = time.time()
        extractor = self.extractor or extract
        mission_input = extractor(task_id, request_text, self.extraction_model)
        extraction_ms = (time.time() - t0) * 1000.0
        d = run_ablation(
            task_id,
            request_text,
            mission_input,
            self.ablation_id,
            seed=seed or 20260623,
            run_id=run_id,
            run_number=run_number,
            started_at=started,
            extraction_duration_ms=extraction_ms,
            domain_profile_mode=self.domain_profile_mode,
            llm_adapter=self.llm_adapter,
        )
        return RunRecord.from_dict(d)
