# Handoff 17 Report: Binding structured-refusal apparatus patch

**Codex session:** Handoff 17 precondition verification
**Eval host:** lattice-ws01
**Date:** 2026-06-04
**Wall clock:** 5 minutes

## Verdict

HALT

## Evidence

- branch created off frozen tag:           no; `feature/binding-refusal-as-gap` was not created
- frozen tag unchanged:                    yes; no tag operation was attempted
- response_parser.py patch applied:        no
- llm_support.py patch applied:            no
- binding.py patch applied:                no
- pipeline.py gap injection applied:       no
- unit tests created:                      no
- unit tests passing:                      not run
- apparatus suite still passes:            not run
- SVB v2 run:
  - any_llm_fallback:                      not run
  - Binding llm_used:                      not run
  - Binding llm_fallback:                  not run
  - n_gap_reports:                         not run
  - binding-attributed gap_reports:        not run
  - first 200 chars of recommendation.rationale:
    not run
- Volt Typhoon v2 sanity:
  - any_llm_fallback:                      not run
  - binding-attributed gap_reports:        not run
- CrowdStrike v2 sanity:
  - any_llm_fallback:                      not run
  - binding-attributed gap_reports:        not run

## What the patch changes for the formal study

Nothing. The patch was not implemented because Task 1 preconditions failed before branch creation. No source, prompt, config, model, tag, or demo artifact was modified.

## What the patch changes for the demo

Nothing. No v2 demo run was executed.

## Anything the PI must decide before proceeding

- Provide or restore an `AEGIS-eval` git checkout where `git -C AEGIS-eval tag --list "mandate-eval-primary*"` includes `mandate-eval-primary-2026q2-v1`.
- Clarify whether `AEGIS-eval` is intended to be a separate nested git repository or whether the top-level project repo is the authoritative AEGIS-eval repo. In this checkout, `git -C AEGIS-eval rev-parse --show-toplevel` resolves to `/Users/ws01admin/Desktop/MANDATE Evaluation/mandate_eval_2026Q2`, not to `/Users/ws01admin/Desktop/MANDATE Evaluation/mandate_eval_2026Q2/AEGIS-eval`.
- Once the frozen tag is locally present and the intended git boundary is clear, rerun Handoff 17 from Task 1.

## Deviations from this handoff

- Stopped during Task 1. The command `git -C AEGIS-eval tag --list "mandate-eval-primary*"` returned no tags, so the required frozen tag was not locally available.
- Did not run `git checkout mandate-eval-primary-2026q2-v1`, did not create `feature/binding-refusal-as-gap`, and did not edit apparatus code.
- Did not run unit tests, the apparatus suite, or any v2 demo verification runs.
