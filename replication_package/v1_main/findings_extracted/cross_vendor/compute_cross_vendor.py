#!/usr/bin/env python3
"""
Cross-vendor structural-invariance analysis for MANDATE 2026Q2 Cond-B pilot (HANDOFF_22).
Read-only over 07_system_outputs/cond_b_xvendor/{qwen,llama,mistral,phi}/*.json.

NOTE ON FIELD PATHS: The coworker briefing described several paths that do NOT match
the on-disk RunRecords (verified 0/300 for every vendor). Corrected paths used here:
  trace entries  -> output.artifact.trace.entries        (briefing said output.artifact.trace was a list)
  COA list       -> output.artifact.courses_of_action    (briefing said output.artifact.coas)
  gap reports    -> output.gap_reports                    (briefing said output.artifact.gap_reports)
  anchor hash    -> output.artifact.anchor.anchor_hash    (briefing said output.artifact.anchor_hash)
These corrected paths reproduce the apparatus's own HANDOFF_22 status metrics for trace
completeness (1.0) and mean gap count (exact match), confirming they are correct.

COA COUNT — RESOLVED. The apparatus status JSON reports mean_coa_count=0.0, which is a BUG,
not the truth. Root cause: scripts/run_handoff22_xvendor.py::_coa_count() scans the keys
("candidate_coas", "candidate_courses_of_action", "coas") — none of which exist in the
records — and returns 0 when none match. The real COA field is `courses_of_action`, which
is present and fully populated on 300/300 records for every vendor (each COA entry has
coa_id, approach, procedures, task_dag, risk_assessment, off_nominal_triggers). The
authoritative mean COA count is therefore computed here from `courses_of_action`.
"""
import json, glob, os, statistics

EVAL = "/sessions/wizardly-dazzling-einstein/mnt/Desktop - lattice-ws01/MANDATE Evaluation/mandate_eval_2026Q2"
BASE = os.path.join(EVAL, "07_system_outputs", "cond_b_xvendor")
OUT  = "/sessions/wizardly-dazzling-einstein/mnt/Desktop/Mandate Data/standalone data results/cross_vendor"
VENDORS = ["qwen", "llama", "mistral"]   # phi excluded: still running (partial)

def load_record(path):
    d = json.load(open(path))
    art = d.get("output", {}).get("artifact", {})
    out = d.get("output", {})
    trace = art.get("trace", {}) or {}
    return {
        "task_id": d.get("task_id"),
        "run_number": d.get("run_number"),
        "ok": bool(d.get("ok")),
        "wall_clock_ms": d.get("wall_clock_ms"),
        "trace_entries": len(trace.get("entries", [])) if isinstance(trace, dict) else 0,
        "gap_count": len(out.get("gap_reports", []) or []),
        "coa_count": len(art.get("courses_of_action", []) or []),   # authoritative COA field
        "anchor_hash": art.get("anchor", {}).get("anchor_hash"),
        "llm_model": d.get("model_versions", {}).get("llm_model"),
    }

# ---- per-vendor aggregates ----
per_vendor = {}
records_by_vendor = {}
for v in VENDORS:
    files = sorted(glob.glob(os.path.join(BASE, v, "*.json")))
    recs = [load_record(f) for f in files]
    records_by_vendor[v] = recs
    ok = [r for r in recs if r["ok"]]
    n_total = len(recs); n_ok = len(ok)
    anchor_hashes = [r["anchor_hash"] for r in ok if r["anchor_hash"]]
    coa_dist = {}
    for r in ok:
        coa_dist[r["coa_count"]] = coa_dist.get(r["coa_count"], 0) + 1
    per_vendor[v] = {
        "vendor": v,
        "model": recs[0]["llm_model"] if recs else None,
        "n_total": n_total,
        "n_ok": n_ok,
        "ok_rate": round(n_ok / n_total, 6) if n_total else None,
        "mean_wall_clock_s": round(statistics.mean(r["wall_clock_ms"] for r in recs) / 1000.0, 3) if recs else None,
        "p2_trace_completeness_rate": round(sum(1 for r in recs if r["trace_entries"] >= 6) / n_total, 6) if n_total else None,
        "mean_coa_count": round(statistics.mean(r["coa_count"] for r in ok), 6) if ok else None,
        "coa_count_distribution": {str(k): v for k, v in sorted(coa_dist.items())},
        "coa_source": "output.artifact.courses_of_action (apparatus mean_coa_count=0.0 is a known bug; see docstring/findings.md)",
        "mean_gap_report_count": round(statistics.mean(r["gap_count"] for r in ok), 6) if ok else None,
        "anchor_hash_uniqueness": round(len(set(anchor_hashes)) / n_ok, 6) if n_ok else None,
        "anchor_hash_n_unique": len(set(anchor_hashes)),
    }

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "per_vendor_aggregates.json"), "w") as f:
    json.dump({"vendors": per_vendor,
               "phi_note": "phi3:14b still running at analysis time (partial); excluded. Lead analyst appends when complete.",
               "field_path_corrections_applied": True,
               "coa_metric_bug_resolved": True}, f, indent=2)

# ---- per-task cross-vendor pairings ----
idx = {v: {(r["task_id"], r["run_number"]): r for r in records_by_vendor[v]} for v in VENDORS}
all_keys = sorted(set().union(*[set(idx[v].keys()) for v in VENDORS]))

jsonl_rows = []
for (task_id, run_idx) in all_keys:
    present = [v for v in VENDORS if (task_id, run_idx) in idx[v]]
    traces = {v: idx[v][(task_id, run_idx)]["trace_entries"] for v in present}
    gaps   = {v: idx[v][(task_id, run_idx)]["gap_count"] for v in present}
    coas   = {v: idx[v][(task_id, run_idx)]["coa_count"] for v in present}
    hashes = {v: idx[v][(task_id, run_idx)]["anchor_hash"] for v in present}
    gap_vals = list(gaps.values()); coa_vals = list(coas.values())
    row = {
        "task_id": task_id,
        "run_idx": run_idx,
        "vendors_present": present,
        "n_vendors": len(present),
        "cross_vendor_trace_completeness": all(t >= 6 for t in traces.values()),
        "per_vendor_trace_entries": traces,
        "cross_vendor_coa_count_variance": round(statistics.pvariance(coa_vals), 6) if len(coa_vals) > 1 else 0.0,
        "per_vendor_coa_count": coas,
        "cross_vendor_gap_count_variance": round(statistics.pvariance(gap_vals), 6) if len(gap_vals) > 1 else 0.0,
        "per_vendor_gap_count": gaps,
        "cross_vendor_anchor_hash_identical": len(set(hashes.values())) == 1,
        "per_vendor_anchor_hash_prefix": {v: (h[:12] if h else None) for v, h in hashes.items()},
    }
    jsonl_rows.append(row)

with open(os.path.join(OUT, "per_task_cross_vendor_invariance.jsonl"), "w") as f:
    for row in jsonl_rows:
        f.write(json.dumps(row) + "\n")

# ---- cross-vendor summary ----
n_tuples = len(jsonl_rows)
summary = {
    "n_task_run_tuples": n_tuples,
    "n_unique_task_ids": len(set(k[0] for k in all_keys)),
    "tuples_with_full_cross_vendor_p2": sum(1 for r in jsonl_rows if r["cross_vendor_trace_completeness"]),
    "tuples_with_identical_anchor_hash_across_vendors": sum(1 for r in jsonl_rows if r["cross_vendor_anchor_hash_identical"]),
    "mean_cross_vendor_coa_count_variance": round(statistics.mean(r["cross_vendor_coa_count_variance"] for r in jsonl_rows), 6),
    "mean_cross_vendor_gap_count_variance": round(statistics.mean(r["cross_vendor_gap_count_variance"] for r in jsonl_rows), 6),
}

print("=== PER-VENDOR AGGREGATES ===")
for v in VENDORS:
    a = per_vendor[v]
    print(f"{v:8s} model={a['model']:14s} n={a['n_total']} ok={a['ok_rate']} "
          f"wall={a['mean_wall_clock_s']:.1f}s P2={a['p2_trace_completeness_rate']} "
          f"COA={a['mean_coa_count']:.3f} {a['coa_count_distribution']} "
          f"gaps={a['mean_gap_report_count']:.3f} hashuniq={a['anchor_hash_uniqueness']}")
print("\n=== CROSS-VENDOR SUMMARY ===")
print(json.dumps(summary, indent=2))
print(f"\nJSONL rows written: {n_tuples} (expected 300)")
