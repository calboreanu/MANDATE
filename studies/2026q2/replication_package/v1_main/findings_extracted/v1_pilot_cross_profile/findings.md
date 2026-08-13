# v1 Pilot Cross-Profile Findings (April 2026)

**Source:** `~/Desktop/AEGIS/logs/` (15 profile-runs across April 13–14, 2026)
**Apparatus:** `~/Desktop/AEGIS/scripts/ab_evaluation.py` with `--profiles deterministic,base,tuned`
**Corpus:** `authorized_lab_manifest.json` (6 cases, all pentest domain)
**Status:** Pilot-tier evidence, N=6 per profile. Predates the 2026Q2 main-corpus evaluation by ~6 weeks. Cited here as historical baseline; not a substitute for v2 multi-vendor Cond-B.

## Three-profile comparison (canonical run, 2026-04-13/14)

| Profile | n_ok / n_cases | check pass % | avg duration (s) | avg COAs | avg gaps | LLM roles active |
|---|---:|---:|---:|---:|---:|---:|
| `deterministic` | 5 / 6 | 100.0 | 0.0 | 1.50 | 1.5 | 0 |
| `base` (Qwen3-32b + Qwen3-8b, untuned, Ollama) | 5 / 6 | 90.5 | 79.7 | 1.17 | 3.2 | 2 |
| `tuned` (mandate-* fine-tuned roles on Qwen3) | 5 / 6 | 92.9 | 101.2 | 1.17 | 3.7 | 3 |

## Key observations

1. **Pipeline ok rate is constant across all three profiles at 5/6 (83.3%).** The deterministic apparatus completes 5 of 6 authorized_lab cases. Adding LLM augmentation (base or tuned) does not change this. One specific case fails structurally across all configurations.

2. **LLM augmentation initially DEGRADES check pass rate before iteration recovers it.** Deterministic achieves 100% check pass. Base Qwen3 drops to 90.5% (-9.5pp). Initial tuned reaches 92.9% (still -7.1pp below deterministic). Iteration cycles eventually return tuned to 100% (see iteration history below).

3. **LLM augmentation adds significant per-case latency.** Deterministic: 0s. Base: +79.7s. Tuned: +101.2s. Tuned is ~25% slower than base — consistent with fine-tuned roles doing more thorough reasoning chains.

4. **LLM modes produce FEWER COAs than deterministic.** Deterministic 1.50 → base/tuned 1.17. This is the first observation of the LLM-augmented Decomposition under-producing COAs relative to the deterministic templated path. Predates the 2026Q2 main-matrix "single-COA prior" finding (which is the canonical fallback path in the absence of structured input).

5. **LLM modes produce MORE gap reports.** Deterministic 1.5 → base 3.2 → tuned 3.7. LLM-augmented modes detect ~2–2.5x more gaps than the rule-based deterministic path. Tuned slightly more than base.

## Tuned iteration history (apparatus-side fix cycle)

Six iteration snapshots on the same 6-case corpus, showing how apparatus-side fixes recovered the tuned profile from its initial 92.9% check pass rate up to 100%:

| Iteration | Check pass % | Notes |
|---|---:|---|
| Initial tuned | 92.9 | Baseline tuned run |
| After intake fix | 100.0 | First role-level patch — recovers fully |
| After interpreter fix | 100.0 | Second role-level patch — holds |
| After interpreter compaction (bad) | 95.2 | Regression: model-compaction broke something |
| Restored after bad compaction | 100.0 | Rollback recovers |
| After binding compaction | 100.0 | Subsequent compaction held |
| After procedure prompt | 100.0 | Final tuned baseline at 100% check pass |

The iteration shows two things: (a) apparatus-side fixes can recover LLM-augmented pass rate to deterministic-level, (b) model compaction (quantization / size reduction) can introduce regressions and needs validation.

## Models / backends used

```
Backend:       Ollama (local)
Models:        qwen3:8b, qwen3:32b (base profile)
               mandate-intake, mandate-interpreter, mandate-decomp,
               mandate-procedure, mandate-binding, mandate-validation (tuned profile)
               (Qwen3-32b fine-tunes via PEFT adapters)
```

**Other LLM families NOT tested in this pilot:** Claude (Anthropic), GPT-4o / GPT-5 (OpenAI), Gemini (Google), Llama (Meta), Mistral, Gemma. These are scheduled for v2 multi-vendor Cond-B per HANDOFF_22 (forthcoming).

## What this data establishes — and what it does not

### Citable as v1 historical evidence

- **The profile axis (deterministic / base / tuned) was tested at pilot N=6 before main-matrix evaluation.** This was not the first measurement.
- **Tuning vs base helps on check pass rate** (+2.4pp on initial run, more after fixes).
- **Apparatus-side iteration cycles matter** — small fixes moved metrics significantly.
- **Single-vendor (Qwen3 via Ollama) cross-profile delta exists empirically.**

### Does NOT establish

- **Cross-vendor variance** — no Claude / GPT / Gemini / Llama / Mistral / Gemma profiles in this data.
- **Multi-domain robustness** — all 6 cases are pentest domain.
- **Statistical contrast at scale** — N=6 per profile is qualitative, not inferential.
- **2026Q2 corpus performance** — different corpus (authorized_lab vs source-conditioned 120/30).

## How this fits into the v2 evaluation

The April 2026 pilot answers the within-vendor question ("does tuning Qwen3 help over base Qwen3 on a small pentest corpus?"). The v2 multi-vendor Cond-B (forthcoming HANDOFF_22) answers the between-vendor question ("does the LLM family driving canonical MANDATE matter for outcomes across the 150-task corpus?"). These are complementary; the pilot motivates the larger study by showing that profile selection does materially affect MANDATE behavior.

## Data files in this directory

- `findings.md` — this document
- `profile_aggregates.json` — extracted per-profile aggregates from all 15 logs

## Source files (original logs preserved in `~/Desktop/AEGIS/logs/`)

```
authorized_lab_eval_deterministic.json                                        (2026-04-13)
authorized_lab_eval_base.json                                                  (2026-04-13)
authorized_lab_eval_tuned.json                                                 (2026-04-13)
authorized_lab_eval_base_after_intake_fix.json                                 (2026-04-13)
authorized_lab_eval_tuned_after_intake_fix.json                                (2026-04-13)
authorized_lab_eval_authorized_lab_base_2026-04-14.json                        (2026-04-14)
authorized_lab_eval_authorized_lab_tuned_after_procedure_prompt_2026-04-14.json (2026-04-14)
authorized_lab_eval_authorized_lab_tuned_after_intake_fix_2026-04-14.json      (2026-04-14)
authorized_lab_eval_authorized_lab_tuned_after_interpreter_fix_2026-04-14.json (2026-04-14)
authorized_lab_eval_authorized_lab_tuned_after_interpreter_compaction_2026-04-14.json (2026-04-14)
authorized_lab_eval_authorized_lab_tuned_after_binding_compaction_2026-04-14.json (2026-04-14)
authorized_lab_eval_authorized_lab_tuned_restored_after_bad_interpreter_compaction_2026-04-14.json (2026-04-14)
authorized_lab_eval_safe_scan_tuned_after_procedure_prompt_2026-04-14.json     (2026-04-14)
authorized_lab_eval_authorized_lab_2026-04-14.json                             (2026-04-14, two-profile aggregate)
```
