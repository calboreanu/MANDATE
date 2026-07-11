"""
Tests for the primary hypothesis-test module (Workstream B6, Notebook 04).

Dependency-light: the tests build synthetic task-level outcome tables in the
exact long format `scoring.aggregate.analysis_table` emits, and check the
behaviour the analysis depends on: paired effect sizes have the right sign and
magnitude, a planted effect is detected and a null effect is not, the
robustness tests fire on the right family, the operational bars compare
against the right quantity, and the Holm step is applied correctly across the
family of five.

Run:  python3 -m pytest apparatus/analysis/tests/test_models.py -q
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import numpy as np

from apparatus.analysis.models import (
    cohens_d, cohens_h, pair_outcome, bootstrap_ci, fit_planned_model,
    paired_test, operational_check, analyze_outcome, run_primary_analysis,
    _binarize, PRIMARY_OUTCOMES, HOLM_STEPS)

DOMAINS = ("security_ops", "financial", "intelligence")
TYPES = ("full_specification", "gap_triggering", "stretch_case")


def _row(system_id, outcome, unit_id, value, domain, task_type):
    unit_kind = "perturbation" if outcome == "O5" else "task"
    return {"system_id": system_id, "outcome": outcome,
            "unit_kind": unit_kind, "unit_id": unit_id, "value": value,
            "n_runs": 10, "n_runs_excluded": 0, "domain": domain,
            "task_type": task_type, "category": task_type}


def mk_table(outcome, n=48, *, effect=0.0, base=0.5, base_sd=0.08,
             binary=False, count=False, seed=1):
    """A synthetic two-system table for one outcome. `effect` shifts
    MANDATE-primary relative to the baseline."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        dom = DOMAINS[i % 3]
        tt = TYPES[(i // 3) % 3]
        uid = "%s-%03d" % (outcome, i)
        if binary:
            pb, pm = base, min(0.98, max(0.02, base + effect))
            vb = float(rng.random() < pb)
            vm = float(rng.random() < pm)
        elif count:
            vb = float(max(0, rng.poisson(base)))
            vm = float(max(0, rng.poisson(max(0.05, base + effect))))
        else:
            shared = rng.normal(0.0, base_sd)        # paired task component
            vb = min(1.0, max(0.0, base + shared + rng.normal(0, base_sd)))
            vm = min(1.0, max(0.0, base + effect + shared
                              + rng.normal(0, base_sd)))
        rows.append(_row("baseline_strongest", outcome, uid, vb, dom, tt))
        rows.append(_row("mandate_primary", outcome, uid, vm, dom, tt))
    return rows


# --- effect sizes ------------------------------------------------------------

def test_cohens_d_sign_and_zero():
    assert cohens_d([1, 2, 3], [0, 1, 2]) > 0
    assert cohens_d([0, 1, 2], [1, 2, 3]) < 0
    assert cohens_d([1, 1, 1], [1, 1, 1]) == 0.0       # no pooled variance


def test_cohens_h_sign():
    assert cohens_h(0.9, 0.6) > 0
    assert cohens_h(0.6, 0.9) < 0
    assert abs(cohens_h(0.5, 0.5)) < 1e-9


# --- pairing -----------------------------------------------------------------

def test_pair_outcome_pairs_on_shared_units():
    table = mk_table("O1", n=12, effect=0.1)
    p = pair_outcome(table, "O1", "mandate_primary", "baseline_strongest")
    assert p.n == 12
    assert p.n_a_only == 0 and p.n_b_only == 0
    assert len(p.vals_a) == len(p.vals_b) == 12


def test_pair_outcome_counts_unpaired_units():
    table = mk_table("O1", n=10, effect=0.1)
    # drop one baseline row and one mandate row for different units
    table = [r for r in table
             if not (r["unit_id"] == "O1-000"
                     and r["system_id"] == "baseline_strongest")
             and not (r["unit_id"] == "O1-001"
                      and r["system_id"] == "mandate_primary")]
    p = pair_outcome(table, "O1", "mandate_primary", "baseline_strongest")
    assert p.n == 8
    assert p.n_a_only == 1            # O1-000: only mandate scored it
    assert p.n_b_only == 1            # O1-001: only baseline scored it


def test_pair_outcome_skips_null_values():
    table = mk_table("O1", n=6, effect=0.1)
    for r in table:
        if r["unit_id"] == "O1-000":
            r["value"] = None
    p = pair_outcome(table, "O1", "mandate_primary", "baseline_strongest")
    assert p.n == 5


# --- planned model: planted effect vs null -----------------------------------

def test_continuous_model_detects_planted_effect():
    table = mk_table("O1", n=60, effect=0.15)
    m = fit_planned_model(
        pair_outcome(table, "O1", "mandate_primary", "baseline_strongest"))
    assert m["effect"] > 0
    assert m["p"] < 0.01


def test_continuous_model_null_effect_is_calibrated():
    # A single synthetic draw can be spuriously significant ~5% of the time,
    # so this checks calibration: across many independent null draws the
    # model must reject at roughly alpha, not manufacture significance.
    rejections = 0
    n_draws = 30
    for s in range(n_draws):
        table = mk_table("O1", n=60, effect=0.0, seed=500 + s)
        m = fit_planned_model(
            pair_outcome(table, "O1", "mandate_primary",
                         "baseline_strongest"))
        if m["p"] < 0.05:
            rejections += 1
    # expected ~1.5 of 30 at a calibrated alpha = 0.05; allow generous slack
    assert rejections <= 6, "null rejection rate too high: %d/%d" % (
        rejections, n_draws)


def test_count_model_detects_reduction():
    # O3: baseline mean count 4, mandate mean count ~1 (lower is better)
    table = mk_table("O3", n=60, base=4.0, effect=-3.0, count=True)
    m = fit_planned_model(
        pair_outcome(table, "O3", "mandate_primary", "baseline_strongest"))
    assert m["effect"] < 0          # mandate fabricates less
    assert m["p"] < 0.01


def test_binary_model_detects_planted_effect():
    table = mk_table("O4", n=80, base=0.55, effect=0.35, binary=True)
    m = fit_planned_model(
        pair_outcome(table, "O4", "mandate_primary", "baseline_strongest"))
    assert m["p"] < 0.05


# --- bootstrap CI ------------------------------------------------------------

def test_bootstrap_ci_brackets_and_orders():
    table = mk_table("O1", n=60, effect=0.15)
    p = pair_outcome(table, "O1", "mandate_primary", "baseline_strongest")
    lo, hi = bootstrap_ci(p, n_boot=400, seed=7)
    assert lo < hi
    assert lo > 0                    # a clear positive effect


def test_bootstrap_ci_nan_for_tiny_n():
    table = mk_table("O1", n=2, effect=0.1)
    p = pair_outcome(table, "O1", "mandate_primary", "baseline_strongest")
    lo, hi = bootstrap_ci(p)
    assert lo != lo and hi != hi      # nan, nan


# --- robustness checks -------------------------------------------------------

def test_robustness_uses_wilcoxon_for_continuous():
    table = mk_table("O1", n=40, effect=0.15)
    r = paired_test(
        pair_outcome(table, "O1", "mandate_primary", "baseline_strongest"))
    assert r["method"] == "wilcoxon"
    assert r["p"] < 0.05


def test_robustness_uses_mcnemar_for_binary():
    table = mk_table("O5", n=60, base=0.5, effect=0.4, binary=True)
    r = paired_test(
        pair_outcome(table, "O5", "mandate_primary", "baseline_strongest"))
    assert r["method"] == "mcnemar"


def test_binarize_drops_exact_half():
    assert _binarize(0.8) == 1
    assert _binarize(0.2) == 0
    assert _binarize(0.5) is None


def test_mcnemar_counts_half_ties():
    table = mk_table("O4", n=20, base=0.6, effect=0.3, binary=True)
    # force two units to a 0.5 task-level tie
    seen = 0
    for r in table:
        if r["system_id"] == "mandate_primary" and seen < 2:
            r["value"] = 0.5
            seen += 1
    r = paired_test(
        pair_outcome(table, "O4", "mandate_primary", "baseline_strongest"))
    assert r["n_ties_excluded"] == 2


# --- operational significance ------------------------------------------------

def test_operational_check_o1_absolute_gap():
    table = mk_table("O1", n=40, effect=0.15)
    op = operational_check(
        "O1", pair_outcome(table, "O1", "mandate_primary",
                           "baseline_strongest"))
    assert op["kind"] == "absolute_gap"
    assert op["threshold"] == 0.10
    assert op["met"] is True            # 0.15 gap clears the 0.10 bar


def test_operational_check_o3_relative_reduction():
    table = mk_table("O3", n=40, base=4.0, effect=-3.0, count=True)
    op = operational_check(
        "O3", pair_outcome(table, "O3", "mandate_primary",
                           "baseline_strongest"))
    assert op["kind"] == "relative_reduction"
    assert op["met"] is True            # ~75% reduction clears 50%


def test_operational_check_o4_absolute_level():
    table = mk_table("O4", n=60, base=0.6, effect=0.35, binary=True)
    op = operational_check(
        "O4", pair_outcome(table, "O4", "mandate_primary",
                           "baseline_strongest"))
    assert op["kind"] == "absolute_level"   # MANDATE's own rate, not a gap
    assert op["threshold"] == 0.90


# --- full primary analysis ---------------------------------------------------

def _all_outcomes_table(effect_scale=1.0, seed=100):
    """One table carrying all five primary outcomes for the two systems."""
    rows = []
    rows += mk_table("O1", n=60, effect=0.15 * effect_scale, seed=seed)
    rows += mk_table("O2a", n=36, effect=0.20 * effect_scale, seed=seed + 1)
    rows += mk_table("O3", n=60, base=4.0, effect=-3.0 * effect_scale,
                     count=True, seed=seed + 2)
    rows += mk_table("O4", n=60, base=0.55, effect=0.35 * effect_scale,
                     binary=True, seed=seed + 3)
    rows += mk_table("O5", n=50, base=0.5, effect=0.40 * effect_scale,
                     binary=True, seed=seed + 4)
    return rows


def test_run_primary_analysis_requires_strongest_baseline():
    table = _all_outcomes_table()
    try:
        run_primary_analysis(table, system_a="mandate_primary")
        assert False, "should require system_b"
    except ValueError:
        pass


def test_run_primary_analysis_confirms_strong_effects():
    table = _all_outcomes_table(effect_scale=1.0)
    rep = run_primary_analysis(table, system_a="mandate_primary",
                               system_b="baseline_strongest", n_boot=300)
    assert set(rep["outcomes"]) == set(PRIMARY_OUTCOMES)
    # every outcome carries a Holm rank 1..5, distinct
    ranks = sorted(rep["outcomes"][oc]["holm_rank"]
                   for oc in PRIMARY_OUTCOMES)
    assert ranks == [1, 2, 3, 4, 5]
    # the planted effects are strong; at least the continuous ones confirm
    assert rep["n_confirmed"] >= 1
    assert rep["any_confirmed"] is True


def test_run_primary_analysis_holm_thresholds_in_order():
    table = _all_outcomes_table()
    rep = run_primary_analysis(table, system_a="mandate_primary",
                               system_b="baseline_strongest", n_boot=200)
    # outcomes sorted by Holm rank must carry the increasing step thresholds
    by_rank = sorted((rep["outcomes"][oc] for oc in PRIMARY_OUTCOMES),
                     key=lambda d: d["holm_rank"])
    assert [d["holm_threshold"] for d in by_rank] == list(HOLM_STEPS)


def test_run_primary_analysis_null_effects_not_confirmed():
    table = _all_outcomes_table(effect_scale=0.0)
    rep = run_primary_analysis(table, system_a="mandate_primary",
                               system_b="baseline_strongest", n_boot=200)
    assert rep["n_confirmed"] == 0
