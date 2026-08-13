# Codex Handoff 14: Phase 9 Analysis Notebooks

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-03
**Estimated wall clock:** 30 to 90 minutes (mostly Notebook 04 mixed-effects fitting and Notebook 05 Bayesian sampling, if installed).
**Blocked on:** Phase 8 grading complete, MANDATE_STRONGEST_BASELINE selected (pre-registered designation).

## Mission

Execute analysis notebooks 01 through 10 end to end against the now-real Phase 6/7/8 data. Each notebook is a thin driver over the unit-tested apparatus analysis modules; they run automatically once their phase inputs exist. Phase 9 fits the primary hypothesis tests (Notebook 04), the Bayesian supplementary (05), exploratory and subgroup (06), sensitivity (07), ablation (08), failure modes (09), and the final tables and figures (10).

**Definition of done.** Every notebook executes cleanly (no Python error other than the gated-skip notebooks 03 + others where data still missing), each notebook's per-result JSON is written under `09_analysis/`, the figures land in `09_analysis/figures/` as SVG and PNG, the final tables in `09_analysis/10_final_tables.json` are populated.

## Tasks

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# Install heavier deps if needed (these are in environment.yml but may
# not be present in a minimal venv)
pip install nbconvert nbformat ipykernel
pip install bambi pymc arviz   # Notebook 05 Bayesian supplementary

# Set the pre-registered strongest baseline so Notebook 04 fires
export MANDATE_STRONGEST_BASELINE=baseline_1   # or whichever the PI pinned

# Execute every notebook in place
python3 -m apparatus.run run-analysis \
  --notebooks 09_analysis \
  --cell-timeout 600
```

The runner executes notebooks in alphabetical order and overwrites each `.ipynb` with the executed result. A notebook that gracefully prints its gated-skip block is treated as success; a hard exception is a failure and the runner reports it.

## Sanity

```zsh
python3 -c "
import json, glob, os
results = sorted(glob.glob('09_analysis/*_result*.json'))
for r in results:
    print(os.path.basename(r), os.path.getsize(r), 'bytes')
print('figures:')
for f in sorted(glob.glob('09_analysis/figures/*.svg')):
    print(' ', os.path.basename(f))
"
```

## Report

`handoffs/HANDOFF_14_report_<YYYY-MM-DD>.md` with: per-notebook verdict (PASS/FAIL/SKIP-gated), primary hypothesis verdicts from Notebook 04 (H1 through H5: confirmed / statistically-significant-operationally-marginal / not significant), IRR from Notebook 01, fallback rate from Notebook 02, ablation effects from Notebook 08, headline failure-mode distribution from Notebook 09. Commit `Handoff 14: Phase 9 analysis`.
