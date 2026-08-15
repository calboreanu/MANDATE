#!/usr/bin/env python3
"""Pairwise system contrasts with bootstrap CIs for the v2 comparative table.

Pre-registration anchor: v2 Protocol Amendment, "Statistical power":
  "Pairwise system contrasts use bootstrap confidence intervals with
   10,000 resamples; effect sizes are reported as Cohen's d on
   per-record outcome scores."
Lineage: pre_registration/ANALYSIS_PLAN.md Notebook 3 (paired Wilcoxon
signed-rank at task level; Holm-Bonferroni family-wise correction).

Design decisions (documented, not silently chosen):
- Contrast family: Cond-B (the apples-to-apples MANDATE condition) vs
  each baseline B1-B6, on the four coverage/structure outcomes
  (minimum_coverage, target_coverage, constraint_coverage,
  trace_completeness). 24 contrasts total.
- Main corpus only (TASK-MAIN-*): B2-B6 have no graded hold-out
  records, so cross-system contrasts are restricted to the shared
  120-task corpus. Table point estimates in the paper include hold-out
  records for MP/Cond-A/Cond-B/B1 (n=1,500); main-only means are also
  reported here for transparency.
- Method 1 (pre-registered primary): per-record percentile bootstrap,
  independent resampling within each system, B=10,000, 95% CI on the
  difference in means; Cohen's d with pooled SD.
- Method 2 (sensitivity): task-clustered bootstrap; resample the 120
  task IDs with replacement, recompute record-weighted means. Records
  within a task share seeds and content, so this respects clustering.
- Method 3: two-sided Wilcoxon signed-rank on the 120 paired task
  means, Holm-Bonferroni corrected across the 24 contrasts.
- Cond-A vs B3 on minimum_coverage is reported separately as a
  descriptive characterization (structured-input condition; not an
  apples-to-apples contrast).
- Seed: 20260710.

Output: analysis/bootstrap_contrasts_results.json + markdown table.
"""
import argparse
import json
import os
import tempfile
import numpy as np
from scipy.stats import wilcoxon

HERE = os.path.dirname(os.path.abspath(__file__))
GRADING = os.path.normpath(os.path.join(
    HERE, "..", "..", "replication_package", "v1_main", "grading", "v2_full_coverage"))
B = 10_000
SEED = 20260710
OUTCOMES = ["minimum_coverage", "target_coverage",
            "constraint_coverage", "trace_completeness"]
BASELINES = ["baseline_1", "baseline_2", "baseline_3",
             "baseline_4", "baseline_5", "baseline_6"]

def load():
    mapping = json.load(open(os.path.join(GRADING, "anonymization_mapping_full.json")))
    recs = []
    with open(os.path.join(GRADING, "ensemble_scores.jsonl")) as f:
        for line in f:
            r = json.loads(line)
            meta = mapping[r["anon_id"]]
            r["system_id"] = meta["system_id"]
            r["task_id"] = meta["task_id"]
            recs.append(r)
    return recs

def arrays(recs, system, outcome, main_only=True):
    vals, tasks = [], []
    for r in recs:
        if r["system_id"] != system:
            continue
        if main_only and not r["task_id"].startswith("TASK-MAIN-"):
            continue
        v = r.get(outcome)
        if v is None:
            continue
        vals.append(float(v))
        tasks.append(r["task_id"])
    return np.array(vals), np.array(tasks)

def per_record_bootstrap(rng, v1, v2):
    n1, n2 = len(v1), len(v2)
    m1 = v1[rng.integers(0, n1, size=(B, n1))].mean(axis=1)
    m2 = v2[rng.integers(0, n2, size=(B, n2))].mean(axis=1)
    d = m1 - m2
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))

def clustered_bootstrap(rng, v1, t1, v2, t2):
    tasks = np.array(sorted(set(t1) & set(t2)))
    sums1 = {t: (v1[t1 == t].sum(), (t1 == t).sum()) for t in tasks}
    sums2 = {t: (v2[t2 == t].sum(), (t2 == t).sum()) for t in tasks}
    s1 = np.array([sums1[t][0] for t in tasks]); c1 = np.array([sums1[t][1] for t in tasks])
    s2 = np.array([sums2[t][0] for t in tasks]); c2 = np.array([sums2[t][1] for t in tasks])
    k = len(tasks)
    idx = rng.integers(0, k, size=(B, k))
    d = (s1[idx].sum(1) / c1[idx].sum(1)) - (s2[idx].sum(1) / c2[idx].sum(1))
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))

def task_means(v, t):
    out = {}
    for task in set(t):
        out[task] = v[t == task].mean()
    return out

def cohens_d(v1, v2):
    n1, n2 = len(v1), len(v2)
    sp = np.sqrt(((n1 - 1) * v1.var(ddof=1) + (n2 - 1) * v2.var(ddof=1)) / (n1 + n2 - 2))
    if sp > 0:
        return float((v1.mean() - v2.mean()) / sp)
    # zero pooled variance: identical constants in both systems -> no effect;
    # differing constants -> effect size undefined (report None)
    return 0.0 if v1.mean() == v2.mean() else None

def holm(pvals):
    order = np.argsort(pvals)
    m = len(pvals)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        val = (m - rank) * pvals[i]
        running = max(running, val)
        adj[i] = min(1.0, running)
    return adj

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--outdir",
        help="output directory (default: a new scratch directory under the system temp root)",
    )
    args = parser.parse_args()
    outdir = os.path.abspath(args.outdir) if args.outdir else tempfile.mkdtemp(
        prefix="mandate-bootstrap-"
    )
    os.makedirs(outdir, exist_ok=True)
    rng = np.random.default_rng(SEED)
    recs = load()
    results, pvals, keys = [], [], []
    for outcome in OUTCOMES:
        vB, tB = arrays(recs, "cond_b", outcome)
        for base in BASELINES:
            vX, tX = arrays(recs, base, outcome)
            lo_r, hi_r = per_record_bootstrap(rng, vB, vX)
            lo_c, hi_c = clustered_bootstrap(rng, vB, tB, vX, tX)
            tmB, tmX = task_means(vB, tB), task_means(vX, tX)
            shared = sorted(set(tmB) & set(tmX))
            diffs = np.array([tmB[t] - tmX[t] for t in shared])
            if np.allclose(diffs, 0):
                p = 1.0
            else:
                p = float(wilcoxon(diffs, zero_method="wilcox",
                                   alternative="two-sided").pvalue)
            row = {
                "contrast": f"cond_b vs {base}",
                "outcome": outcome,
                "mean_cond_b_main": float(vB.mean()),
                "mean_baseline_main": float(vX.mean()),
                "delta": float(vB.mean() - vX.mean()),
                "ci95_per_record": [lo_r, hi_r],
                "ci95_task_clustered": [lo_c, hi_c],
                "cohens_d_per_record": cohens_d(vB, vX),
                "wilcoxon_p_task_level": p,
                "n_tasks_paired": len(shared),
                "n_records": [int(len(vB)), int(len(vX))],
            }
            results.append(row)
            pvals.append(p)
            keys.append((outcome, base))
    adj = holm(np.array(pvals))
    for row, a in zip(results, adj):
        row["wilcoxon_p_holm_adjusted"] = float(a)
        row["significant_at_0.05_holm"] = bool(a < 0.05)

    # descriptive: Cond-A vs B3 minimum coverage (structured-input characterization)
    vA, tA = arrays(recs, "cond_a", "minimum_coverage")
    v3, t3 = arrays(recs, "baseline_3", "minimum_coverage")
    lo_r, hi_r = per_record_bootstrap(rng, vA, v3)
    lo_c, hi_c = clustered_bootstrap(rng, vA, tA, v3, t3)
    descriptive = {
        "contrast": "cond_a vs baseline_3 (descriptive; structured input)",
        "outcome": "minimum_coverage",
        "delta": float(vA.mean() - v3.mean()),
        "ci95_per_record": [lo_r, hi_r],
        "ci95_task_clustered": [lo_c, hi_c],
        "cohens_d_per_record": cohens_d(vA, v3),
    }

    out = {
        "seed": SEED, "B": B,
        "scope": "main corpus only (TASK-MAIN-*), shared 120 tasks",
        "pre_registration_anchor": "v2 Protocol Amendment 'Statistical power'; ANALYSIS_PLAN.md Notebook 3",
        "primary_contrasts": results,
        "descriptive_cond_a_vs_b3": descriptive,
    }
    with open(os.path.join(outdir, "bootstrap_contrasts_results.json"), "w") as f:
        json.dump(out, f, indent=1)

    lines = ["| Outcome | Contrast | Δ (B−baseline) | 95% CI (record) | 95% CI (task-clustered) | d | p (Holm) |",
             "|---|---|---|---|---|---|---|"]
    for r in results:
        cd = r["cohens_d_per_record"]
        cd_s = "{:+.2f}".format(cd) if cd is not None else "n/a"
        lines.append("| {o} | Cond-B vs {b} | {d:+.3f} | [{r0:+.3f}, {r1:+.3f}] | [{c0:+.3f}, {c1:+.3f}] | {cd} | {p:.2g} |".format(
            o=r["outcome"], b=r["contrast"].split()[-1], d=r["delta"],
            r0=r["ci95_per_record"][0], r1=r["ci95_per_record"][1],
            c0=r["ci95_task_clustered"][0], c1=r["ci95_task_clustered"][1],
            cd=cd_s, p=r["wilcoxon_p_holm_adjusted"]))
    with open(os.path.join(outdir, "bootstrap_contrasts_table.md"), "w") as f:
        f.write("# Bootstrap contrasts (v2 comparative table)\n\n" +
                "\n".join(lines) + "\n\nDescriptive Cond-A vs B3 (min cov): Δ {:+.3f}, record CI [{:+.3f}, {:+.3f}], clustered CI [{:+.3f}, {:+.3f}], d {:+.2f}\n".format(
                    descriptive["delta"], *descriptive["ci95_per_record"],
                    *descriptive["ci95_task_clustered"], descriptive["cohens_d_per_record"]))
    print("written:", outdir)

if __name__ == "__main__":
    main()
