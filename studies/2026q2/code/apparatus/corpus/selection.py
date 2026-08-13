"""
PI-side selection helper for the 40-per-domain main corpus selection
(Workstream C2, post-Handoff-03).

The Handoff 03 pool at `03_corpus/main/candidates_main.jsonl` has 262
candidates after dedup, biased toward the source with the largest chunk
pool inside each domain (NIST 800-53 dominates security, NIST 800-37
dominates finance, the two ODNI ATAs dominate intel). A uniform random
40-pick would preserve that bias; a stratified water-fill across sources
balances it.

`stratified_propose` is the algorithm: per (domain, category) it
iteratively gives one candidate to the source with the lowest current
allocation, until the cell's target is hit. The pre-selection is a
*proposal* the PI reads and edits before applying; the function does not
decide the corpus on the PI's behalf.

`render_proposal_md` writes a markdown file with one section per cell
and a `[x]` checkbox per candidate. The PI toggles `[x]` to `[ ]` to
swap a candidate out and `[ ]` to `[x]` to swap one in. `parse_proposal`
reads the edited file. `build_selection_json` validates that every
domain ends with exactly 40 accepted candidates and writes the same
JSON shape Handoff 06 already consumes (now scaled to 120 entries with
`TASK-MAIN-<DOM>-NNN` task ids).
"""
from __future__ import annotations

import re
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from typing import Optional

# Default per-(domain, category) targets: 14 + 13 + 13 = 40 per domain.
# The PI can override on the CLI.
DEFAULT_CATEGORY_TARGETS = {
    "full_specification": 14, "gap_triggering": 13, "stretch_case": 13}

DOMAIN_SHORT = {"security_operations_reporting": "SEC",
                "financial_reporting": "FIN",
                "intelligence_collection_tasking": "INT"}


def _by_cell(candidates: list):
    """Group candidates by (domain, category), preserving input order."""
    out = OrderedDict()
    for c in candidates:
        key = (c.get("domain", ""), c.get("category", ""))
        out.setdefault(key, []).append(c)
    return out


def stratified_propose(candidates: list,
                        targets: Optional[dict] = None) -> set:
    """Propose an accepted set by water-filling across sources within
    each (domain, category) cell.

    Returns a set of (domain, category, candidate_idx) tuples.
    """
    targets = dict(targets or DEFAULT_CATEGORY_TARGETS)
    by_cell = _by_cell(candidates)
    accepted = set()
    for (domain, category), cands in by_cell.items():
        target = targets.get(category, 0)
        if target <= 0:
            continue
        by_source = OrderedDict()
        for c in cands:
            src = c.get("derived_from", {}).get("name", "") or "?"
            by_source.setdefault(src, []).append(c)
        # water-fill: give one to the source with the lowest current
        # allocation that still has candidates available
        counts = {s: 0 for s in by_source}
        available = {s: list(v) for s, v in by_source.items()}
        chosen = []
        while len(chosen) < target:
            ready = [(counts[s], s) for s in by_source if available[s]]
            if not ready:
                break
            ready.sort()
            s = ready[0][1]
            c = available[s].pop(0)
            chosen.append(c)
            counts[s] += 1
        for c in chosen:
            accepted.add((domain, category, c.get("candidate_idx")))
    return accepted


# --- markdown proposal -----------------------------------------------------

_HEADER = """# Main corpus selection proposal

This file is a pre-selection across the main corpus pool, water-filled by
source within each (domain x category) cell so no single document
dominates. Edit the `[x]` checkboxes: flip `[x]` to `[ ]` to drop a
candidate from the selection, flip `[ ]` to `[x]` to add one in. Exactly
40 candidates per domain must be checked when you run
`apparatus.corpus.cli select-main --apply`.

A candidate's `derived_from` reference tells you which real public
document the task is grounded in.
"""

_CELL_HEADER = "\n## {DOMAIN} / {CATEGORY}  (target {TARGET})\n"

_ITEM = """
### {MARK} {SHORT}-{CAT_SHORT}-{IDX:03d}  candidate_idx={IDX}

- derived_from: `{REF}`
  - source: {NAME}

{TEXT}

"""


def render_proposal_md(candidates: list, accepted: set,
                        targets: Optional[dict] = None) -> str:
    """Render an editable markdown proposal."""
    targets = dict(targets or DEFAULT_CATEGORY_TARGETS)
    by_cell = _by_cell(candidates)
    parts = [_HEADER]
    cat_short = {"full_specification": "FULL",
                  "gap_triggering": "GAP",
                  "stretch_case": "STRETCH"}
    for (domain, category), cands in by_cell.items():
        target = targets.get(category, 0)
        parts.append(_CELL_HEADER.format(
            DOMAIN=domain, CATEGORY=category, TARGET=target))
        for c in cands:
            idx = int(c.get("candidate_idx", 0))
            mark = ("[x]" if (domain, category, idx) in accepted
                    else "[ ]")
            ref = c.get("derived_from", {}).get("reference_id", "")
            name = c.get("derived_from", {}).get("name", "")
            text = (c.get("text", "") or "").strip()
            parts.append(_ITEM.format(
                MARK=mark, SHORT=DOMAIN_SHORT.get(domain, domain[:3].upper()),
                CAT_SHORT=cat_short.get(category, category[:6].upper()),
                IDX=idx, REF=ref, NAME=name, TEXT=text))
    return "".join(parts)


_HEADING_RE = re.compile(
    r"^### \[(?P<mark>[ xX])\] \S+\s+candidate_idx=(?P<idx>\d+)",
    re.MULTILINE)
_SECTION_RE = re.compile(
    r"^## (?P<domain>\S+) / (?P<category>\S+)", re.MULTILINE)


def parse_proposal(text: str) -> set:
    """Read an edited markdown proposal and return the set of accepted
    (domain, category, candidate_idx) tuples. Whitespace in the checkbox
    counts as unchecked; `x` or `X` counts as checked."""
    # walk the text, tracking the current cell as headings appear
    accepted = set()
    current = None
    pos = 0
    while pos < len(text):
        sec_m = _SECTION_RE.search(text, pos)
        head_m = _HEADING_RE.search(text, pos)
        # whichever comes first
        if sec_m is None and head_m is None:
            break
        if sec_m is not None and (head_m is None
                                   or sec_m.start() < head_m.start()):
            current = (sec_m.group("domain"), sec_m.group("category"))
            pos = sec_m.end()
            continue
        # head_m
        mark = head_m.group("mark")
        idx = int(head_m.group("idx"))
        if current is not None and mark.lower() == "x":
            accepted.add((current[0], current[1], idx))
        pos = head_m.end()
    return accepted


# --- main_selection.json ---------------------------------------------------

@dataclass
class SelectionReport:
    accepted_per_domain: dict = field(default_factory=dict)
    per_category: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    selection: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def build_selection_json(candidates: list, accepted: set,
                          task_id_prefix: str = "TASK-MAIN",
                          per_domain_target: int = 40
                          ) -> SelectionReport:
    """Validate and assemble a Handoff-06-compatible selection JSON for
    the main corpus.

    Validation: exactly `per_domain_target` candidates accepted per
    domain; every accepted entry must be in the candidates pool.
    """
    rep = SelectionReport()
    by_dom_cat = OrderedDict()
    pool_keys = set()
    for c in candidates:
        key = (c["domain"], c["category"], int(c["candidate_idx"]))
        pool_keys.add(key)
    # report any accepted that is not in the pool
    bogus = accepted - pool_keys
    if bogus:
        rep.errors.append("accepted entries not in pool: %s"
                          % sorted(bogus)[:5])
    # count per domain and per (domain, category)
    by_dom = defaultdict(int)
    by_dom_cat_count = defaultdict(int)
    for (d, cat, idx) in accepted & pool_keys:
        by_dom[d] += 1
        by_dom_cat_count[(d, cat)] += 1
    for d, n in sorted(by_dom.items()):
        rep.accepted_per_domain[d] = n
        if n != per_domain_target:
            rep.errors.append(
                "%s has %d accepted; expected %d" % (d, n, per_domain_target))
    for k, n in sorted(by_dom_cat_count.items()):
        rep.per_category["%s/%s" % k] = n

    # build the selection list with deterministic task_id assignment
    # within each domain, sorted by (category, candidate_idx) for stable
    # downstream pairing
    sel = []
    by_dom_list = defaultdict(list)
    for c in candidates:
        key = (c["domain"], c["category"], int(c["candidate_idx"]))
        if key in accepted and key in pool_keys:
            by_dom_list[c["domain"]].append(c)
    for d in sorted(by_dom_list):
        cands = sorted(by_dom_list[d],
                        key=lambda c: (c["category"],
                                        int(c["candidate_idx"])))
        for n, c in enumerate(cands, start=1):
            short = DOMAIN_SHORT.get(d, d[:3].upper())
            sel.append({
                "domain": d, "candidate_idx": int(c["candidate_idx"]),
                "category": c["category"],
                "task_id": "%s-%s-%03d" % (task_id_prefix, short, n),
                "derived_from_reference_id":
                    c.get("derived_from", {}).get("reference_id", ""),
            })
    rep.selection = sel
    return rep
