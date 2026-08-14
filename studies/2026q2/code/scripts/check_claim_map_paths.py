#!/usr/bin/env python3
"""Check that every literal path cited in docs/CLAIM_TO_DATA_MAP.md exists.

Backtick spans in the map are treated as candidate paths when they start with
a known study-root directory (or requirements.txt). Brace alternations
({a,b}) are expanded; spans containing shell commands, flags, URLs, or
wildcards other than a trailing component glob are skipped. Globs must match
at least one file. Run from the study root; exit 0 iff nothing is missing.
"""
import glob as globmod
import itertools
import re
import sys

BASES = ("replication_package/", "code/", "docs/", "analysis/",
         "pre_registration/", "engineering_provenance/", "supplement_pdfs/",
         "requirements.txt",
         # unprefixed component dirs are treated as paths so that a missing
         # replication_package/ prefix is caught, not silently skipped:
         "v0_pilot/", "v0_5_pilot/", "v1_main/", "v2_complete/",
         "v3_corrected_routing/", "retained_study_data/")

def expand_braces(s):
    m = re.search(r"\{([^{}]*)\}", s)
    if not m:
        return [s]
    head, tail = s[:m.start()], s[m.end():]
    return list(itertools.chain.from_iterable(
        expand_braces(head + alt + tail) for alt in m.group(1).split(",")))

def main():
    text = open("docs/CLAIM_TO_DATA_MAP.md", encoding="utf-8").read()
    missing, checked = [], 0
    for span in re.findall(r"`([^`]+)`", text):
        span = span.strip()
        if not span.startswith(BASES):
            continue
        if any(tok in span for tok in (" ", "--")):
            continue
        for cand in expand_braces(span):
            checked += 1
            if "*" in cand:
                if not globmod.glob(cand):
                    missing.append(cand)
            else:
                if not globmod.glob(cand.rstrip("/")):
                    missing.append(cand)
    print(f"checked {checked} path candidates; missing: {len(missing)}")
    for m in missing:
        print("MISSING:", m)
    return 1 if missing else 0

if __name__ == "__main__":
    sys.exit(main())
