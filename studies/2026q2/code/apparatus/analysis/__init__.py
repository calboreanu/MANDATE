"""Statistical analysis for the MANDATE evaluation (Workstream B6).

Built: power.py, the simulation-based power analysis (ANALYSIS_PLAN
Notebook 03), which is also a pre-registration deposit gate.
"""
from .power import (
    run_power_analysis, run_outcome, power_continuous, power_binary,
    power_at, simulate_continuous, simulate_binary, run_test_continuous,
    run_test_binary, D_SCENARIOS, H_SCENARIOS, HOLM_ALPHA, LOOSE_ALPHA,
    TARGET_POWER, OPERATIONAL_EFFECT, PRIMARY_OUTCOMES, OutcomePower,
    ScenarioPower,
)

__all__ = [
    "run_power_analysis", "run_outcome", "power_continuous", "power_binary",
    "power_at", "simulate_continuous", "simulate_binary",
    "run_test_continuous", "run_test_binary", "D_SCENARIOS", "H_SCENARIOS",
    "HOLM_ALPHA", "LOOSE_ALPHA", "TARGET_POWER", "OPERATIONAL_EFFECT",
    "PRIMARY_OUTCOMES", "OutcomePower", "ScenarioPower",
]
