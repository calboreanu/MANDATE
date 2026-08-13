# Handoff 16 Report: Demo re-run from original source binaries

**Codex session:** Handoff 16 precondition verification
**Eval host:** lattice-ws01
**Date:** 2026-06-04
**Wall clock:** 2 minutes total across the three Ollama runs (0 minutes run time; halted before Task 2)

## Verdict

HALT

## Evidence

- from-binaries indexes verified:           volt=2093 crwd=413 svb=619
- pypdf / python-docx / python-pptx:        pypdf=6.12.2 / python-docx missing (`ModuleNotFoundError: No module named 'docx'`) / python-pptx missing (`ModuleNotFoundError: No module named 'pptx'`)
- Volt Typhoon run ok / wall_clock_ms:      not run / not run
  - all_llm_used / any_llm_fallback:        not run / not run
  - n_coas / coa1_name:                     not run / not run
- CrowdStrike run ok / wall_clock_ms:       not run / not run
  - all_llm_used / any_llm_fallback:        not run / not run
  - n_coas / coa1_name:                     not run / not run
- SVB collapse run ok / wall_clock_ms:      not run / not run
  - all_llm_used / any_llm_fallback:        not run / not run
  - n_coas / coa1_name:                     not run / not run
- llm_defaults.json restored (no git diff): yes

## Cross-domain single-COA finding under binary-sourced inputs

Not assessed. Handoff 16 halted during Task 1 because `python-docx` and `python-pptx` are not importable in the project venv. No `output_ollama_from_binaries/` RunRecords were produced, so the cross-domain single-COA finding is neither reaffirmed nor invalidated by this session.

## Validator gap-acknowledgment delta

Not assessed. No from-binaries Ollama runs were started, so there are no new validator rationale strings to compare against the prior `output_ollama/` artifacts.

## SVB anchor distillation delta

Not assessed. No SVB from-binaries RunRecord was produced, so there is no new anchor text to compare against the prior deterministic-prefix shape.

## Anything the PI must decide before proceeding

- Install the missing extractor dependencies in the project venv (`python-docx` and `python-pptx`) or approve an equivalent environment repair, then rerun Handoff 16 from Task 1.
- After the imports pass, proceed with the three swap-and-run blocks and the binary-sourced comparison report.

## Deviations from this handoff

- Stopped during Task 1 after the extractor-library import check failed. No config swap, no Ollama run, no RunRecord generation, no comparison table, and no edits to `AEGIS-eval/configs/llm_defaults.json` occurred.
- Verified that Ollama was reachable at `http://localhost:11434` and that all six `mandate-*` role models were loaded before the library import failure was recorded.
