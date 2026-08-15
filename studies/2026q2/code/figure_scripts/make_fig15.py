#!/usr/bin/env python3
"""Regenerate SI Figure: per-record minimum-coverage distributions (12,000
records, all nine systems) with the paper's pattern-shell labels (no framework
names). Reads the public deposit's ensemble scores + anonymization mapping.
Deterministic jitter (golden-ratio sequence) -- no randomness, reproducible.

Usage: python3 make_fig15.py <study_root> <out_dir>
"""
import json, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

INK, SEC, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, BASE, BLUE, SURF = "#e1e0d9", "#c3c2b7", "#2a78d6", "#ffffff"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8.0,
    "axes.edgecolor": BASE, "axes.linewidth": 0.7,
    "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "xtick.labelcolor": SEC, "ytick.labelcolor": SEC,
    "figure.facecolor": SURF, "axes.facecolor": SURF,
    "pdf.fonttype": 42,
})

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
OUT = sys.argv[2] if len(sys.argv) > 2 else "."
G = os.path.join(ROOT, "replication_package/v1_main/grading/v2_full_coverage")

ORDER = [
    ("mandate_primary", "MANDATE-\nprimary"),
    ("cond_a", "Cond-A"),
    ("cond_b", "Cond-B"),
    ("baseline_1", "B1\n(Sonnet)"),
    ("baseline_2", "B2\n(GPT-4o)"),
    ("baseline_3", "B3\nReAct"),
    ("baseline_4", "B4\nplanner-\nreviewer"),
    ("baseline_5", "B5\nseq. analyst-\nreviewer"),
    ("baseline_6", "B6\nrevision-\ngraph"),
]

mapping = json.load(open(os.path.join(G, "anonymization_mapping_full.json")))
vals = {k: [] for k, _ in ORDER}
for line in open(os.path.join(G, "ensemble_scores.jsonl")):
    e = json.loads(line)
    m = mapping.get(e["anon_id"])
    if not m:
        continue
    v = e.get("minimum_coverage")
    if v is None:
        continue
    s = m["system_id"]
    if s in vals:
        vals[s].append(v)

PHI = 0.6180339887498949
fig, ax = plt.subplots(figsize=(5.7, 2.9))
for i, (key, label) in enumerate(ORDER):
    v = vals[key]
    xs = [i + (((j * PHI) % 1.0) - 0.5) * 0.62 for j in range(len(v))]
    ax.plot(xs, v, ls="none", marker="o", ms=1.1, color=BLUE, alpha=0.10,
            mec="none", rasterized=True)
    mean = sum(v) / len(v)
    ax.plot([i - 0.36, i + 0.36], [mean, mean], color=INK, lw=1.6,
            solid_capstyle="butt", zorder=5)
    ax.text(i, mean + 0.045, f"{mean:.3f}", ha="center", va="bottom",
            fontsize=6.2, color=INK,
            bbox=dict(fc="#ffffff", ec="none", alpha=0.75, pad=0.6))
ax.plot([], [], color=INK, lw=1.6, label="system mean")
ax.set_xticks(range(len(ORDER)))
ax.set_xticklabels([l for _, l in ORDER], fontsize=6.4)
ax.set_ylim(-0.03, 1.03)
ax.set_xlim(-0.6, len(ORDER) - 0.4)
ax.set_ylabel("Per-record minimum coverage", fontsize=7.5)
ax.grid(axis="y", color=GRID, lw=0.5)
ax.set_axisbelow(True)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.0), fontsize=7,
          frameon=False, handlelength=1.4)
fig.tight_layout(pad=0.5)
fig.savefig(os.path.join(OUT, "fig15_mincov_distributions.pdf"), dpi=300)
print("written", os.path.join(OUT, "fig15_mincov_distributions.pdf"),
      {k: len(v) for k, v in vals.items()})
