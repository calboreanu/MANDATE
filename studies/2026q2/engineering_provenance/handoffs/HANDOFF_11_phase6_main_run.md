# Codex Handoff 11: Phase 6 Main Run + Anonymization

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-03
**Estimated wall clock:** **hundreds of hours of compute**, mostly Ollama 32B inference for MANDATE-primary. Run in segments; never expect this in one bash call.
**Blocked on:** `corpus_freeze_v1`, `gt_freeze_v1`, `baseline_freeze_v1`, pre-registration deposited on Zenodo, PI written approval (PROTOCOL_LOCK Section 13).

## Mission

Execute Phase 6: run every pre-registered system over the corpus at the pre-registered run counts, capture every RunRecord into the run ledger, anonymize the outputs for Phase 8 grading. This is the substantive data-collection step the entire protocol exists to support.

Per PROTOCOL_LOCK Section 2 and Section 6.3:

- MANDATE-primary on the 120 main tasks at 10 runs each.
- Baselines B1 through B6 on the 120 main tasks at 10 runs each.
- MANDATE-primary and baselines on the 350-perturbation suite at 5 runs each.
- 5 alternative MANDATE backends on the 30-task ablation subset at 10 runs each.
- 30 hold-out tasks: MANDATE-primary and the designated strongest baseline at 10 runs each.
- 1 human-expert upper bound on 30 tasks at 1 run.

**Definition of done.** Every RunRecord persisted under `07_system_outputs/<system_id>/`, every record carrying the per-role `llm_used` and `llm_fallback` flags, anonymized copies written to `08_grading/anonymized_outputs/` with the identity mapping at `07_system_outputs/anonymization_mapping.json` (gitignored). `outputs_freeze_v1` tag.

## Tasks

The full Phase 6 matrix is too large for one bash invocation. Run each system in its own session. Resume by re-running the same command; the harness ledger is append-only and re-runs overwrite same-id RunRecord files harmlessly.

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# MANDATE-primary, Ollama mode, fine-tuned six-role pipeline
python3 -m apparatus.run run-system \
  --system mandate_primary \
  --aegis ./AEGIS-eval \
  --ollama-mode \
  --code-ref mandate-eval-primary-2026q2-v1 \
  --tasks 04_ground_truth/main_tasks.jsonl \
  --runs 10 \
  --output 07_system_outputs/mandate_primary

# Each baseline B1-B6 on the main corpus
for B in baseline_1 baseline_2 baseline_3 baseline_4 baseline_5 baseline_6; do
  python3 -m apparatus.run run-system \
    --system $B --tasks 04_ground_truth/main_tasks.jsonl \
    --runs 10 --output 07_system_outputs/$B
done

# Perturbation runs (MANDATE-primary and baselines, 5 runs each)
for SYS in mandate_primary baseline_1 baseline_2 baseline_3 baseline_4 baseline_5 baseline_6; do
  python3 -m apparatus.run run-system \
    --system $SYS \
    --aegis ./AEGIS-eval --ollama-mode \
    --tasks 06_perturbations/perturbation_suite.jsonl \
    --runs 5 \
    --output 07_system_outputs/$SYS/perturbations
done

# Hold-out runs (MANDATE-primary + strongest baseline)
python3 -m apparatus.run run-system \
  --system mandate_primary --aegis ./AEGIS-eval --ollama-mode \
  --tasks 04_ground_truth/holdout_tasks.jsonl \
  --runs 10 --output 07_system_outputs/mandate_primary/holdout
python3 -m apparatus.run run-system \
  --system "$STRONGEST_BASELINE" \
  --tasks 04_ground_truth/holdout_tasks.jsonl \
  --runs 10 --output 07_system_outputs/$STRONGEST_BASELINE/holdout

# Anonymize after every system has run
python3 -m apparatus.run anonymize \
  --in 07_system_outputs \
  --out 08_grading/anonymized_outputs \
  --mapping-path 07_system_outputs/anonymization_mapping.json \
  --seed 20260601

# Tag the freeze
git tag -a outputs_freeze_v1 -m "Phase 6 outputs frozen"
```

## Report

`handoffs/HANDOFF_11_report_<YYYY-MM-DD>.md` with: per-system run count, completion rate, MANDATE fallback rate, total compute hours, anonymization integrity check, `outputs_freeze_v1` tag confirmed. Commit incrementally per system; final commit after the freeze tag with `Handoff 11: Phase 6 outputs frozen`.
