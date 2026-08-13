import sys
from pathlib import Path

import os
MLT_SRC = (Path(os.environ["MLT_ROOT"]) if os.environ.get("MLT_ROOT") else Path.home() / "Desktop" / "MLT-Governance-Stack") / "src"
if str(MLT_SRC) not in sys.path:
    sys.path.insert(0, str(MLT_SRC))

from mlt.mandate.models import MissionInput
from mlt.sdk.llm import LLMAdapter, LLMConfig, LLMResponse

from apparatus.harness.records import OUTPUT_MANDATE_AS_CODE
from apparatus.systems.mandate_canonical import (
    AnthropicMLTAdapter,
    CondASystem,
    CondBSystem,
    OllamaMLTAdapter,
    _resolve_domain_profile,
    run_cond_a,
    run_cond_b,
)


class FakeMLTAdapter(LLMAdapter):
    def __init__(self, *, constraints=None):
        self.config = LLMConfig(model_path="fake", retry_count=0)
        self.calls = []
        self.constraints = list(constraints or ["FORBIDS data_exfiltration"])

    def generate(self, prompt, schema):
        self.calls.append((prompt, schema))
        props = schema.get("properties", {})
        output = {}
        if "mission_id" in props:
            output.update({
                "mission_id": "TASK-X",
                "intent": "Plan the mission.",
                "minimum_outcome": "Minimum outcome.",
                "target_outcome": "Target outcome.",
                "constraints": list(self.constraints),
                "scope": ["scope"],
                "risk_tolerance": "LOW",
            })
        else:
            output["decision_summary"] = "Use deterministic core."
            if "minimum_outcome" in props:
                output["minimum_outcome"] = "Minimum outcome."
            if "target_outcome" in props:
                output["target_outcome"] = "Target outcome."
            if "risk_tolerance" in props:
                output["risk_tolerance"] = "LOW"
            if "candidate_coa_count" in props:
                output["candidate_coa_count"] = 1
            if "selected_reference_ids" in props:
                output["selected_reference_ids"] = []
        return LLMResponse(
            output=output,
            tokens_used=7,
            latency_ms=1.0,
            raw_response={
                "input_tokens": 4,
                "output_tokens": 3,
                "cost_usd": 0.000057,
                "text": "{}",
            },
        )

    def generate_with_trace(self, prompt, schema):
        response = self.generate(prompt, schema)
        return response, {"calls": len(self.calls)}


class FlakyMLTAdapter(FakeMLTAdapter):
    def generate(self, prompt, schema):
        if not self.calls:
            self.calls.append((prompt, schema))
            raise RuntimeError("529 overloaded_error")
        return super().generate(prompt, schema)


class FakeTextClient:
    provider = "mock"

    def generate(self, **kwargs):
        from apparatus.baselines.llm_client import LLMResponse
        return LLMResponse(
            text='{"decision_summary": "ok"}',
            model=kwargs["model"],
            input_tokens=3,
            output_tokens=2,
        )


def mission_input():
    return MissionInput(
        mission_id="TASK-X",
        intent="Assess the mission.",
        minimum_outcome="Minimum outcome.",
        target_outcome="Target outcome.",
        constraints=["FORBIDS data_exfiltration"],
        risk_tolerance="LOW",
    )


def test_run_cond_a_returns_runrecord_dict():
    d = run_cond_a("TASK-X", "request", mission_input(), seed=1)
    assert d["system_id"] == "cond_a"
    assert d["task_id"] == "TASK-X"
    assert d["output_type"] == OUTPUT_MANDATE_AS_CODE
    assert d["output"]["artifact"]["anchor"]["mission_intent"]
    assert d["decoding_params"]["domain_profile_mode"] == "default"
    assert d["decoding_params"]["domain_profile_name"] is None
    assert d["output"]["domain_profile_mode"] == "default"
    assert d["output"]["domain_profile_name"] is None
    assert d["execution_state"] in {
        "EXECUTABLE",
        "NON_EXECUTABLE_GAPS",
        "NON_EXECUTABLE_VALIDATION",
        "FAILED",
    }
    assert d["contract_schema_version"] == "mandate-result-envelope.v1"
    assert d["output"]["result_envelope"]["execution_state"] == d["execution_state"]


def test_resolve_domain_profile_default_mode_returns_none():
    assert _resolve_domain_profile("TASK-MAIN-INT-034", "default") is None
    assert _resolve_domain_profile("TASK-MAIN-SEC-001", "default") is None
    assert _resolve_domain_profile("TASK-MAIN-FIN-001", "default") is None


def test_resolve_domain_profile_auto_mode_routes_int():
    profile = _resolve_domain_profile("TASK-MAIN-INT-034", "auto")
    assert profile is not None
    assert profile.domain_id == "defense_intel"


def test_resolve_domain_profile_auto_mode_routes_sec():
    profile = _resolve_domain_profile("TASK-MAIN-SEC-014", "auto")
    assert profile is not None
    assert profile.domain_id == "incident_response"


def test_resolve_domain_profile_auto_mode_fin_falls_back_to_none():
    assert _resolve_domain_profile("TASK-MAIN-FIN-001", "auto") is None


def test_resolve_domain_profile_malformed_task_id_returns_none():
    assert _resolve_domain_profile("NO-COLONS", "auto") is None
    assert _resolve_domain_profile("", "auto") is None


def test_run_cond_a_records_auto_domain_profile_metadata():
    d = run_cond_a(
        "TASK-MAIN-INT-034",
        "request",
        mission_input(),
        seed=1,
        domain_profile_mode="auto",
    )
    assert d["decoding_params"]["domain_profile_mode"] == "auto"
    assert d["decoding_params"]["domain_profile_name"] == "defense_intel"
    assert d["output"]["domain_profile_mode"] == "auto"
    assert d["output"]["domain_profile_name"] == "defense_intel"


def test_cond_a_system_uses_injected_extractor():
    def fake_extract(task_id, task_text, model):
        return mission_input()

    rec = CondASystem(extractor=fake_extract).run(
        "request", run_id="cond_a__TASK-X__r01",
        task_id="TASK-X", run_number=1, seed=10)
    assert rec.system_id == "cond_a"
    assert rec.ok is False
    assert rec.execution_state == "NON_EXECUTABLE_GAPS"
    assert rec.role_timings[0].role_name == "PreExtractor"


def test_anthropic_mlt_adapter_parses_json_text():
    adapter = AnthropicMLTAdapter(model="mock", client=FakeTextClient())
    resp = adapter.generate("prompt", {"type": "object"})
    assert resp.output == {"decision_summary": "ok"}
    assert resp.tokens_used == 5
    assert resp.raw_response["model"] == "mock"


def test_run_cond_b_with_fake_adapter_runs_pipeline():
    d = run_cond_b("TASK-X", "Assess the mission.", FakeMLTAdapter(), seed=2)
    assert d["system_id"] == "cond_b"
    assert d["task_id"] == "TASK-X"
    assert d["output"]["artifact"]["anchor"]["mission_intent"]
    assert len(d["role_timings"]) == 6
    assert d["api_cost_usd"] is not None
    assert d["api_cost_usd"] >= 0.0
    assert d["output"]["provider_response_count"] == len(d["output"]["provider_responses"])
    assert d["output"]["provider_responses"]
    assert d["output"]["provider_responses"][0]["role"]
    assert d["output"]["provider_responses"][0]["raw_response"]["retry"]["attempts"] == 1
    assert d["output"]["provider_responses"][0]["raw_response"]["retry"]["final_status"] == "success"
    assert d["execution_state"] in {
        "EXECUTABLE",
        "NON_EXECUTABLE_GAPS",
        "NON_EXECUTABLE_VALIDATION",
        "FAILED",
    }


def extraction_gap_reports(record):
    return [
        gap for gap in record["output"].get("gap_reports", [])
        if gap.get("gap_source") == "EXTRACTION_GAP"
    ]


def test_cond_b_wrapper_routes_invalid_constraints_to_gaps():
    adapter = FakeMLTAdapter(constraints=[
        "FORBIDS exfil",
        "Must align with NIST 800-37",
    ])
    d = run_cond_b("TASK-X", "Assess the mission.", adapter, seed=2)
    anchor = d["output"]["artifact"]["anchor"]
    gaps = extraction_gap_reports(d)
    assert d["ok"] is True
    assert anchor["constraints"] == ["FORBIDS exfil"]
    assert len(gaps) == 1
    assert gaps[0]["gap_type"] == "UNKNOWN_PATTERN"
    assert gaps[0]["gap_source"] == "EXTRACTION_GAP"
    assert "Must align with NIST 800-37" in gaps[0]["reason"]
    assert d["output"]["metadata"]["extraction_failed_constraints"] == 1


def test_cond_b_wrapper_passes_through_valid_constraints():
    adapter = FakeMLTAdapter(constraints=[
        "FORBIDS exfil",
        "target.scope IN ['system_a']",
    ])
    d = run_cond_b("TASK-X", "Assess the mission.", adapter, seed=2)
    anchor = d["output"]["artifact"]["anchor"]
    assert d["ok"] is False
    assert d["execution_state"] == "NON_EXECUTABLE_GAPS"
    assert anchor["constraints"] == ["FORBIDS exfil", "target.scope IN ['system_a']"]
    assert extraction_gap_reports(d) == []
    assert d["output"]["metadata"]["extraction_failed_constraints"] == 0


def test_cond_b_wrapper_run_completes_on_all_invalid():
    adapter = FakeMLTAdapter(constraints=[
        "Must align with NIST 800-37",
        "Deliver final report within two weeks",
        "No operational disruption",
        "Coordinate with the board",
        "Use approved playbooks",
    ])
    d = run_cond_b("TASK-X", "Assess the mission.", adapter, seed=2)
    anchor = d["output"]["artifact"]["anchor"]
    gaps = extraction_gap_reports(d)
    assert d["ok"] is True
    assert anchor["constraints"] == []
    assert len(gaps) == 5
    assert d["output"]["metadata"]["extraction_failed_constraints"] == 5


def test_cond_b_wrapper_uses_retrying_llm_client():
    adapter = FlakyMLTAdapter()
    d = run_cond_b(
        "TASK-X",
        "Assess the mission.",
        adapter,
        seed=2,
        retry_backoff_sec=(0.0, 0.0, 0.0),
    )
    assert d["ok"] is True
    assert d["output"]["artifact"]["anchor"]["mission_intent"]
    assert len(adapter.calls) >= 2


def test_cond_b_system_accepts_injected_adapter():
    rec = CondBSystem(llm_adapter=FakeMLTAdapter()).run(
        "Assess the mission.", run_id="cond_b__TASK-X__r01",
        task_id="TASK-X", run_number=1, seed=10)
    assert rec.system_id == "cond_b"
    assert rec.output_type == OUTPUT_MANDATE_AS_CODE
    assert rec.model_versions["llm_model"] == "fake"


def test_cond_b_system_anthropic_default_unchanged(monkeypatch):
    created = {}

    class FakeAnthropicAdapter(FakeMLTAdapter):
        def __init__(self, model):
            super().__init__()
            self.config = LLMConfig(model_path=model, retry_count=0)
            created["model"] = model

    monkeypatch.setattr(
        "apparatus.systems.mandate_canonical.AnthropicMLTAdapter",
        FakeAnthropicAdapter,
    )
    rec = CondBSystem(llm_backend="anthropic", llm_model="mock").run(
        "Assess the mission.", run_id="cond_b__TASK-X__r01",
        task_id="TASK-X", run_number=1, seed=10)
    assert rec.system_id == "cond_b"
    assert rec.ok is True
    assert created["model"] == "mock"
    assert rec.decoding_params["llm_backend"] == ""


def test_ollama_mlt_adapter_smoke():
    calls = []

    def fake_call_json(**kwargs):
        calls.append(kwargs)
        return {
            "mission_id": "TASK-X",
            "intent": "Plan the mission.",
            "constraints": ["FORBIDS data_exfiltration"],
        }

    adapter = OllamaMLTAdapter(
        model="qwen2.5:32b",
        seed=20260624,
        call_json=fake_call_json,
    )
    resp = adapter.generate("prompt", {"type": "object"})
    assert resp.output["mission_id"] == "TASK-X"
    assert resp.raw_response["provider"] == "ollama"
    assert calls[0]["model"] == "qwen2.5:32b"
    assert calls[0]["format"] == "json"
    assert calls[0]["options"]["temperature"] == 0.0
    assert calls[0]["options"]["seed"] == 20260624


def test_cond_b_system_accepts_ollama_backend(monkeypatch):
    created = {}

    class FakeOllamaAdapter(FakeMLTAdapter):
        provider = "ollama"

        def __init__(self, model):
            super().__init__()
            self.config = LLMConfig(model_path=model, retry_count=0)
            created["model"] = model

        def set_seed(self, seed):
            created["seed"] = seed

    monkeypatch.setattr(
        "apparatus.systems.mandate_canonical.OllamaMLTAdapter",
        FakeOllamaAdapter,
    )
    rec = CondBSystem(llm_backend="ollama", llm_model="llama3.2:3b").run(
        "Assess the mission.", run_id="cond_b__TASK-X__r01",
        task_id="TASK-X", run_number=1, seed=20260624)
    assert rec.system_id == "cond_b"
    assert rec.ok is True
    assert rec.decoding_params["llm_backend"] == "ollama"
    assert rec.model_versions["llm_model"] == "llama3.2:3b"
    assert created == {"model": "llama3.2:3b", "seed": 20260624}


def test_cond_b_rejects_unknown_backend_without_adapter():
    import pytest
    with pytest.raises(ValueError):
        CondBSystem(llm_backend="openai")
