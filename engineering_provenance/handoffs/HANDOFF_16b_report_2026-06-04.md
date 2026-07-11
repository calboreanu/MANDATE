# Handoff 16b Report: Demo re-run from original source binaries

**Codex session:** Handoff 16b resume after 16 halt
**Eval host:** lattice-ws01
**Date:** 2026-06-04
**Wall clock:** 9.4 minutes total across the three Ollama runs

## Verdict

HALT

## Evidence

- HANDOFF_16 halt resolved (python-docx/pptx not required for runtime): yes
- from-binaries indexes verified:           volt=2093 crwd=413 svb=619
- pypdf / python-docx / python-pptx:        pypdf=6.12.2 / python-docx not checked by 16b / python-pptx not checked by 16b
- Volt Typhoon run ok / wall_clock_ms:      True / 166678.112
  - all_llm_used / any_llm_fallback:        True / False
  - procedure.rag_retriever_wired:          True
  - n_coas / coa1_name:                     1 / Minimal manual assessment approach
- CrowdStrike run ok / wall_clock_ms:       True / 172030.647
  - all_llm_used / any_llm_fallback:        True / False
  - procedure.rag_retriever_wired:          True
  - n_coas / coa1_name:                     1 / Minimal manual assessment approach
- SVB collapse run ok / wall_clock_ms:      True / 215105.7711
  - all_llm_used / any_llm_fallback:        True / True
  - procedure.rag_retriever_wired:          True
  - n_coas / coa1_name:                     1 / Minimal manual assessment approach
  - fallback role / reason:                 Binding / LLM response parsing failed after 3 attempt(s): schema validation failed: 'decision_summary' is a required property
- llm_defaults.json restored (no git diff): yes

## Cross-domain single-COA finding under binary-sourced inputs

Not reaffirmed as a valid handoff conclusion because the SVB from-binaries run tripped the required no-fallback gate. The raw from-binaries artifacts do show `n_coas=1` in all three scenarios, but the SVB artifact was produced with a Binding-role fallback, so the full three-scenario comparison is invalid under the Handoff 16b decision boundary.

## Validator gap-acknowledgment delta

Not assessed. Task 5 comparison was not run because Handoff 16b requires stopping on any `any_llm_fallback=True` condition. The raw from-binaries validator rationales are preserved in the RunRecords for follow-up, but they should not be used for the planned prior-vs-binary comparison until the SVB Binding fallback is resolved.

## SVB anchor distillation delta

Not assessed as a final comparison because the SVB RunRecord has `any_llm_fallback=True`. The raw SVB from-binaries anchor minimum is 247 characters and is cleaner than the earlier deterministic-prefix shape, but this should be treated as provisional until the no-fallback success criterion passes.

## Anything the PI must decide before proceeding

- Decide whether to rerun SVB only after investigating the Binding role parse failure, or rerun all three scenarios for a clean synchronized comparison.
- Inspect the SVB Binding output path: `demo/svb_collapse/output_ollama_from_binaries/mandate_primary__TASK-DEMO-SVB-001__r01.json`; the recorded fallback reason is `schema validation failed: 'decision_summary' is a required property`.
- Do not update `demo/MANDATE_DEMO_FINDINGS.md` or `demo/UPSTREAM_MANDATE_NOTE_decomposition_bias.md` from this 16b run until the no-fallback gate passes or the PI explicitly accepts fallback-contaminated evidence.

## Deviations from this handoff

- The first verbatim Volt swap used `llm_rag_index='demo/volt_typhoon/rag/volt_typhoon__from_binaries.jsonl'` and failed before any Ollama run because the apparatus resolves relative `llm_rag_index` values under `--aegis` (`./AEGIS-eval/demo/...`). `llm_defaults.json` was restored immediately and no artifact was written.
- The three successful swap-and-run blocks used absolute `llm_rag_index` paths to the same from-binaries indexes. This is functionally equivalent to the handoff's intended target paths and was necessary because of the apparatus path-resolution behavior.
- Stopped before Task 5 comparison after SVB reported `any_llm_fallback=True` for the Binding role. No comparison table was produced.
