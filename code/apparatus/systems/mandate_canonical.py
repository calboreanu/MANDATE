"""Adapter from the eval apparatus to canonical MLT MANDATE v1.0.0rc1.

Two conditions are exposed:

* Cond-A: Sonnet pre-extracts a structured ``MissionInput``; deterministic
  canonical MLT MANDATE performs the planning.
* Cond-B: canonical MLT MANDATE runs with its LLM advisory hooks enabled,
  using an Anthropic-backed ``mlt.sdk.llm.LLMAdapter`` bridge.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Optional

from apparatus.baselines.base import extract_json
from apparatus.baselines.llm_client import AnthropicClient
from apparatus.harness.records import (
    OUTPUT_GAP_REPORT,
    OUTPUT_MANDATE_AS_CODE,
    RoleTiming,
    RunRecord,
)
from apparatus.harness.system import System
from apparatus.llm_retry import DEFAULT_RETRY_BACKOFF_SEC, RetryingLLMClient

MLT_ROOT = Path.home() / "Desktop" / "MLT-Governance-Stack"
MLT_SRC = MLT_ROOT / "src"
if str(MLT_SRC) not in sys.path:
    sys.path.insert(0, str(MLT_SRC))

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


CODE_REF = "mlt-stack-1.0.0rc1"
COND_A_LABEL = "MANDATE v1.0.0rc1, structured-input, deterministic"
COND_B_LABEL = "MANDATE v1.0.0rc1, LLM-augmented Interpreter, end-to-end"
_TASK_DOMAIN_TO_PROFILE_NAME = {
    "INT": "defense_intel",
    "SEC": "incident_response",
    "FIN": None,  # no canonical financial profile in MLT v1.0.0rc1
}
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
    ):
        self.client = client or AnthropicClient()
        self.model = model
        self.config = LLMConfig(
            model_path=model,
            max_tokens=max_tokens,
            temperature=temperature,
            retry_count=retry_count,
        )

    def generate(self, prompt: str, schema: dict) -> LLMResponse:
        t0 = time.time()
        resp = self.client.generate(
            system=("You are a schema-constrained MANDATE role assistant. "
                    "Return JSON only."),
            user=prompt,
            model=self.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        parsed, _ = extract_json(resp.text)
        output: Any = parsed if parsed is not None else resp.text
        return LLMResponse(
            output=output,
            tokens_used=int((resp.input_tokens or 0) + (resp.output_tokens or 0)),
            latency_ms=(time.time() - t0) * 1000.0,
            raw_response={
                "model": self.model,
                "input_tokens": resp.input_tokens,
                "output_tokens": resp.output_tokens,
                "cost_usd": resp.cost_usd,
                "text": resp.text,
            },
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
        self.constraint_gap_events: list[dict[str, str]] = []

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
        output_type=OUTPUT_MANDATE_AS_CODE if artifact else OUTPUT_GAP_REPORT,
        output={
            "artifact": artifact,
            "gap_reports": gap_reports,
            "has_gaps": bool(gap_reports),
            # Honest schema-validity verdict from the engine (P0-G): an ablation
            # may emit an artifact (ok=True) that is intentionally schema-invalid
            # (A1 single-pass, A6 empty trace). Graders must read this, not ok.
            "schema_valid": getattr(result, "schema_valid", None),
        },
        ok=bool(getattr(result, "ok", False)),
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
    routing_adapter = ConstraintGapRoutingAdapter(resilient_adapter)
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
        if getattr(result, "artifact", None):
            metadata = result.artifact.setdefault("metadata", {})
            metadata["extraction_failed_constraints"] = len(extraction_gap_specs)
            metadata["extraction_failed_constraint_texts"] = [
                event["text"] for event in routing_adapter.constraint_gap_events
                if event.get("text")
            ]
    adapter_cfg = getattr(llm_adapter, "config", None)
    model = getattr(adapter_cfg, "model_path", getattr(llm_adapter, "model", ""))
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
        model_versions={"mlt": CODE_REF, "llm_model": model},
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
        api_cost_usd=None,
    )
    if isinstance(rec.output, dict):
        failed_count = len(extraction_gap_specs)
        rec.output.setdefault("metadata", {})["extraction_failed_constraints"] = failed_count
        rec.output["extraction_failed_constraints"] = failed_count
        rec.output["domain_profile_mode"] = domain_profile_mode
        rec.output["domain_profile_name"] = profile_name
    return rec.to_dict()


class CondASystem(System):
    system_id = "cond_a"
    system_label = COND_A_LABEL
    output_type = OUTPUT_MANDATE_AS_CODE

    def __init__(self, extraction_model: str = "claude-sonnet-4-6",
                 extractor=None, domain_profile_mode: str = "default"):
        self.extraction_model = extraction_model
        self.extractor = extractor
        self.domain_profile_mode = domain_profile_mode

    def run(self, request_text: str, *, run_id: str, task_id: str,
            run_number: int, seed: Optional[int] = None) -> RunRecord:
        from apparatus.harness.records import utc_now_iso
        from apparatus.preprocess.extract_mission_input import extract

        started = utc_now_iso()
        t0 = time.time()
        extractor = self.extractor or extract
        mission_input = extractor(task_id, request_text, self.extraction_model)
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
            self.llm_adapter = AnthropicMLTAdapter(model=llm_model)
        self.domain_profile_mode = domain_profile_mode

    def run(self, request_text: str, *, run_id: str, task_id: str,
            run_number: int, seed: Optional[int] = None) -> RunRecord:
        if hasattr(self.llm_adapter, "set_seed"):
            self.llm_adapter.set_seed(seed or 20260623)
        d = run_cond_b(
            task_id,
            request_text,
            self.llm_adapter,
            seed=seed or 20260623,
            run_id=run_id,
            run_number=run_number,
            domain_profile_mode=self.domain_profile_mode,
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
