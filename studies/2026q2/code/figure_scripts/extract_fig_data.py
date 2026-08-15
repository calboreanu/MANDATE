#!/usr/bin/env python3
"""Extract figure source data from the MANDATE study release (stdlib only).

Run from any directory after checking out ``calboreanu/MANDATE`` at tag
``v2.0.9``:

    python3 studies/2026q2/code/figure_scripts/extract_fig_data.py \
      > /tmp/fig_source_extract.json

Produces the per-task and per-domain ensemble means consumed by
make_figures.py. All other figure inputs are transcribed release constants
(fig_constants.json, provenance documented inside that file).
"""
import json, sys
from collections import defaultdict
from pathlib import Path

STUDY_ROOT = Path(__file__).resolve().parents[2]
BASE = STUDY_ROOT / "replication_package" / "v1_main"
mapping = json.load(open(BASE / "grading/v2_full_coverage/anonymization_mapping_full.json"))

acc = defaultdict(list)      # (system, task) -> [minimum_coverage]
dom_acc = defaultdict(list)  # (system, domain) -> [minimum_coverage]
n = 0
for line in open(BASE / "grading/v2_full_coverage/ensemble_scores.jsonl"):
    r = json.loads(line); n += 1
    mi = mapping[r["anon_id"]]
    task, sys_id = mi["task_id"], mi["system_id"]
    mc = r["minimum_coverage"]
    if mc is None or not task.startswith("TASK-MAIN-"):
        continue
    acc[(sys_id, task)].append(mc)
    dom_acc[(sys_id, task.split("-")[2])].append(mc)

assert n == 12000, f"expected 12,000 ensemble records, got {n}"

task_means = defaultdict(dict)
for (s, t), v in acc.items():
    task_means[s][t] = round(sum(v) / len(v), 6)
for s in ("cond_a", "cond_b", "baseline_1", "baseline_3"):
    assert len(task_means[s]) == 120, f"{s}: expected 120 main tasks"

doms = {}
for (s, d), v in sorted(dom_acc.items()):
    doms.setdefault(s, {})[d] = [round(sum(v) / len(v), 4), len(v)]

json.dump({
    "task_means_min_coverage": {s: task_means[s] for s in
                                ("cond_a", "cond_b", "baseline_1", "baseline_3")},
    "domain_means_min_coverage": doms,
}, sys.stdout, indent=None)
