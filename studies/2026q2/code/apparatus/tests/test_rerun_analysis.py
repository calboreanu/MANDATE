from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from mlt.mandate.models import MissionInput
from mlt.mandate.execution_contract import build_result_envelope
from mlt.sdk.llm import LLMAdapter, LLMConfig, LLMResponse

from apparatus.baselines.llm_client import BudgetedLLMClient, LLMResponse as TextLLMResponse
from apparatus.harness.ledger import CampaignCostLedger
from apparatus.harness.records import RunRecord
from apparatus.harness.runner import Task, run_matrix
from apparatus.harness.ledger import RunLedger
from apparatus.preprocess.extract_mission_input import extract
from apparatus.preprocess.extract_mission_input import EXTRACTION_PROMPT
from apparatus.rerun_analysis import (
    _validate_cost_ledger,
    load_json,
    provider_cost_sum,
    sha256_file,
    sha256_text,
    summarize,
    validate_record,
)
from apparatus.systems import mandate_canonical as mc
from apparatus.systems.mandate_canonical import run_cond_a, run_cond_b


class FakeMLTAdapter(LLMAdapter):
    provider = "anthropic"

    def __init__(self):
        self.config = LLMConfig(model_path="claude-sonnet-4-6", max_tokens=4096, retry_count=0)
        self.calls = []
        self._role = ""

    def set_current_role(self, role_name):
        self._role = str(role_name or "")

    def generate(self, prompt, schema):
        self.calls.append((prompt, schema))
        props = schema.get("properties", {})
        output = {
            "decision_summary": "Use deterministic core.",
        }
        if "mission_id" in props:
            output.update({
                "mission_id": "TASK-MAIN-FIN-001",
                "intent": "Assess reporting controls.",
                "minimum_outcome": "Minimum outcome.",
                "target_outcome": "Target outcome.",
                "constraints": ["FORBIDS data_exfiltration"],
                "scope": ["financial reporting"],
                "risk_tolerance": "LOW",
            })
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
        actual = 0.000057
        reservation_id = f"fake-{self._role or 'UNKNOWN_ROLE'}-{len(self.calls)}"
        return LLMResponse(
            output=output,
            tokens_used=7,
            latency_ms=1.0,
            raw_response={
                "input_tokens": 4,
                "output_tokens": 3,
                "cost_usd": actual,
                "budget_reservation_id": reservation_id,
                "budget_attempts": [{
                    "budget_reservation_id": reservation_id,
                    "reservation_id": reservation_id,
                    "role": self._role or "UNKNOWN_ROLE",
                    "status": "success",
                    "cost_usd": actual,
                    "debit_usd": actual,
                    "cost_basis": "authoritative_response",
                    "input_tokens": 4,
                    "output_tokens": 3,
                    "recovered": False,
                }],
                "budget_total_cost_usd": actual,
                "budget_cost_accounting": "exact",
                "text": "{}",
            },
        )

    def generate_with_trace(self, prompt, schema):
        response = self.generate(prompt, schema)
        return response, {"provider": self.provider, "model": self.config.model_path}


def _mission_input() -> MissionInput:
    prompt = "rendered prompt"
    return MissionInput(
        mission_id="TASK-MAIN-FIN-001",
        intent="Assess reporting controls.",
        minimum_outcome="Minimum outcome.",
        target_outcome="Target outcome.",
        constraints=["FORBIDS data_exfiltration"],
        risk_tolerance="LOW",
        metadata={
            "extraction_model": "claude-sonnet-4-6",
            "input_tokens": 10,
            "output_tokens": 20,
            "extraction_cost_usd": 0.00033,
            "extraction_prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "extraction_prompt_template_sha256": sha256_text(EXTRACTION_PROMPT),
            "raw_provider_response": {
                "provider": "anthropic",
                "model": "claude-sonnet-4-6",
                "input_tokens": 10,
                "output_tokens": 20,
                "cost_usd": 0.00033,
                "response_cost_usd": 0.00033,
                "budget_reservation_id": "fake-cond-a-1",
                "budget_attempts": [{
                    "budget_reservation_id": "fake-cond-a-1",
                    "reservation_id": "fake-cond-a-1",
                    "role": "PreExtractor",
                    "status": "success",
                    "cost_usd": 0.00033,
                    "debit_usd": 0.00033,
                    "cost_basis": "authoritative_response",
                    "input_tokens": 10,
                    "output_tokens": 20,
                    "recovered": False,
                }],
                "budget_total_cost_usd": 0.00033,
                "budget_cost_accounting": "exact",
                "text": "{}",
                "retry": {"attempts": 1, "max_attempts": 4, "errors": [], "final_status": "success"},
            },
        },
    )


def _records():
    cond_a = run_cond_a(
        "TASK-MAIN-FIN-001",
        "Assess reporting controls.",
        _mission_input(),
        run_id="cond_a__TASK-MAIN-FIN-001__r01",
        run_number=1,
        seed=20260624,
    )
    cond_b = run_cond_b(
        "TASK-MAIN-FIN-001",
        "Assess reporting controls.",
        FakeMLTAdapter(),
        run_id="cond_b__TASK-MAIN-FIN-001__r01",
        run_number=1,
        seed=20260624,
        domain_profile_mode="auto",
    )
    blocking_gap = next(g for g in cond_a["output"]["gap_reports"] if g["severity"] == "BLOCKING")
    cond_b["output"]["gap_reports"].append(copy.deepcopy(blocking_gap))
    env = build_result_envelope(
        ok=cond_b["ok"],
        artifact=cond_b["output"]["artifact"],
        gap_reports=cond_b["output"]["gap_reports"],
        schema_valid=cond_b["output"]["schema_valid"],
        errors=cond_b.get("errors") or [],
        validation=cond_b["output"].get("validation"),
    )
    cond_b["output"]["result_envelope"] = env
    cond_b["output"]["execution_state"] = env["execution_state"]
    cond_b["execution_state"] = env["execution_state"]
    cond_b["ok"] = env["ok"]
    return cond_a, cond_b


def _ledger(tmp_path, records):
    ledger = CampaignCostLedger(str(tmp_path / "cost.jsonl"), 1.0)
    for record in records:
        ledger.append(RunRecord.from_dict(record))
    return tmp_path / "cost.jsonl"


def _preflight_manifest(records=None):
    eval_root = mc.APPARATUS_ROOT
    mlt_root = mc.MLT_ROOT
    provider_schema_sha256_by_role = {}
    for record in list(records or []):
        for response in (record.get("output", {}) or {}).get("provider_responses", []) or []:
            if not isinstance(response, dict):
                continue
            role = str(response.get("role") or "")
            if not role:
                continue
            provider_schema_sha256_by_role[role] = response.get("schema_sha256")
    return {
        "mlt_root": str(mlt_root),
        "eval_root": str(eval_root),
        "mlt_commit": mc.MLT_GIT_COMMIT,
        "apparatus_commit": mc.APPARATUS_GIT_COMMIT,
        "paid_execution_allowed_after_preflight": True,
        "authorization_cap_usd": 300.0,
        "remaining_authorization_usd": 300.0,
        "source_hashes": {
            "mlt": dict(mc.MLT_EXPERIMENT_SOURCE_HASHES),
            "apparatus": dict(mc.APPARATUS_EXPERIMENT_SOURCE_HASHES),
        },
        "schema_hashes": {
            "result_envelope_schema": sha256_file(mlt_root / "src/mlt/schemas/mandate-result-envelope.schema.json"),
            "runrecord_schema_v1": sha256_file(eval_root / "replication_package/v1_main/schemas/runrecord_schema_v1.json"),
        },
        "prompt_source_hashes": {
            "mlt_prompt_templates_py": sha256_file(mlt_root / "src/mlt/sdk/llm/prompt_templates.py"),
            "extract_mission_input_py": sha256_file(eval_root / "code/apparatus/preprocess/extract_mission_input.py"),
        },
        "prompt_template_hashes": {
            "cond_a_extraction_prompt_template": sha256_text(EXTRACTION_PROMPT),
        },
        "provider_schema_sha256_by_role": provider_schema_sha256_by_role,
        "corpus_hashes": {},
        "v1_condition_hashes": {},
    }


def _schema():
    return load_json(mc.MLT_ROOT / "src/mlt/schemas/mandate-result-envelope.schema.json")


def _summarize(tmp_path, records, *, manifest=None, corpus_rows=None):
    cond_a, cond_b = records
    return summarize(
        {
            "cond_a": [cond_a],
            "cond_b": [cond_b],
        },
        smoke=True,
        cost_ledger=_ledger(tmp_path, [cond_a, cond_b]),
        preflight_manifest=manifest or _preflight_manifest([cond_a, cond_b]),
        corpus_rows=corpus_rows or {},
    )


def _validate(record, *, condition="cond_a", manifest=None, corpus_rows=None):
    return validate_record(
        record,
        condition=condition,
        preflight_manifest=manifest or _preflight_manifest(),
        corpus_rows=corpus_rows or {},
        result_envelope_schema=_schema(),
    )


def _ledger_rows(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _provider_json_for_role(role: str) -> dict:
    if role == "Intake":
        return {
            "mission_id": "TASK-MAIN-FIN-001",
            "intent": "Assess reporting controls.",
            "constraints": ["FORBIDS data_exfiltration"],
            "scope": ["financial reporting"],
            "assumptions": [],
        }
    if role == "Interpreter":
        return {
            "decision_summary": "Anchor the reporting-control mission.",
            "minimum_outcome": "Minimum outcome.",
            "target_outcome": "Target outcome.",
            "risk_tolerance": "LOW",
        }
    if role == "Decomposition":
        return {
            "decision_summary": "Use one bounded candidate path.",
            "candidate_coa_count": 1,
            "scope_override": ["financial reporting"],
        }
    if role == "Procedure":
        return {
            "decision_summary": "Use deterministic procedure binding.",
            "selected_reference_ids": [],
        }
    if role == "Binding":
        return {
            "decision_summary": "Keep the deterministic recommendation.",
            "risk_notes": [],
            "fallback_sequence": [],
            "rationale_override": "Use the lowest-risk auditable path.",
        }
    if role == "Validation":
        return {
            "decision_summary": "Validate minimum/target alignment.",
            "validation_focus": ["minimum_outcome", "constraints"],
        }
    return {"decision_summary": "Use deterministic core."}


class FakeAnthropicTextClient:
    provider = "anthropic"

    def __init__(self, *, fail_once: bool = False):
        self.fail_once = fail_once
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(dict(kwargs))
        if self.fail_once and len(self.calls) == 1:
            raise RuntimeError("429 Too Many Requests")
        prompt = str(kwargs.get("user") or "")
        role = "UNKNOWN_ROLE"
        for line in prompt.splitlines():
            if line.startswith("ROLE: "):
                role = line.split("ROLE: ", 1)[1].strip()
                break
        text = json.dumps(_provider_json_for_role(role))
        return TextLLMResponse(
            text=text,
            model=kwargs["model"],
            input_tokens=11,
            output_tokens=17,
        )


class FakeExtractorClient:
    provider = "anthropic"

    def __init__(self):
        self.calls = 0

    def generate(self, **kwargs):
        self.calls += 1
        return TextLLMResponse(
            text=json.dumps({
                "mission_id": "TASK-MAIN-FIN-001",
                "intent": "Assess reporting controls.",
                "minimum_outcome": "Minimum outcome.",
                "target_outcome": "Target outcome.",
                "constraints": ["FORBIDS data_exfiltration"],
                "scope": ["financial reporting"],
                "risk_tolerance": "LOW",
                "available_tools": [],
            }),
            model=kwargs["model"],
            input_tokens=12,
            output_tokens=24,
        )


def _stage_stale_attempt(cost_ledger, *, run_id: str, system_id: str, role: str, state: str) -> str:
    rid = cost_ledger.reserve_call(
        run_id=run_id,
        system_id=system_id,
        task_id="TASK-MAIN-FIN-001",
        run_number=1,
        role=role,
        model="claude-sonnet-4-6",
        reserved_cost_usd=0.05,
    )
    if state in {"dispatch_started", "response_received"}:
        cost_ledger.mark_dispatch_started(rid)
    if state == "response_received":
        cost_ledger.mark_response_received(
            rid,
            actual_cost_usd=0.012345,
            input_tokens=5,
            output_tokens=6,
        )
    return rid


def _assert_cost_reconciles(record: dict, cost_ledger: CampaignCostLedger):
    run_id = record["run_id"]
    settlement_total = cost_ledger.run_settlement_total(run_id)
    assert round(float(record["api_cost_usd"] or 0.0), 6) == settlement_total
    assert provider_cost_sum(record) == settlement_total
    summary = next(
        row for row in _ledger_rows(cost_ledger.path)
        if row.get("row_type") == "record_summary"
        and row.get("run_id") == run_id
    )
    assert round(float(summary["api_cost_usd"]), 6) == settlement_total


def _assert_smoke_analyzer_passes(tmp_path, cost_ledger: CampaignCostLedger, record: dict, condition: str):
    base_a, base_b = _records()
    if condition == "cond_a":
        cond_a = record
        cond_b = base_b
        if not cost_ledger.has_record_summary(cond_b["run_id"]):
            cost_ledger.append(RunRecord.from_dict(cond_b))
    else:
        cond_a = base_a
        cond_b = record
        if not cost_ledger.has_record_summary(cond_a["run_id"]):
            cost_ledger.append(RunRecord.from_dict(cond_a))
    report, issues = summarize(
        {
            "cond_a": [cond_a],
            "cond_b": [cond_b],
        },
        smoke=True,
        cost_ledger=Path(cost_ledger.path),
        preflight_manifest=_preflight_manifest([cond_a, cond_b]),
        corpus_rows=({
            "TASK-MAIN-FIN-001": {
                "task_id": "TASK-MAIN-FIN-001",
                "request_text": "Assess reporting controls.",
            },
        } if condition == "cond_a" else {}),
    )
    assert issues == []
    assert report["ok"] is True


def test_smoke_summary_counts_primary_denominator(tmp_path):
    cond_a, cond_b = _records()
    report, issues = _summarize(tmp_path, (cond_a, cond_b))
    assert issues == []
    assert report["primary_denominator_N"] == 2
    assert report["executable_with_blocking_count"] == 0


def _mutated_record(mutator):
    cond_a, _ = _records()
    rec = copy.deepcopy(cond_a)
    mutator(rec)
    return rec


@pytest.mark.parametrize("mutator, expected", [
    (lambda r: (r.__setitem__("ok", True), r["output"]["result_envelope"].__setitem__("ok", True)), "NON_EXECUTABLE_GAPS"),
    (lambda r: r["output"]["result_envelope"].pop("missing_result"), "required"),
    (lambda r: r.__setitem__("contract_schema_version", "bogus.v999"), "unknown contract"),
    (lambda r: r.__setitem__("api_cost_usd", None), "missing or null API cost"),
    (lambda r: r["output"].pop("mission_input_metadata"), "provider provenance"),
    (lambda r: r["output"]["result_envelope"].__setitem__("execution_state", "EXECUTABLE"), "state mismatch"),
    (lambda r: r["output"]["result_envelope"].__setitem__("schema_valid", False), "schema-validity mismatch"),
])
def test_validate_record_rejects_adversarial_cases(mutator, expected):
    issues = _validate(_mutated_record(mutator), condition="cond_a")
    assert any(expected in issue for issue in issues)


def test_validate_record_rejects_executable_with_blocking_signal():
    def mutate(rec):
        rec["execution_state"] = "EXECUTABLE"
        rec["ok"] = True
        rec["output"]["execution_state"] = "EXECUTABLE"
        rec["output"]["result_envelope"]["execution_state"] = "EXECUTABLE"
        rec["output"]["result_envelope"]["ok"] = True

    issues = _validate(_mutated_record(mutate), condition="cond_a")
    assert any("EXECUTABLE" in issue for issue in issues)


def test_summary_rejects_n_zero_report(tmp_path):
    cond_a, cond_b = _records()
    for rec in (cond_a, cond_b):
        rec["output"]["gap_reports"] = []
        env = rec["output"]["result_envelope"]
        env["gap_report_count"] = 0
        env["has_blocking_or_insufficient_signal"] = False
    report, issues = _summarize(tmp_path, (cond_a, cond_b))
    assert not report["ok"]
    assert any("N=0" in issue for issue in issues)


def test_validate_record_rejects_missing_source_hashes():
    rec = _mutated_record(lambda r: r["model_versions"].pop("mlt_source_hashes"))
    issues = _validate(rec)
    assert any("missing mlt source hashes" in issue for issue in issues)


def test_validate_record_rejects_changed_source_hash():
    def mutate(rec):
        hashes = rec["model_versions"]["apparatus_source_hashes"]
        key = next(iter(hashes))
        hashes[key] = "0" * 64

    issues = _validate(_mutated_record(mutate))
    assert any("apparatus source hashes changed entries" in issue for issue in issues)


def test_summary_rejects_mixed_source_hash_maps(tmp_path):
    cond_a, cond_b = _records()
    cond_b["model_versions"]["mlt_source_hashes"] = dict(cond_b["model_versions"]["mlt_source_hashes"])
    key = next(iter(cond_b["model_versions"]["mlt_source_hashes"]))
    cond_b["model_versions"]["mlt_source_hashes"][key] = "1" * 64
    _report, issues = _summarize(tmp_path, (cond_a, cond_b))
    assert any("mixed mlt_source_hashes" in issue for issue in issues)


def test_summary_rejects_manifest_file_hash_mismatch(tmp_path):
    cond_a, cond_b = _records()
    manifest = _preflight_manifest()
    key = next(iter(manifest["source_hashes"]["mlt"]))
    manifest["source_hashes"]["mlt"][key] = "2" * 64
    _report, issues = _summarize(tmp_path, (cond_a, cond_b), manifest=manifest)
    assert any("preflight manifest mlt source hash mismatch" in issue for issue in issues)


def test_validate_record_rejects_prompt_template_mismatch():
    def mutate(rec):
        rec["output"]["mission_input_metadata"]["extraction_prompt_template_sha256"] = "3" * 64

    issues = _validate(_mutated_record(mutate))
    assert any("prompt template hash mismatch" in issue for issue in issues)


def test_validate_record_rejects_rendered_cond_a_prompt_mismatch():
    cond_a, _ = _records()
    corpus_rows = {
        "TASK-MAIN-FIN-001": {"task_id": "TASK-MAIN-FIN-001", "request_text": "different frozen task text"}
    }
    issues = _validate(cond_a, corpus_rows=corpus_rows)
    assert any("rendered extraction prompt hash mismatch" in issue for issue in issues)


def test_validate_record_rejects_retry_not_success():
    def mutate(rec):
        rec["output"]["mission_input_metadata"]["raw_provider_response"]["retry"]["final_status"] = "failed_exhausted"

    issues = _validate(_mutated_record(mutate))
    assert any("unresolved retry/provider errors" in issue for issue in issues)


def test_validate_record_rejects_missing_decoding_flags():
    def mutate(rec):
        rec["decoding_params"].pop("emit_gaps")

    issues = _validate(_mutated_record(mutate))
    assert any("wrong model/configuration" in issue for issue in issues)


def test_validate_record_rejects_cond_b_schema_hash_mismatch():
    cond_a, cond_b = _records()
    manifest = _preflight_manifest([cond_a, cond_b])
    cond_b = copy.deepcopy(cond_b)
    cond_b["output"]["provider_responses"][0]["schema_sha256"] = "4" * 64
    issues = _validate(cond_b, condition="cond_b", manifest=manifest)
    assert any("schema hash mismatch" in issue for issue in issues)


def test_validate_record_rejects_cond_b_prompt_hash_mismatch():
    cond_a, cond_b = _records()
    manifest = _preflight_manifest([cond_a, cond_b])
    cond_b = copy.deepcopy(cond_b)
    cond_b["output"]["provider_responses"][0]["prompt_sha256"] = "5" * 64
    issues = _validate(cond_b, condition="cond_b", manifest=manifest)
    assert any("prompt hash mismatch" in issue for issue in issues)


def test_validate_record_rejects_missing_rendered_prompt_evidence():
    cond_a, cond_b = _records()
    manifest = _preflight_manifest([cond_a, cond_b])
    cond_b = copy.deepcopy(cond_b)
    cond_b["output"]["provider_responses"][0].pop("rendered_prompt", None)
    cond_b["output"]["provider_responses"][0].pop("canonical_prompt_payload", None)
    issues = _validate(cond_b, condition="cond_b", manifest=manifest)
    assert any("missing rendered prompt evidence" in issue for issue in issues)


def test_validate_record_accepts_dynamic_cond_b_prompt_hashes():
    _cond_a, cond_b1 = _records()
    cond_b2 = run_cond_b(
        "TASK-MAIN-FIN-002",
        "Assess a different reporting workflow.",
        FakeMLTAdapter(),
        run_id="cond_b__TASK-MAIN-FIN-002__r01",
        run_number=1,
        seed=20260624,
        domain_profile_mode="auto",
    )
    manifest = _preflight_manifest([cond_b1])
    issues1 = _validate(cond_b1, condition="cond_b", manifest=manifest)
    issues2 = _validate(cond_b2, condition="cond_b", manifest=manifest)
    assert issues1 == []
    assert issues2 == []
    prompts1 = {r["role"]: r["prompt_sha256"] for r in cond_b1["output"]["provider_responses"]}
    prompts2 = {r["role"]: r["prompt_sha256"] for r in cond_b2["output"]["provider_responses"]}
    assert prompts1 != prompts2


def test_validate_record_rejects_missing_budget_attempts():
    _cond_a, cond_b = _records()
    manifest = _preflight_manifest([cond_b])
    cond_b = copy.deepcopy(cond_b)
    cond_b["output"]["provider_responses"][0]["raw_response"].pop("budget_attempts")
    issues = _validate(cond_b, condition="cond_b", manifest=manifest)
    assert any("missing budget fields" in issue for issue in issues)


def test_cost_ledger_requires_settlement_attempt_evidence_exactly_once(tmp_path):
    cond_a, _cond_b = _records()
    ledger = CampaignCostLedger(str(tmp_path / "cost.jsonl"), 1.0)
    rid = ledger.reserve_call(
        run_id=cond_a["run_id"],
        system_id="cond_a",
        task_id=cond_a["task_id"],
        run_number=cond_a["run_number"],
        role="PreExtractor",
        model="claude-sonnet-4-6",
        reserved_cost_usd=0.01,
    )
    ledger.mark_dispatch_started(rid)
    ledger.mark_response_received(rid, actual_cost_usd=0.00033, input_tokens=10, output_tokens=20)
    ledger.settle_call(
        rid,
        actual_cost_usd=0.00033,
        input_tokens=10,
        output_tokens=20,
        status="success",
        cost_basis="authoritative_response",
    )
    raw = cond_a["output"]["mission_input_metadata"]["raw_provider_response"]
    raw["budget_reservation_id"] = rid
    raw["budget_attempts"][0]["budget_reservation_id"] = rid
    raw["budget_attempts"][0]["reservation_id"] = rid
    ledger.append_record_summary(RunRecord.from_dict(cond_a))

    missing = copy.deepcopy(cond_a)
    missing_raw = missing["output"]["mission_input_metadata"]["raw_provider_response"]
    missing_raw["budget_attempts"][0]["budget_reservation_id"] = "missing-from-ledger"
    missing_raw["budget_attempts"][0]["reservation_id"] = "missing-from-ledger"
    issues = _validate_cost_ledger([missing], tmp_path / "cost.jsonl")
    assert any("appears 0 times" in issue for issue in issues)

    duplicate = copy.deepcopy(cond_a)
    duplicate_raw = duplicate["output"]["mission_input_metadata"]["raw_provider_response"]
    duplicate_raw["budget_attempts"].append(copy.deepcopy(duplicate_raw["budget_attempts"][0]))
    issues = _validate_cost_ledger([duplicate], tmp_path / "cost.jsonl")
    assert any("appears 2 times" in issue for issue in issues)


def test_production_cond_b_retry_costs_reconcile_and_analyze(tmp_path):
    task = Task("TASK-MAIN-FIN-001", "Assess reporting controls.")
    cost_ledger = CampaignCostLedger(str(tmp_path / "cost.jsonl"), 5.0)
    client = FakeAnthropicTextClient(fail_once=True)
    adapter = mc.AnthropicMLTAdapter(client=client, cost_ledger=cost_ledger)
    system = mc.CondBSystem(
        llm_adapter=adapter,
        domain_profile_mode="auto",
        cost_ledger=cost_ledger,
        retry_backoff_sec=(0.0,),
    )
    records = run_matrix(
        system,
        [task],
        n_runs=1,
        ledger=RunLedger(str(tmp_path / "cond_b_ledger.jsonl")),
        output_dir=str(tmp_path / "cond_b"),
        seed_base=20260623,
        verbose=False,
        cost_ledger=cost_ledger,
    )
    record = records[0].to_dict()
    _assert_cost_reconciles(record, cost_ledger)
    retried = [
        response for response in record["output"]["provider_responses"]
        if len(response["raw_response"].get("budget_attempts") or []) > 1
    ]
    assert retried
    raw = retried[0]["raw_response"]
    assert raw["retry"]["attempts"] == 2
    assert raw["retry"]["final_status"] == "success"
    assert raw["budget_cost_accounting"] == "conservative_upper_bound"
    statuses = {attempt["status"] for attempt in raw["budget_attempts"]}
    assert "failed_dispatch_uncertain_reserved_bound" in statuses
    assert "success" in statuses
    _assert_smoke_analyzer_passes(tmp_path, cost_ledger, record, "cond_b")


@pytest.mark.parametrize("stale_state", ["reserved", "dispatch_started", "response_received"])
def test_cond_a_recovered_stale_attempts_reconcile_and_resume(tmp_path, monkeypatch, stale_state):
    import apparatus.preprocess.extract_mission_input as emi

    task = Task("TASK-MAIN-FIN-001", "Assess reporting controls.")
    run_id = "cond_a__TASK-MAIN-FIN-001__r01"
    cost_ledger = CampaignCostLedger(str(tmp_path / "cost.jsonl"), 5.0)
    stale_rid = _stage_stale_attempt(
        cost_ledger,
        run_id=run_id,
        system_id="cond_a",
        role="PreExtractor",
        state=stale_state,
    )
    live_client = FakeExtractorClient()
    monkeypatch.setattr(emi, "AnthropicClient", lambda: live_client)
    records = run_matrix(
        mc.CondASystem(cost_ledger=cost_ledger),
        [task],
        n_runs=1,
        ledger=RunLedger(str(tmp_path / "cond_a_ledger.jsonl")),
        output_dir=str(tmp_path / "cond_a"),
        seed_base=20260623,
        verbose=False,
        cost_ledger=cost_ledger,
    )
    record = records[0].to_dict()
    attempts = record["output"]["mission_input_metadata"]["raw_provider_response"]["budget_attempts"]
    recovered = [attempt for attempt in attempts if attempt["budget_reservation_id"] == stale_rid]
    assert recovered and recovered[0]["recovered"] is True
    if stale_state == "dispatch_started":
        assert record["output"]["mission_input_metadata"]["raw_provider_response"]["budget_cost_accounting"] == "conservative_upper_bound"
    _assert_cost_reconciles(record, cost_ledger)

    resume_client = FakeExtractorClient()
    monkeypatch.setattr(emi, "AnthropicClient", lambda: resume_client)
    resumed = run_matrix(
        mc.CondASystem(cost_ledger=cost_ledger),
        [task],
        n_runs=1,
        ledger=RunLedger(str(tmp_path / "cond_a_resume_ledger.jsonl")),
        output_dir=str(tmp_path / "cond_a"),
        seed_base=20260623,
        verbose=False,
        skip_existing=True,
        cost_ledger=cost_ledger,
    )
    assert len(resumed) == 1
    assert resume_client.calls == 0
    _assert_cost_reconciles(resumed[0].to_dict(), cost_ledger)
    _assert_smoke_analyzer_passes(tmp_path, cost_ledger, record, "cond_a")


@pytest.mark.parametrize("stale_state", ["reserved", "dispatch_started", "response_received"])
def test_cond_b_recovered_stale_attempts_reconcile_and_resume(tmp_path, stale_state):
    task = Task("TASK-MAIN-FIN-001", "Assess reporting controls.")
    run_id = "cond_b__TASK-MAIN-FIN-001__r01"
    cost_ledger = CampaignCostLedger(str(tmp_path / "cost.jsonl"), 5.0)
    stale_rid = _stage_stale_attempt(
        cost_ledger,
        run_id=run_id,
        system_id="cond_b",
        role="Intake",
        state=stale_state,
    )
    client = FakeAnthropicTextClient()
    adapter = mc.AnthropicMLTAdapter(client=client, cost_ledger=cost_ledger)
    records = run_matrix(
        mc.CondBSystem(
            llm_adapter=adapter,
            domain_profile_mode="auto",
            cost_ledger=cost_ledger,
            retry_backoff_sec=(0.0,),
        ),
        [task],
        n_runs=1,
        ledger=RunLedger(str(tmp_path / "cond_b_ledger.jsonl")),
        output_dir=str(tmp_path / "cond_b"),
        seed_base=20260623,
        verbose=False,
        cost_ledger=cost_ledger,
    )
    record = records[0].to_dict()
    intake = next(r for r in record["output"]["provider_responses"] if r["role"] == "Intake")
    recovered = [
        attempt for attempt in intake["raw_response"]["budget_attempts"]
        if attempt["budget_reservation_id"] == stale_rid
    ]
    assert recovered and recovered[0]["recovered"] is True
    if stale_state == "dispatch_started":
        assert intake["raw_response"]["budget_cost_accounting"] == "conservative_upper_bound"
    _assert_cost_reconciles(record, cost_ledger)

    resume_client = FakeAnthropicTextClient()
    resume_adapter = mc.AnthropicMLTAdapter(client=resume_client, cost_ledger=cost_ledger)
    resumed = run_matrix(
        mc.CondBSystem(
            llm_adapter=resume_adapter,
            domain_profile_mode="auto",
            cost_ledger=cost_ledger,
            retry_backoff_sec=(0.0,),
        ),
        [task],
        n_runs=1,
        ledger=RunLedger(str(tmp_path / "cond_b_resume_ledger.jsonl")),
        output_dir=str(tmp_path / "cond_b"),
        seed_base=20260623,
        verbose=False,
        skip_existing=True,
        cost_ledger=cost_ledger,
    )
    assert len(resumed) == 1
    assert resume_client.calls == []
    _assert_cost_reconciles(resumed[0].to_dict(), cost_ledger)
    _assert_smoke_analyzer_passes(tmp_path, cost_ledger, record, "cond_b")


def test_no_network_run_matrix_smoke_passes_strict_analyzer(tmp_path):
    class FakeExtractorClient:
        provider = "anthropic"

        def generate(self, **kwargs):
            return TextLLMResponse(
                text=json.dumps({
                    "mission_id": "TASK-MAIN-FIN-001",
                    "intent": "Assess reporting controls.",
                    "minimum_outcome": "Minimum outcome.",
                    "target_outcome": "Target outcome.",
                    "constraints": ["FORBIDS data_exfiltration"],
                    "scope": ["financial reporting"],
                    "risk_tolerance": "LOW",
                    "available_tools": [],
                }),
                model=kwargs["model"],
                input_tokens=12,
                output_tokens=24,
            )

    class FakePaidCondASystem:
        system_id = "cond_a"
        system_label = "Cond-A simulated"

        def __init__(self, cost_ledger):
            self.cost_ledger = cost_ledger

        def run(self, request_text, *, run_id, task_id, run_number, seed=None):
            client = BudgetedLLMClient(
                FakeExtractorClient(),
                cost_ledger=self.cost_ledger,
                run_id=run_id,
                system_id=self.system_id,
                task_id=task_id,
                run_number=run_number,
                role="PreExtractor",
            )
            mi = extract(
                task_id,
                request_text,
                client=client,
                retry_backoff_sec=(),
            )
            return RunRecord.from_dict(run_cond_a(
                task_id,
                request_text,
                mi,
                seed=seed,
                run_id=run_id,
                run_number=run_number,
            ))

    class FakePaidMLTAdapter(LLMAdapter):
        provider = "anthropic"

        def __init__(self, cost_ledger):
            self.cost_ledger = cost_ledger
            self.config = LLMConfig(model_path="claude-sonnet-4-6", max_tokens=4096, retry_count=0)
            self._role = ""
            self._ctx = {"run_id": "", "system_id": "cond_b", "task_id": "", "run_number": 1}

        def set_current_role(self, role_name):
            self._role = str(role_name or "")

        def set_budget_context(self, *, run_id, system_id, task_id, run_number):
            self._ctx = {
                "run_id": run_id,
                "system_id": system_id,
                "task_id": task_id,
                "run_number": int(run_number),
            }

        def generate(self, prompt, schema):
            rid = self.cost_ledger.reserve_call(
                run_id=self._ctx["run_id"],
                system_id=self._ctx["system_id"],
                task_id=self._ctx["task_id"],
                run_number=self._ctx["run_number"],
                role=self._role or "UNKNOWN_ROLE",
                model="claude-sonnet-4-6",
                reserved_cost_usd=0.01,
            )
            self.cost_ledger.mark_dispatch_started(rid)
            props = schema.get("properties", {})
            output = {"decision_summary": "Use deterministic core."}
            if "mission_id" in props:
                output.update({
                    "mission_id": "TASK-MAIN-FIN-001",
                    "intent": "Assess reporting controls.",
                    "minimum_outcome": "Minimum outcome.",
                    "target_outcome": "Target outcome.",
                    "constraints": ["FORBIDS data_exfiltration"],
                    "scope": ["financial reporting"],
                    "risk_tolerance": "LOW",
                })
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
            actual = 0.000057
            self.cost_ledger.mark_response_received(rid, actual_cost_usd=actual, input_tokens=4, output_tokens=3)
            self.cost_ledger.settle_call(
                rid,
                actual_cost_usd=actual,
                input_tokens=4,
                output_tokens=3,
                status="success",
                cost_basis="authoritative_response",
            )
            return LLMResponse(
                output=output,
                tokens_used=7,
                latency_ms=1.0,
                raw_response={
                    "input_tokens": 4,
                    "output_tokens": 3,
                    "cost_usd": actual,
                    "budget_reservation_id": rid,
                    "budget_attempts": [{
                        "budget_reservation_id": rid,
                        "status": "success",
                        "cost_usd": actual,
                        "cost_basis": "authoritative_response",
                    }],
                    "budget_total_cost_usd": actual,
                    "budget_cost_accounting": "exact",
                    "text": "{}",
                },
            )

        def generate_with_trace(self, prompt, schema):
            response = self.generate(prompt, schema)
            return response, {"provider": self.provider, "model": self.config.model_path}

    class FakePaidCondBSystem:
        system_id = "cond_b"
        system_label = "Cond-B simulated"

        def __init__(self, cost_ledger):
            self.adapter = FakePaidMLTAdapter(cost_ledger)

        def run(self, request_text, *, run_id, task_id, run_number, seed=None):
            self.adapter.set_budget_context(
                run_id=run_id,
                system_id=self.system_id,
                task_id=task_id,
                run_number=run_number,
            )
            return RunRecord.from_dict(run_cond_b(
                task_id,
                request_text,
                self.adapter,
                seed=seed,
                run_id=run_id,
                run_number=run_number,
                domain_profile_mode="auto",
                retry_backoff_sec=(),
            ))

    task = Task("TASK-MAIN-FIN-001", "Assess reporting controls.")
    cost_path = tmp_path / "cost.jsonl"
    cost_ledger = CampaignCostLedger(str(cost_path), 1.0)
    cond_a_records = run_matrix(
        FakePaidCondASystem(cost_ledger),
        [task],
        n_runs=1,
        ledger=RunLedger(str(tmp_path / "cond_a_ledger.jsonl")),
        output_dir=str(tmp_path / "cond_a"),
        seed_base=20260623,
        verbose=False,
        cost_ledger=cost_ledger,
    )
    cond_b_records = run_matrix(
        FakePaidCondBSystem(cost_ledger),
        [task],
        n_runs=1,
        ledger=RunLedger(str(tmp_path / "cond_b_ledger.jsonl")),
        output_dir=str(tmp_path / "cond_b"),
        seed_base=20260623,
        verbose=False,
        cost_ledger=cost_ledger,
    )
    cond_a_record = cond_a_records[0].to_dict()
    cond_b_record = cond_b_records[0].to_dict()
    blocking_gap = next(g for g in _records()[0]["output"]["gap_reports"] if g["severity"] == "BLOCKING")
    cond_b_record["output"]["gap_reports"].append(copy.deepcopy(blocking_gap))
    env = build_result_envelope(
        ok=cond_b_record["ok"],
        artifact=cond_b_record["output"]["artifact"],
        gap_reports=cond_b_record["output"]["gap_reports"],
        schema_valid=cond_b_record["output"]["schema_valid"],
        errors=cond_b_record.get("errors") or [],
        validation=cond_b_record["output"].get("validation"),
    )
    cond_b_record["output"]["result_envelope"] = env
    cond_b_record["output"]["execution_state"] = env["execution_state"]
    cond_b_record["execution_state"] = env["execution_state"]
    cond_b_record["ok"] = env["ok"]
    report, issues = summarize(
        {
            "cond_a": [cond_a_record],
            "cond_b": [cond_b_record],
        },
        smoke=True,
        cost_ledger=cost_path,
        preflight_manifest=_preflight_manifest([cond_a_record, cond_b_record]),
        corpus_rows={task.task_id: {"task_id": task.task_id, "text": task.request_text}},
    )
    assert issues == []
    assert report["ok"] is True
    assert report["cost_accounting"]["record_summary_count"] == 2
