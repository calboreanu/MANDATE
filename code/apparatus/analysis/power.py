"""
Simulation-based power analysis (Workstream B6, ANALYSIS_PLAN Notebook 03).

PROTOCOL_LOCK Section 6.5 and ANALYSIS_PLAN require a simulation-based power
analysis, run before Phase 6, that simulates the actual design, runs the
planned tests, and reports the minimum detectable effect (MDE) at 80% power.
PROTOCOL_LOCK Section 13 halts the study if the MDE exceeds the operational
significance threshold for any primary outcome.

Design simulated (PROTOCOL_LOCK Sections 1, 3, 6):
  120 tasks, 3 domains, 3 task types, two paired systems (MANDATE-primary vs
  the designated strongest baseline). Per Section 6.3 the unit of analysis is
  the task and the per-task metric is the median across the 10 runs, so this
  module simulates the task-level aggregate directly: the 10-run collapse only
  reduces within-task measurement noise, folded into the residual.

Tests, matching the pre-registered analysis (Sections 6.1 and 6.2):

  Continuous outcomes (O1, O2a, O2b, O3). The planned model is
  metric ~ system + domain + task_type + system:domain + (1 | task_id).
  For the two-system paired design simulated here, the system fixed-effect
  test reduces exactly to the paired comparison of within-task differences:
  the task random intercept and the task-level covariates domain and
  task_type are identical for both systems on a given task and cancel in the
  difference (mandate minus baseline). The paired t-test on those differences
  is therefore an exact, fast, and numerically robust evaluation of the
  planned system test for this design, and avoids fitting a near-degenerate
  mixed model 5,000 times. It is, if anything, slightly conservative relative
  to the pre-registered beta / fractional-logistic mixed model, which is the
  safe direction for a power analysis.

  Binary outcomes (O4, O5). McNemar's test on the paired per-task outcomes.
  The binary primary analysis (Section 6.1) is a logistic mixed-effects
  model; McNemar is the pre-registered paired binary test (Section 6.2) and,
  for a two-system paired design, is the conditional-efficient test of the
  within-task system effect, because concordant pairs carry no within-task
  system information once the task is conditioned out. It is mildly
  conservative relative to the logistic mixed model, so the binary-outcome
  power reported here is a conservative lower bound.

Effect-size scenarios are Section 6.5: d in {0.4, 0.5, 0.6} for continuous,
Cohen's h in {0.20, 0.25, 0.30} for proportions.

Significance threshold. Per-outcome power is reported at two thresholds:
HOLM_ALPHA = 0.01, the most stringent Holm-Bonferroni step (the
ANALYSIS_PLAN power pseudocode uses 0.01), and LOOSE_ALPHA = 0.05, the
loosest step. The MDE and the halt decision use the conservative 0.01, so a
flagged halt is a prompt to review (expand sample or re-specify), per
Section 13, not an automatic stop. The realized per-outcome Holm threshold
falls somewhere in [0.01, 0.05].
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

# PROTOCOL_LOCK Section 6.5 effect-size scenarios.
D_SCENARIOS = (0.4, 0.5, 0.6)
H_SCENARIOS = (0.20, 0.25, 0.30)

HOLM_ALPHA = 0.01      # most stringent Holm step; MDE / halt use this
LOOSE_ALPHA = 0.05     # loosest Holm step; reported alongside
TARGET_POWER = 0.80

# Operational effect thresholds (PROTOCOL_LOCK Section 7). The Section 13
# halt rule fires if the design's MDE at 80% power exceeds these.
OPERATIONAL_EFFECT = {
    "O1_anchor_completeness":    ("d", 0.4),
    "O2a_gap_recall":            ("h", 0.3),
    "O3_fabrication_rate":       ("d", 0.4),
    "O4_schema_validity":        ("h", 0.4),
    "O5_adversarial_resistance": ("h", 0.4),
}

PRIMARY_OUTCOMES = (
    ("O1_anchor_completeness", "d"),
    ("O2a_gap_recall", "h"),
    ("O3_fabrication_rate", "d"),
    ("O4_schema_validity", "h"),
    ("O5_adversarial_resistance", "h"),
)

# Effective sample size per primary outcome. The outcomes are not all measured
# on the full 120-task corpus:
#   O1, O3, O4  the full 120 main-corpus tasks
#   O2a         the 36 gap-triggering tasks (12 per domain x 3; PREREG 3.1)
#   O5          the 50 prompt-injection perturbations (PROTOCOL_LOCK 1)
# Using a uniform 120 would overstate power for O2a and O5.
OUTCOME_N = {
    "O1_anchor_completeness": 120,
    "O2a_gap_recall": 36,
    "O3_fabrication_rate": 120,
    "O4_schema_validity": 120,
    "O5_adversarial_resistance": 50,
}

DEFAULT_N_TASKS = 120
DEFAULT_ICC = 0.5            # share of task-level variance that is between-task


# --- continuous outcomes -----------------------------------------------------

def simulate_continuous(effect_d: float, rng, n_tasks: int = DEFAULT_N_TASKS,
                        icc: float = DEFAULT_ICC, n_domains: int = 3,
                        n_task_types: int = 3):
    """Simulate task-level data for two paired systems on a continuous,
    standardized outcome.

    The within-system task-level metric has SD 1 by construction, so the
    system mean shift equals Cohen's d directly. `icc` is the share of that
    variance carried by the (1 | task_id) random intercept, shared across the
    two systems for a task, which induces the paired structure. Returns a list
    of row dicts: task_id, domain, task_type, system, metric.
    """
    sd_between = math.sqrt(icc)
    sd_within = math.sqrt(1.0 - icc)
    domain_eff = np.linspace(-0.05, 0.05, n_domains)
    type_eff = np.linspace(-0.05, 0.05, n_task_types)
    rows = []
    for t in range(n_tasks):
        domain = t % n_domains
        task_type = (t // n_domains) % n_task_types
        task_intercept = rng.normal(0.0, sd_between)
        fixed = domain_eff[domain] + type_eff[task_type]
        for system, shift in (("baseline", 0.0), ("mandate", effect_d)):
            metric = (task_intercept + fixed + shift
                      + rng.normal(0.0, sd_within))
            rows.append({"task_id": t, "domain": domain,
                         "task_type": task_type, "system": system,
                         "metric": metric})
    return rows


def run_test_continuous(rows) -> float:
    """Two-sided p-value for the system effect: a paired t-test on the
    within-task differences (see the module docstring for why this is the
    exact system test of the planned mixed model for a two-system paired
    design)."""
    by_task = {}
    for r in rows:
        by_task.setdefault(r["task_id"], {})[r["system"]] = r["metric"]
    diffs = [v["mandate"] - v["baseline"] for v in by_task.values()
             if "mandate" in v and "baseline" in v]
    if len(diffs) < 2:
        return 1.0
    from scipy import stats
    _, p = stats.ttest_1samp(diffs, 0.0)
    return float(p) if p == p else 1.0


# --- binary outcomes ---------------------------------------------------------

def _p_from_h(base_rate: float, effect_h: float) -> float:
    """The MANDATE success rate that is Cohen's h above `base_rate`."""
    phi_base = 2.0 * math.asin(math.sqrt(base_rate))
    p = math.sin((phi_base + effect_h) / 2.0) ** 2
    return min(0.999, max(0.001, p))


def simulate_binary(effect_h: float, rng, base_rate: float = 0.7,
                    n_tasks: int = DEFAULT_N_TASKS, icc: float = DEFAULT_ICC):
    """Simulate paired per-task binary outcomes for two systems via a latent
    normal model: a shared task component (the random intercept) plus a
    system-specific shift calibrated so the marginal rates are `base_rate`
    and the rate Cohen's h above it. Returns (baseline[], mandate[])."""
    from statistics import NormalDist
    nd = NormalDist()
    p_mandate = _p_from_h(base_rate, effect_h)
    c = nd.inv_cdf(1.0 - base_rate)                  # baseline threshold
    delta = c - nd.inv_cdf(1.0 - p_mandate)          # MANDATE latent shift
    sd_between = math.sqrt(icc)
    sd_within = math.sqrt(1.0 - icc)
    baseline, mandate = [], []
    for _ in range(n_tasks):
        b = rng.normal(0.0, sd_between)
        baseline.append(int(b + rng.normal(0.0, sd_within) > c))
        mandate.append(int(b + delta + rng.normal(0.0, sd_within) > c))
    return baseline, mandate


def run_test_binary(baseline, mandate) -> float:
    """McNemar's test on the paired per-task binary outcomes; two-sided
    p-value."""
    from statsmodels.stats.contingency_tables import mcnemar
    n01 = sum(1 for b, m in zip(baseline, mandate) if b == 0 and m == 1)
    n10 = sum(1 for b, m in zip(baseline, mandate) if b == 1 and m == 0)
    n00 = sum(1 for b, m in zip(baseline, mandate) if b == 0 and m == 0)
    n11 = sum(1 for b, m in zip(baseline, mandate) if b == 1 and m == 1)
    table = [[n11, n10], [n01, n00]]
    exact = (n01 + n10) < 25
    try:
        res = mcnemar(table, exact=exact, correction=True)
        p = float(res.pvalue)
        return p if p == p else 1.0
    except Exception:
        return 1.0


# --- p-value collection ------------------------------------------------------

def pvalues_continuous(effect_d: float, n_simulations: int, rng,
                       **sim_kwargs) -> list:
    return [run_test_continuous(
            simulate_continuous(effect_d, rng, **sim_kwargs))
            for _ in range(n_simulations)]


def pvalues_binary(effect_h: float, n_simulations: int, rng,
                   **sim_kwargs) -> list:
    out = []
    for _ in range(n_simulations):
        baseline, mandate = simulate_binary(effect_h, rng, **sim_kwargs)
        out.append(run_test_binary(baseline, mandate))
    return out


def power_at(pvalues, alpha: float) -> float:
    """Fraction of simulations rejecting the null at `alpha`."""
    if not pvalues:
        return 0.0
    return sum(1 for p in pvalues if p < alpha) / len(pvalues)


def power_continuous(effect_d: float, n_simulations: int, rng,
                     alpha: float = HOLM_ALPHA, **sim_kwargs) -> float:
    """Convenience: empirical power for a continuous effect at `alpha`."""
    return power_at(pvalues_continuous(effect_d, n_simulations, rng,
                                       **sim_kwargs), alpha)


def power_binary(effect_h: float, n_simulations: int, rng,
                 alpha: float = HOLM_ALPHA, **sim_kwargs) -> float:
    """Convenience: empirical power for a binary effect at `alpha`."""
    return power_at(pvalues_binary(effect_h, n_simulations, rng,
                                   **sim_kwargs), alpha)


# --- power sweep, MDE, halt --------------------------------------------------

@dataclass
class ScenarioPower:
    effect_size: float
    n_simulations: int
    power_holm: float        # power at HOLM_ALPHA (0.01), conservative
    power_loose: float       # power at LOOSE_ALPHA (0.05)


@dataclass
class OutcomePower:
    outcome: str
    effect_kind: str                                  # "d" or "h"
    sample_size: int = None                            # tasks / perturbations
    scenarios: list = field(default_factory=list)     # list[ScenarioPower]
    mde_at_target: float = None        # smallest effect reaching TARGET_POWER
    operational_threshold: float = None
    halt: bool = False                 # MDE exceeds the operational threshold

    def to_dict(self) -> dict:
        return {
            "outcome": self.outcome, "effect_kind": self.effect_kind,
            "sample_size": self.sample_size,
            "scenarios": [{"effect_size": s.effect_size,
                           "n_simulations": s.n_simulations,
                           "power_at_0.01": s.power_holm,
                           "power_at_0.05": s.power_loose}
                          for s in self.scenarios],
            "mde_at_target_power": self.mde_at_target,
            "operational_threshold": self.operational_threshold,
            "target_power": TARGET_POWER, "halt": self.halt,
        }


def _interpolate_mde(scenarios) -> float:
    """Smallest effect size reaching TARGET_POWER on the conservative (0.01)
    power curve, linearly interpolating between adjacent scenarios. None if
    even the largest tested effect does not reach target power."""
    pts = sorted((s.effect_size, s.power_holm) for s in scenarios)
    for (e_lo, p_lo), (e_hi, p_hi) in zip(pts, pts[1:]):
        if p_lo < TARGET_POWER <= p_hi:
            if p_hi == p_lo:
                return e_hi
            frac = (TARGET_POWER - p_lo) / (p_hi - p_lo)
            return round(e_lo + frac * (e_hi - e_lo), 4)
    if pts and pts[0][1] >= TARGET_POWER:
        return pts[0][0]
    return None


def run_outcome(outcome: str, effect_kind: str, n_simulations: int, rng,
                scenarios=None, **sim_kwargs) -> OutcomePower:
    """Run the power sweep for one outcome and assemble the halt comparison."""
    if effect_kind == "d":
        grid = scenarios or D_SCENARIOS
        pval_fn = pvalues_continuous
    elif effect_kind == "h":
        grid = scenarios or H_SCENARIOS
        pval_fn = pvalues_binary
    else:
        raise ValueError("effect_kind must be 'd' or 'h'")
    sweep = []
    for eff in grid:
        pvals = pval_fn(eff, n_simulations, rng, **sim_kwargs)
        sweep.append(ScenarioPower(
            effect_size=eff, n_simulations=n_simulations,
            power_holm=power_at(pvals, HOLM_ALPHA),
            power_loose=power_at(pvals, LOOSE_ALPHA)))
    op = OPERATIONAL_EFFECT.get(outcome)
    op_threshold = op[1] if op else None
    mde = _interpolate_mde(sweep)
    halt = False
    if op_threshold is not None:
        # halt if the design cannot reach 80% power at the operationally
        # meaningful effect: MDE undefined within the grid, or above threshold
        halt = (mde is None) or (mde > op_threshold)
    return OutcomePower(outcome=outcome, effect_kind=effect_kind,
                        sample_size=sim_kwargs.get("n_tasks"),
                        scenarios=sweep, mde_at_target=mde,
                        operational_threshold=op_threshold, halt=halt)


def run_power_analysis(n_simulations: int = 5000, seed: int = 20260523,
                       binary_base_rate: float = 0.7) -> dict:
    """Run the full pre-registered power analysis across the five primary
    outcomes, each at its own effective sample size (OUTCOME_N). Returns a
    report dict with the overall halt decision (PROTOCOL_LOCK Section 13).

    `binary_base_rate` is the assumed strongest-baseline success rate for the
    binary outcomes (O4, O5) and the proportion outcome O2a. It is an
    ASSUMPTION; before deposit it should be set from the Phase 0 pilot or PI
    input, since McNemar power depends on it. The default 0.7 is a placeholder.
    """
    rng = np.random.default_rng(seed)
    results = []
    for outcome, kind in PRIMARY_OUTCOMES:
        kwargs = {"n_tasks": OUTCOME_N[outcome]}
        if kind == "h":
            kwargs["base_rate"] = binary_base_rate
        results.append(run_outcome(outcome, kind, n_simulations, rng,
                                   **kwargs))
    return {
        "n_simulations": n_simulations, "seed": seed,
        "outcome_n": dict(OUTCOME_N), "binary_base_rate": binary_base_rate,
        "holm_alpha": HOLM_ALPHA, "loose_alpha": LOOSE_ALPHA,
        "target_power": TARGET_POWER,
        "outcomes": [r.to_dict() for r in results],
        "halt": any(r.halt for r in results),
        "halt_outcomes": [r.outcome for r in results if r.halt],
    }
