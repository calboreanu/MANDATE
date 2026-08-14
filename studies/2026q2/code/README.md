# code/ — Evaluation Apparatus Snapshot

- `apparatus/` — the evaluation harness: adapters for the six MANDATE pipeline
  roles plus the Cond-A extraction stage,
  baseline shells (B1–B6), perturbation generator, three-judge grading
  (`grade-v2`, shape-neutral v2 rubric, per-record checkpointing with
  `--skip-existing` resume), anonymization, and analysis helpers. Snapshot of
  the tree that produced every record in `replication_package/`; upstream
  apparatus tag `mandate-eval-primary-2026q2-v1` (commit `4f8af83`).
- `scripts/` — the run orchestrators used in production: cross-vendor Cond-B
  (`run_handoff22_xvendor.py`), ablations (`run_handoff23_ablations.py`),
  perturbation runs (`run_handoff24_perturbations.py`), parallel Phase B
  generation+grading (`run_handoff24b_parallel.py`, includes the provider
  probe gate), the Stage-4 resume daemon, and the all-ablations MVP runner
  (`run_ablation_mvp.py`).

Environment: Python 3.12.12 (see `docs/ENVIRONMENT.md`; note the
`environment.yml` 3.11 pin discrepancy documented there). MANDATE-primary
fine-tunes are served via local Ollama and are referenced by the upstream
tag, not redistributed. API-backed systems require ANTHROPIC_API_KEY,
OPENAI_API_KEY, GOOGLE_API_KEY in `.env` (never commit it).

The canonical MANDATE implementation under test is `mlt-stack 1.0.0rc1`
(not vendored here; the stack repo has since advanced to v1.0.3 — replicate
against 1.0.0rc1).
