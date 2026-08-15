#!/usr/bin/env python3
"""contrast-restricted reliability, per-judge deltas, aggregation verification, fabrication means, B2 triage, deficit attribution.
Run from the study root: python3 code/figure_scripts/compute_restricted_reliability.py .
Computes, from the deposited records with the deposit's own alpha implementation,
the values stated in the paper's review-revision round."""

import gzip, json, statistics
from collections import Counter, defaultdict

import sys
R = sys.argv[1] if len(sys.argv) > 1 else "."
STREAMS = {
    "gpt4o":  f"{R}/replication_package/retained_study_data/full_coverage_judge_gpt4o.jsonl.gz",
    "claude": f"{R}/replication_package/retained_study_data/full_coverage_judge_claude.jsonl.gz",
    "gemini": f"{R}/replication_package/retained_study_data/full_coverage_judge_gemini.jsonl.gz",
}


def alpha_interval(units):  # verbatim from deposit compute_reliability.py
    pooled = [v for u in units for v in u]
    n, S, S2 = len(pooled), sum(pooled), sum(v * v for v in pooled)
    De = 2.0 * (n * S2 - S * S) / (n * (n - 1))
    if not De:
        return 1.0
    Do_num = sum((len(u) * sum(v * v for v in u) - sum(u) ** 2) / (len(u) - 1) for u in units)
    Do = 2.0 * Do_num / sum(len(u) for u in units)
    return 1 - Do / De


mapping = json.load(open(f"{R}/replication_package/v1_main/grading/v2_full_coverage/anonymization_mapping_full.json"))
ens = {}
for line in open(f"{R}/replication_package/v1_main/grading/v2_full_coverage/ensemble_scores.jsonl"):
    e = json.loads(line); ens[e["anon_id"]] = e
judges = {}
for jid, path in STREAMS.items():
    d = {}
    with gzip.open(path, "rt") as f:
        for line in f:
            r = json.loads(line); d[r["anon_id"]] = r
    judges[jid] = d

CONT = ["minimum_coverage", "target_coverage", "constraint_coverage", "fabrication_count", "trace_completeness"]
DISC = ["mission_intent_match", "gap_classification"]

# ---- 1. aggregation rule verification (median / majority) ----
mism = Counter()
for aid, e in ens.items():
    vals = {o: [judges[j][aid].get(o) for j in STREAMS] for o in CONT + DISC}
    for o in CONT:
        v = [x for x in vals[o] if x is not None]
        med = statistics.median(v) if v else None
        if e.get(o) != med and not (e.get(o) is None and med is None):
            if not (isinstance(e.get(o), float) and isinstance(med, (int, float)) and abs(e[o] - med) < 1e-9):
                mism[o] += 1
    for o in DISC:
        v = [x for x in vals[o] if x is not None]
        if v:
            modal, _ = Counter(v).most_common(1)[0]
            if e.get(o) != modal:
                mism[o] += 1
print("AGGREGATION MISMATCHES (median/majority rule):", dict(mism) or "ZERO on all outcomes")

# ---- helpers ----
main_ids = {aid for aid, m in mapping.items() if "-MAIN-" in m["task_id"]}
def dom(task_id): return task_id.split("-")[2]
SYSTEMS = sorted({m["system_id"] for m in mapping.values()})

def task_means(score_of, system, outcome):
    per = defaultdict(list)
    for aid in main_ids:
        m = mapping[aid]
        if m["system_id"] != system: continue
        v = score_of(aid, outcome)
        if v is not None: per[m["task_id"]].append(v)
    return {t: sum(v)/len(v) for t, v in per.items()}

ens_score = lambda aid, o: ens[aid].get(o)
def judge_score(j): return lambda aid, o: judges[j][aid].get(o)

# ---- 2. headline reconciliation: ensemble + per-judge deltas vs B1..B6 ----
print("\nMIN-COVERAGE TASK-MEAN DELTAS (cond_b - baseline), 120 shared tasks:")
tm_ens = {s: task_means(ens_score, s, "minimum_coverage") for s in SYSTEMS}
hdr = ["contrast", "ensemble"] + list(STREAMS) + ["mean-of-judges"]
print("  " + " | ".join(f"{h:>14}" for h in hdr))
sensitivity = {}
for b in [f"baseline_{i}" for i in range(1, 7)]:
    tasks = sorted(set(tm_ens["cond_b"]) & set(tm_ens[b]))
    d_ens = sum(tm_ens["cond_b"][t] - tm_ens[b][t] for t in tasks) / len(tasks)
    row = [f"vs {b}", f"{d_ens:+.4f}"]
    jd = []
    for j in STREAMS:
        tmc = task_means(judge_score(j), "cond_b", "minimum_coverage")
        tmb = task_means(judge_score(j), b, "minimum_coverage")
        dj = sum(tmc[t] - tmb[t] for t in tasks) / len(tasks)
        jd.append(dj); row.append(f"{dj:+.4f}")
    row.append(f"{sum(jd)/3:+.4f}")
    sensitivity[b] = {"ensemble": d_ens, "per_judge": dict(zip(STREAMS, jd)),
                      "sign_consistent": len({d < 0 for d in jd}) == 1}
    print("  " + " | ".join(f"{c:>14}" for c in row))
    if b in ("baseline_1", "baseline_3"):
        fav_b = sum(1 for t in tasks if tm_ens["cond_b"][t] < tm_ens[b][t] - 1e-12)
        fav_c = sum(1 for t in tasks if tm_ens["cond_b"][t] > tm_ens[b][t] + 1e-12)
        print(f"      favor counts vs {b}: {fav_b} favor baseline, {fav_c} favor cond_b, {len(tasks)-fav_b-fav_c} tie")

# ---- 3. contrast-restricted reliability ----
def restricted_alpha(system_set, outcome):
    units = []
    for aid in main_ids:
        if mapping[aid]["system_id"] in system_set:
            vals = [judges[j][aid].get(outcome) for j in STREAMS]
            vals = [v for v in vals if v is not None]
            if len(vals) >= 2: units.append(vals)
    return alpha_interval(units), len(units)

a_all, n_all = restricted_alpha(set(SYSTEMS), "minimum_coverage")
print(f"\nRELIABILITY (interval alpha, deposit formula):")
print(f"  pooled all-system main+holdout... main-only alpha={a_all:.4f} (n={n_all})")
for pair in [("cond_b", "baseline_3"), ("cond_b", "baseline_1")]:
    a, n = restricted_alpha(set(pair), "minimum_coverage")
    print(f"  restricted {pair}: alpha={a:.4f} (n={n})")
for solo in ["cond_b", "baseline_3", "baseline_1"]:
    a, n = restricted_alpha({solo}, "minimum_coverage")
    print(f"  within-{solo}: alpha={a:.4f} (n={n})")

# ---- 4. fabrication column (task means, ensemble) ----
print("\nFABRICATION COUNT task means (main corpus, ensemble):")
for s in SYSTEMS:
    tm = task_means(ens_score, s, "fabrication_count")
    if tm: print(f"  {s:18s} {sum(tm.values())/len(tm):.3f}")

# ---- 5. B2 mission-intent triage ----
print("\nB2 (baseline_2) MISSION-INTENT TRIAGE (main corpus):")
b2 = [aid for aid in main_ids if mapping[aid]["system_id"] == "baseline_2"]
em = [ens[aid]["mission_intent_match"] for aid in b2 if ens[aid].get("mission_intent_match") is not None]
print(f"  ensemble mean: {sum(em)/len(em):.3f} (n={len(em)})")
for j in STREAMS:
    jm = [judges[j][aid].get("mission_intent_match") for aid in b2]
    jm = [v for v in jm if v is not None]
    print(f"  judge {j}: mean {sum(jm)/len(jm):.3f}")
zero3 = sum(1 for aid in b2 if all(judges[j][aid].get("mission_intent_match") == 0 for j in STREAMS))
one3 = sum(1 for aid in b2 if all(judges[j][aid].get("mission_intent_match") == 1 for j in STREAMS))
print(f"  unanimous-0 records: {zero3}/{len(b2)}; unanimous-1: {one3}/{len(b2)}; split: {len(b2)-zero3-one3}")
bydom = defaultdict(list)
for aid in b2: bydom[dom(mapping[aid]["task_id"])].append(ens[aid]["mission_intent_match"])
for d, v in sorted(bydom.items()): print(f"  domain {d}: mean {sum(v)/len(v):.3f} (n={len(v)})")
# compare same-pattern B1 (Claude) for the contrast the panel cited
b1 = [aid for aid in main_ids if mapping[aid]["system_id"] == "baseline_1"]
em1 = [ens[aid]["mission_intent_match"] for aid in b1 if ens[aid].get("mission_intent_match") is not None]
print(f"  (B1 same-pattern ensemble mean: {sum(em1)/len(em1):.3f})")

# ---- 6. deficit attribution: 112 B3-favoring tasks ----
print("\nDEFICIT ATTRIBUTION (cond_b vs baseline_3, min coverage):")
tasks = sorted(set(tm_ens["cond_b"]) & set(tm_ens["baseline_3"]))
fav3 = [t for t in tasks if tm_ens["cond_b"][t] < tm_ens["baseline_3"][t] - 1e-12]
per_dom = defaultdict(list)
for t in tasks: per_dom[dom(t)].append(tm_ens["cond_b"][t] - tm_ens["baseline_3"][t])
for d, v in sorted(per_dom.items()):
    nfav = sum(1 for t in fav3 if dom(t) == d)
    print(f"  domain {d}: mean delta {sum(v)/len(v):+.4f} over {len(v)} tasks; {nfav} favor B3")
worst = sorted(tasks, key=lambda t: tm_ens["cond_b"][t] - tm_ens["baseline_3"][t])[:5]
print("  5 worst tasks:", [(t, round(tm_ens['cond_b'][t]-tm_ens['baseline_3'][t],3)) for t in worst])

json.dump({"sensitivity": sensitivity}, open("sensitivity.json", "w"), indent=1)
print("\nDONE")
