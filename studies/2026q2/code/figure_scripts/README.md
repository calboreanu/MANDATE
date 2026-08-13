# Manuscript figure reproduction

These scripts generate the evidence-communication figures from the published
MANDATE study data. Paths are resolved from the scripts' installed location, so
the commands may be run from the repository root after checking out
`study-release-2026.08.13`.

## Re-extract source data

```bash
python3 studies/2026q2/code/figure_scripts/extract_fig_data.py \
  > /tmp/fig_source_extract.json
cmp /tmp/fig_source_extract.json \
  studies/2026q2/code/figure_scripts/fig_source_extract.json
```

The extractor is Python-standard-library only. It reads the retained
12,000-record ensemble file and its anonymization mapping, restricts the task
plots to the 120-task main corpus, and recomputes the per-task and per-domain
means.

## Render figures

```bash
python3 -m venv /tmp/mandate-figures-venv
source /tmp/mandate-figures-venv/bin/activate
python3 -m pip install -r \
  studies/2026q2/code/figure_scripts/requirements.txt
python3 studies/2026q2/code/figure_scripts/make_figures.py \
  /tmp/mandate-figures
```

The command writes six vector PDFs. `fig_constants.json` identifies the exact
release tables and analysis files from which non-record constants were taken;
`fig_source_extract.json` is the deterministic extractor output used by the
paired-task and domain exhibits.
