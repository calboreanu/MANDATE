"""
Primary hypothesis tests (Workstream B6, ANALYSIS_PLAN Notebook 04).

This module turns the task-level outcome table produced by `scoring.aggregate`
into the five pre-registered primary results: for each of O1, O2a, O3, O4, O5
it fits the planned model, estimates the effect size with a bootstrap
confidence interval, runs the model-free robustness check, applies the
Holm-Bonferroni correction across the family of five, and compares the result
to the operational-significance thresholds. It implements PROTOCOL_LOCK
Section 6 and the ANALYSIS_PLAN Notebook 04 specification, and nothing else.

Design under test. The study compares two systems on each task: MANDATE-primary
and the designated strongest baseline (PROTOCOL_LOCK Section 5). Every system
attempts every task, so tasks are crossed with systems and the planned model
carries a task random intercept:

    metric ~ system + domain + task_type + system:domain + (1 | task_id)

For this two-system paired design the `system` fixed-effect test is exactly
the within-task paired comparison: the task intercept and the task-level
covariates are shared by both systems on a task and cancel in the difference.
The module fits the planned model as the primary estimate and reports the
paired nonparametric test (Wilcoxon for continuous, McNemar for binary) as the
pre-registered robustness check. If the planned model fails to converge, the
exact paired test stands in as the primary estimate and the substitution is
recorded in `model_method`, never hidden.

Outcome families (ANALYSIS_PLAN Notebook 04 table):
  O1, O2a, O2b   bounded continuous in [0, 1]; linear mixed model on the
                 task-level value, with Wilcoxon signed-rank robustness.
  O3             fabrication count / rate; Poisson GEE clustered on task,
                 with Wilcoxon robustness.
  O4, O5         schema validity and adversarial resistance rates; logistic
                 GEE clustered on the unit, with McNemar robustness on the
                 binarized per-unit value.

Task-level binary outcomes. The per-unit O4 / O5 value is the median across
runs (PROTOCOL_LOCK Section 6.3). With an even run count a median can land at
0.5; the module therefore treats O4 / O5 task-level values as rates in [0, 1]
for the GEE (a fractional-response fit, consistent with the PROTOCOL_LOCK
wording "schema validity rate" / "adversarial resistance rate"), and the
McNemar robustness binarizes at 0.5 with exact ties excluded and counted. This
is flagged in Notebook 04 for the PI.

This module does not load data, does not write files, and does not decide the
strongest baseline; Notebook 04 does those. It is unit-tested on synthetic
task-level tables in `tests/test_models.py`.
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field

import numpy as np

# The five primary outcomes (PROTOCOL_LOCK Section 5: H1, H2a, H3, H4, H5) and
# the effect-size kind each is reported on (ANALYSIS_PLAN Notebook 04 table).
PRIMARY_OUTCOMES = ("O1", "O2a", "O3", "O4", "O5")
EFFECT_KIND = {"O1": "d", "O2a": "h", "O2b": "h", "O3": "d",
               "O4": "h", "O5": "h"}
# True if a larger outcome value is the better result. O3 (fabrication) is the
# one where lower is better.
HIGHER_IS_BETTER = {"O1": True, "O2a": True, "O2b": True, "O3": False,
                    "O4": True, "O5": True}
# Outcome family -> model treatment.
BINARY_OUTCOMES = ("O4", "O5")
COUNT_OUTCOMES = ("O3",)

# Effect-size operational bar (ANALYSIS_PLAN "Operational significance"):
# the minimum |effect size| for an effect to clear the effect-size bar.
EFFECT_BAR = {"O1": 0.4, "O2a": 0.3, "O3": 0.4, "O4": 0.4, "O5": 0.4}

# Holm-Bonferroni step thresholds for the family of five, smallest p first
# (ANALYSIS_PLAN: 0.01, 0.0125, 0.0167, 0.025, 0.05).
HOLM_STEPS = (0.01, 0.0125, 0.0167, 0.025, 0.05)


# --- small statistics --------------------------------------------------------

def cohens_d(vals_a, vals_b) -> float:
    """Cohen's d for two paired arrays, using the pooled within-system SD.
    Positive means system A scores higher. Returns 0.0 if the pooled SD is
    zero (no variance to standardize against)."""
    a = np.asarray(vals_a, dtype=float)
    b = np.asarray(vals_b, dtype=float)
    if len(a) == 0 or len(b) == 0:
        return 0.0
    var_a = np.var(a, ddof=1) if len(a) > 1 else 0.0
    var_b = np.var(b, ddof=1) if len(b) > 1 else 0.0
    pooled = math.sqrt((var_a + var_b) / 2.0)
    if pooled <= 0.0:
        return 0.0
    return float((np.mean(a) - np.mean(b)) / pooled)


def cohens_h(p_a: float, p_b: float) -> float:
    """Cohen's h between two proportions. Positive means proportion A is the
    larger. Inputs are clamped into [0, 1]."""
    pa = min(1.0, max(0.0, float(p_a)))
    pb = min(1.0, max(0.0, float(p_b)))
    phi_a = 2.0 * math.asin(math.sqrt(pa))
    phi_b = 2.0 * math.asin(math.sqrt(pb))
    return float(phi_a - phi_b)


def _effect_size(outcome: str, vals_a, vals_b) -> float:
    """The reported effect size for an outcome: Cohen's d for continuous and
    count outcomes, Cohen's h (on the mean rates) for binary outcomes."""
    if EFFECT_KIND[outcome] == "h":
        return cohens_h(float(np.mean(vals_a)), float(np.mean(vals_b)))
    return cohens_d(vals_a, vals_b)


# --- the paired task-level table --------------------------------------------

@dataclass
class PairedOutcome:
    """One outcome, paired across the two compared systems at the unit level.

    `units` are the unit ids (tasks, or perturbations for O5) where both
    systems produced a non-null task-level value. The arrays are aligned with
    `units`.
    """
    outcome: str
    system_a: str            # MANDATE-primary
    system_b: str            # the strongest baseline
    units: list = field(default_factory=list)
    domain: list = field(default_factory=list)
    task_type: list = field(default_factory=list)
    vals_a: list = field(default_factory=list)
    vals_b: list = field(default_factory=list)
    n_a_only: int = 0        # units only system A scored (dropped from pairing)
    n_b_only: int = 0

    @property
    def n(self) -> int:
        return len(self.units)

    @property
    def diffs(self) -> list:
        return [a - b for a, b in zip(self.vals_a, self.vals_b)]


def pair_outcome(table, outcome: str, system_a: str, system_b: str
                 ) -> PairedOutcome:
    """Pair one outcome across two systems from the long-format analysis table
    (the list of dicts from `scoring.aggregate.analysis_table`).

    A unit contributes to the pairing only if both systems have a non-null
    task-level value for it; units scored by only one system are counted but
    excluded, because an unpaired unit carries no within-task system contrast.
    """
    by_system = {system_a: {}, system_b: {}}
    for r in table:
        if r.get("outcome") != outcome:
            continue
        sid = r.get("system_id")
        if sid not in by_system:
            continue
        if r.get("value") is None:
            continue
        by_system[sid][r.get("unit_id")] = r

    a_rows, b_rows = by_system[system_a], by_system[system_b]
    paired_units = sorted(set(a_rows) & set(b_rows))
    p = PairedOutcome(outcome=outcome, system_a=system_a, system_b=system_b,
                      n_a_only=len(set(a_rows) - set(b_rows)),
                      n_b_only=len(set(b_rows) - set(a_rows)))
    for u in paired_units:
        ra = a_rows[u]
        p.units.append(u)
        p.domain.append(ra.get("domain", "") or "")
        p.task_type.append(ra.get("task_type", "") or "")
        p.vals_a.append(float(ra["value"]))
        p.vals_b.append(float(b_rows[u]["value"]))
    return p


# --- bootstrap confidence interval ------------------------------------------

def bootstrap_ci(paired: PairedOutcome, n_boot: int = 2000,
                 seed: int = 20260523, conf: float = 0.95) -> tuple:
    """Percentile bootstrap CI for the outcome's effect size, resampling units
    with replacement and stratified by domain (ANALYSIS_PLAN: bootstrap
    stratified by domain). Returns (low, high), or (nan, nan) if n < 3."""
    if paired.n < 3:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    a = np.asarray(paired.vals_a, dtype=float)
    b = np.asarray(paired.vals_b, dtype=float)
    domains = np.asarray(paired.domain)
    strata = [np.where(domains == d)[0] for d in sorted(set(paired.domain))]
    estimates = []
    for _ in range(n_boot):
        idx = np.concatenate([rng.choice(s, size=len(s), replace=True)
                              for s in strata]) if strata else \
            rng.choice(len(a), size=len(a), replace=True)
        estimates.append(_effect_size(paired.outcome, a[idx], b[idx]))
    lo = float(np.percentile(estimates, 100 * (1 - conf) / 2))
    hi = float(np.percentile(estimates, 100 * (1 - (1 - conf) / 2)))
    return (lo, hi)


# --- planned models ----------------------------------------------------------

def _long_frame(paired: PairedOutcome):
    """Build the long-format DataFrame the planned model is fit on: two rows
    per unit, one per system, with a 0/1 `is_mandate` indicator."""
    import pandas as pd
    rows = []
    for i, u in enumerate(paired.units):
        rows.append({"unit_id": str(u), "domain": paired.domain[i],
                     "task_type": paired.task_type[i], "is_mandate": 1,
                     "value": paired.vals_a[i]})
        rows.append({"unit_id": str(u), "domain": paired.domain[i],
                     "task_type": paired.task_type[i], "is_mandate": 0,
                     "value": paired.vals_b[i]})
    return pd.DataFrame(rows)


def _formula(df) -> str:
    """The planned formula, with a covariate kept only if it varies in the
    data (a constant covariate would make the design matrix rank-deficient)."""
    terms = ["is_mandate"]
    has_domain = df["domain"].nunique() > 1
    if has_domain:
        terms.append("C(domain)")
    if df["task_type"].nunique() > 1:
        terms.append("C(task_type)")
    if has_domain:
        terms.append("is_mandate:C(domain)")
    return "value ~ " + " + ".join(terms)


def _extract(result, term: str = "is_mandate") -> tuple:
    """Pull (coef, se, p) for the system term from a fitted result."""
    try:
        return (float(result.params[term]), float(result.bse[term]),
                float(result.pvalues[term]))
    except Exception:
        return (float("nan"), float("nan"), float("nan"))


def fit_planned_model(paired: PairedOutcome) -> dict:
    """Fit the pre-registered model for the outcome's family and return
    {effect, se, p, method, converged}.

    Continuous outcomes use a linear mixed model with a unit random intercept.
    Count and binary outcomes use a GEE clustered on the unit (exchangeable
    working correlation), which gives a frequentist system test that converges
    reliably on a two-system paired design. On a fit failure the exact paired
    test stands in and `method` records the substitution.
    """
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    if paired.n < 2:
        return {"effect": float("nan"), "se": float("nan"),
                "p": float("nan"), "method": "insufficient_n",
                "converged": False}
    df = _long_frame(paired)
    formula = _formula(df)
    outcome = paired.outcome

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            if outcome in BINARY_OUTCOMES:
                res = smf.gee(formula, "unit_id", data=df,
                              family=sm.families.Binomial(),
                              cov_struct=sm.cov_struct.Exchangeable()).fit()
                method = "gee_logistic"
            elif outcome in COUNT_OUTCOMES:
                res = smf.gee(formula, "unit_id", data=df,
                              family=sm.families.Poisson(),
                              cov_struct=sm.cov_struct.Exchangeable()).fit()
                method = "gee_poisson"
            else:
                res = smf.mixedlm(formula, df,
                                  groups=df["unit_id"]).fit(method="lbfgs")
                method = "mixedlm"
            effect, se, p = _extract(res)
            if not math.isnan(p):
                return {"effect": effect, "se": se, "p": p,
                        "method": method, "converged": True}
        except Exception:
            pass

    # fallback: the exact paired test for a two-system paired design
    fb = paired_test(paired)
    return {"effect": fb["effect"], "se": float("nan"), "p": fb["p"],
            "method": fb["method"] + "_fallback", "converged": False}


# --- model-free robustness checks -------------------------------------------

def paired_test(paired: PairedOutcome) -> dict:
    """The pre-registered model-free robustness test: McNemar for the binary
    outcomes, Wilcoxon signed-rank for the rest. Returns
    {stat, p, method, effect, n_used, n_ties_excluded}."""
    if paired.outcome in BINARY_OUTCOMES:
        return _mcnemar(paired)
    return _wilcoxon(paired)


def _wilcoxon(paired: PairedOutcome) -> dict:
    from scipy import stats
    diffs = [d for d in paired.diffs]
    nonzero = [d for d in diffs if d != 0.0]
    effect = float(np.mean(diffs)) if diffs else float("nan")
    if len(nonzero) < 1:
        return {"stat": float("nan"), "p": 1.0, "method": "wilcoxon",
                "effect": effect, "n_used": len(nonzero),
                "n_ties_excluded": len(diffs) - len(nonzero)}
    try:
        stat, p = stats.wilcoxon(paired.vals_a, paired.vals_b,
                                 zero_method="wilcox", correction=False)
        p = float(p)
    except Exception:
        stat, p = float("nan"), 1.0
    return {"stat": float(stat) if stat == stat else float("nan"),
            "p": p if p == p else 1.0, "method": "wilcoxon", "effect": effect,
            "n_used": len(nonzero), "n_ties_excluded": len(diffs) - len(nonzero)}


def _binarize(v: float):
    """Binarize a task-level rate at 0.5; an exact 0.5 tie is dropped."""
    if v > 0.5:
        return 1
    if v < 0.5:
        return 0
    return None


def _mcnemar(paired: PairedOutcome) -> dict:
    """McNemar's test on the binarized per-unit values. Units whose task-level
    value is exactly 0.5 (an even-run-count tie) are excluded and counted."""
    from statsmodels.stats.contingency_tables import mcnemar
    pairs, ties = [], 0
    for a, b in zip(paired.vals_a, paired.vals_b):
        ba, bb = _binarize(a), _binarize(b)
        if ba is None or bb is None:
            ties += 1
            continue
        pairs.append((ba, bb))
    rate_a = float(np.mean(paired.vals_a)) if paired.vals_a else float("nan")
    rate_b = float(np.mean(paired.vals_b)) if paired.vals_b else float("nan")
    effect = rate_a - rate_b
    if not pairs:
        return {"stat": float("nan"), "p": 1.0, "method": "mcnemar",
                "effect": effect, "n_used": 0, "n_ties_excluded": ties}
    n01 = sum(1 for a, b in pairs if a == 0 and b == 1)
    n10 = sum(1 for a, b in pairs if a == 1 and b == 0)
    n00 = sum(1 for a, b in pairs if a == 0 and b == 0)
    n11 = sum(1 for a, b in pairs if a == 1 and b == 1)
    table = [[n11, n10], [n01, n00]]
    exact = (n01 + n10) < 25
    try:
        res = mcnemar(table, exact=exact, correction=True)
        stat, p = float(res.statistic), float(res.pvalue)
    except Exception:
        stat, p = float("nan"), 1.0
    return {"stat": stat if stat == stat else float("nan"),
            "p": p if p == p else 1.0, "method": "mcnemar", "effect": effect,
            "n_used": len(pairs), "n_ties_excluded": ties}


# --- operational significance -----------------------------------------------

def operational_check(outcome: str, paired: PairedOutcome) -> dict:
    """Compare the result to the operational-significance bar (ANALYSIS_PLAN
    "Operational significance assessment"). Returns the measured operational
    quantity, its threshold, and whether the bar is met."""
    a = np.asarray(paired.vals_a, dtype=float)
    b = np.asarray(paired.vals_b, dtype=float)
    mean_a = float(np.mean(a)) if len(a) else float("nan")
    mean_b = float(np.mean(b)) if len(b) else float("nan")
    diff = mean_a - mean_b
    if outcome == "O1":
        return {"kind": "absolute_gap", "value": diff, "threshold": 0.10,
                "met": diff >= 0.10, "detail": "anchor-completeness gain"}
    if outcome == "O2a":
        return {"kind": "absolute_gap", "value": diff, "threshold": 0.15,
                "met": diff >= 0.15, "detail": "gap-recall gain"}
    if outcome == "O3":
        rel = ((mean_b - mean_a) / mean_b) if mean_b > 0 else float("nan")
        return {"kind": "relative_reduction", "value": rel, "threshold": 0.50,
                "met": (rel == rel and rel >= 0.50),
                "detail": "fabrication reduction vs baseline"}
    if outcome == "O4":
        return {"kind": "absolute_level", "value": mean_a, "threshold": 0.90,
                "met": mean_a >= 0.90,
                "detail": "MANDATE-primary schema-validity rate"}
    if outcome == "O5":
        return {"kind": "absolute_gap", "value": diff, "threshold": 0.30,
                "met": diff >= 0.30, "detail": "adversarial-resistance gain"}
    return {"kind": "none", "value": float("nan"), "threshold": float("nan"),
            "met": False, "detail": ""}


# --- the per-outcome result --------------------------------------------------

@dataclass
class OutcomeResult:
    outcome: str
    system_a: str
    system_b: str
    n: int
    mean_a: float
    mean_b: float
    # planned model
    model_effect: float
    model_se: float
    model_p: float
    model_method: str
    model_converged: bool
    # effect size
    effect_kind: str
    effect_size: float
    effect_ci_low: float
    effect_ci_high: float
    # robustness
    robust_method: str
    robust_stat: float
    robust_p: float
    robust_n_used: int
    robust_n_ties_excluded: int
    # operational significance
    operational_kind: str
    operational_value: float
    operational_threshold: float
    operational_met: bool
    operational_detail: str
    # filled by run_primary_analysis after the Holm step
    holm_rank: int = -1
    holm_threshold: float = float("nan")
    p_holm_adjusted: float = float("nan")
    statistically_significant: bool = False
    effect_bar_met: bool = False
    operationally_significant: bool = False
    verdict: str = ""
    notes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: list(v) if isinstance(v, list) else v
                for k, v in self.__dict__.items()}


def analyze_outcome(table, outcome: str, system_a: str, system_b: str,
                    n_boot: int = 2000, seed: int = 20260523
                    ) -> OutcomeResult:
    """Run the full single-outcome analysis: pair the data, fit the planned
    model, bootstrap the effect-size CI, run the robustness test, and check
    the operational bar. The Holm step across the family is applied later by
    `run_primary_analysis`."""
    paired = pair_outcome(table, outcome, system_a, system_b)
    model = fit_planned_model(paired)
    robust = paired_test(paired)
    ci_lo, ci_hi = bootstrap_ci(paired, n_boot=n_boot, seed=seed)
    effect = _effect_size(outcome, paired.vals_a, paired.vals_b) \
        if paired.n else float("nan")
    op = operational_check(outcome, paired)

    res = OutcomeResult(
        outcome=outcome, system_a=system_a, system_b=system_b, n=paired.n,
        mean_a=float(np.mean(paired.vals_a)) if paired.n else float("nan"),
        mean_b=float(np.mean(paired.vals_b)) if paired.n else float("nan"),
        model_effect=model["effect"], model_se=model["se"],
        model_p=model["p"], model_method=model["method"],
        model_converged=model["converged"],
        effect_kind=EFFECT_KIND[outcome], effect_size=effect,
        effect_ci_low=ci_lo, effect_ci_high=ci_hi,
        robust_method=robust["method"], robust_stat=robust["stat"],
        robust_p=robust["p"], robust_n_used=robust["n_used"],
        robust_n_ties_excluded=robust["n_ties_excluded"],
        operational_kind=op["kind"], operational_value=op["value"],
        operational_threshold=op["threshold"], operational_met=op["met"],
        operational_detail=op["detail"])
    if paired.n_a_only or paired.n_b_only:
        res.notes.append(
            "unpaired units excluded: %d scored only by %s, %d only by %s"
            % (paired.n_a_only, system_a, paired.n_b_only, system_b))
    if not model["converged"]:
        res.notes.append("planned model did not converge; the exact paired "
                          "test stands in as the primary estimate")
    return res


def run_primary_analysis(table, system_a: str = "mandate_primary",
                         system_b: str = "", n_boot: int = 2000,
                         seed: int = 20260523) -> dict:
    """Run the five primary hypothesis tests and apply the Holm-Bonferroni
    correction across the family (PROTOCOL_LOCK Section 6, ANALYSIS_PLAN
    Notebook 04).

    `system_b` is the designated strongest baseline; it must be set by the
    caller (Notebook 04), since "strongest" is a pre-registered designation,
    not something this module may infer from the data.

    An outcome is reported as confirmed only if it clears both bars: the
    statistical bar (Holm-adjusted p below its step threshold and the effect
    size at or beyond its effect-size bar, in the hypothesized direction) and
    the operational bar. An outcome clearing only the statistical bar is
    reported "statistically significant, operationally marginal."
    """
    if not system_b:
        raise ValueError("system_b (the designated strongest baseline) must "
                          "be provided; it is a pre-registered designation")

    results = {oc: analyze_outcome(table, oc, system_a, system_b,
                                   n_boot=n_boot, seed=seed)
               for oc in PRIMARY_OUTCOMES}

    # Holm-Bonferroni across the family of five, smallest raw p first.
    order = sorted(PRIMARY_OUTCOMES,
                   key=lambda oc: (results[oc].model_p
                                   if results[oc].model_p == results[oc].model_p
                                   else 1.0))
    running_max = 0.0
    for rank, oc in enumerate(order):
        r = results[oc]
        step = HOLM_STEPS[rank]
        raw_p = r.model_p if r.model_p == r.model_p else 1.0
        # Holm-adjusted p, enforced monotone non-decreasing down the sequence.
        adj = min(1.0, raw_p * (len(PRIMARY_OUTCOMES) - rank))
        running_max = max(running_max, adj)
        r.holm_rank = rank + 1
        r.holm_threshold = step
        r.p_holm_adjusted = running_max
        r.statistically_significant = raw_p < step
        # effect size at or beyond bar, in the hypothesized direction
        favorable = (r.effect_size > 0) if HIGHER_IS_BETTER[oc] \
            else (r.effect_size < 0)
        r.effect_bar_met = favorable and abs(r.effect_size) >= EFFECT_BAR[oc]
        r.operationally_significant = (r.statistically_significant
                                       and r.effect_bar_met
                                       and r.operational_met)
        if r.operationally_significant:
            r.verdict = "confirmed: statistically and operationally significant"
        elif r.statistically_significant and r.effect_bar_met:
            r.verdict = ("statistically significant, operationally marginal")
        elif r.statistically_significant:
            r.verdict = ("statistically significant, effect-size bar not met")
        else:
            r.verdict = "not significant after Holm correction"

    return {
        "system_a": system_a, "system_b": system_b,
        "holm_order": list(order),
        "n_boot": n_boot, "seed": seed,
        "outcomes": {oc: results[oc].to_dict() for oc in PRIMARY_OUTCOMES},
        "any_confirmed": any(results[oc].operationally_significant
                             for oc in PRIMARY_OUTCOMES),
        "n_confirmed": sum(results[oc].operationally_significant
                           for oc in PRIMARY_OUTCOMES),
    }
