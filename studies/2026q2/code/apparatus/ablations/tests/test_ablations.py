"""
Tests for the seven-ablation manifest and the AblationSystem adapter
(Workstream A4).

Run:  python3 -m pytest apparatus/ablations/tests -q
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pytest

from apparatus.ablations import (ABLATIONS, AblationKind, PRIMARY_IDS,
                                 SECONDARY_IDS, AblationSystem,
                                 AblationNotReadyError, get_ablation,
                                 list_ablations)

# AEGIS-eval is the frozen MANDATE source. The config-switch tests need it;
# the manifest tests do not.
AEGIS_EVAL_SRC = os.path.join(_PROJECT_ROOT, "AEGIS-eval", "src")
HAS_AEGIS = os.path.isdir(os.path.join(AEGIS_EVAL_SRC, "mandate"))


# --- manifest ---------------------------------------------------------------

def test_manifest_has_exactly_seven():
    assert sorted(ABLATIONS) == ["A1", "A2", "A3", "A4", "A5", "A6", "A7"]


def test_primary_and_secondary_partition_matches_protocol():
    primaries = [s.id for s in ABLATIONS.values() if s.is_primary]
    secondaries = [s.id for s in ABLATIONS.values() if not s.is_primary]
    assert sorted(primaries) == list(PRIMARY_IDS)
    assert sorted(secondaries) == list(SECONDARY_IDS)


def test_config_switches_are_a3_and_a5():
    cs = sorted(s.id for s in ABLATIONS.values()
                if s.kind is AblationKind.CONFIG_SWITCH)
    assert cs == ["A3", "A5"]


def test_aegis_variants_are_the_other_five():
    av = sorted(s.id for s in ABLATIONS.values()
                if s.kind is AblationKind.AEGIS_VARIANT)
    assert av == ["A1", "A2", "A4", "A6", "A7"]


def test_aegis_variants_start_with_no_ref_set():
    """Variant ablations are not silently runnable: their aegis_ref starts
    empty so `ready` is False until upstream pins them."""
    for s in ABLATIONS.values():
        if s.kind is AblationKind.AEGIS_VARIANT:
            assert s.aegis_ref == ""
            assert s.ready is False


def test_config_switches_are_ready_immediately():
    for s in ABLATIONS.values():
        if s.kind is AblationKind.CONFIG_SWITCH:
            assert s.ready is True


def test_get_ablation_is_case_insensitive_and_rejects_unknown():
    assert get_ablation("a3").id == "A3"
    assert get_ablation("A3").id == "A3"
    with pytest.raises(KeyError):
        get_ablation("A9")


def test_list_ablations_filters():
    assert [s.id for s in list_ablations(primary=True)] == list(PRIMARY_IDS)
    assert [s.id for s in list_ablations(primary=False)] == list(SECONDARY_IDS)
    # only config switches are ready until upstream pins variants
    assert [s.id for s in list_ablations(ready_only=True)] == ["A3", "A5"]


def test_system_id_namespaces_ablations():
    assert ABLATIONS["A3"].system_id == "ablation_a3"
    assert ABLATIONS["A6"].system_label.startswith("Ablation A6")


# --- AblationSystem ---------------------------------------------------------

def test_unbuilt_aegis_variant_refuses_to_run():
    """A1 has no variant ref yet, so instantiating its AblationSystem raises
    the explicit AblationNotReadyError; it does not silently substitute
    MANDATE-primary."""
    with pytest.raises(AblationNotReadyError) as exc:
        AblationSystem(ablation_id="A1",
                       primary_aegis_src_path=AEGIS_EVAL_SRC or "/nonexistent")
    assert "A1" in str(exc.value)
    assert "variant" in str(exc.value).lower()


def test_variant_ref_without_source_path_still_refuses():
    """Set a ref but no source path: still refuses, because we cannot tell
    which checkout to import from."""
    # patch a ref on a fresh copy to avoid mutating the module-level dict
    ABLATIONS["A1"].aegis_ref = "mandate-eval-ablation-a1-2026q2-v1"
    try:
        with pytest.raises(AblationNotReadyError):
            AblationSystem(ablation_id="A1",
                           primary_aegis_src_path=AEGIS_EVAL_SRC
                           or "/nonexistent",
                           variant_src_path="")
    finally:
        ABLATIONS["A1"].aegis_ref = ""


@pytest.mark.skipif(not HAS_AEGIS,
                    reason="AEGIS-eval not present in this checkout")
def test_a3_config_switch_runs_deterministic_and_records_metadata():
    """A3 (emit_gaps=False) runs from the same frozen MANDATE source as
    MANDATE-primary and records the ablation identity in the run record."""
    sys_ = AblationSystem(ablation_id="A3",
                          primary_aegis_src_path=AEGIS_EVAL_SRC,
                          primary_code_ref=("mandate-eval-primary"
                                             "-2026q2-v1"))
    desc = sys_.describe()
    assert desc["system_id"] == "ablation_a3"
    assert desc["ablation_id"] == "A3"
    assert desc["ablation_kind"] == "config_switch"
    assert desc["is_primary_ablation"] is True
    assert desc["ablation_config_overrides"] == {"emit_gaps": False}

    rec = sys_.run("Stand up a triage capability for ransomware containment "
                   "under a 4-hour MTTC, using only enterprise-approved "
                   "tooling, while preserving forensic evidence.",
                   run_id="a3-smoke", task_id="TASK-CAL-SEC-001",
                   run_number=1, seed=20260601)
    assert rec.system_id == "ablation_a3"
    assert rec.code_ref == "mandate-eval-primary-2026q2-v1"
    assert rec.decoding_params == {"mode": "deterministic"}
    assert rec.ok is True
    assert any(rt.role_name == "Validation" for rt in rec.role_timings)


@pytest.mark.skipif(not HAS_AEGIS,
                    reason="AEGIS-eval not present in this checkout")
def test_a5_config_switch_runs_with_no_registry():
    """A5 (success_registry=None) runs from the same frozen source. The
    PipelineConfig override registers as a deterministic-mode kwarg."""
    sys_ = AblationSystem(ablation_id="A5",
                          primary_aegis_src_path=AEGIS_EVAL_SRC,
                          primary_code_ref=("mandate-eval-primary"
                                             "-2026q2-v1"))
    rec = sys_.run("Stand up a finance close-cycle review capability that "
                   "meets the audit committee's cycle-time target.",
                   run_id="a5-smoke", task_id="TASK-CAL-FIN-001",
                   run_number=1, seed=20260601)
    assert rec.system_id == "ablation_a5"
    assert rec.ok is True
