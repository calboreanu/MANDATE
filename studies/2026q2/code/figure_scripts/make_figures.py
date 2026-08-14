#!/usr/bin/env python3
"""Generate the evidence-communication figures for the MANDATE manuscript.

Inputs (repo-relative when run from the study release; here, local copies):
  fig_constants.json      -- transcribed release constants (provenance inside)
  fig_source_extract.json -- per-task ensemble means extracted from
                             replication_package/v1_main/grading/v2_full_coverage/
                             (see extract_fig_data.py)
Outputs: PDF figures, grayscale-safe, one accent hue, position-first encoding.
"""
import json, sys, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

INK    = "#0b0b0b"
SEC    = "#52514e"
MUTED  = "#898781"
GRID   = "#e1e0d9"
BASE   = "#c3c2b7"
BLUE   = "#2a78d6"   # accent / conformant
LBLUE  = "#9ec5f4"   # secondary bar
CRIT   = "#d03b3b"   # violation (always labeled, never color-alone)
SURF   = "#ffffff"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8.0,
    "axes.edgecolor": BASE, "axes.linewidth": 0.7,
    "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "xtick.labelcolor": SEC, "ytick.labelcolor": SEC,
    "figure.facecolor": SURF, "axes.facecolor": SURF,
    "pdf.fonttype": 42,
})

HERE = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(os.path.join(HERE, "fig_constants.json")))
X = json.load(open(os.path.join(HERE, "fig_source_extract.json")))
OUT = sys.argv[1] if len(sys.argv) > 1 else HERE
os.makedirs(OUT, exist_ok=True)


def box(ax, x, y, w, h, text, fc="#f4f4f2", ec=BASE, tc=INK, fs=8, lw=0.9, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012",
                                fc=fc, ec=ec, lw=lw, mutation_aspect=1.0))
    ax.text(x + w/2, y + h/2, text, ha="center", va="center", fontsize=fs,
            color=tc, fontweight="bold" if bold else "normal", linespacing=1.25)


def arrow(ax, x1, y1, x2, y2, color=SEC, lw=1.1, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=9, color=color, lw=lw, linestyle=ls))


# ---------------------------------------------------------------- fig20 routing
def fig20():
    fig, ax = plt.subplots(figsize=(5.7, 2.9))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    r = C["routing"]
    # panel titles
    ax.text(0.25, 0.965, "Evaluated build\n(frozen campaign)", ha="center",
            fontsize=8, fontweight="bold", color=INK, va="top")
    ax.text(0.75, 0.965, "Successor implementation\n(post-hoc conformance check)", ha="center",
            fontsize=8, fontweight="bold", color=INK, va="top")
    ax.plot([0.5, 0.5], [0.02, 0.86], color=GRID, lw=0.8)
    # left column
    box(ax, 0.065, 0.70, 0.37, 0.12, "3,000 canonical records\n(Cond-A 1,500 + Cond-B 1,500)")
    box(ax, 0.065, 0.44, 0.37, 0.12,
        "3,000 signal-carrying records\n(blocking or insufficient-for-automation)")
    arrow(ax, 0.25, 0.70, 0.25, 0.565)
    box(ax, 0.065, 0.08, 0.37, 0.17,
        "3,000 completed ok=true mandates\n(retrospective fail-closed\ninconsistencies)",
        fc="#fbeaea", ec=CRIT, tc=CRIT, bold=True, fs=7.3)
    arrow(ax, 0.25, 0.44, 0.25, 0.265, color=CRIT)
    ax.text(0.258, 0.35, "no state gate (fail-open)", fontsize=7, color=CRIT, ha="left")
    # right column
    box(ax, 0.565, 0.70, 0.37, 0.12, "3,000 regenerated records\n(same corpus and recorded schedule)")
    box(ax, 0.565, 0.44, 0.30, 0.12,
        "2,999 signal-carrying records\n(measured from fresh gap sets)")
    arrow(ax, 0.72, 0.70, 0.72, 0.565)
    box(ax, 0.565, 0.08, 0.30, 0.17,
        "2,999\nNON_EXECUTABLE_GAPS\n0 routing-contract violations",
        fc="#e8f0fb", ec=BLUE, tc="#1c5cab", bold=True, fs=7.3)
    arrow(ax, 0.68, 0.44, 0.68, 0.265, color=BLUE)
    ax.text(0.688, 0.35, "signal predicate →\nexecution state (fail-closed)",
            fontsize=6.8, color="#1c5cab", ha="left")
    # the one no-signal record
    box(ax, 0.885, 0.08, 0.105, 0.17, "1 record,\nno signal:\nEXECUTABLE", fs=6.3)
    arrow(ax, 0.955, 0.70, 0.945, 0.26, color=MUTED, lw=0.8, ls=(0, (3, 2)))
    fig.tight_layout(pad=0.4)
    fig.savefig(os.path.join(OUT, "fig20_routing_conformance.pdf"))
    plt.close(fig)


# ------------------------------------------------------------------ fig21 forest
def fig21():
    panels = [("minimum_coverage", "Minimum coverage"),
              ("target_coverage", "Target coverage"),
              ("constraint_coverage", "Constraint coverage")]
    fig, axes = plt.subplots(3, 1, figsize=(5.7, 4.6), sharex=True)
    XL = 0.16
    for ax, (key, title) in zip(axes, panels):
        data = C["contrasts_task_clustered"][key]
        names = list(data.keys())
        ys = list(range(len(names)))[::-1]
        ax.axvline(0, color=BASE, lw=0.9)
        for y, n in zip(ys, names):
            d, lo, hi = data[n]
            if hi > XL:  # off-scale (B2): arrow + printed value
                ax.annotate("", xy=(XL*0.97, y), xytext=(XL*0.72, y),
                            arrowprops=dict(arrowstyle="-|>", color=BLUE, lw=1.4))
                ax.text(XL*0.70, y, f"+{d:.3f} [{lo:+.3f}, {hi:+.3f}]",
                        ha="right", va="center", fontsize=7, color=SEC)
            else:
                ax.plot([lo, hi], [y, y], color=BLUE, lw=1.6, solid_capstyle="butt")
                ax.plot([d], [y], marker="o", ms=4.5, color=BLUE, mec=SURF, mew=0.6)
                ax.text(XL*1.02, y, f"{d:+.3f}", ha="left", va="center",
                        fontsize=7, color=SEC)
        ax.set_yticks(ys); ax.set_yticklabels(names, fontsize=7.5)
        ax.set_xlim(-XL, XL*1.22)
        ax.set_title(title, fontsize=8.5, loc="left", color=INK, pad=2)
        ax.grid(axis="x", color=GRID, lw=0.5)
        ax.set_axisbelow(True)
        for s in ("top", "right"): ax.spines[s].set_visible(False)
    axes[-1].set_xlabel("Δ = Cond-B − baseline (task-clustered 95% CI; positive favors Cond-B)",
                        fontsize=7.5)
    axes[0].text(0.0, 1.30, "Exploratory intervals; 120 shared main-corpus tasks.\n"
                 "Cond-A excluded: structured-input upper bound, not a fair contrast.",
                 transform=axes[0].transAxes, fontsize=7, color=MUTED, va="bottom")
    fig.tight_layout(pad=0.5, h_pad=1.0, rect=(0, 0, 1, 0.955))
    fig.savefig(os.path.join(OUT, "fig21_contrast_forest.pdf"))
    plt.close(fig)


# ------------------------------------------------------------- fig22 paired tasks
def fig22():
    tm = X["task_means_min_coverage"]
    fig, axes = plt.subplots(1, 2, figsize=(5.7, 2.9), sharey=False)
    pairs = [("baseline_1", "vs. B1 single-prompt (Sonnet)", (-0.044, -0.009), -0.026),
             ("baseline_3", "vs. B3 ReAct pattern", (-0.129, -0.095), -0.112)]
    for ax, (base, title, ci, delta) in zip(axes, pairs):
        tasks = sorted(tm["cond_b"].keys())
        diffs = sorted(tm["cond_b"][t] - tm[base][t] for t in tasks)
        neg = sum(1 for d in diffs if d < -1e-12); pos = sum(1 for d in diffs if d > 1e-12)
        tie = len(diffs) - neg - pos
        ax.axvline(0, color=BASE, lw=0.9)
        ax.plot(diffs, range(len(diffs)), ls="none", marker="o", ms=2.6,
                color=BLUE, alpha=0.55, mec="none")
        ax.plot([ci[0], ci[1]], [-8, -8], color=INK, lw=2.2, solid_capstyle="butt")
        ax.plot([delta], [-8], marker="D", ms=5, color=INK, mec=SURF, mew=0.6)
        ax.set_ylim(-14, len(diffs) + 2)
        ax.set_title(title, fontsize=8.5, loc="left", color=INK)
        ax.set_xlabel("per-task Δ minimum coverage", fontsize=7.5)
        ax.text(0.02, 0.97, f"{neg}/120 favor baseline\n{pos}/120 favor Cond-B\n{tie} ties",
                transform=ax.transAxes, fontsize=7, color=SEC, va="top")
        ax.set_yticks([])
        ax.grid(axis="x", color=GRID, lw=0.5); ax.set_axisbelow(True)
        for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    axes[0].set_ylabel("120 shared tasks, ranked by Δ", fontsize=7.5)
    fig.text(0.01, 0.005, "Dots: paired task means (10 recorded executions each). "
             "Black: mean Δ with exploratory task-clustered 95% CI.",
             fontsize=7, color=MUTED)
    fig.tight_layout(pad=0.5, rect=(0, 0.03, 1, 1))
    fig.savefig(os.path.join(OUT, "fig22_paired_tasks.pdf"))
    plt.close(fig)


# ------------------------------------------------------------ fig23 reliability
def fig23():
    R = C["full_coverage_alpha"]; rows = R["outcomes"]
    fig, ax = plt.subplots(figsize=(5.7, 2.6))
    ys = list(range(len(rows)))[::-1]
    ax.axvline(R["floor"], color=INK, lw=1.0, ls=(0, (4, 2)))
    ax.text(R["floor"] + 0.008, len(rows) - 0.40, "0.667 protocol floor",
            fontsize=7, color=INK)
    for y, r in zip(ys, rows):
        above = r["alpha"] >= R["floor"]
        col = BLUE if above else MUTED
        ax.plot([0, r["alpha"]], [y, y], color=col, lw=1.2, alpha=0.35)
        ax.plot([r["alpha"]], [y], marker="o", ms=5.5, color=col, mec=SURF, mew=0.6)
        ax.text(r["alpha"] + 0.014, y, f'{r["alpha"]:.3f}', fontsize=7, color=SEC,
                va="center")
        if "alpha_nominal" in r:
            ax.plot([r["alpha_nominal"]], [y], marker="s", ms=4.5, mfc="none",
                    mec=MUTED, mew=1.0)
            ax.text(r["alpha_nominal"] + 0.012, y - 0.34,
                    f'{r["alpha_nominal"]:.3f} (nominal)', fontsize=6.3, color=MUTED)
        tag = "above floor" if above else "below floor (descriptive)"
        ax.text(1.01, y, tag, fontsize=7, color=(BLUE if above else SEC), va="center")
    ax.set_yticks(ys)
    ax.set_yticklabels([f'{r["name"]} ({r["metric"]})' for r in rows], fontsize=7.5)
    ax.set_xlim(0.0, 1.0); ax.set_ylim(-0.8, len(rows) - 0.2)
    ax.set_xlabel("Measured full-coverage Krippendorff \u03b1 (3 judges \u00d7 12,000 records, shape-neutral rubric)",
                  fontsize=7.5)
    ax.grid(axis="x", color=GRID, lw=0.5); ax.set_axisbelow(True)
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    fig.tight_layout(pad=0.5)
    fig.savefig(os.path.join(OUT, "fig23_judge_reliability.pdf"))
    plt.close(fig)


# ------------------------------------------------------------- fig24 xvendor
def fig24():
    V = C["xvendor"]; n = len(V["vendors"])
    xs = list(range(n)); w = 0.36
    fig, ax = plt.subplots(figsize=(5.7, 2.5))
    b1 = ax.bar([x - w/2 for x in xs], V["llm_path_pct"], w, color=BLUE,
                label="completed fully on the LLM path")
    b2 = ax.bar([x + w/2 for x in xs], V["valid_after_fallback_pct"], w,
                color=LBLUE, hatch="///", edgecolor=SURF, lw=0.5,
                label="structurally valid after deterministic fallback")
    for r in list(b1) + list(b2):
        ax.text(r.get_x() + r.get_width()/2, r.get_height() + 1.5,
                f"{r.get_height():.0f}%" if r.get_height() % 1 == 0 else f"{r.get_height():.1f}%",
                ha="center", fontsize=7, color=SEC)
    ax.set_xticks(xs); ax.set_xticklabels(V["vendors"], fontsize=7.5)
    ax.set_ylim(0, 112); ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel("% of 300 records", fontsize=7.5)
    ax.grid(axis="y", color=GRID, lw=0.5); ax.set_axisbelow(True)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.0), ncol=2, fontsize=7,
              frameon=False, handlelength=1.4, columnspacing=1.2)
    fig.tight_layout(pad=0.5)
    fig.savefig(os.path.join(OUT, "fig24_xvendor_twolayer.pdf"))
    plt.close(fig)


# ------------------------------------------------------- fig25 evidence pipeline
def fig25():
    fig, ax = plt.subplots(figsize=(5.7, 3.3))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.text(0.30, 0.985, "Judged branch (all 9 systems)", ha="center", fontsize=8.5,
            fontweight="bold", color=INK)
    ax.text(0.81, 0.985, "Provenance branch\n(MANDATE artifacts only; baselines emit no chains)",
            ha="center", fontsize=7.6, fontweight="bold", color=INK, va="top")
    steps = ["150 frozen tasks (120 main + 30 hold-out)",
             "10,800 main records (120 \u00d7 9 \u00d7 10)\n+ 1,200 hold-out records (30 \u00d7 4 \u00d7 10)",
             "12,000 anonymized graded outputs",
             "3 judges \u00d7 12,000 = 36,000 retained judge records",
             "12,000 ensemble aggregates\n(0 reconciliation mismatches)",
             "120 task means \u2192 24 task-clustered contrasts",
             "claim tables and figures"]
    y = 0.90; h = 0.104; gap = 0.018
    for i, s in enumerate(steps):
        box(ax, 0.05, y - h, 0.50, h, s, fs=7.0,
            fc="#e8f0fb" if i in (3, 4) else "#f4f4f2",
            ec=BLUE if i in (3, 4) else BASE)
        if i < len(steps) - 1:
            arrow(ax, 0.30, y - h, 0.30, y - h - gap + 0.003)
        y -= (h + gap)
    dsteps = ["5,680 campaign chains\n(3,000 canonical + 1,480 primary\n+ 1,200 cross-vendor)",
              "34,080 campaign entries",
              "+ 3,000 successor chains\n\u2192 18,000 entries",
              "52,080 entries: entry, parent, chain,\nanchor digests recomputed (Sect. 6.3)"]
    y = 0.86; h2 = 0.135; gap2 = 0.035
    for i, s in enumerate(dsteps):
        box(ax, 0.63, y - h2, 0.35, h2, s, fs=7.0)
        if i < len(dsteps) - 1:
            arrow(ax, 0.805, y - h2, 0.805, y - h2 - gap2 + 0.003)
        y -= (h2 + gap2)
    fig.tight_layout(pad=0.4)
    fig.savefig(os.path.join(OUT, "fig25_evidence_pipeline.pdf"))
    plt.close(fig)


if __name__ == "__main__":
    fig20(); fig21(); fig22(); fig23(); fig24(); fig25()
    print("figures written to", OUT)
