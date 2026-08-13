"""
Ensemble aggregation and inter-judge reliability (Workstream B5).

PLAYBOOK Section 8: aggregate the three judges per dimension (binary by
majority, continuous by median, categorical by majority; the ordinal
trace_completeness is aggregated by median); compute pairwise Cohen's kappa
and Krippendorff's alpha; the protocol halts if grader IRR falls below 0.4.
2-1 splits on the discrete dimensions are flagged so they can feed the
human-vs-judge calibration sample (PROTOCOL_LOCK Section 8.5 / 11.4).
"""
from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

# discrete dimensions where a 2-1 split is a meaningful disagreement
DISCRETE_DIMS = ("mission_intent_match", "gap_classification",
                 "adversarial_compliance")
HALT_KAPPA = 0.4   # PLAYBOOK Section 8: halt if grader IRR below this


def _non_none(values):
    return [v for v in values if v is not None]


def _majority(values):
    """Return (modal_value, is_unanimous). None modal value if all None."""
    v = _non_none(values)
    if not v:
        return None, True
    counts = Counter(v)
    modal, _ = counts.most_common(1)[0]
    return modal, len(counts) == 1


def _median(values):
    v = _non_none(values)
    return statistics.median(v) if v else None


@dataclass
class EnsembleScore:
    """The three judges aggregated for one anonymized output."""
    anon_id: str
    mission_intent_match: Optional[int] = None
    minimum_coverage: Optional[float] = None
    target_coverage: Optional[float] = None
    constraint_coverage: Optional[float] = None
    fabrication_count: Optional[float] = None
    gap_classification: Optional[str] = None
    trace_completeness: Optional[float] = None
    adversarial_compliance: Optional[int] = None
    has_disagreement: bool = False           # 2-1 split on a discrete dim
    n_judges: int = 0
    judge_ids: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "anon_id": self.anon_id,
            "mission_intent_match": self.mission_intent_match,
            "minimum_coverage": self.minimum_coverage,
            "target_coverage": self.target_coverage,
            "constraint_coverage": self.constraint_coverage,
            "fabrication_count": self.fabrication_count,
            "gap_classification": self.gap_classification,
            "trace_completeness": self.trace_completeness,
            "adversarial_compliance": self.adversarial_compliance,
            "has_disagreement": self.has_disagreement,
            "n_judges": self.n_judges, "judge_ids": self.judge_ids,
        }


def aggregate(scores: list) -> EnsembleScore:
    """Aggregate a list of JudgeScore for one output into an EnsembleScore."""
    if not scores:
        raise ValueError("aggregate() needs at least one JudgeScore")
    mim, mim_u = _majority([s.mission_intent_match for s in scores])
    gc, gc_u = _majority([s.gap_classification for s in scores])
    ac, ac_u = _majority([s.adversarial_compliance for s in scores])
    return EnsembleScore(
        anon_id=scores[0].anon_id,
        mission_intent_match=mim,
        minimum_coverage=_median([s.minimum_coverage for s in scores]),
        target_coverage=_median([s.target_coverage for s in scores]),
        constraint_coverage=_median([s.constraint_coverage for s in scores]),
        fabrication_count=_median([s.fabrication_count for s in scores]),
        gap_classification=gc,
        trace_completeness=_median([s.trace_completeness for s in scores]),
        adversarial_compliance=ac,
        has_disagreement=not (mim_u and gc_u and ac_u),
        n_judges=len(scores),
        judge_ids=[s.judge_id for s in scores],
    )


def aggregate_schema(checks: list):
    """Majority-aggregate the judges' Section 4a schema checks for one output
    into a single binary schema-validity verdict (the basis of outcome O4).

    A judge's check is schema-valid only if its parseable, schema_compliant
    and consumable_without_repair all hold (the SchemaCheck.o4_valid property,
    PROMPTS.md Section 4a). Checks that did not parse are dropped first; a
    strict majority of the surviving checks decides the verdict. The argument
    is duck-typed: any object exposing `o4_valid` and `parse_ok` works, so
    this module needs no import from `judge`.

    Returns (o4_valid, has_disagreement, n_checks):
      o4_valid         True / False, or None if no check parsed
      has_disagreement True on a non-unanimous split, so a 2-1 schema
                       disagreement can feed the human-vs-judge calibration
                       sample alongside the discrete rubric dimensions
      n_checks         number of parsed checks that were counted
    """
    flags = [bool(getattr(c, "o4_valid", False)) for c in checks
             if getattr(c, "parse_ok", False)]
    if not flags:
        return None, False, 0
    n_true = sum(flags)
    n = len(flags)
    o4 = n_true > n / 2.0
    unanimous = n_true == 0 or n_true == n
    return o4, (not unanimous), n


# --- inter-judge reliability -------------------------------------------------

def cohen_kappa(labels_a: list, labels_b: list):
    """Cohen's kappa for two judges over aligned label lists. Items where
    either judge is None are dropped. Returns a float, or None if it cannot
    be computed."""
    pairs = [(x, y) for x, y in zip(labels_a, labels_b)
             if x is not None and y is not None]
    if len(pairs) < 2:
        return None
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    if len(set(xs)) < 2 and len(set(ys)) < 2:
        # both judges gave a single constant label: kappa is undefined;
        # report perfect agreement if the constants match, else none.
        return 1.0 if xs == ys else 0.0
    try:
        from sklearn.metrics import cohen_kappa_score
        return float(cohen_kappa_score(xs, ys))
    except Exception:
        return None


def krippendorff_alpha(values_by_judge: dict, level: str = "nominal"):
    """Krippendorff's alpha across judges for one dimension. `level` is
    'nominal', 'ordinal', or 'interval'. Returns a float or None."""
    rows = list(values_by_judge.values())
    if not rows or len(rows[0]) == 0:
        return None
    if len(rows) >= 2 and all(row == rows[0] for row in rows[1:]):
        # Some krippendorff package versions return undefined when observed
        # disagreement is exactly zero. For the harness, identical aligned
        # judge labels are perfect reliability.
        return 1.0
    try:
        import numpy as np
        import krippendorff
    except ImportError:
        return None
    if level == "nominal":
        cats = sorted({v for row in rows for v in row if v is not None},
                      key=str)
        cmap = {c: i for i, c in enumerate(cats)}
        matrix = [[cmap[v] if v is not None else np.nan for v in row]
                  for row in rows]
    else:
        matrix = [[float(v) if v is not None else np.nan for v in row]
                  for row in rows]
    try:
        return float(krippendorff.alpha(reliability_data=matrix,
                                        level_of_measurement=level))
    except Exception:
        return None


def collect_dimension(graded: list, dimension: str) -> dict:
    """From a list of GradedOutput, pull one dimension's value from each judge
    in a consistent judge order. Returns {judge_id: [values aligned by output]}."""
    judge_ids = [s.judge_id for s in graded[0].judge_scores] if graded else []
    out = {jid: [] for jid in judge_ids}
    for g in graded:
        by_judge = {s.judge_id: s for s in g.judge_scores}
        for jid in judge_ids:
            s = by_judge.get(jid)
            out[jid].append(getattr(s, dimension, None) if s else None)
    return out


def grader_irr(graded: list) -> dict:
    """Inter-judge reliability over a set of GradedOutput.

    Pairwise Cohen's kappa on the discrete dimensions and Krippendorff's alpha
    per dimension. `halt` is True if the minimum pairwise kappa is below the
    PLAYBOOK Section 8 threshold of 0.4.
    """
    report = {"n_outputs": len(graded), "pairwise_kappa": {},
              "krippendorff_alpha": {}, "min_pairwise_kappa": None,
              "halt": False, "halt_threshold": HALT_KAPPA}
    if not graded:
        return report

    levels = {"mission_intent_match": "nominal",
              "gap_classification": "nominal",
              "adversarial_compliance": "nominal",
              "minimum_coverage": "interval", "target_coverage": "interval",
              "constraint_coverage": "interval",
              "trace_completeness": "ordinal", "fabrication_count": "interval"}
    kappas = []
    for dim in levels:
        by_judge = collect_dimension(graded, dim)
        report["krippendorff_alpha"][dim] = krippendorff_alpha(
            by_judge, level=levels[dim])
        if dim in ("mission_intent_match", "gap_classification"):
            jids = list(by_judge)
            for i in range(len(jids)):
                for j in range(i + 1, len(jids)):
                    k = cohen_kappa(by_judge[jids[i]], by_judge[jids[j]])
                    report["pairwise_kappa"]["%s:%s|%s"
                                             % (dim, jids[i], jids[j])] = k
                    if k is not None:
                        kappas.append(k)
    if kappas:
        report["min_pairwise_kappa"] = min(kappas)
        report["halt"] = min(kappas) < HALT_KAPPA
    return report
