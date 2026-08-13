"""
Tests for the simulation-based power analysis (Workstream B6).

These use small simulation counts so they run fast; the real Notebook 03 run
uses 5,000 simulations per PROTOCOL_LOCK Section 6.5. The tests check the
behaviour that must hold for the analysis to be trustworthy: power rises with
effect size, power under the null sits near alpha, and the MDE / halt logic
is correct.

Run:  python3 -m pytest apparatus/analysis/tests -q   (from the project root)
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import numpy as np

from apparatus.analysis.power import (
    simulate_continuous, run_test_continuous, simulate_binary,
    run_test_binary, _p_from_h, power_continuous, power_binary, power_at,
    _interpolate_mde, run_outcome, ScenarioPower, OPERATIONAL_EFFECT,
    PRIMARY_OUTCOMES, HOLM_ALPHA)

N_SIMS = 60          # small, for fast tests


def rng(seed=0):
    return np.random.default_rng(seed)


# --- simulation shape --------------------------------------------------------

def test_simulate_continuous_shape():
    rows = simulate_continuous(0.5, rng(1), n_tasks=40)
    assert len(rows) == 80                       # 40 tasks x 2 systems
    systems = {r["system"] for r in rows}
    assert systems == {"baseline", "mandate"}
    for r in rows:
        assert set(r) == {"task_id", "domain", "task_type", "system",
                          "metric"}


def test_continuous_test_returns_valid_p():
    p = run_test_continuous(simulate_continuous(0.5, rng(2), n_tasks=40))
    assert 0.0 <= p <= 1.0


def test_simulate_binary_shape():
    base, mand = simulate_binary(0.25, rng(3), n_tasks=50)
    assert len(base) == len(mand) == 50
    assert all(v in (0, 1) for v in base + mand)


def test_binary_test_returns_valid_p():
    base, mand = simulate_binary(0.25, rng(4), n_tasks=50)
    p = run_test_binary(base, mand)
    assert 0.0 <= p <= 1.0


# --- effect-size mapping -----------------------------------------------------

def test_p_from_h():
    assert abs(_p_from_h(0.7, 0.0) - 0.7) < 1e-9
    assert _p_from_h(0.7, 0.3) > 0.7
    assert _p_from_h(0.5, 0.25) > 0.5


# --- power behaviour ---------------------------------------------------------

def test_continuous_power_rises_with_effect():
    p_null = power_continuous(0.0, N_SIMS, rng(10), n_tasks=120)
    p_big = power_continuous(0.6, N_SIMS, rng(11), n_tasks=120)
    assert p_null < 0.20            # under the null, near alpha
    assert p_big > 0.70             # a large effect is well powered
    assert p_big > p_null


def test_binary_power_rises_with_effect():
    p_null = power_binary(0.0, N_SIMS, rng(12), n_tasks=120)
    p_eff = power_binary(0.30, N_SIMS, rng(13), n_tasks=120)
    assert p_null < 0.20
    assert p_eff > p_null


def test_power_at():
    pv = [0.001, 0.02, 0.2, 0.6]
    assert power_at(pv, 0.01) == 0.25
    assert power_at(pv, 0.05) == 0.5
    assert power_at([], 0.01) == 0.0


# --- MDE interpolation -------------------------------------------------------

def test_interpolate_mde_crossing():
    sweep = [ScenarioPower(0.4, 60, power_holm=0.60, power_loose=0.7),
             ScenarioPower(0.5, 60, power_holm=0.90, power_loose=0.95)]
    mde = _interpolate_mde(sweep)
    assert abs(mde - 0.4667) < 0.01      # 0.8 crossing interpolated


def test_interpolate_mde_all_powered():
    sweep = [ScenarioPower(0.4, 60, power_holm=0.85, power_loose=0.9),
             ScenarioPower(0.5, 60, power_holm=0.95, power_loose=0.99)]
    assert _interpolate_mde(sweep) == 0.4


def test_interpolate_mde_underpowered():
    sweep = [ScenarioPower(0.4, 60, power_holm=0.30, power_loose=0.4),
             ScenarioPower(0.5, 60, power_holm=0.55, power_loose=0.6)]
    assert _interpolate_mde(sweep) is None


# --- run_outcome -------------------------------------------------------------

def test_run_outcome_structure():
    res = run_outcome("O1_anchor_completeness", "d", N_SIMS, rng(20),
                      n_tasks=120)
    assert res.outcome == "O1_anchor_completeness"
    assert len(res.scenarios) == 3
    assert isinstance(res.halt, bool)
    assert res.operational_threshold == 0.4
    d = res.to_dict()
    assert d["target_power"] == 0.80 and "scenarios" in d


def test_operational_effect_covers_all_primary_outcomes():
    assert set(OPERATIONAL_EFFECT) == {o for o, _ in PRIMARY_OUTCOMES}
