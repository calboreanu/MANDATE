# v0_5_pilot — April 2026 Cross-Profile Pilot (T3)

The data behind supplement §6.7: the 6-case `authorized_lab` pentest corpus
run under three LLM configurations (deterministic, Qwen3-base, Qwen3-tuned),
showing the same 5/6 ok-rate across configurations — early evidence that the
framework, not the model, is the controlled variable.

- `logs/` — 41 JSON artifacts: `AUTHLAB-RUN-001_*` raw run logs,
  `authorized_lab_eval_*` cross-profile evaluation outputs, and
  `adapter_manifest_*` LoRA adapter manifests (rank/alpha/seed provenance for
  the Qwen3 fine-tunes).

The cross-profile aggregates are quoted in the supplement; the raw logs here
are the source. The fine-tuned model weights are referenced by the upstream
apparatus tag (`mandate-eval-primary-2026q2-v1`, commit `4f8af83`) and are
not redistributed.
