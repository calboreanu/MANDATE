"""
Descriptive analyses for Notebooks 01 and 02 (Workstream B6).

Notebook 01 (Corpus and Signoff Summary) and Notebook 02 (System Output
Summary) are descriptive: they characterize the frozen corpus, the SME
sign-off process, inter-rater reliability, and the raw behaviour of the
systems, before any hypothesis is tested. This module holds the computations
both notebooks drive, so the notebooks stay thin and the statistics are
unit-tested.

Nothing here generates study data or fits a hypothesis test. The functions
take already-collected records (corpus task metadata, SME sign-off logs,
rater judgements, harness RunRecords) and summarize them.

Inter-rater reliability is reported with the McHugh (2012) interpretation
bands the ANALYSIS_PLAN specifies, and `kappa_with_ci` carries a bootstrap
confidence interval so the notebook can show the uncertainty, not just a
point estimate.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass

import numpy as np

from ..grading.ensemble import cohen_kappa, krippendorff_alpha

# McHugh (2012) agreement bands, as ANALYSIS_PLAN Notebook 01 specifies.
MCHUGH_BANDS = (
    (0.80, "strong agreement"),
    (0.60, "moderate (acceptable with caveat)"),
    (0.40, "weak (pause, recalibrate)"),
    (float("-inf"), "poor (halt)"),
)


def mchugh_band(kappa) -> str:
    """The McHugh interpretation band for a kappa value."""
    if kappa is None or kappa != kappa:
        return "undefined"
    for floor, label in MCHUGH_BANDS:
        if kappa >= floor:
            return label
    return "poor (halt)"


def _pctile_summary(values) -> dict:
    """mean / median / p95 / min / max for a numeric list; empty-safe."""
    v = [float(x) for x in values if x is not None]
    if not v:
        return {"n": 0, "mean": None, "median": None, "p95": None,
                "min": None, "max": None}
    arr = np.asarray(v, dtype=float)
    return {"n": len(v), "mean": float(arr.mean()),
            "median": float(np.median(arr)),
            "p95": float(np.percentile(arr, 95)),
            "min": float(arr.min()), "max": float(arr.max())}


def _as_dict(record) -> dict:
    """A RunRecord (or anything with to_dict) or a plain dict, as a dict."""
    if hasattr(record, "to_dict"):
        return record.to_dict()
    return dict(record)


# --- Notebook 01: corpus and sign-off ---------------------------------------

def corpus_summary(tasks) -> dict:
    """Composition of the frozen corpus. `tasks` is a list of dicts with at
    least `domain`, `category`, and optionally `task_type` and `word_count`.
    """
    by_domain, by_category, by_type = {}, {}, {}
    for t in tasks:
        by_domain[t.get("domain", "")] = by_domain.get(t.get("domain", ""),
                                                        0) + 1
        by_category[t.get("category", "")] = by_category.get(
            t.get("category", ""), 0) + 1
        tt = t.get("task_type", "")
        by_type[tt] = by_type.get(tt, 0) + 1
    return {
        "n_tasks": len(tasks),
        "by_domain": dict(sorted(by_domain.items())),
        "by_category": dict(sorted(by_category.items())),
        "by_task_type": dict(sorted(by_type.items())),
        "word_count": _pctile_summary([t.get("word_count")
                                       for t in tasks]),
    }


def kappa_with_ci(rater_a, rater_b, n_boot: int = 10000,
                  seed: int = 20260523, conf: float = 0.95) -> dict:
    """Cohen's kappa between two raters with a percentile bootstrap CI
    (ANALYSIS_PLAN Notebook 01). Items where either rater is None are dropped
    before scoring. Returns point estimate, CI, McHugh band, and n."""
    pairs = [(x, y) for x, y in zip(rater_a, rater_b)
             if x is not None and y is not None]
    point = cohen_kappa([p[0] for p in pairs], [p[1] for p in pairs])
    out = {"kappa": point, "ci_low": None, "ci_high": None,
           "band": mchugh_band(point), "n_items": len(pairs)}
    if point is None or len(pairs) < 3:
        return out
    rng = np.random.default_rng(seed)
    idx = np.arange(len(pairs))
    estimates = []
    for _ in range(n_boot):
        s = rng.choice(idx, size=len(idx), replace=True)
        k = cohen_kappa([pairs[i][0] for i in s], [pairs[i][1] for i in s])
        if k is not None:
            estimates.append(k)
    if estimates:
        out["ci_low"] = float(np.percentile(estimates,
                                            100 * (1 - conf) / 2))
        out["ci_high"] = float(np.percentile(estimates,
                                             100 * (1 - (1 - conf) / 2)))
    return out


def reliability_summary(ratings_by_rater: dict, level: str = "nominal"
                        ) -> dict:
    """Inter-rater reliability across all raters: pairwise Cohen's kappa and
    a single Krippendorff's alpha. `ratings_by_rater` maps rater id to a list
    of judgements aligned across items."""
    raters = list(ratings_by_rater)
    pairwise = {}
    for i in range(len(raters)):
        for j in range(i + 1, len(raters)):
            k = cohen_kappa(ratings_by_rater[raters[i]],
                            ratings_by_rater[raters[j]])
            pairwise["%s|%s" % (raters[i], raters[j])] = {
                "kappa": k, "band": mchugh_band(k)}
    alpha = krippendorff_alpha(ratings_by_rater, level=level)
    kappas = [d["kappa"] for d in pairwise.values() if d["kappa"] is not None]
    return {"pairwise_kappa": pairwise, "krippendorff_alpha": alpha,
            "min_pairwise_kappa": min(kappas) if kappas else None,
            "n_raters": len(raters)}


def signoff_summary(signoffs) -> dict:
    """SME sign-off completion. `signoffs` is a list of dicts with `reviewer`,
    `task_id`, `minutes`, and optional `flagged` (bool). Reports per-reviewer
    time statistics and the count of flagged tasks."""
    by_reviewer = {}
    flagged = 0
    for s in signoffs:
        by_reviewer.setdefault(s.get("reviewer", ""), []).append(
            s.get("minutes"))
        if s.get("flagged"):
            flagged += 1
    return {
        "n_signoffs": len(signoffs),
        "by_reviewer": {r: _pctile_summary(mins)
                        for r, mins in sorted(by_reviewer.items())},
        "n_flagged": flagged,
    }


def realism_summary(ratings, threshold: float = 2.5) -> dict:
    """Realism-audit ratings. `ratings` is a list of dicts with `task_id` and
    `rating`. Reports the mean, the rating distribution, and the tasks that
    fall below `threshold` and need disposition."""
    vals = [r.get("rating") for r in ratings if r.get("rating") is not None]
    dist = {}
    for v in vals:
        dist[v] = dist.get(v, 0) + 1
    below = [r.get("task_id") for r in ratings
             if r.get("rating") is not None and r.get("rating") < threshold]
    return {"n_rated": len(vals),
            "mean_rating": float(np.mean(vals)) if vals else None,
            "distribution": dict(sorted(dist.items())),
            "threshold": threshold,
            "below_threshold_tasks": below}


# --- Notebook 02: system output summary -------------------------------------

def completion_rates(records) -> dict:
    """Per-system execution completion: the fraction of runs that finished ok
    and the count that errored. `records` is a list of RunRecords or dicts."""
    by_system = {}
    for rec in records:
        d = _as_dict(rec)
        sid = d.get("system_id", "")
        slot = by_system.setdefault(sid, {"n": 0, "ok": 0, "errored": 0})
        slot["n"] += 1
        if d.get("ok"):
            slot["ok"] += 1
        else:
            slot["errored"] += 1
    for slot in by_system.values():
        slot["completion_rate"] = (slot["ok"] / slot["n"]
                                   if slot["n"] else None)
    return dict(sorted(by_system.items()))


def mandate_fallback_summary(records) -> dict:
    """MANDATE-primary silent-fallback accounting (Notebook 02). Across the
    MANDATE-primary runs: the run-level fallback rate, and the per-role count
    of fallbacks. A nonzero rate means some runs are not clean observations
    of MANDATE-primary and must be handled in the analysis."""
    n_runs = 0
    n_fellback = 0
    by_role = {}
    for rec in records:
        d = _as_dict(rec)
        if d.get("system_id") != "mandate_primary":
            continue
        n_runs += 1
        if d.get("any_llm_fallback"):
            n_fellback += 1
        for rt in d.get("role_timings", []) or []:
            if rt.get("llm_fallback"):
                role = rt.get("role_name", "")
                by_role[role] = by_role.get(role, 0) + 1
    return {"n_mandate_runs": n_runs, "n_runs_with_fallback": n_fellback,
            "fallback_rate": (n_fellback / n_runs) if n_runs else None,
            "fallback_by_role": dict(sorted(by_role.items()))}


def role_timing_summary(records, system_id: str = "mandate_primary") -> dict:
    """Per-role timing for one system: median / p95 / max duration in ms
    (Notebook 02). Pulls `role_timings` from each RunRecord."""
    by_role = {}
    for rec in records:
        d = _as_dict(rec)
        if d.get("system_id") != system_id:
            continue
        for rt in d.get("role_timings", []) or []:
            by_role.setdefault(rt.get("role_name", ""), []).append(
                rt.get("duration_ms", 0.0))
    return {role: _pctile_summary(durs)
            for role, durs in sorted(by_role.items())}


def cost_summary(records) -> dict:
    """Per-system cost and compute aggregation (PROTOCOL_LOCK Section 16,
    Notebook 02 Table 6). Sums API cost in USD, input and output tokens,
    wall-clock time, and local compute time across each system's runs.

    A system whose runs do not carry an API cost (MANDATE-primary, the
    alternative backends, the ablations) reports its `local_compute_ms`
    and leaves `api_cost_usd_total` at None; a system whose runs carry an
    API cost (the baselines) reports both. The study-level total is the
    sum of available figures, with the limitation noted plainly.
    """
    by_system = {}
    for rec in records:
        d = _as_dict(rec)
        sid = d.get("system_id", "")
        slot = by_system.setdefault(sid, {
            "n_runs": 0, "n_ok": 0, "api_cost_usd_total": 0.0,
            "any_api_cost": False, "input_tokens_total": 0,
            "output_tokens_total": 0, "wall_clock_ms_total": 0.0,
            "local_compute_ms_total": 0.0, "n_with_local_compute": 0})
        slot["n_runs"] += 1
        if d.get("ok"):
            slot["n_ok"] += 1
        cost = d.get("api_cost_usd")
        if cost is not None:
            slot["api_cost_usd_total"] += float(cost)
            slot["any_api_cost"] = True
        mv = d.get("model_versions") or {}
        slot["input_tokens_total"] += int(mv.get("total_input_tokens", 0)
                                           or 0)
        slot["output_tokens_total"] += int(mv.get("total_output_tokens", 0)
                                            or 0)
        slot["wall_clock_ms_total"] += float(d.get("wall_clock_ms") or 0.0)
        lcm = d.get("local_compute_ms")
        if lcm is not None:
            slot["local_compute_ms_total"] += float(lcm)
            slot["n_with_local_compute"] += 1

    # finalize per-system: collapse the API-cost reporting, add per-run mean
    for sid, slot in by_system.items():
        if slot["any_api_cost"]:
            slot["api_cost_usd_per_run_mean"] = (
                slot["api_cost_usd_total"] / slot["n_runs"])
        else:
            slot["api_cost_usd_total"] = None
            slot["api_cost_usd_per_run_mean"] = None
        slot.pop("any_api_cost", None)

    total_api = sum((s["api_cost_usd_total"] or 0.0)
                    for s in by_system.values())
    total_runs = sum(s["n_runs"] for s in by_system.values())
    total_wc = sum(s["wall_clock_ms_total"] for s in by_system.values())
    total_lc = sum(s["local_compute_ms_total"] for s in by_system.values())
    return {"by_system": dict(sorted(by_system.items())),
            "study_total": {"n_runs": total_runs,
                             "api_cost_usd": total_api,
                             "wall_clock_ms": total_wc,
                             "local_compute_ms": total_lc}}


def run_stability(runs_by_unit: dict, equivalence_fn) -> dict:
    """Stochastic stability across runs (Notebook 02). `runs_by_unit` maps a
    unit id to its list of run outputs; `equivalence_fn(x, y)` decides whether
    two runs are equivalent. Reports the per-unit agreement (all runs mutually
    equivalent) and the system-level stability rate.
    """
    per_unit = {}
    stable = 0
    unstable_units = []
    for unit, runs in runs_by_unit.items():
        if len(runs) < 2:
            per_unit[unit] = True
            stable += 1
            continue
        ok = all(equivalence_fn(runs[i], runs[i + 1])
                 for i in range(len(runs) - 1))
        per_unit[unit] = ok
        if ok:
            stable += 1
        else:
            unstable_units.append(unit)
    n = len(runs_by_unit)
    return {"n_units": n, "n_stable": stable,
            "stability_rate": (stable / n) if n else None,
            "unstable_units": sorted(unstable_units),
            "per_unit_stable": per_unit}
