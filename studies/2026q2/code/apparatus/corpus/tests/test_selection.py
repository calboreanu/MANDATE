"""Tests for the main-corpus selection helper (Workstream C2)."""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pytest

from apparatus.corpus.selection import (stratified_propose,
                                          render_proposal_md,
                                          parse_proposal,
                                          build_selection_json,
                                          DEFAULT_CATEGORY_TARGETS,
                                          DOMAIN_SHORT)


def _cand(domain, category, idx, source, text="placeholder"):
    return {"domain": domain, "category": category, "candidate_idx": idx,
            "text": text,
            "derived_from": {"reference_id": "%s-%03d" % (source, idx),
                              "source": source.split("-")[0],
                              "name": source}}


def _pool(domain="financial_reporting", category="full_specification",
          source_counts=None):
    """A small synthetic pool: dict of source_name -> count."""
    out = []
    idx = 1
    for src, n in (source_counts or {"S1": 10, "S2": 10}).items():
        for _ in range(n):
            out.append(_cand(domain, category, idx, src))
            idx += 1
    return out


# --- stratified_propose -----------------------------------------------------

def test_water_fill_balances_two_equal_sources():
    pool = _pool(source_counts={"S1": 20, "S2": 20})
    accepted = stratified_propose(pool,
                                    targets={"full_specification": 6})
    # six picks split 3/3 across the two sources
    by_src = {}
    for c in pool:
        if (c["domain"], c["category"],
                c["candidate_idx"]) in accepted:
            by_src.setdefault(c["derived_from"]["name"], 0)
            by_src[c["derived_from"]["name"]] += 1
    assert by_src == {"S1": 3, "S2": 3}


def test_water_fill_caps_dominant_source():
    """When one source dominates the cell, water-fill caps its share."""
    pool = _pool(source_counts={"BIG": 50, "S1": 5, "S2": 5, "S3": 5})
    accepted = stratified_propose(pool,
                                    targets={"full_specification": 12})
    by_src = {}
    for c in pool:
        if (c["domain"], c["category"],
                c["candidate_idx"]) in accepted:
            by_src.setdefault(c["derived_from"]["name"], 0)
            by_src[c["derived_from"]["name"]] += 1
    # BIG gets 3, the three smaller sources get 3 each, total 12
    assert by_src == {"BIG": 3, "S1": 3, "S2": 3, "S3": 3}


def test_water_fill_exhausts_to_pool_size():
    """If the target exceeds the pool, accept everything available."""
    pool = _pool(source_counts={"S1": 4})
    accepted = stratified_propose(pool,
                                    targets={"full_specification": 10})
    assert len(accepted) == 4


def test_water_fill_respects_per_category_targets():
    cells = []
    for cat, n in [("full_specification", 14), ("gap_triggering", 13),
                    ("stretch_case", 13)]:
        cells.extend(_pool(category=cat,
                            source_counts={"X": n + 5, "Y": n + 5}))
    accepted = stratified_propose(cells)
    by_cat = {}
    for c in cells:
        if (c["domain"], c["category"],
                c["candidate_idx"]) in accepted:
            by_cat.setdefault(c["category"], 0)
            by_cat[c["category"]] += 1
    assert by_cat == {"full_specification": 14,
                       "gap_triggering": 13, "stretch_case": 13}


# --- markdown round-trip ---------------------------------------------------

def test_markdown_roundtrip_preserves_accepted_set():
    import re
    pool = _pool(source_counts={"S1": 8, "S2": 8})
    accepted = stratified_propose(pool,
                                    targets={"full_specification": 4})
    md = render_proposal_md(pool, accepted,
                              targets={"full_specification": 4})
    assert "## financial_reporting / full_specification" in md
    # count only the per-item heading checkboxes, ignoring the header text
    items_accepted = len(re.findall(r"^### \[x\] ", md, re.MULTILINE))
    items_skipped = len(re.findall(r"^### \[ \] ", md, re.MULTILINE))
    assert items_accepted == 4
    assert items_skipped == 12      # 16 - 4
    # round trip
    back = parse_proposal(md)
    assert back == accepted


def test_markdown_parse_respects_user_edits():
    pool = _pool(source_counts={"S1": 4, "S2": 4})
    accepted = stratified_propose(pool,
                                    targets={"full_specification": 2})
    md = render_proposal_md(pool, accepted,
                              targets={"full_specification": 2})
    # the PI swaps one out and one in
    md_edited = md.replace("[x]", "[t]", 1)         # one [x] -> [t]
    md_edited = md_edited.replace("[t]", "[ ]")    # then [t] -> [ ]
    md_edited = md_edited.replace("[ ]", "[x]", 1)  # bump the next [ ] up
    parsed = parse_proposal(md_edited)
    # count remained at 2; the specific membership shifted
    assert len(parsed) == 2


# --- build_selection_json --------------------------------------------------

def test_build_selection_validates_40_per_domain():
    pool = []
    for d in ("security_operations_reporting", "financial_reporting",
              "intelligence_collection_tasking"):
        for cat in ("full_specification", "gap_triggering",
                     "stretch_case"):
            pool.extend(_pool(domain=d, category=cat,
                              source_counts={"S1": 30}))
    accepted = stratified_propose(pool)
    rep = build_selection_json(pool, accepted)
    assert rep.ok, rep.errors
    assert all(n == 40 for n in rep.accepted_per_domain.values())
    assert len(rep.selection) == 120
    # task ids look like TASK-MAIN-SEC-001 etc.
    for e in rep.selection:
        assert e["task_id"].startswith("TASK-MAIN-")
        assert e["task_id"].split("-")[2] in {"SEC", "FIN", "INT"}


def test_build_selection_rejects_wrong_per_domain_count():
    pool = []
    for d in ("security_operations_reporting", "financial_reporting",
              "intelligence_collection_tasking"):
        for cat in ("full_specification", "gap_triggering",
                     "stretch_case"):
            pool.extend(_pool(domain=d, category=cat,
                              source_counts={"S1": 30}))
    accepted = stratified_propose(pool)
    # drop a security accept so its count is 39
    for k in list(accepted):
        if k[0] == "security_operations_reporting":
            accepted.discard(k)
            break
    rep = build_selection_json(pool, accepted)
    assert not rep.ok
    assert any("security_operations_reporting" in e for e in rep.errors)


def test_build_selection_rejects_bogus_accept():
    pool = _pool(domain="financial_reporting",
                 category="full_specification",
                 source_counts={"S1": 14})
    # add an accept for a candidate_idx not in the pool
    accepted = stratified_propose(pool,
                                    targets={"full_specification": 14,
                                              "gap_triggering": 0,
                                              "stretch_case": 0})
    accepted.add(("financial_reporting", "full_specification", 9999))
    rep = build_selection_json(pool, accepted, per_domain_target=14)
    assert not rep.ok
    assert any("not in pool" in e for e in rep.errors)
