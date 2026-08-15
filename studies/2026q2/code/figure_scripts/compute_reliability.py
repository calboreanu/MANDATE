#!/usr/bin/env python3
"""Full-coverage inter-judge reliability for the MANDATE study release.

Computes Krippendorff's alpha per outcome from the three retained
full-coverage judge streams (3 judges x 12,000 records), using closed-form
O(n) disagreement sums. Metrics: interval for the coverage/count outcomes,
nominal for categorical ones; judged trace completeness is reported under
BOTH interval and nominal treatments because the scale choice materially
changes the value.

Run from the release root:

    python3 compute_reliability.py > full_coverage_reliability.json
"""
import gzip, json, sys
from collections import Counter

STREAMS = {
    "gpt4o":  "replication_package/retained_study_data/full_coverage_judge_gpt4o.jsonl.gz",
    "claude": "replication_package/retained_study_data/full_coverage_judge_claude.jsonl.gz",
    "gemini": "replication_package/retained_study_data/full_coverage_judge_gemini.jsonl.gz",
}
OUTCOMES = [
    ("minimum_coverage", "interval"),
    ("target_coverage", "interval"),
    ("constraint_coverage", "interval"),
    ("mission_intent_match", "nominal"),
    ("gap_classification", "nominal"),
    ("fabrication_count", "interval"),
    ("trace_completeness", "interval"),
    ("trace_completeness", "ordinal"),
    ("trace_completeness", "nominal"),
]


def alpha_interval(units):
    pooled = [v for u in units for v in u]
    n, S, S2 = len(pooled), sum(pooled), sum(v * v for v in pooled)
    De = 2.0 * (n * S2 - S * S) / (n * (n - 1))
    if not De:
        return 1.0
    Do_num = sum((len(u) * sum(v * v for v in u) - sum(u) ** 2) / (len(u) - 1) for u in units)
    Do = 2.0 * Do_num / sum(len(u) for u in units)
    return 1 - Do / De


def alpha_nominal(units):
    pooled = [v for u in units for v in u]
    n, c = len(pooled), Counter(pooled)
    De = (n * n - sum(k * k for k in c.values())) / (n * (n - 1))
    if not De:
        return 1.0
    Do_num = 0.0
    for u in units:
        cu = Counter(u)
        Do_num += (len(u) ** 2 - sum(k * k for k in cu.values())) / 2 / (len(u) - 1)
    Do = 2.0 * Do_num / sum(len(u) for u in units)
    return 1 - Do / De


def alpha_ordinal(units):
    """Krippendorff alpha with the standard marginal-frequency ordinal metric."""
    domain = sorted({value for unit in units for value in unit})
    index = {value: i for i, value in enumerate(domain)}
    size = len(domain)
    coincidences = [[0.0] * size for _ in range(size)]
    for unit in units:
        counts = Counter(index[value] for value in unit)
        denominator = max(len(unit), 2) - 1
        for i in range(size):
            for j in range(size):
                value = counts[i] * counts[j] - (counts[i] if i == j else 0)
                coincidences[i][j] += value / denominator
    marginals = [sum(coincidences[i][j] for i in range(size)) for j in range(size)]
    total = sum(marginals)
    expected = [[0.0] * size for _ in range(size)]
    for i in range(size):
        for j in range(size):
            expected[i][j] = (
                marginals[i] * marginals[j] - (marginals[i] if i == j else 0)
            ) / (total - 1)
    distances = [[0.0] * size for _ in range(size)]
    for i in range(size):
        for j in range(size):
            lo, hi = sorted((i, j))
            between = sum(marginals[lo : hi + 1])
            distances[i][j] = (between - (marginals[lo] + marginals[hi]) / 2) ** 2
    observed_disagreement = sum(
        coincidences[i][j] * distances[i][j]
        for i in range(size) for j in range(size)
    )
    expected_disagreement = sum(
        expected[i][j] * distances[i][j]
        for i in range(size) for j in range(size)
    )
    return 1 - observed_disagreement / expected_disagreement


def main():
    streams = {}
    for j, path in STREAMS.items():
        d = {}
        with gzip.open(path, "rt") as fh:
            for line in fh:
                r = json.loads(line)
                d[r["anon_id"]] = r
        streams[j] = d
    ids = sorted(set.intersection(*(set(s) for s in streams.values())))
    out = {"n_units": len(ids), "alpha": {}}
    for outcome, metric in OUTCOMES:
        units = []
        for i in ids:
            vals = [streams[j][i].get(outcome) for j in streams]
            vals = [v for v in vals if v is not None]
            if len(vals) >= 2:
                units.append(vals)
        if metric == "interval":
            a = alpha_interval(units)
        elif metric == "ordinal":
            a = alpha_ordinal(units)
        else:
            a = alpha_nominal(units)
        out["alpha"][f"{outcome}__{metric}"] = round(a, 3)
    json.dump(out, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
