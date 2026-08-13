"""
End-to-end tests for the canonical (MLT) ablation runner.

These exercise `apparatus.systems.mandate_canonical.run_ablation`, which runs
each pre-registered ablation (A1-A7) against canonical MLT MANDATE v1.0.0rc1 on
a pre-extracted MissionInput. A2/A4/A6/A7 (and A3/A5) are deterministic; A1
(role separation) requires an LLM adapter and is exercised with a stub.

Skipped automatically if the canonical MLT engine is not importable in this
checkout.
"""
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

try:
    from apparatus.systems.mandate_canonical import (
        CANONICAL_ABLATION_OVERRIDES,
        run_ablation,
    )
    from mlt.mandate.models import MissionInput
    from mlt.sdk.llm.adapter import LLMResponse

    _HAVE_CANON = True
    _IMPORT_ERR = ""
except Exception as exc:  # pragma: no cover - environment dependent
    _HAVE_CANON = False
    _IMPORT_ERR = str(exc)

pytestmark = pytest.mark.skipif(
    not _HAVE_CANON, reason=f"canonical MLT engine not importable: {_IMPORT_ERR}"
)

TASK_ID = "TASK-SMOKE-SEC-001"


def _mission() -> "MissionInput":
    return MissionInput.from_dict({
        "mission_id": TASK_ID,
        "intent": "Identify exploitable vulnerabilities in external-facing services",
        "scope": ["10.0.1.0/24"],
        "minimum_outcome": "Enumerate external services and identify vulnerabilities",
        "target_outcome": "Achieve initial access via a confirmed exploitable vulnerability",
        "constraints": ["FORBIDS data_exfiltration", "execution.duration <= PT4H"],
        "risk_tolerance": "LOW",
        "available_tools": [
            {"tool_id": "nmap", "tool_class": "RECON", "description": "network scanner"}
        ],
    })


def _run(ablation_id, **kw):
    return run_ablation(TASK_ID, "scan the external network", _mission(), ablation_id, **kw)


def test_all_seven_ablations_have_canonical_overrides():
    assert sorted(CANONICAL_ABLATION_OVERRIDES) == ["A1", "A2", "A3", "A4", "A5", "A6", "A7"]


def test_a2_record_collapses_tolerance_bands():
    rec = _run("A2")
    assert rec["ok"] is True
    assert rec["system_id"] == "ablation_a2"
    assert rec["code_ref"].startswith("mlt-stack-1.0.3+mandate-result-envelope.v1@")
    assert "target" not in rec["output"]["artifact"]["anchor"]


def test_a4_record_omits_validation_signal():
    rec = _run("A4")
    assert rec["ok"] is True
    assert rec["system_id"] == "ablation_a4"
    meta = rec["output"]["artifact"]["metadata"]
    assert "validation_algorithm" not in meta["sources_consulted"]


def test_a6_record_suppresses_trace():
    rec = _run("A6")
    assert rec["ok"] is False
    assert rec["execution_state"] == "NON_EXECUTABLE_VALIDATION"
    assert rec["output"]["artifact"]["trace"]["entry_count"] == 0
    assert rec["output"]["artifact"]["trace"]["entries"] == []


def test_a7_record_drops_nist_rmf():
    rec = _run("A7")
    assert rec["ok"] is True
    assert "nist_rmf" not in rec["output"]["artifact"]["metadata"]


def test_a1_requires_adapter_no_silent_fallback():
    rec = _run("A1")
    assert rec["ok"] is False
    assert any("adapter" in e.lower() for e in rec["errors"])


def test_a1_single_pass_with_stub_adapter():
    class _Cfg:
        retry_count = 0

    class _Stub:
        def __init__(self):
            self.config = _Cfg()

        def generate(self, prompt, schema):
            return LLMResponse(
                output={
                    "anchor": {
                        "mission_intent": "combined",
                        "minimum": {"description": "m"},
                        "target": {"description": "t"},
                        "constraints": [],
                    },
                    "courses_of_action": [
                        {"coa_id": "COA-1", "approach": "single",
                         "task_dag": {"nodes": [], "edges": []}}
                    ],
                    "recommendation": {"primary_coa": "COA-1", "fallback_sequence": [],
                                       "rationale": "x"},
                },
                tokens_used=1,
                latency_ms=1.0,
            )

    rec = _run("A1", llm_adapter=_Stub())
    assert rec["ok"] is False
    assert rec["execution_state"] == "NON_EXECUTABLE_VALIDATION"
    assert rec["system_id"] == "ablation_a1"
    assert rec["output"]["artifact"]["metadata"]["ablation"] == "A1_role_separation_single_pass"


def test_unknown_ablation_id_rejected():
    with pytest.raises(KeyError):
        _run("A9")
