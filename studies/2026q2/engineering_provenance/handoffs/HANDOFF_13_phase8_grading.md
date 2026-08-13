# Codex Handoff 13: Phase 8 Three-Judge Grading

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-03
**Estimated wall clock:** **dozens of hours**, three judges x every anonymized output.
**Blocked on:** `outputs_freeze_v1` and `ablation_freeze_v1`, `gt_freeze_v1`, API keys for GPT-4o (OpenAI), Claude Opus (Anthropic), Gemini 2.5 Pro (Google) in `.env`. Budget at least a few hundred dollars in API spend.

## Mission

Run the three-judge ensemble (PROTOCOL_LOCK Section 8) over every anonymized output, plus the 20% double-grading sample, compute inter-judge reliability with the halt threshold (Cohen's kappa below 0.40 halts the study).

**Definition of done.** Per-judge per-output `JudgeScore` records under `08_grading/judge_<n>_<family>/`. Aggregated ensemble scores at `08_grading/ensemble_aggregated/ensemble_scores.jsonl`. IRR report at `08_grading/irr.json`. Schema-validity checks under `08_grading/schema_checks/`. Halt assessed.

## Tasks

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

# write the judges config
cat > 08_grading/judges_config.json <<'EOF'
{"gpt4o": "gpt-4o-2024-11-20",
 "claude": "claude-opus-4-6",
 "gemini": "gemini-2.5-pro"}
EOF

python3 -m apparatus.run grade \
  --anonymized 08_grading/anonymized_outputs \
  --ground-truth 04_ground_truth/ground_truth.json \
  --judges-config 08_grading/judges_config.json \
  --out 08_grading
```

The grading pipeline writes per-judge score JSONL, the aggregated ensemble, and the IRR report. The 20% double-grading sample and the human-vs-judge calibration on 100 outputs (FORMS Section 6) are separate runs; see PLAYBOOK Phase 8.5 for the calibration design.

## Halt check

```zsh
python3 -c "
import json
irr = json.load(open('08_grading/irr.json'))
print('min pairwise kappa:', irr.get('min_pairwise_kappa'))
print('halt:', irr.get('halt'))
"
```

If `halt: true`, stop. The protocol's IRR halt is binding (PROTOCOL_LOCK Section 8).

## Report

`handoffs/HANDOFF_13_report_<YYYY-MM-DD>.md` with: outputs graded, per-judge cost, min pairwise kappa, halt decision, anomalies (double-graded sample stability). Commit `Handoff 13: Phase 8 grading`.
