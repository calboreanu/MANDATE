# code/figure_scripts — figure generation and verification tooling

This is the canonical figure and verification tree for the study snapshot
included in the MANDATE v2.0.3 publication release. Run everything from the
study root (`studies/2026q2/` in the repository).

| File | What it is |
|---|---|
| `extract_fig_data.py` | Extracts `fig_source_extract.json` (per-task ensemble means) from the release grading set. Deterministic: regenerates byte-identically. |
| `fig_source_extract.json` | The extracted per-task means consumed by `make_figures.py`. |
| `main_only_coverage.json` | Main-corpus-only coverage means (extract byproduct). |
| `fig_constants.json` | Transcribed release constants with provenance notes (measured full-coverage reliability is the live posture; sampled v1 values are halt history). |
| `make_figures.py` | Regenerates the manuscript's empirical figures from the two JSON inputs. Creates its output directory; renders the measured-reliability figure. Usage: `python3 code/figure_scripts/make_figures.py <outdir>`. |
| `fig2_standalone.tex` | Standalone TikZ source for the routing-flow figure (successor-gate annotation). |
| `verify_trace_hashes_full.py` | Trace-hash verifier over **every trace-bearing artifact in the deposit** (campaign, cross-vendor, successor check, perturbations, A3/A5 ablations, ablation-MVP incl. its canonical run). Expected from a fresh clone: 17,050 artifacts; 100,500/100,500 entry hashes; 83,600/83,600 parent links; 16,900/16,900 chain digests; 17,050/17,050 anchor hashes; 150 deliberately empty traces (the A6 no-search-trace ablation); exit 0. The artifact-level `metadata.output_hash`/`input_hash` are carried values from the proprietary core and are not recomputed (manuscript §4.2). |
| `trace_hash_report.json` | Committed machine-readable report from running the verifier against this release's public tree. |
| `compute_reliability.py` | Full-coverage inter-judge reliability (Krippendorff α, closed-form) from the three retained judge streams (3 × 12,000). |
| `full_coverage_reliability.json` | Committed output of `compute_reliability.py` against this release. |
| `requirements.txt` | Pinned plotting dependency. |

Both verification scripts are invoked, with hard expected-value assertions,
by the targeted release-integrity verifier
(`code/scripts/verify_study_release.py`).
