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
DESC   = "#6da7ec"   # descriptive outcomes (same hue, lighter step)
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
    fig, ax = plt.subplots(figsize=(5.15, 3.35))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    r = C["routing"]
    # panel titles
    ax.text(0.25, 0.965, "Evaluated build\n(frozen campaign)", ha="center",
            fontsize=8, fontweight="bold", color=INK, va="top")
    ax.text(0.75, 0.965, "Successor implementation\n(signal-conditional check)", ha="center",
            fontsize=8, fontweight="bold", color=INK, va="top")
    ax.plot([0.5, 0.5], [0.055, 0.86], color=GRID, lw=0.8)
    # left column
    box(ax, 0.065, 0.70, 0.37, 0.12, "3,000 canonical records\n(Cond-A 1,500 + Cond-B 1,500)")
    box(ax, 0.065, 0.44, 0.37, 0.12,
        "3,000 signal-carrying records\n(blocking or insufficient-for-automation)")
    arrow(ax, 0.25, 0.70, 0.25, 0.565)
    box(ax, 0.065, 0.08, 0.37, 0.17,
        "3,000 completed ok=true mandates\n(retrospective inconsistencies\nunder the later fail-closed contract)",
        fc="#fbeaea", ec=CRIT, tc=CRIT, bold=True, fs=8.0)
    arrow(ax, 0.25, 0.44, 0.25, 0.265, color=CRIT)
    ax.text(0.258, 0.35, "no successor state gate", fontsize=8, color=CRIT, ha="left")
    # right column
    box(ax, 0.565, 0.70, 0.37, 0.12, "3,000 regenerated records\n(same corpus and recorded schedule)")
    box(ax, 0.565, 0.44, 0.30, 0.12,
        "2,999 signal-carrying records\n(measured from fresh gap sets)")
    arrow(ax, 0.72, 0.70, 0.72, 0.565)
    box(ax, 0.565, 0.08, 0.30, 0.17,
        "2,999\nNON_EXECUTABLE_GAPS\n0 executable-with-signal",
        fc="#e8f0fb", ec=BLUE, tc="#1c5cab", bold=True, fs=8.0)
    arrow(ax, 0.68, 0.44, 0.68, 0.265, color=BLUE)
    ax.text(0.688, 0.35, "signal predicate →\nexecution state (fail-closed)",
            fontsize=8.0, color="#1c5cab", ha="left")
    # the one no-signal record
    box(ax, 0.875, 0.08, 0.12, 0.17, "1 record,\nno signal:\nEXECUTABLE", fs=8.0)
    arrow(ax, 0.955, 0.70, 0.945, 0.26, color=MUTED, lw=0.8, ls=(0, (3, 2)))
    ax.text(0.5, 0.002, "one-sided signal check — pass-through, specificity, and causal effect remain open",
            fontsize=8.0, color=SEC, ha="center", va="bottom", fontstyle="italic")
    fig.tight_layout(pad=0.4)
    fig.savefig(os.path.join(OUT, "fig20_routing_conformance.pdf"))
    plt.close(fig)


# ------------------------------------------------------------------ fig21 forest
JUDGE_TAGS = {"B1": "direction reverses", "B2": "same direction",
              "B3": "same direction", "B4": "direction reverses",
              "B5": "direction reverses", "B6": "direction reverses"}


def _forest(panels, fname, figh, note_y, rect_top, tags=False):
    # Minimum coverage is emphasized; other exploratory outcomes use a lighter
    # step of the same hue. Coefficients are labeled without a pass/fail cutoff.
    fig, axes = plt.subplots(len(panels), 1, figsize=(5.15, figh), sharex=True)
    if len(panels) == 1:
        axes = [axes]
    XL = 0.16
    for ax, (key, title, reliable) in zip(axes, panels):
        mark = BLUE if reliable else DESC
        val_ink = SEC
        data = C["contrasts_task_clustered"][key]
        names = list(data.keys())
        ys = list(range(len(names)))[::-1]
        ax.axvline(0, color=BASE, lw=0.9)
        for y, n in zip(ys, names):
            d, lo, hi = data[n]
            if hi > XL:  # off-scale (B2): arrow + printed value
                ax.annotate("", xy=(XL*0.97, y), xytext=(XL*0.78, y),
                            arrowprops=dict(arrowstyle="-|>", color=mark, lw=1.4))
                if tags:
                    ax.plot([XL*0.97], [y], marker="o", ms=4.6,
                            mfc=mark, mec=mark, mew=0.6)
                ax.text(XL*0.72, y, f"+{d:.3f}\n[{lo:+.3f}, {hi:+.3f}]",
                        ha="right", va="center", fontsize=8.0, color=val_ink,
                        linespacing=1.15,
                        bbox=dict(fc=SURF, ec="none", alpha=1.0, pad=0.6))
            else:
                ax.plot([lo, hi], [y, y], color=mark, lw=1.9 if reliable else 1.4,
                        solid_capstyle="butt")
                judge_tag = JUDGE_TAGS.get(n[:2], "") if tags else ""
                reversal = "reverses" in judge_tag
                ax.plot([d], [y], marker="s" if reversal else "o",
                        ms=5.0 if reliable else 4.0,
                        mfc=SURF if reversal else mark, mec=mark,
                        mew=1.0 if reversal else 0.6)
                ax.text(XL*1.02, y, f"{d:+.3f}", ha="left", va="center",
                        fontsize=8.0, color=val_ink)
        ax.set_yticks(ys)
        ax.set_yticklabels(names, fontsize=8.5,
                           color=INK if reliable else SEC)
        ax.set_xlim(-XL, XL*1.22)
        ax.set_title(title, fontsize=8.5, loc="left", pad=2,
                     color=INK if reliable else SEC,
                     fontweight="bold" if reliable else "normal")
        ax.grid(axis="x", color=GRID, lw=0.5)
        ax.set_axisbelow(True)
        for s in ("top", "right"): ax.spines[s].set_visible(False)
    axes[-1].set_xlabel("Δ = Cond-B − baseline (task-bootstrap 95% CI)",
                        fontsize=8.5)
    note = ("120 shared tasks; exploratory task-bootstrap intervals.\n"
            "Cond-A omitted (non-comparable structured-input condition).")
    if tags:
        note += ("\nFilled = judge-direction agreement; open = reversal "
                 "($\\alpha_{pair}=.618$).")
    fig.text(0.02 if tags else 0.34, 0.975, note, fontsize=7.6 if tags else 8.2,
             color=MUTED, va="top",
             linespacing=1.18)
    if tags:
        fig.subplots_adjust(left=0.38, right=0.97, bottom=0.20, top=0.70)
    else:
        fig.subplots_adjust(left=0.34, right=0.96, bottom=0.15,
                            top=rect_top, hspace=0.55)
    fig.savefig(os.path.join(OUT, fname))
    plt.close(fig)


def fig21():
    # Main paper: minimum coverage, the outcome with the highest pooled agreement.
    _forest([("minimum_coverage",
              "Minimum coverage — pooled $\\alpha$ = 0.855",
              True)],
            "fig21_contrast_forest.pdf", 2.95, 1.16, 0.84, tags=True)
    # Supplement companion: lower-agreement outcomes, descriptive.
    _forest([("target_coverage",
              "Target coverage — descriptive ($\\alpha$ = 0.586)",
              False),
             ("constraint_coverage",
              "Constraint coverage — descriptive ($\\alpha$ = 0.589)",
              False)],
            "fig21b_descriptive_forest.pdf", 4.25, 1.30, 0.93)


# ------------------------------------------------------------- fig22 paired tasks
def fig22():
    tm = X["task_means_min_coverage"]
    fig, axes = plt.subplots(1, 2, figsize=(5.15, 3.35), sharey=False)
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
        ax.set_xlim(-0.42, 0.42)  # one shared x-scale across both panels
        ax.set_title(title, fontsize=8.5, loc="left", color=INK)
        ax.set_xlabel("per-task Δ minimum coverage", fontsize=8.5)
        ax.text(0.02, 0.97, f"{neg}/120 favor baseline\n{pos}/120 favor Cond-B\n{tie} ties",
                transform=ax.transAxes, fontsize=8, color=SEC, va="top",
                bbox=dict(fc=SURF, ec="none", alpha=1.0, pad=0.8))
        ax.set_yticks([])
        ax.grid(axis="x", color=GRID, lw=0.5); ax.set_axisbelow(True)
        for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    axes[0].set_ylabel("120 shared tasks, ranked by Δ", fontsize=8.5)
    fig.text(0.02, 0.055,
             "Dots: paired task means (10 recorded executions each).\n"
             "Black: mean Δ with exploratory task-clustered 95% CI.",
             fontsize=7.8, color=MUTED, va="bottom", linespacing=1.15)
    fig.subplots_adjust(left=0.10, right=0.98, bottom=0.24,
                        top=0.88, wspace=0.25)
    fig.savefig(os.path.join(OUT, "fig22_paired_tasks.pdf"))
    plt.close(fig)


# ------------------------------------------------------------ fig23 reliability
def fig23():
    R = C["full_coverage_alpha"]; rows = R["outcomes"]
    fig, ax = plt.subplots(figsize=(5.15, 3.55))
    ys = list(range(len(rows)))[::-1]
    for y, r in zip(ys, rows):
        is_minimum = r["name"].lower().startswith("minimum")
        col = BLUE if is_minimum else DESC
        ax.plot([0, r["alpha"]], [y, y], color=col, lw=1.2, alpha=0.35)
        ax.plot([r["alpha"]], [y], marker="o", ms=5.5, color=col, mec=SURF, mew=0.6)
        ax.text(r["alpha"] + 0.014, y, f'{r["alpha"]:.3f}', fontsize=8, color=SEC,
                va="center")
        if "alpha_nominal" in r:
            ax.plot([r["alpha_nominal"]], [y], marker="s", ms=4.5, mfc="none",
                    mec=SEC, mew=1.0)
            ax.text(r["alpha_nominal"] + 0.012, y - 0.34,
                    f'{r["alpha_nominal"]:.3f} (nominal)', fontsize=8, color=MUTED)
        if "alpha_ordinal" in r:
            ax.plot([r["alpha_ordinal"]], [y], marker="^", ms=4.5, mfc="none",
                    mec=SEC, mew=1.0)
            ax.text(r["alpha_ordinal"] + 0.012, y + 0.30,
                    f'{r["alpha_ordinal"]:.3f} (ordinal)', fontsize=8, color=MUTED)
        tag = "pooled" if is_minimum else "descriptive"
        if is_minimum:
            # Open marker: Cond-B/B3-restricted estimate, illustrating
            # analysis-set dependence rather than a threshold crossing.
            ax.plot([0.618], [y], marker="o", ms=5.5, mfc="none", mec=BLUE, mew=1.1)
            ax.text(0.604, y - 0.34, "0.618 (decisive pair)", fontsize=8,
                    color=SEC, ha="right")
            tag = "pooled .855;\npair .618"
        ax.text(1.04, y, tag, fontsize=8, color=(BLUE if is_minimum else SEC), va="center")
    ax.set_yticks(ys)
    ax.set_yticklabels([f'{r["name"]} ({r["metric"]})' for r in rows], fontsize=8.2)
    ax.set_xlim(0.0, 1.28)
    ax.set_xticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_ylim(-0.8, len(rows) - 0.2)
    ax.set_xlabel("Measured full-coverage Krippendorff \u03b1\n(3 judges \u00d7 12,000 records; shape-neutral rubric)",
                  fontsize=8.2)
    ax.text(0.0, -0.20, "No α acceptance threshold was specified.",
            transform=ax.transAxes, fontsize=8, color=MUTED, va="top")
    ax.grid(axis="x", color=GRID, lw=0.5); ax.set_axisbelow(True)
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    fig.subplots_adjust(left=0.43, right=0.97, bottom=0.23, top=0.97)
    fig.savefig(os.path.join(OUT, "fig23_judge_reliability.pdf"))
    plt.close(fig)


# ------------------------------------------------------------- fig24 xvendor
def fig24():
    # Nested quantities drawn as nested geometry: LLM-path completion is a
    # subset of structural validity after fallback, so the bar is a 100%
    # stack — solid = completed on the LLM path, hatched = rescued by the
    # deterministic fallback.
    V = C["xvendor"]; n = len(V["vendors"])
    xs = list(range(n)); w = 0.55
    llm = V["llm_path_pct"]
    rescued = [round(t - l, 1) for t, l in zip(V["valid_after_fallback_pct"], llm)]
    fig, ax = plt.subplots(figsize=(5.15, 3.0))
    ax.bar(xs, llm, w, color=BLUE, label="completed fully on the LLM path")
    ax.bar(xs, rescued, w, bottom=llm, color=LBLUE, hatch="///",
           edgecolor=SURF, lw=0.5, label="rescued by the deterministic fallback")
    for x, l, r in zip(xs, llm, rescued):
        if l >= 12:
            ax.text(x, l/2, f"{l:g}%", ha="center", va="center",
                    fontsize=8.2, color=SURF, fontweight="bold")
        elif l > 0:
            ax.text(x, l + 2, f"{l:g}%", ha="center", fontsize=8, color=SEC)
        else:
            ax.text(x, 2.5, "0% on LLM path", ha="center", va="bottom",
                    fontsize=8, color="#1c5cab", fontweight="bold",
                    bbox=dict(fc=SURF, ec="none", alpha=1.0, pad=1.0))
        if r >= 12:
            ax.text(x, l + r/2, f"{r:g}% rescued", ha="center", va="center",
                    fontsize=8, color="#1c5cab",
                    bbox=dict(fc=SURF, ec="none", alpha=1.0, pad=1.0))
        elif r > 0:
            ax.text(x, 102.5, f"{r:g}% rescued", ha="center", va="bottom",
                    fontsize=8, color="#1c5cab")
    ax.set_xticks(xs); ax.set_xticklabels(V["vendors"], fontsize=8.5)
    ax.set_ylim(0, 112); ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel("% of 300 records", fontsize=8.5)
    ax.axhline(100, color=BASE, lw=0.7, ls=(0, (2, 2)))
    ax.grid(axis="y", color=GRID, lw=0.5); ax.set_axisbelow(True)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.0), ncol=2, fontsize=8,
              frameon=False, handlelength=1.4, columnspacing=1.2)
    fig.tight_layout(pad=0.5)
    fig.savefig(os.path.join(OUT, "fig24_xvendor_twolayer.pdf"))
    plt.close(fig)


# ------------------------------------------------------- fig25 evidence pipeline
def fig25():
    fig, ax = plt.subplots(figsize=(5.15, 4.05))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.text(0.30, 0.985, "Judged branch (all 9 systems)", ha="center", fontsize=8.5,
            fontweight="bold", color=INK)
    ax.text(0.8025, 0.985, "Provenance branch\n(MANDATE artifacts only; baselines emit no chains)",
            ha="center", fontsize=8.2, fontweight="bold", color=INK, va="top")
    steps = ["150 frozen tasks (120 main + 30 hold-out)",
             "10,800 main records (120 \u00d7 9 \u00d7 10)\n+ 1,200 hold-out records (30 \u00d7 4 \u00d7 10)",
             "12,000 anonymized graded outputs",
             "3 judges \u00d7 12,000 = 36,000 retained judge records",
             "12,000 ensemble aggregates\n(0 reconciliation mismatches)",
             "120 task means per system\n\u2192 24 task-clustered contrasts",
             "claim tables and figures"]
    y = 0.90; h = 0.104; gap = 0.018
    for i, s in enumerate(steps):
        box(ax, 0.05, y - h, 0.50, h, s, fs=8.0,
            fc="#e8f0fb" if i in (3, 4) else "#f4f4f2",
            ec=BLUE if i in (3, 4) else BASE)
        if i < len(steps) - 1:
            arrow(ax, 0.30, y - h, 0.30, y - h - gap + 0.003)
        y -= (h + gap)
    dsteps = ["5,680 campaign chains\n(3,000 canonical + 1,480 primary\n+ 1,200 cross-vendor)",
              "34,080 campaign entries",
              "+ 3,000 successor chains\n\u2192 18,000 entries",
              "52,080 core campaign + successor\nentries: entry, parent, chain,\nanchor digests recomputed (Sect. 6.3)",
              "declared source-of-record scope:\n100,500 entries across 17,050 artifacts\n(derived copies + legacy pilot excluded)"]
    y = 0.86; h2 = 0.125; gap2 = 0.028
    for i, s in enumerate(dsteps):
        last = (i == len(dsteps) - 1)
        box(ax, 0.615, y - h2, 0.375, h2, s, fs=8.0,
            fc="#e8f0fb" if last else "#f4f4f2", ec=BLUE if last else BASE)
        if i < len(dsteps) - 1:
            arrow(ax, 0.8025, y - h2, 0.8025, y - h2 - gap2 + 0.003)
        y -= (h2 + gap2)
    fig.tight_layout(pad=0.4)
    fig.savefig(os.path.join(OUT, "fig25_evidence_pipeline.pdf"))
    plt.close(fig)


if __name__ == "__main__":
    fig20(); fig21(); fig22(); fig23(); fig24(); fig25()
    print("figures written to", OUT)
