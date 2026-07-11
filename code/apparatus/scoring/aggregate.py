"""
Task-level aggregation of the O1-O5 outcomes (Workstream B7).

PROTOCOL_LOCK Section 6.3: the unit of analysis is the task, and the per-task
metric is the median across the (up to 10) runs. The replication across runs
reduces within-task measurement noise; it does not multiply the sample size.
O5 is the exception: its unit is the prompt-injection perturbation trial
(PROTOCOL_LOCK Section 4, O5 row), so O5 aggregates per perturbation.

`task_level` collapses the per-run OutcomeRows to one value per
(system, unit, outcome). `analysis_table` returns the same content as a
long-format list of dict rows: this is what Notebook 04 loads to fit

    metric ~ system + domain + task_type + system:domain + (1 | task_id)

for each primary outcome. The aggregation does not fit models or test
hypotheses; that is Notebook 04.

Unclean runs. A run flagged not-clean (it failed, or a fine-tuned MANDATE
role silently fell back) is excluded from the median by default and counted
in `n_runs_excluded`, so the exclusion is visible rather than silent. A unit
whose every run was excluded yields value None with n_runs = 0; that is a
real gap in the evidence and is surfaced, not dropped.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Optional

from .outcomes import OUTCOME_IDS

# Whether a larger outcome value is the better result. O3 (fabrication) is the
# one outcome where lower is better; this matters only for the best / worst
# aggregators used by the Notebook 07 sensitivity analyses.
HIGHER_IS_BETTER = {"O1": True, "O2a": True, "O2b": True, "O3": False,
                    "O4": True, "O5": True}

# The run-collapse aggregators. "median" is the PROTOCOL_LOCK Section 6.3
# primary; "mean", "best", "worst" are the pre-registered Notebook 07
# sensitivity variants.
AGGREGATORS = ("median", "mean", "best", "worst")


def _collapse(values, outcome: str, agg: str) -> float:
    """Collapse a unit's contributing run values with one aggregator."""
    if agg == "median":
        return statistics.median(values)
    if agg == "mean":
        return statistics.mean(values)
    if agg == "best":
        return max(values) if HIGHER_IS_BETTER[outcome] else min(values)
    if agg == "worst":
        return min(values) if HIGHER_IS_BETTER[outcome] else max(values)
    raise ValueError("unknown aggregator: %r (use one of %s)"
                     % (agg, ", ".join(AGGREGATORS)))


@dataclass
class TaskOutcome:
    """One outcome aggregated to the unit of analysis for one system."""
    system_id: str
    outcome: str                       # O1 / O2a / O2b / O3 / O4 / O5
    unit_kind: str                     # "task" or "perturbation"
    unit_id: str
    value: Optional[float]             # median across contributing runs
    n_runs: int                        # runs contributing to the median
    n_runs_excluded: int = 0           # non-None runs dropped as unclean
    domain: str = ""
    task_type: str = ""
    category: str = ""

    def to_dict(self) -> dict:
        return {
            "system_id": self.system_id, "outcome": self.outcome,
            "unit_kind": self.unit_kind, "unit_id": self.unit_id,
            "value": self.value, "n_runs": self.n_runs,
            "n_runs_excluded": self.n_runs_excluded,
            "domain": self.domain, "task_type": self.task_type,
            "category": self.category,
        }


def task_level(rows, *, exclude_unclean: bool = True,
               agg: str = "median") -> list:
    """Collapse per-run OutcomeRows to the task-level (O5: perturbation-level)
    unit of analysis.

    For each outcome and each (system, unit) the value is that outcome
    aggregated over the contributing runs. `agg` selects the run-collapse:
    "median" is the PROTOCOL_LOCK Section 6.3 primary; "mean", "best" and
    "worst" are the Notebook 07 sensitivity variants ("best" and "worst" are
    direction-aware, so for O3 fabrication "best" is the lowest count).

    Runs where the outcome is None do not contribute (the outcome does not
    apply to them). When `exclude_unclean` is True, runs flagged not-clean
    are dropped from the aggregate and counted in n_runs_excluded.

    Returns a list of TaskOutcome, ordered by outcome then (system, unit).
    """
    out = []
    for oid in OUTCOME_IDS:
        is_o5 = (oid == "O5")
        unit_kind = "perturbation" if is_o5 else "task"
        groups: dict = {}
        for r in rows:
            if r.outcome(oid) is None:
                continue
            unit_id = (r.perturbation_id or r.task_id) if is_o5 else r.task_id
            groups.setdefault((r.system_id, unit_id), []).append(r)
        for (system_id, unit_id), grp in sorted(groups.items()):
            vals = []
            excluded = 0
            for r in grp:
                if exclude_unclean and not r.clean:
                    excluded += 1
                    continue
                vals.append(r.outcome(oid))
            meta = grp[0]
            out.append(TaskOutcome(
                system_id=system_id, outcome=oid, unit_kind=unit_kind,
                unit_id=unit_id,
                value=(_collapse(vals, oid, agg) if vals else None),
                n_runs=len(vals), n_runs_excluded=excluded,
                domain=meta.domain, task_type=meta.task_type,
                category=meta.category))
    return out


def analysis_table(rows, *, exclude_unclean: bool = True,
                   agg: str = "median") -> list:
    """The long-format analysis table: one dict per (system, unit, outcome).

    This is the table Notebook 04 loads to fit the pre-registered
    mixed-effects models. Rows whose value is None are kept, so a missing
    cell is explicit in the table rather than absent from it. `agg` passes
    through to `task_level` so the Notebook 07 sensitivity variants reuse the
    same table builder.
    """
    return [t.to_dict() for t in task_level(rows, agg=agg,
                                            exclude_unclean=exclude_unclean)]
