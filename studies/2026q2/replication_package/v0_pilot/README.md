# v0_pilot — April 2026 Pilot Evidence (T2)

The data behind the paper's §12 Tier-1 pilot tables (and supplement §1.1).

- `eval_results/` — the deterministic evaluation JSONs + logs backing the
  500-test static suite (99.8% pass) and the 8-scenario deterministic run
  (32/32 structural property checks).
- `live_runs/` — the 8 paper-derived scenarios and LLM-mode artifacts
  (40/48 role invocations via LLM, 8 deterministic fallbacks; trace
  completeness held on every run).
- `aegis_eval_results.tar.gz` — packaged static-suite results.
- `paper_section_12_tables/` — the three LaTeX tables exactly as reproduced
  in the paper/supplement (`tab_static-eval`, `tab_det-vs-llm`,
  `tab_llm-run`).
- `PROGRESS_LOG.md`, `LATEX_TABLES.md` — authoring provenance.

Note: the AEGIS reference implementation itself is proprietary and is not
redistributed; these artifacts are its evaluation outputs. See
`prior_published_paper/CITATION_TO_PAPER.md`.
