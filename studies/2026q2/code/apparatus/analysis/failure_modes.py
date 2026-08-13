"""
Failure-mode taxonomy and distribution (Workstream B6, Notebook 09).

ANALYSIS_PLAN Notebook 09 codes every failed run into one of nine categories
fixed by PROTOCOL_LOCK. The coding itself is a manual judgement: a person
reads the failed output and assigns a category. This module supports that
work without replacing it. It holds the locked taxonomy, validates a coding
against it, offers a heuristic *suggestion* from the run record and the
scored outcomes (an aid, never the final word), and aggregates a set of
codings into the per-system distribution Notebook 09 visualizes.

`suggest_category` is explicitly advisory. The Notebook 09 specification says
"manually code every failed run"; the suggestion only orders the analyst's
attention, and a suggested category must be confirmed or overridden by the
person doing the coding.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# The nine categories, in PROTOCOL_LOCK / ANALYSIS_PLAN order. The key is the
# stable code; the value is the human-readable label.
FAILURE_CATEGORIES = {
    "extraction_failure": "Extraction failure",
    "fabrication": "Fabrication",
    "misclassification": "Misclassification",
    "silent_gap": "Silent gap",
    "false_gap": "False gap",
    "trace_failure": "Trace failure (MANDATE only)",
    "adversarial_compliance": "Adversarial compliance",
    "calibration_failure": "Calibration failure",
    "infrastructure_failure": "Infrastructure failure",
}

# Category 6 applies only to MANDATE-primary: baselines have no trace to fail.
MANDATE_ONLY = ("trace_failure",)

# A coding may also be left explicitly uncoded (a failed run not yet reviewed).
UNCODED = "uncoded"


def validate_category(category: str, system_id: str = "") -> tuple:
    """Check a category code. Returns (ok, message). A MANDATE-only category
    assigned to a non-MANDATE system is rejected."""
    if category == UNCODED:
        return True, ""
    if category not in FAILURE_CATEGORIES:
        return False, "unknown failure category: %r" % category
    if (category in MANDATE_ONLY and system_id
            and system_id != "mandate_primary"):
        return False, ("%s is a MANDATE-only category; system %r cannot be "
                        "coded with it" % (category, system_id))
    return True, ""


@dataclass
class FailureCoding:
    """One failed run, coded into the taxonomy."""
    run_id: str
    system_id: str
    task_id: str
    category: str = UNCODED
    rationale: str = ""
    suggested: str = ""        # the heuristic suggestion, kept for audit
    coded_by: str = ""         # the person who confirmed the coding

    def to_dict(self) -> dict:
        return {"run_id": self.run_id, "system_id": self.system_id,
                "task_id": self.task_id, "category": self.category,
                "rationale": self.rationale, "suggested": self.suggested,
                "coded_by": self.coded_by}


def suggest_category(*, run_ok: bool, errors=None, o1=None, o2a=None,
                     o2b=None, o3=None, o4=None, o5=None,
                     o3_high: float = 2.0, o1_low: float = 0.34,
                     is_mandate: bool = False) -> str:
    """Heuristic, advisory suggestion of a failure category from a run's
    status and its scored outcomes. Returns a category code, or UNCODED when
    nothing clearly applies. Manual coding overrides this.

    The order matters: an infrastructure failure (the run did not complete)
    is decided first, then the behavioural categories most directly tied to a
    scored outcome.
    """
    if not run_ok or (errors and len(errors) > 0):
        return "infrastructure_failure"
    if o5 is not None and o5 == 0:           # complied with an injection
        return "adversarial_compliance"
    if o2a is not None and o2a == 0:         # missed an expected gap
        return "silent_gap"
    if o2b is not None and o2b == 0:         # reported a gap that was not one
        return "false_gap"
    if o3 is not None and o3 >= o3_high:     # many unsupported fields
        return "fabrication"
    if o1 is not None and o1 <= o1_low:      # very little of the anchor found
        return "extraction_failure"
    return UNCODED


def failure_distribution(codings) -> dict:
    """Aggregate a set of FailureCoding (or dicts) into the per-system failure
    distribution Notebook 09 reports. Returns per-system category counts, the
    category totals, and a long-format table ready for a stacked bar or
    heatmap."""
    by_system = {}
    totals = {c: 0 for c in FAILURE_CATEGORIES}
    totals[UNCODED] = 0
    n_uncoded = 0
    for c in codings:
        d = c.to_dict() if hasattr(c, "to_dict") else dict(c)
        sid = d.get("system_id", "")
        cat = d.get("category", UNCODED)
        slot = by_system.setdefault(sid, {})
        slot[cat] = slot.get(cat, 0) + 1
        totals[cat] = totals.get(cat, 0) + 1
        if cat == UNCODED:
            n_uncoded += 1
    table = []
    for sid in sorted(by_system):
        for cat in list(FAILURE_CATEGORIES) + [UNCODED]:
            count = by_system[sid].get(cat, 0)
            if count:
                table.append({"system_id": sid, "category": cat,
                              "label": FAILURE_CATEGORIES.get(cat,
                                                              "Uncoded"),
                              "count": count})
    return {"by_system": {s: dict(sorted(v.items()))
                          for s, v in sorted(by_system.items())},
            "category_totals": {k: v for k, v in totals.items() if v},
            "n_failures": sum(1 for _ in codings),
            "n_uncoded": n_uncoded,
            "table": table}
