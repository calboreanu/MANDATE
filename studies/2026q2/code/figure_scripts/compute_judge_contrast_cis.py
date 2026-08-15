#!/usr/bin/env python3
"""Per-judge task-clustered CIs for the two minimum-coverage headline contrasts.

Run from the study root:

    python3 code/figure_scripts/compute_judge_contrast_cis.py
"""
import gzip
import json
from collections import defaultdict

import numpy as np


ROOT = "replication_package"
SEED = 20260710
B = 10_000
JUDGES = ("gpt4o", "claude", "gemini")
BASELINES = ("baseline_3", "baseline_1")


def main():
    mapping = json.load(open(
        f"{ROOT}/v1_main/grading/v2_full_coverage/anonymization_mapping_full.json",
        encoding="utf-8",
    ))
    streams = {}
    for judge in JUDGES:
        path = f"{ROOT}/retained_study_data/full_coverage_judge_{judge}.jsonl.gz"
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            streams[judge] = {row["anon_id"]: row for row in map(json.loads, handle)}

    rng = np.random.default_rng(SEED)
    result = {"seed": SEED, "B": B, "outcome": "minimum_coverage", "contrasts": {}}
    for baseline in BASELINES:
        result["contrasts"][baseline] = {}
        for judge in JUDGES:
            values = defaultdict(lambda: defaultdict(list))
            for anon_id, meta in mapping.items():
                if not meta["task_id"].startswith("TASK-MAIN-"):
                    continue
                if meta["system_id"] not in ("cond_b", baseline):
                    continue
                value = streams[judge][anon_id].get("minimum_coverage")
                if value is not None:
                    values[meta["system_id"]][meta["task_id"]].append(float(value))
            tasks = sorted(set(values["cond_b"]) & set(values[baseline]))
            deltas = np.array([
                np.mean(values["cond_b"][task]) - np.mean(values[baseline][task])
                for task in tasks
            ])
            indices = rng.integers(0, len(deltas), size=(B, len(deltas)))
            bootstrap = deltas[indices].mean(axis=1)
            lo, hi = np.percentile(bootstrap, [2.5, 97.5])
            result["contrasts"][baseline][judge] = {
                "delta": round(float(deltas.mean()), 6),
                "ci95_task_clustered": [round(float(lo), 6), round(float(hi), 6)],
                "n_tasks": len(tasks),
            }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
