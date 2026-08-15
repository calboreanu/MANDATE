#!/usr/bin/env python3
"""12,000-unit alpha reproduction, fabrication scopes, COA counts, representation/fallback split.
Run from the study root: python3 code/figure_scripts/compute_kround_checks.py .
Computes, from the deposited records with the deposit's own alpha implementation,
the values stated in the paper's review-revision round."""

import gzip, json, glob, os, statistics
from collections import Counter, defaultdict

import sys
R = sys.argv[1] if len(sys.argv) > 1 else "."
STREAMS = {
    "gpt4o":  f"{R}/replication_package/retained_study_data/full_coverage_judge_gpt4o.jsonl.gz",
    "claude": f"{R}/replication_package/retained_study_data/full_coverage_judge_claude.jsonl.gz",
    "gemini": f"{R}/replication_package/retained_study_data/full_coverage_judge_gemini.jsonl.gz",
}

def alpha_interval(units):
    pooled = [v for u in units for v in u]
    n, S, S2 = len(pooled), sum(pooled), sum(v * v for v in pooled)
    De = 2.0 * (n * S2 - S * S) / (n * (n - 1))
    if not De: return 1.0
    Do_num = sum((len(u) * sum(v * v for v in u) - sum(u) ** 2) / (len(u) - 1) for u in units)
    Do = 2.0 * Do_num / sum(len(u) for u in units)
    return 1 - Do / De

mapping = json.load(open(f"{R}/replication_package/v1_main/grading/v2_full_coverage/anonymization_mapping_full.json"))
judges = {}
for jid, path in STREAMS.items():
    d = {}
    with gzip.open(path, "rt") as f:
        for line in f: r = json.loads(line); d[r["anon_id"]] = r
    judges[jid] = d
ens = {}
for line in open(f"{R}/replication_package/v1_main/grading/v2_full_coverage/ensemble_scores.jsonl"):
    e = json.loads(line); ens[e["anon_id"]] = e

# ---- 12,000-unit alpha reproduction (paper's 0.855) ----
units = []
for aid in mapping:
    vals = [judges[j][aid].get("minimum_coverage") for j in STREAMS]
    vals = [v for v in vals if v is not None]
    if len(vals) >= 2: units.append(vals)
print(f"12,000-unit min-coverage alpha: {alpha_interval(units):.4f} (n={len(units)})  [paper: 0.855]")

# ---- fabrication scopes ----
for scope, pred in [("main", lambda t: "-MAIN-" in t), ("main+holdout", lambda t: True)]:
    for s in ("cond_b", "baseline_3"):
        v = [ens[a]["fabrication_count"] for a, m in mapping.items()
             if m["system_id"] == s and pred(m["task_id"]) and ens[a].get("fabrication_count") is not None]
        print(f"fabrication {s} {scope}: record-mean {sum(v)/len(v):.3f} (n={len(v)})")

# ---- COA counts ----
def coa_count(rec):
    out = rec.get("output") or {}
    if not isinstance(out, dict): return 0
    for k in ("coas", "courses_of_action"):
        if isinstance(out.get(k), list): return len(out[k])
    art = out.get("artifact") or out.get("mandate") or {}
    if isinstance(art, dict):
        for k in ("coas", "courses_of_action"):
            if isinstance(art.get(k), list): return len(art[k])
    return 0

tot = {}
for sysname in ("cond_a", "cond_b"):
    for tier in ("main", "holdout"):
        p = f"{R}/replication_package/v1_main/system_outputs/{sysname}_{tier}.jsonl"
        n_rec = n_coa = 0
        dist = Counter()
        first_keys = None
        for line in open(p):
            rec = json.loads(line); n_rec += 1
            c = coa_count(rec); n_coa += c; dist[c] += 1
            if first_keys is None:
                o = rec.get("output")
                first_keys = list(o.keys())[:12] if isinstance(o, dict) else str(type(o))
        tot[(sysname, tier)] = (n_rec, n_coa, dict(dist))
        print(f"COA {sysname} {tier}: records {n_rec}, COAs {n_coa}, dist {dict(sorted(dist.items()))}")
        if n_coa == 0: print("   output keys:", first_keys)
canon_all = sum(v[1] for v in tot.values())
canon_main = tot[("cond_a","main")][1] + tot[("cond_b","main")][1]
print(f"canonical COAs main+holdout: {canon_all}; main-only: {canon_main}  [paper says 4,402]")

# ---- O4 / schema-check artifacts in deposit ----
print("\nO4 schema-check artifact search:")
hits = []
for pat in ("*schema*", "*o4*", "*O4*"):
    hits += glob.glob(f"{R}/replication_package/**/{pat}", recursive=True)
for h in sorted(set(hits))[:15]:
    print("  ", h.replace(R + "/", ""), os.path.getsize(h) if os.path.isfile(h) else "(dir)")

# ---- B2 raw output peek: 3 lowest-mission records ----
print("\nB2 raw peek (3 records where all judges scored mission 0):")
b2zero = [a for a, m in mapping.items() if m["system_id"] == "baseline_2" and "-MAIN-" in m["task_id"]
          and all(judges[j][a].get("mission_intent_match") == 0 for j in STREAMS)][:3]
b2recs = {}
for line in open(f"{R}/replication_package/v1_main/system_outputs/baseline_2_main.jsonl"):
    rec = json.loads(line); b2recs[rec["run_id"]] = rec
for a in b2zero:
    rid = mapping[a]["run_id"]; rec = b2recs.get(rid)
    if rec is None: print("  ", rid, "NOT FOUND"); continue
    o = rec.get("output")
    s = json.dumps(o)[:220] if o is not None else "None"
    print(f"  {rid}: ok={rec.get('ok')} output_type={rec.get('output_type')} len={len(json.dumps(o)) if o else 0}")
    print(f"    head: {s}")

# ---- representation + fallback split on B3-favoring tasks ----
print("\nCond-B representation on B3-favoring vs other tasks:")
tm = defaultdict(lambda: defaultdict(list))
for a, m in mapping.items():
    if "-MAIN-" in m["task_id"] and m["system_id"] in ("cond_b", "baseline_3"):
        v = ens[a].get("minimum_coverage")
        if v is not None: tm[m["system_id"]][m["task_id"]].append(v)
tmm = {s: {t: sum(v)/len(v) for t, v in d.items()} for s, d in tm.items()}
fav3 = {t for t in tmm["cond_b"] if tmm["cond_b"][t] < tmm["baseline_3"][t] - 1e-12}
cb = {}
for line in open(f"{R}/replication_package/v1_main/system_outputs/cond_b_main.jsonl"):
    rec = json.loads(line); cb[rec["run_id"]] = rec
otypes_fav, otypes_rest, fb_fav, fb_rest = Counter(), Counter(), 0, 0
n_fav = n_rest = 0
for rid, rec in cb.items():
    t = rec["task_id"]
    tgt = (t in fav3)
    (otypes_fav if tgt else otypes_rest)[rec.get("output_type")] += 1
    if rec.get("any_llm_fallback"):
        if tgt: fb_fav += 1
        else: fb_rest += 1
    if tgt: n_fav += 1
    else: n_rest += 1
print(f"  B3-favoring tasks ({len(fav3)}): output types {dict(otypes_fav)}; fallback {fb_fav}/{n_fav}")
print(f"  other tasks: output types {dict(otypes_rest)}; fallback {fb_rest}/{n_rest}")
print("\nDONE")
