"""
Tests for the anonymization pipeline (Workstream B4).

Run:  python3 -m pytest apparatus/tests -q   (from the project root)
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from apparatus.harness.records import RunRecord, RoleTiming
from apparatus.anonymize import Anonymizer, verify_mapping


def _records():
    """Two systems x two tasks. The MANDATE record carries six role timings
    with role names that would identify it; the baseline record does not."""
    mandate = []
    for t in ("T1", "T2"):
        mandate.append(RunRecord(
            run_id="mandate_primary__%s__r01" % t, task_id=t,
            system_id="mandate_primary", system_label="MANDATE-primary",
            run_number=1, output_type="MANDATE_AS_CODE", ok=True,
            role_timings=[RoleTiming(r, "success")
                          for r in ("Intake", "Interpreter", "Decomposition",
                                    "Procedure", "Binding", "Validation")],
            output={"artifact": {"anchor": {"mission_intent": "do the task"}}}))
    baseline = []
    for t in ("T1", "T2"):
        baseline.append(RunRecord(
            run_id="baseline_1__%s__r01" % t, task_id=t,
            system_id="baseline_1", system_label="B1 single-prompt (Claude)",
            run_number=1, output_type="BASELINE_SCHEMA:specification", ok=True,
            output={"specification": {"mission_intent": "do the task"}}))
    return mandate + baseline


def test_anonymize_strips_identity():
    result = Anonymizer(seed=1).anonymize(_records())
    assert len(result.outputs) == 4
    for o in result.outputs:
        assert set(o.keys()) == {"anon_id", "task_id", "output_type",
                                 "output", "ok"}
        # no identity, and no role_timings (role names identify MANDATE)
        assert "system_id" not in o and "system_label" not in o
        assert "role_timings" not in o
    # the mapping holds the identity
    assert len(result.mapping) == 4
    for anon, ident in result.mapping.items():
        assert ident["system_id"] in ("mandate_primary", "baseline_1")


def test_anon_ids_unique():
    result = Anonymizer(seed=2).anonymize(_records())
    ids = [o["anon_id"] for o in result.outputs]
    assert len(ids) == len(set(ids)) == 4


def test_deterministic_with_seed():
    r1 = Anonymizer(seed=42).anonymize(_records())
    r2 = Anonymizer(seed=42).anonymize(_records())
    assert [o["anon_id"] for o in r1.outputs] == \
           [o["anon_id"] for o in r2.outputs]
    assert r1.mapping == r2.mapping


def test_mapping_resolves_to_correct_system():
    recs = _records()
    result = Anonymizer(seed=3).anonymize(recs)
    # every run_id appears exactly once in the mapping, with its real system
    by_run = {ident["run_id"]: ident["system_id"]
              for ident in result.mapping.values()}
    assert by_run["mandate_primary__T1__r01"] == "mandate_primary"
    assert by_run["baseline_1__T2__r01"] == "baseline_1"


def test_identity_token_scrub():
    rec = RunRecord(run_id="x", task_id="T1", system_id="mandate_primary",
                    system_label="MANDATE-primary", run_number=1, ok=True,
                    output={"specification": {"mission_intent":
                            "MANDATE produced this specification"}})
    result = Anonymizer(seed=4).anonymize([rec], identity_tokens=["MANDATE"])
    text = result.outputs[0]["output"]["specification"]["mission_intent"]
    assert "MANDATE" not in text and "[redacted]" in text


def test_verify_mapping_passes_and_detects_tamper():
    result = Anonymizer(seed=5).anonymize(_records())
    ok, problems = verify_mapping(result)
    assert ok and problems == []
    # tamper: drop a mapping entry
    result.mapping.pop(next(iter(result.mapping)))
    ok2, problems2 = verify_mapping(result)
    assert not ok2 and problems2


def test_mapping_carries_run_health_flags():
    """The mapping must expose ok / any_llm_fallback / schema_valid so the
    primary-analysis notebook's `clean` outcome gate can actually exclude unclean
    runs. Previously these were absent from the mapping, so the notebook saw
    ok=True / fallback=False / schema_valid=None and the gate never fired."""
    rec = RunRecord(
        run_id="mandate_primary__T9__r01", task_id="T9",
        system_id="mandate_primary", system_label="MANDATE-primary",
        run_number=1, output_type="MANDATE_AS_CODE", ok=True,
        output={"artifact": {"anchor": {"mission_intent": "x"}},
                "schema_valid": False})
    result = Anonymizer(seed=7).anonymize([rec])
    ident = next(iter(result.mapping.values()))
    assert {"ok", "any_llm_fallback", "schema_valid"} <= set(ident.keys())
    assert ident["schema_valid"] is False   # flows from output.schema_valid


def test_mapping_round_trips(tmp_path):
    result = Anonymizer(seed=6).anonymize(_records())
    out_p = str(tmp_path / "anon.json")
    map_p = str(tmp_path / "mapping.json")
    Anonymizer(seed=6).save(result, out_p, map_p)
    assert json.load(open(map_p)) == result.mapping
    loaded = json.load(open(out_p))
    assert len(loaded) == 4
