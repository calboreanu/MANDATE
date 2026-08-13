# Codex Handoff 08: Hold-Out Corpus (30 tasks, 4th domain)

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-03
**Estimated wall clock:** 30 to 60 minutes (source build + ~90 generations).
**Blocked on:** PI confirms the hold-out 4th domain (default: `software_engineering_specification` per Decisions memo Section 1); Anthropic balance at least $5.

## Mission

Generate the 30-task hold-out corpus in the 4th domain via the same source-first pipeline used for the main corpus (PROMPTS Section 1, source-conditioned). The hold-out domain is outside the four MANDATE training-corpus domains and outside the three main evaluation domains, so a hold-out evaluation here tests generalization.

**Definition of done.** A deduped hold-out pool at `03_corpus/holdout/candidates_holdout.jsonl` with at least 35 candidates (allowing PI selection of 30 with slack), every candidate carrying `derived_from`, leakage at or below 5%.

## Tasks

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# 1. build the hold-out domain source index
python3 -m apparatus.corpus.cli source-build \
  --domain software_engineering_specification \
  --project-root "$PWD" \
  --out rag/embeddings/build_report_holdout.json

# 2. generate candidates: 3 categories x 15 chunks each = 45 candidates
mkdir -p 03_corpus/holdout 03_corpus/candidates_source_first_holdout
SEED=20260603
for CAT in full_specification gap_triggering stretch_case; do
  python3 -m apparatus.corpus.cli source-generate \
    --domain software_engineering_specification \
    --category $CAT --n-chunks 15 --seed $SEED \
    --project-root "$PWD" \
    --out 03_corpus/candidates_source_first_holdout
  SEED=$((SEED+1))
done

# 3. dedup + leakage
python3 -m apparatus.corpus.cli dedup \
  --in 03_corpus/candidates_source_first_holdout \
  --threshold 0.85 \
  --out 03_corpus/holdout/dedup_report.json \
  --kept-out 03_corpus/holdout/candidates_holdout.jsonl

python3 -m apparatus.corpus.cli leakage \
  --in 03_corpus/holdout/candidates_holdout.jsonl \
  --reference AEGIS-eval/training/seed_corpus.json \
  --threshold 0.85 \
  --out 03_corpus/holdout/leakage_audit.json
```

## Report

`handoffs/HANDOFF_08_report_<YYYY-MM-DD>.md` with: URLs fetched/failed for the SE domain, candidates generated, dedup count, leakage rate, Anthropic cost, PROCEED or HALT verdict. After PROCEED, the PI's manual step is selecting 30 from the deduped pool. Commit with `Handoff 08: hold-out corpus (software_engineering_specification)`.
