#!/usr/bin/env python3
"""Independent-implementation canonicalization cross-check for the MANDATE
study release.

Re-verifies a deterministic sample of deposited trace hashes -- the first 125
trace-bearing artifacts of each canonical and fine-tune main-corpus file --
using the third-party `rfc8785` package (Trail of Bits) as the JCS
canonicalizer, sharing no code with the release's own domain-limited
canonicalizer. A pass bounds the risk that the release verifier and the
generating core share a canonicalization deviation.

Requires: pip install rfc8785

Run from the study root:

    python3 code/figure_scripts/cross_check_rfc8785_sample.py --root .

Exit code 0 iff every sampled entry hash, chain digest, and anchor hash
matches under the independent implementation.
"""
import argparse, hashlib, json, os, sys

import rfc8785

FILES = [
    "replication_package/v1_main/system_outputs/cond_a_main.jsonl",
    "replication_package/v1_main/system_outputs/cond_b_main.jsonl",
    "replication_package/v1_main/system_outputs/mandate_primary_main.jsonl",
]
SAMPLE_PER_FILE = 125


def sha_independent(obj):
    return hashlib.sha256(rfc8785.dumps(obj)).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    checked = ok = chains = chains_ok = anchors = anchors_ok = 0
    for rel in FILES:
        path = os.path.join(args.root, rel)
        n_art = 0
        for line in open(path):
            rec = json.loads(line)
            out = rec.get("output") or {}
            if not isinstance(out, dict):
                continue
            trace = out.get("trace") or (out.get("artifact") or {}).get("trace")
            if not isinstance(trace, dict) or not trace.get("entries"):
                continue
            n_art += 1
            if n_art > SAMPLE_PER_FILE:
                break
            ehashes = []
            for e in trace["entries"]:
                stored = e.get("hash")
                got = sha_independent({k: v for k, v in e.items() if k != "hash"})
                checked += 1
                if got == stored:
                    ok += 1
                ehashes.append(stored)
            if trace.get("chain_hash"):
                chains += 1
                if sha_independent(ehashes) == trace["chain_hash"]:
                    chains_ok += 1
            anchor = out.get("anchor")
            if not isinstance(anchor, dict) and isinstance(out.get("artifact"), dict):
                anchor = out["artifact"].get("anchor")
            if isinstance(anchor, dict) and anchor.get("anchor_hash"):
                anchors += 1
                body = {k: v for k, v in anchor.items() if k != "anchor_hash"}
                if sha_independent(body) == anchor["anchor_hash"]:
                    anchors_ok += 1
    report = {"entry_hashes": f"{ok}/{checked}", "chain_digests": f"{chains_ok}/{chains}",
              "anchor_hashes": f"{anchors_ok}/{anchors}",
              "ok": ok == checked and chains_ok == chains and anchors_ok == anchors}
    print(json.dumps(report, indent=1))
    sys.exit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
