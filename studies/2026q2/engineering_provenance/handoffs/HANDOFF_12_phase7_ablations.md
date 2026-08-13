# Codex Handoff 12: Phase 7 Ablation Runs

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-03
**Estimated wall clock:** **tens to hundreds of hours**, gated on which ablations have upstream tags.
**Blocked on:** `outputs_freeze_v1`, upstream MANDATE variant tags for A1, A2, A4, A6, A7 (TO_FILL D11). A3 and A5 (config switches) run today from AEGIS-eval without upstream work.

## Mission

Run each ablation A1 through A7 on the 30-task ablation subset at 10 runs each (2,100 RunRecords total), capture every record into the run ledger, anonymize the outputs alongside the Phase 6 set. PROTOCOL_LOCK Section 5 designates A1, A2, A3 as primary ablations (main paper); A4 through A7 as secondary (supplement).

**Definition of done.** RunRecords for every available ablation at `07_system_outputs/ablation_<id>/`. Variants whose `aegis_ref` is empty raise `AblationNotReadyError` and Codex reports that ablation as skipped rather than silently substituting MANDATE-primary. `ablation_freeze_v1` tag once every available ablation has run.

## Tasks

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# A3 and A5 (config switches): no upstream needed
for A in ablation_a3 ablation_a5; do
  python3 -m apparatus.run run-system \
    --system $A \
    --aegis ./AEGIS-eval --ollama-mode \
    --code-ref mandate-eval-primary-2026q2-v1 \
    --tasks 04_ground_truth/ablation_subset.jsonl \
    --runs 10 --output 07_system_outputs/$A
done

# A1, A2, A4, A6, A7 require upstream AEGIS variant tags. For each, the
# upstream team has built `AEGIS-eval-<id>/` and `apparatus/ablations/
# manifest.py` has its `aegis_ref` set. If the manifest entry is empty,
# the run will raise AblationNotReadyError; record the skip and continue.
for A in ablation_a1 ablation_a2 ablation_a4 ablation_a6 ablation_a7; do
  VARIANT_SRC="./AEGIS-eval-${A#ablation_}/src"
  if [ -d "$VARIANT_SRC" ]; then
    python3 -m apparatus.run run-system \
      --system $A \
      --aegis ./AEGIS-eval --ollama-mode \
      --variant-src "$VARIANT_SRC" \
      --tasks 04_ground_truth/ablation_subset.jsonl \
      --runs 10 --output 07_system_outputs/$A
  else
    echo "SKIP $A (variant src not present)"
  fi
done

# Re-anonymize so the ablation outputs join the anonymized set
python3 -m apparatus.run anonymize \
  --in 07_system_outputs \
  --out 08_grading/anonymized_outputs \
  --mapping-path 07_system_outputs/anonymization_mapping.json \
  --seed 20260601

git tag -a ablation_freeze_v1 -m "Phase 7 ablations frozen"
```

## Report

`handoffs/HANDOFF_12_report_<YYYY-MM-DD>.md` with: per-ablation run count and skip list, the mean MANDATE-primary anchor delta vs each ablation on the calibration sample, ablation_freeze_v1 tag confirmed. Commit per-ablation, final commit `Handoff 12: Phase 7 ablations frozen`.
