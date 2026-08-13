# Handoff 01 Report: MANDATE Verification

**Codex session:** Handoff 01 eval-host verification session
**Eval host:** lattice-ws01
**Date:** 2026-06-03
**Wall clock:** 18 minutes

## Verdict

PROCEED

## Evidence

- A1 verification:                   PASS
- Apparatus unit suite:              195/195
- Deterministic smoke:               PASS
- AEGIS-eval commit captured:        4f8af83d12ef1ffdedcf7c5f53a0f9a2c062b06f
- AEGIS-eval tag captured:           mandate-eval-primary-2026q2-v1
- Ollama version:                    0.21.1
- Six mandate-* SHA-256 digests:     listed in provenance_evidence.md
- Any role with llm_fallback=True:   none

## Anything the PI must decide before proceeding

- D10 remains a PI sign-off item before pre-registration deposit: accept the frozen AEGIS per-role temperatures or require a temperature-0 override. No apparatus change was made.

## Deviations from this handoff

- `setup/run_a1_verification.sh` wrote `A1_verification_report.json`, not the handoff-named `a1_report.json`; the emitted report records `verdict: PASS`, 6/6 passing runs, all six roles on fine-tuned models, no fallback, and 6/6 anchor contrasts.
- `setup/capture_provenance.sh --aegis ./AEGIS-eval` initially recorded `./AEGIS-eval` as not a git repository because the frozen tree is a `git archive` extraction. I added the frozen tag/commit from `AEGIS-eval/_AEGIS_EVAL_README.txt` and the resolved decoding parameters from `AEGIS-eval/configs/llm_defaults.json` to `provenance_evidence.md`; no setup script or apparatus source was edited.
- The project root had no `.git` repository when the commit step began; I initialized Git in the project root before committing this report, consistent with the pending `git init` note in `README.md`.
