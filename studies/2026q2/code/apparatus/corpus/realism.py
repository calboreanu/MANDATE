"""
SME realism-audit aggregation (Workstream C2, FORMS Section 4).

Each of the 120 selected main-corpus tasks is rated 1 to 5 on realism by
each SME. The protocol halts a task (review or substitute) if its mean
rating across SMEs falls below 2.5 (PROTOCOL_LOCK Section 13 / FORMS
Section 4).

This module handles the bookkeeping. SMEs rate independently on a CSV
template generated per rater; the aggregator reads every rater's CSV,
computes per-task summary statistics, flags below-threshold tasks, and
reports Krippendorff alpha across raters as an additional IRR signal.
The SMEs are not asked to produce JSON or learn a new schema; a CSV
opens in Excel or any text editor.
"""
from __future__ import annotations

import csv
import os
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

REALISM_HALT_THRESHOLD = 2.5


@dataclass
class RealismRating:
    task_id: str
    rater_id: str
    rating: Optional[float]
    notes: str = ""

    def to_dict(self) -> dict:
        return {"task_id": self.task_id, "rater_id": self.rater_id,
                "rating": self.rating, "notes": self.notes}


@dataclass
class TaskSummary:
    task_id: str
    ratings: list = field(default_factory=list)
    raters: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    @property
    def n(self) -> int:
        return len([r for r in self.ratings if r is not None])

    @property
    def mean(self) -> Optional[float]:
        v = [float(r) for r in self.ratings if r is not None]
        return statistics.mean(v) if v else None

    @property
    def median(self) -> Optional[float]:
        v = [float(r) for r in self.ratings if r is not None]
        return statistics.median(v) if v else None

    @property
    def below_threshold(self) -> bool:
        m = self.mean
        return m is not None and m < REALISM_HALT_THRESHOLD

    def to_dict(self) -> dict:
        return {"task_id": self.task_id, "n_ratings": self.n,
                "ratings": list(self.ratings),
                "raters": list(self.raters),
                "mean": self.mean, "median": self.median,
                "below_threshold": self.below_threshold,
                "notes": list(self.notes)}


# --- template generation ----------------------------------------------------

def render_rating_template(tasks: list, rater_id: str) -> str:
    """Build a CSV rating template for one rater. `tasks` is a list of
    dicts with `task_id`, `text` (or `request_text`), and optionally
    `domain` and `category`. The CSV opens in Excel or any editor; the
    rater fills in `rating` (1 to 5) and optional `notes`."""
    rows = []
    for t in tasks:
        text = (t.get("text") or t.get("request_text") or "").replace(
            "\r", " ").replace("\n", " ").strip()
        if len(text) > 200:
            text = text[:200] + " ..."
        rows.append({
            "task_id": t.get("task_id", ""),
            "domain": t.get("domain", ""),
            "category": t.get("category", ""),
            "text_preview": text,
            "rating": "",
            "notes": "",
            "rater_id": rater_id,
        })
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["task_id", "domain", "category",
                                          "text_preview", "rating", "notes",
                                          "rater_id"])
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def write_template(tasks: list, rater_id: str, out_path: str) -> str:
    """Write the rater's CSV template to `out_path`."""
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".",
                  exist_ok=True)
    with open(out_path, "w", newline="") as f:
        f.write(render_rating_template(tasks, rater_id))
    return out_path


# --- parsing ----------------------------------------------------------------

def parse_rating_csv(path: str) -> list:
    """Read a rater's CSV and return RealismRating records. Empty rating
    cells are treated as None (rater has not rated the task); ratings
    outside the 1 to 5 range are recorded as None with a note."""
    out = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rid = (row.get("rater_id") or "").strip()
            tid = (row.get("task_id") or "").strip()
            raw = (row.get("rating") or "").strip()
            notes = (row.get("notes") or "").strip()
            if not tid:
                continue
            rating = None
            if raw:
                try:
                    v = float(raw)
                    if 1.0 <= v <= 5.0:
                        rating = v
                    else:
                        notes = ("[out-of-range rating %s] " % raw) + notes
                except ValueError:
                    notes = ("[invalid rating %r] " % raw) + notes
            out.append(RealismRating(task_id=tid, rater_id=rid,
                                       rating=rating, notes=notes))
    return out


# --- aggregation ------------------------------------------------------------

def aggregate(ratings: list) -> dict:
    """Per-task summary plus an overall report.

    Returns: {by_task: {task_id: TaskSummary.to_dict()}, halt_list,
    n_raters, halt_threshold, irr: krippendorff_alpha or None}.
    """
    by_task = {}
    raters_seen = set()
    for r in ratings:
        s = by_task.setdefault(r.task_id, TaskSummary(task_id=r.task_id))
        s.ratings.append(r.rating)
        s.raters.append(r.rater_id)
        if r.notes:
            s.notes.append("[%s] %s" % (r.rater_id, r.notes))
        raters_seen.add(r.rater_id)
    halt = [tid for tid, s in by_task.items() if s.below_threshold]

    # IRR via Krippendorff alpha (interval; ratings are ordinal but the
    # protocol treats the 1 to 5 scale as quasi-interval, FORMS Section 4)
    irr_val = None
    try:
        from ..grading.ensemble import krippendorff_alpha
        # build a {rater_id: [rating_for_task_in_fixed_order]} matrix
        task_order = sorted(by_task)
        rater_order = sorted(raters_seen)
        by_rater = {rid: [None] * len(task_order) for rid in rater_order}
        task_index = {tid: i for i, tid in enumerate(task_order)}
        for r in ratings:
            by_rater[r.rater_id][task_index[r.task_id]] = r.rating
        irr_val = krippendorff_alpha(by_rater, level="interval")
    except Exception:
        pass

    return {"by_task": {tid: s.to_dict() for tid, s in by_task.items()},
            "halt_list": halt,
            "n_raters": len(raters_seen),
            "n_tasks": len(by_task),
            "halt_threshold": REALISM_HALT_THRESHOLD,
            "halt_count": len(halt),
            "krippendorff_alpha": irr_val}


def parse_inputs(paths: list) -> list:
    """Read every rater CSV and return a single rating list."""
    out = []
    for p in paths:
        if os.path.isdir(p):
            for fn in sorted(os.listdir(p)):
                if fn.endswith(".csv"):
                    out.extend(parse_rating_csv(os.path.join(p, fn)))
        elif os.path.isfile(p):
            out.extend(parse_rating_csv(p))
    return out
