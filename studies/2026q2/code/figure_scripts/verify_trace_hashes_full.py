#!/usr/bin/env python3
"""Trace-hash verifier for every trace-bearing artifact in the MANDATE study release.

Recomputes, for every deposited MANDATE artifact across all trace-bearing
tiers -- the comparative campaign (canonical Cond-A/Cond-B and
MANDATE-primary, main and hold-out), the cross-vendor runs, the successor
routing-check outputs, the Phase-A perturbation artifacts, the A3/A5
source-ablation artifacts, and the auxiliary ablation-MVP records (canonical run plus all seven ablation variants):

  - every trace-entry hash: SHA-256 over the RFC 8785-canonicalized entry
    object with its "hash" field removed and its "parent_hashes" array
    embedded in the hashed content;
  - every parent link (each parent hash must be a preceding entry's hash);
  - every chain digest: SHA-256 over the canonicalized array of entry hashes;
  - every anchor hash: SHA-256 over the canonicalized anchor object with its
    "anchor_hash" field removed.

Structural absences are counted, never silently skipped: artifacts without a
trace object and artifacts without an anchor are tallied in the report
("artifacts_without_trace", "anchors_absent"). The artifact-level
metadata.output_hash / input_hash fields are carried values computed by the
proprietary core; their generating construction is not deposited and they are
NOT recomputed here.

Out of scope, with reasons: grading and retained judge streams (judgments,
not pipeline artifacts); pilot v0/v0_5 outputs (predate the 2026Q2 trace
contract and carry no artifact envelope); findings extracts and the ablation-MVP anonymized_outputs/ grading copies
(derived, identity-stripped views of records verified at source).

Canonicalization is the deposited artifacts' contract: property names sorted
by UTF-16 code units, no insignificant whitespace, UTF-8 output, ES6 number
serialization for the value domain the artifacts exercise (integral floats
serialize without a fractional part). This verifier is domain-limited in the
sense of the paper's Section 4.2.

Run from the study root:

    python3 code/figure_scripts/verify_trace_hashes_full.py --root . \
        --report trace_hash_report.json

Exit code 0 iff every present hash, parent link, chain digest, and anchor
hash recomputes; the JSON report carries per-file counts either way.
"""
import argparse, gzip, hashlib, json, math, os, sys

FILES = [
    "replication_package/v1_main/system_outputs/cond_a_main.jsonl",
    "replication_package/v1_main/system_outputs/cond_a_holdout.jsonl",
    "replication_package/v1_main/system_outputs/cond_b_main.jsonl",
    "replication_package/v1_main/system_outputs/cond_b_holdout.jsonl",
    "replication_package/v1_main/system_outputs/mandate_primary_main.jsonl",
    "replication_package/v1_main/system_outputs/mandate_primary_holdout.jsonl",
    "replication_package/v2_complete/cross_vendor/cond_b_xvendor_qwen.jsonl",
    "replication_package/v2_complete/cross_vendor/cond_b_xvendor_llama.jsonl",
    "replication_package/v2_complete/cross_vendor/cond_b_xvendor_mistral.jsonl",
    "replication_package/v2_complete/cross_vendor/cond_b_xvendor_phi.jsonl",
    "replication_package/v3_corrected_routing/outputs/cond_a_rerun.jsonl.gz",
    "replication_package/v3_corrected_routing/outputs/cond_b_rerun.jsonl.gz",
    "replication_package/v2_complete/perturbations_mandate/cond_a_perturbations.jsonl",
    "replication_package/v2_complete/perturbations_mandate/cond_b_perturbations.jsonl",
    "replication_package/v2_complete/perturbations_mandate/mandate_primary_perturbations.jsonl",
    "replication_package/v2_complete/ablations/a3_no_gap_analysis_main.jsonl",
    "replication_package/v2_complete/ablations/a3_no_gap_analysis_holdout.jsonl",
    "replication_package/v2_complete/ablations/a5_no_registry_main.jsonl",
    "replication_package/v2_complete/ablations/a5_no_registry_holdout.jsonl",
]

# Directories of per-record JSON files (one record per file), globbed relative to --root.
RECORD_DIRS = [
    "replication_package/v2_complete/ablation_mvp/canonical",
    "replication_package/v2_complete/ablation_mvp/ablation_a1",
    "replication_package/v2_complete/ablation_mvp/ablation_a2",
    "replication_package/v2_complete/ablation_mvp/ablation_a3",
    "replication_package/v2_complete/ablation_mvp/ablation_a4",
    "replication_package/v2_complete/ablation_mvp/ablation_a5",
    "replication_package/v2_complete/ablation_mvp/ablation_a6",
    "replication_package/v2_complete/ablation_mvp/ablation_a7",
]


def es6_number(x):
    if isinstance(x, bool):
        raise TypeError
    if isinstance(x, int):
        return str(x)
    if math.isnan(x) or math.isinf(x):
        raise ValueError("non-finite number in canonical JSON")
    if x == int(x) and abs(x) < 1e21:
        return str(int(x))
    return repr(x)


def canonical(obj):
    if obj is None:
        return "null"
    if obj is True:
        return "true"
    if obj is False:
        return "false"
    if isinstance(obj, (int, float)):
        return es6_number(obj)
    if isinstance(obj, str):
        return json.dumps(obj, ensure_ascii=False)
    if isinstance(obj, list):
        return "[" + ",".join(canonical(v) for v in obj) + "]"
    if isinstance(obj, dict):
        items = sorted(obj.items(), key=lambda kv: kv[0].encode("utf-16-be"))
        return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + canonical(v)
                              for k, v in items) + "}"
    raise TypeError(type(obj))


def sha(obj):
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def verify_artifact(art, counters):
    ok = True
    trace = art.get("trace")
    if not trace:
        counters["artifacts_without_trace"] += 1
        anchor = art.get("anchor")
        if anchor:
            counters["anchors"] += 1
            if sha({k: v for k, v in anchor.items() if k != "anchor_hash"}) == anchor.get("anchor_hash"):
                counters["anchor_ok"] += 1
            else:
                counters["anchor_fail"] += 1
                ok = False
        else:
            counters["anchors_absent"] += 1
        return ok
    entries = trace.get("entries") or []
    seen = set()
    for e in entries:
        counters["entries"] += 1
        claimed = e.get("hash")
        body = {k: v for k, v in e.items() if k != "hash"}
        if sha(body) == claimed:
            counters["entry_hash_ok"] += 1
        else:
            counters["entry_hash_fail"] += 1
            ok = False
        for p in e.get("parent_hashes") or []:
            counters["parent_links"] += 1
            if p in seen:
                counters["parent_ok"] += 1
            else:
                counters["parent_fail"] += 1
                ok = False
        seen.add(claimed)
    if not entries and not trace.get("chain_hash"):
        # Deliberately traceless variant (e.g. the A6 no-search-trace ablation):
        # zero entries and an empty chain digest, by construction. Counted, not failed.
        counters["empty_traces"] += 1
    else:
        counters["chains"] += 1
        if sha([e.get("hash") for e in entries]) == trace.get("chain_hash"):
            counters["chain_ok"] += 1
        else:
            counters["chain_fail"] += 1
            ok = False
    anchor = art.get("anchor")
    if anchor:
        counters["anchors"] += 1
        if sha({k: v for k, v in anchor.items() if k != "anchor_hash"}) == anchor.get("anchor_hash"):
            counters["anchor_ok"] += 1
        else:
            counters["anchor_fail"] += 1
            ok = False
    else:
        counters["anchors_absent"] += 1
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default="trace_hash_report.json")
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    report = {"files": {}, "totals": {}, "ok": True}
    keys = ["records", "artifacts", "entries", "entry_hash_ok", "entry_hash_fail",
            "parent_links", "parent_ok", "parent_fail", "chains", "chain_ok",
            "chain_fail", "anchors", "anchor_ok", "anchor_fail",
            "artifacts_without_trace", "anchors_absent", "empty_traces"]
    totals = {k: 0 for k in keys}
    for rel in FILES:
        path = os.path.join(args.root, rel)
        if not os.path.exists(path):
            report["files"][rel] = {"error": "missing"}
            report["ok"] = False
            continue
        c = {k: 0 for k in keys}
        opener = gzip.open if path.endswith(".gz") else open
        with opener(path, "rt") as fh:
            for line in fh:
                rec = json.loads(line)
                c["records"] += 1
                art = (rec.get("output") or {}).get("artifact")
                if not art:
                    continue
                c["artifacts"] += 1
                if not verify_artifact(art, c):
                    report["ok"] = False
        report["files"][rel] = c
        for k in keys:
            totals[k] += c[k]
    import glob as _glob
    for rel in RECORD_DIRS:
        dir_path = os.path.join(args.root, rel)
        record_paths = sorted(_glob.glob(os.path.join(dir_path, "*.json")))
        if not record_paths:
            report["files"][rel] = {"error": "missing or empty"}
            report["ok"] = False
            continue
        c = {k: 0 for k in keys}
        for rp in record_paths:
            with open(rp, "rt") as fh:
                rec = json.load(fh)
            c["records"] += 1
            art = (rec.get("output") or {}).get("artifact")
            if not art:
                continue
            c["artifacts"] += 1
            if not verify_artifact(art, c):
                report["ok"] = False
        report["files"][rel] = c
        for k in keys:
            totals[k] += c[k]
    report["totals"] = totals
    with open(args.report, "w") as fh:
        json.dump(report, fh, indent=2)
    print(json.dumps(totals, indent=2))
    print("OK" if report["ok"] else "FAIL")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
