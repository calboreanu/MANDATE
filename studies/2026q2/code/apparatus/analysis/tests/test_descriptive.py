"""
Tests for the descriptive analyses (Workstream B6, Notebooks 01 and 02).

Run:  python3 -m pytest apparatus/analysis/tests/test_descriptive.py -q
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from apparatus.analysis.descriptive import (
    mchugh_band, kappa_with_ci, corpus_summary, signoff_summary,
    realism_summary, reliability_summary, completion_rates,
    mandate_fallback_summary, role_timing_summary, run_stability,
    cost_summary)


def rec(system_id, ok=True, any_fb=False, timings=None):
    return {"system_id": system_id, "ok": ok, "any_llm_fallback": any_fb,
            "role_timings": timings or []}


def rt(role, ms, fb=False):
    return {"role_name": role, "duration_ms": ms, "llm_fallback": fb}


# --- McHugh bands ------------------------------------------------------------

def test_mchugh_bands():
    assert mchugh_band(0.92) == "strong agreement"
    assert mchugh_band(0.70).startswith("moderate")
    assert mchugh_band(0.50).startswith("weak")
    assert mchugh_band(0.20).startswith("poor")
    assert mchugh_band(None) == "undefined"


# --- kappa with CI -----------------------------------------------------------

def test_kappa_with_ci_perfect_agreement():
    a = [1, 0, 1, 1, 0, 1, 0, 0]
    out = kappa_with_ci(a, list(a), n_boot=200)
    assert abs(out["kappa"] - 1.0) < 1e-9
    assert out["band"] == "strong agreement"
    assert out["n_items"] == 8


def test_kappa_with_ci_partial_agreement_has_interval():
    a = [1, 1, 1, 1, 0, 0, 0, 0, 1, 0]
    b = [1, 1, 1, 0, 0, 0, 0, 1, 1, 0]
    out = kappa_with_ci(a, b, n_boot=400, seed=3)
    assert 0.0 < out["kappa"] < 1.0
    assert out["ci_low"] <= out["kappa"] <= out["ci_high"]


def test_kappa_with_ci_drops_none_items():
    a = [1, 0, None, 1, 0]
    b = [1, 0, 1, 1, None]
    out = kappa_with_ci(a, b, n_boot=50)
    assert out["n_items"] == 3        # two items dropped


# --- corpus summary ----------------------------------------------------------

def test_corpus_summary_counts():
    tasks = [
        {"domain": "security_ops", "category": "full_specification",
         "task_type": "triage", "word_count": 300},
        {"domain": "security_ops", "category": "gap_triggering",
         "task_type": "triage", "word_count": 500},
        {"domain": "financial", "category": "full_specification",
         "task_type": "report", "word_count": 700},
    ]
    s = corpus_summary(tasks)
    assert s["n_tasks"] == 3
    assert s["by_domain"] == {"financial": 1, "security_ops": 2}
    assert s["by_category"]["full_specification"] == 2
    assert s["word_count"]["median"] == 500.0


# --- sign-off and realism ----------------------------------------------------

def test_signoff_summary_per_reviewer():
    signoffs = [
        {"reviewer": "carter", "task_id": "T1", "minutes": 20},
        {"reviewer": "carter", "task_id": "T2", "minutes": 30,
         "flagged": True},
        {"reviewer": "mckay", "task_id": "T3", "minutes": 40},
    ]
    s = signoff_summary(signoffs)
    assert s["n_signoffs"] == 3
    assert s["n_flagged"] == 1
    assert s["by_reviewer"]["carter"]["n"] == 2
    assert s["by_reviewer"]["carter"]["median"] == 25.0


def test_realism_summary_flags_below_threshold():
    ratings = [{"task_id": "T1", "rating": 4.0},
               {"task_id": "T2", "rating": 2.0},
               {"task_id": "T3", "rating": 3.5}]
    s = realism_summary(ratings, threshold=2.5)
    assert s["below_threshold_tasks"] == ["T2"]
    assert abs(s["mean_rating"] - 3.1666666) < 1e-3


# --- reliability across raters ----------------------------------------------

def test_reliability_summary_three_raters():
    ratings = {
        "r1": [1, 0, 1, 1, 0, 0],
        "r2": [1, 0, 1, 0, 0, 0],
        "r3": [1, 0, 1, 1, 0, 1],
    }
    s = reliability_summary(ratings, level="nominal")
    assert s["n_raters"] == 3
    assert len(s["pairwise_kappa"]) == 3      # 3 pairs


# --- Notebook 02: system output ----------------------------------------------

def test_completion_rates_per_system():
    records = [rec("mandate_primary", ok=True),
               rec("mandate_primary", ok=False),
               rec("baseline_b1", ok=True)]
    cr = completion_rates(records)
    assert cr["mandate_primary"]["completion_rate"] == 0.5
    assert cr["mandate_primary"]["errored"] == 1
    assert cr["baseline_b1"]["completion_rate"] == 1.0


def test_mandate_fallback_summary():
    records = [
        rec("mandate_primary", any_fb=True,
            timings=[rt("Procedure", 10, fb=True), rt("Binding", 5)]),
        rec("mandate_primary", any_fb=False,
            timings=[rt("Procedure", 9)]),
        rec("baseline_b1", any_fb=False),     # ignored: not MANDATE
    ]
    s = mandate_fallback_summary(records)
    assert s["n_mandate_runs"] == 2
    assert s["n_runs_with_fallback"] == 1
    assert s["fallback_rate"] == 0.5
    assert s["fallback_by_role"] == {"Procedure": 1}


def test_role_timing_summary():
    records = [
        rec("mandate_primary", timings=[rt("Intake", 10), rt("Intake", 20)]),
        rec("mandate_primary", timings=[rt("Intake", 30)]),
    ]
    s = role_timing_summary(records, system_id="mandate_primary")
    assert s["Intake"]["n"] == 3
    assert s["Intake"]["median"] == 20.0
    assert s["Intake"]["max"] == 30.0


def test_run_stability():
    runs_by_unit = {
        "T1": ["a", "a", "a"],          # stable
        "T2": ["a", "b", "a"],          # unstable
        "T3": ["x"],                    # single run: stable by definition
    }
    s = run_stability(runs_by_unit, lambda x, y: x == y)
    assert s["n_stable"] == 2
    assert s["unstable_units"] == ["T2"]
    assert abs(s["stability_rate"] - 2 / 3) < 1e-9


# --- cost and compute summary -----------------------------------------------

def _cost_rec(sid, *, api=None, in_tok=0, out_tok=0, wc=0.0, lc=None,
              ok=True):
    return {"system_id": sid, "ok": ok, "api_cost_usd": api,
            "wall_clock_ms": wc, "local_compute_ms": lc,
            "model_versions": {"total_input_tokens": in_tok,
                                "total_output_tokens": out_tok},
            "role_timings": []}


def test_cost_summary_baselines_carry_api_cost_mandate_carries_local_compute():
    records = [
        _cost_rec("baseline_1", api=0.03, in_tok=120, out_tok=80, wc=500),
        _cost_rec("baseline_1", api=0.02, in_tok=100, out_tok=70, wc=450),
        _cost_rec("mandate_primary", api=None, wc=4000, lc=4000),
        _cost_rec("mandate_primary", api=None, wc=3800, lc=3800),
    ]
    s = cost_summary(records)
    b1 = s["by_system"]["baseline_1"]
    assert b1["n_runs"] == 2
    assert abs(b1["api_cost_usd_total"] - 0.05) < 1e-9
    assert abs(b1["api_cost_usd_per_run_mean"] - 0.025) < 1e-9
    assert b1["input_tokens_total"] == 220
    assert b1["output_tokens_total"] == 150
    mp = s["by_system"]["mandate_primary"]
    # no API cost -> reported as None, not a misleading 0.0
    assert mp["api_cost_usd_total"] is None
    assert mp["api_cost_usd_per_run_mean"] is None
    assert mp["local_compute_ms_total"] == 7800.0
    assert s["study_total"]["n_runs"] == 4


def test_cost_summary_excludes_failed_runs_from_ok_count_only():
    """A run that errored still counts toward n_runs (the resources were
    spent), but n_ok is the cleanly-completed subset."""
    records = [_cost_rec("baseline_2", api=0.04, ok=True),
               _cost_rec("baseline_2", api=0.0, ok=False)]
    s = cost_summary(records)
    b2 = s["by_system"]["baseline_2"]
    assert b2["n_runs"] == 2 and b2["n_ok"] == 1
