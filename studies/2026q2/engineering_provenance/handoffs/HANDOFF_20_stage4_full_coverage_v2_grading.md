# Codex Handoff 20: Stage 4 — Full-coverage v2 grading under Framing 2

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-23 (post-Stage-3-completion)
**Authoritative input docs:**
- v2 Protocol Amendment (Section: "Restored pre-registration coverage")
- Empirical Evidence Supplemental (Deviation Table, row 8 D-08 revoked + row 9 D-09 pivot)
- HANDOFF_19 §4 (original sampled v2 grading spec, now superseded by this handoff)
- HANDOFF_19c (retry layer + probe utilities; both required for Stage 4)
- HANDOFF_19d (DomainProfile patch; verified working in Stage 3 Cond-B)

**Stage 3 inputs (all on disk, all committed):**
- Cond-A main: 1200 records at `07_system_outputs/cond_a/cond_a__TASK-MAIN-*.json`
- Cond-A holdout: 300 records at `07_system_outputs/cond_a/holdout/cond_a__TASK-HOLDOUT-*.json`
- Cond-B main: 1200 records at `07_system_outputs/cond_b/cond_b__TASK-MAIN-*.json`
- Cond-B holdout: 300 records at `07_system_outputs/cond_b/holdout/cond_b__TASK-*.json`

**Estimated wall clock:** 24-36 hours for the main grading pass (12,000 records × 3 judges with 5-way concurrent grading per Phase 8 retry-layer patches).
**Estimated cost:** ~$7,700 (~$0.21 per record × 12,000 + IRR double-grade ~20%).
**Halt rule:** PROTOCOL_LOCK §8 κ ≥ 0.40 minimum pairwise on the IRR sample; full-coverage grading is binding (no recourse to sampling-based excuses).

---

## Why this exists, and why Framing 2 not Framing 1

The supplement Deviation Table row 8 documents the v1 cost-driven Phase 8 deviations (D-08): stratified N=700 sample, Sonnet substituted for Opus, 10% IRR. Per PI directive 2026-06-23 these are REVOKED for v2 grading. The v2 Protocol Amendment specifies the full pre-registration coverage:

- **Full coverage** — all 12,000 records graded (3,000 v2 Cond-A/B + 1,500 v1 mandate_primary re-grade + 7,500 baselines re-grade); no statistical sampling.
- **Claude Opus 4.6** as the Anthropic judge — the pre-registered model. No self-grading bias caveat (Opus is generation-different from every baseline planner).
- **20% double-grade IRR sample** — pre-registered fraction. Per-pair κ + Krippendorff α computed at full statistical power.
- **PROTOCOL_LOCK §8** κ ≥ 0.40 binding on the full-coverage IRR sample, not a sample-of-a-sample.

This handoff covers Stage 4 only. Stage 6 (O5 perturbation runs against the 350-perturbation suite) ships in HANDOFF_21 once Stage 4 lands.

## Stage 4 scope

| System / condition | Records to grade | Source |
|---|---|---|
| Cond-X (v1 mandate_primary re-grade) | 1500 | `07_system_outputs/mandate_primary/mandate_primary__TASK-MAIN-*.json` |
| Cond-A | 1500 | `07_system_outputs/cond_a/{,holdout/}cond_a__*.json` |
| Cond-B | 1500 | `07_system_outputs/cond_b/{,holdout/}cond_b__*.json` |
| Baseline B1 | 1500 | `07_system_outputs/baseline_1/baseline_1__*.json` |
| Baseline B2 | 1200 | `07_system_outputs/baseline_2/baseline_2__*.json` |
| Baseline B3 | 1205 | `07_system_outputs/baseline_3/baseline_3__*.json` |
| Baseline B4 | 1206 | `07_system_outputs/baseline_4/baseline_4__*.json` |
| Baseline B5 | 1206 | `07_system_outputs/baseline_5/baseline_5__*.json` |
| Baseline B6 | 1206 | `07_system_outputs/baseline_6/baseline_6__*.json` |
| **Total to grade** | **~12,023** | (use the actual on-disk counts; ~12K is the planning number) |

Plus the 20% double-grade IRR sample: ~2,400 additional second-pass gradings stratified across the 9 system conditions.

---

## Preconditions

```zsh
cd "$HOME/Desktop/Desktop - lattice-ws01/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate || true  # noqa — .venv/bin/python direct invocation preferred per HANDOFF_19b housekeeping

# 1. judges_config.json: confirm Opus, GPT-4o, Gemini 2.5 Pro
test -f 08_grading/judges_config.json
grep -q "claude-opus-4-6"   08_grading/judges_config.json || { echo "HALT: Opus not in judges_config; restore per D-10 revocation"; exit 1; }
grep -q "gpt-4o-2024-11-20" 08_grading/judges_config.json || { echo "HALT: GPT-4o judge missing"; exit 1; }
grep -q "gemini-2.5-pro"    08_grading/judges_config.json || { echo "HALT: Gemini judge missing"; exit 1; }
echo "judges_config.json under D-10 (Opus restored)"

# 2. Apparatus has v2 rubric + retry/probe utilities (from HANDOFF_19/19c/19d)
.venv/bin/python -c "
from apparatus.grading import rubric_v2
from apparatus.llm_retry import call_with_retry, RetryingLLMClient
from apparatus.grading.judge import Judge
print('apparatus v2 grading components present')
"

# 3. Provider probes (Anthropic, Gemini). OpenAI doesn't typically have
#    overloaded windows but we'll probe Anthropic + Gemini explicitly.
.venv/bin/python -m apparatus.probe_anthropic --probes 3 || { echo "HALT: Anthropic probe failed"; exit 1; }
.venv/bin/python -m apparatus.grading.probe_gemini --probes 3 || { echo "HALT: Gemini probe failed"; exit 1; }
echo "all probe gates passed"

# 4. The 9000 v1 anonymized records still on disk from the prior Phase 8
n_old=$(ls 08_grading/anonymized_outputs/OUT-*.json 2>/dev/null | wc -l)
echo "v1 anonymized records on disk: $n_old"

# 5. Confirm Stage 3 Cond-A + Cond-B records present
test "$(ls 07_system_outputs/cond_a/cond_a__TASK-MAIN-*.json 2>/dev/null | wc -l)" = "1200"
test "$(ls 07_system_outputs/cond_a/holdout/cond_a__TASK-*.json 2>/dev/null | wc -l)" = "300"
test "$(ls 07_system_outputs/cond_b/cond_b__TASK-MAIN-*.json 2>/dev/null | wc -l)" = "1200"
test "$(ls 07_system_outputs/cond_b/holdout/cond_b__TASK-*.json 2>/dev/null | wc -l)" = "300"
echo "Stage 3 Cond-A + Cond-B record counts match expected (1200 + 300 each)"

# 6. Move v1 D-08 sampled grading artifacts out of the way (preserve audit
#    trail; v2 will produce a parallel 08_grading_v2/ tree).
test -d 08_grading_v2 || mkdir -p 08_grading_v2
test -f 08_grading/irr.json && mv 08_grading/irr.json 08_grading_v2/_v1_d08_irr.json.bak
echo "08_grading_v2/ ready"

# 7. API keys
.venv/bin/python -c "
import os
from pathlib import Path
for line in Path('.env').read_text().splitlines():
    if '=' in line:
        k, v = line.split('=', 1); os.environ[k] = v.strip()
assert os.environ.get('ANTHROPIC_API_KEY','').startswith('sk-ant')
assert os.environ.get('OPENAI_API_KEY','').startswith('sk-')
assert os.environ.get('GOOGLE_API_KEY','').strip()
print('all three API keys set')
"
```

**Success criteria.** All seven preconditions print confirmation. Any failure halts before any grading spend.

---

## Task 1 — Restore Opus in judges_config.json (D-10 commit)

The v1 D-08 deviation substituted Sonnet for Opus on the Anthropic judge. D-10 revokes that substitution. Edit `08_grading/judges_config.json`:

```json
{
  "anthropic": {
    "model": "claude-opus-4-6",
    "max_tokens": 2048,
    "temperature": 0.0
  },
  "openai": {
    "model": "gpt-4o-2024-11-20",
    "max_tokens": 2048,
    "temperature": 0.0
  },
  "google": {
    "model": "gemini-2.5-pro",
    "max_tokens": 8192,
    "temperature": 0.0
  }
}
```

Commit message: `D-10 restoration: judges_config.json Anthropic judge restored to claude-opus-4-6 (revoke D-08 Sonnet substitution per supplement Deviation Table row 8 amendment). Pre-registered ensemble fully restored. No self-grading bias caveat applies.`

## Task 2 — Anonymize Cond-A and Cond-B records

Extend `08_grading/anonymized_outputs/` to cover the 3,000 new Cond-A + Cond-B records. Reuse the existing anonymization pattern (the v1 anonymization for mandate_primary + B1-B6 is preserved at `07_system_outputs/anonymization_mapping.json`).

```zsh
.venv/bin/python -m apparatus.run anonymize \
  --inputs 07_system_outputs/cond_a 07_system_outputs/cond_a/holdout \
           07_system_outputs/cond_b 07_system_outputs/cond_b/holdout \
  --mapping-output 08_grading_v2/anonymization_mapping_v2_additions.json \
  --base-mapping 07_system_outputs/anonymization_mapping.json \
  --output-dir 08_grading_v2/anonymized_outputs
```

The base-mapping flag preserves v1 anon_id allocations; new records get fresh `OUT-XXXXXXXX` IDs that don't collide with the v1 9,000.

Then merge:
```zsh
.venv/bin/python -c "
import json
v1 = json.load(open('07_system_outputs/anonymization_mapping.json'))
v2_add = json.load(open('08_grading_v2/anonymization_mapping_v2_additions.json'))
merged = {**v1, **v2_add}
json.dump(merged, open('08_grading_v2/anonymization_mapping_full.json','w'), indent=2)
print(f'v1 ids: {len(v1)}, v2 additions: {len(v2_add)}, total: {len(merged)}')
"
```

Verify count: ~9000 + 3000 = ~12,000.

Symlink the v1 anonymized outputs into `08_grading_v2/anonymized_outputs/` so the grader sees a single directory of 12,000:
```zsh
cd 08_grading_v2/anonymized_outputs
for f in ../../08_grading/anonymized_outputs/OUT-*.json; do
  test ! -e "$(basename $f)" && ln -s "$f" "$(basename $f)"
done
cd ../..
ls 08_grading_v2/anonymized_outputs/OUT-*.json | wc -l
# Expected: ~12,000
```

## Task 3 — Confirm the v2 rubric path is wired

`apparatus/grading/rubric_v2.py` was landed in HANDOFF_19 Stage 1. Stage 4 uses it via the `grade-v2` CLI command. Smoke test:

```zsh
.venv/bin/python -m apparatus.run grade-v2 --help 2>&1 | grep -q "rubric_v2\|v2 rubric" || \
  { echo "HALT: grade-v2 CLI not present; check HANDOFF_19 Stage 1 plumbing"; exit 1; }
echo "grade-v2 CLI present"
```

## Task 4 — Fire Stage 4 grading

```zsh
cd "$HOME/Desktop/Desktop - lattice-ws01/MANDATE Evaluation/mandate_eval_2026Q2"

# Probe gate immediately before launch (provider weather)
.venv/bin/python -m apparatus.probe_anthropic --probes 3 \
  && .venv/bin/python -m apparatus.grading.probe_gemini --probes 3 \
  || { echo "HALT: provider probe failed; wait and retry"; exit 1; }

# Fire grade-v2 with full coverage
.venv/bin/python -m apparatus.run grade-v2 \
  --anonymized 08_grading_v2/anonymized_outputs \
  --ground-truth 04_ground_truth/ground_truth.json \
  --judges-config 08_grading/judges_config.json \
  --rubric v2 \
  --out 08_grading_v2 \
  --full-coverage \
  --double-grade-pct 0.20 \
  --double-grade-seed 20260624 \
  --skip-existing \
  --max-workers 5 \
  2> >(tee -a logs/HANDOFF_20_stage4_grade_v2.stderr >&2)
```

**Flag notes:**
- `--full-coverage`: ungates the sampled-grading default; processes every anonymized record in the directory.
- `--double-grade-pct 0.20`: pre-registered IRR fraction. Reverts D-08 amendment.
- `--double-grade-seed 20260624`: deterministic seed for the IRR sub-sample; documented for reproducibility.
- `--skip-existing`: per-record checkpoint resume support from HANDOFF_13f patches.
- `--max-workers 5`: same concurrent-judge pattern as the v1 Phase 8 retry-layer-patched grading.

**Expected wall clock:** ~24-36 hours. ~30 seconds per record × 12,000 records / 5-way concurrency on the per-record judge fan-out. Cumulative cost trends at ~$0.55/min during execution.

## Task 5 — Monitor

Run every ~30 minutes during the live grading:

```zsh
.venv/bin/python - <<'PY'
import os, glob, json, time
TARGETS = {"main": 12000, "double_grade": 2400}
n_main = len(glob.glob("08_grading_v2/by_record/*.json"))
n_dg   = len(glob.glob("08_grading_v2/double_grade/by_record/*.json"))
n_inc  = len(glob.glob("08_grading_v2/incomplete_grades/*.json"))
print(f"main checkpoints:        {n_main}/{TARGETS['main']} ({n_main/TARGETS['main']*100:.1f}%)")
print(f"double-grade checkpoints: {n_dg}/{TARGETS['double_grade']} ({n_dg/TARGETS['double_grade']*100:.1f}%)")
print(f"incomplete (will redo):   {n_inc}")

# Recent checkpoint freshness
files = sorted(glob.glob("08_grading_v2/by_record/*.json"),
               key=lambda f: -os.path.getmtime(f))
if files:
    age_s = time.time() - os.path.getmtime(files[0])
    print(f"latest checkpoint age:    {age_s:.0f}s")

# Per-judge cost so far (read from a few recent checkpoints)
if files:
    recent = files[:200]
    cost = 0.0
    for f in recent:
        d = json.load(open(f))
        for s in d.get("judge_scores", []):
            cost += float(s.get("cost_usd", 0) or 0)
    avg = cost / len(recent) if recent else 0
    print(f"avg cost/record (recent 200): ${avg:.4f}")
    print(f"projected total cost:     ${avg * TARGETS['main']:.0f}")
PY
```

**Escalation triggers:**
- After 1 hour, `by_record/` count < 50 → catastrophic throughput. Halt and investigate.
- `incomplete_grades/` count grows past 5% of completed records → judges throwing more errors than the retry layer is absorbing. Inspect the stderr log.
- One judge dominates `incomplete_grades/` (>90%) → provider outage. Run the relevant probe and decide hold-vs-continue.
- Cumulative cost approaching $9,000 → halt and escalate (20% over the $7,700 envelope).

## Task 6 — Halt-or-PROCEED check on the IRR sample

After main + double-grade complete:

```zsh
.venv/bin/python - <<'PY'
import json
irr = json.load(open("08_grading_v2/irr.json"))
print("Stage 4 IRR (full coverage, D-10 restored):")
print(f"  per-pair Cohen's kappa:")
for pair, k in irr.get("pairwise_kappa", {}).items():
    print(f"    {pair}: {k:.3f}")
print(f"  min pairwise kappa: {irr.get('min_pairwise_kappa'):.3f}")
print(f"  halt verdict: {irr.get('halt')}")
print()
print(f"  per-outcome Krippendorff alpha:")
for out_name, alpha in irr.get("krippendorff_alpha", {}).items():
    print(f"    {out_name}: {alpha:.3f}")
print()
print(f"  double-grade sample size: {irr.get('double_grade',{}).get('sample_size')}")
print(f"  double-grade pass1 min kappa: {irr.get('double_grade',{}).get('pass1_irr',{}).get('min_pairwise_kappa'):.3f}")
print(f"  double-grade pass2 min kappa: {irr.get('double_grade',{}).get('pass2_irr',{}).get('min_pairwise_kappa'):.3f}")
PY
```

**Decision:**
- `min_pairwise_kappa >= 0.40` → PROCEED to Stage 5 analysis
- `min_pairwise_kappa < 0.40` → HALT under PROTOCOL_LOCK §8. Diagnose:
  - Which judge pair is the lowest?
  - Which outcome is the lowest α?
  - Compared to v1 D-08 IRR (which halted at κ=0.296 on mission_intent under Sonnet-Gemini), does the v2 Opus ensemble cleared mission_intent? Did a different outcome become the rate-limiter?
  - Is the failing outcome under v2 rubric semantically tighter than v1's, so disagreement is structural rather than rubric-driven?

If HALT under v2 full-coverage Opus, the diagnosis IS the methodological finding: it means the cross-judge disagreement is intrinsic to the LLM-as-judge measurement under the canonical MANDATE schema, regardless of rubric design. That's publishable as a Finding 8 candidate.

## Task 7 — Cross-condition analysis (post-PROCEED)

When IRR passes, compute the per-condition, per-outcome ensemble means and the v1-vs-v2 deltas. Save aggregates to `08_grading_v2/ensemble_aggregated/`:

```zsh
.venv/bin/python -m apparatus.run analyze-v2 \
  --grading 08_grading_v2 \
  --anonymization 08_grading_v2/anonymization_mapping_full.json \
  --systems mandate_primary,cond_a,cond_b,baseline_1,baseline_2,baseline_3,baseline_4,baseline_5,baseline_6 \
  --domains FIN,INT,SEC,SES \
  --out 09_analysis/v2/cross_condition_summary.json
```

The analyze-v2 command may not yet exist; if missing, write a one-off Python script that computes:
- Per-system per-outcome mean + 95% bootstrap CI (10,000 resamples)
- Per-domain stratification
- Cond-X (mandate_primary) v1-vs-v2 score delta per record per outcome (the schema-mismatch penalty quantification — Finding 6)
- Cond-A vs Cond-B contrast (DomainProfile selection effect — Finding 7)
- Cross-baseline distribution

## Report

`handoffs/HANDOFF_20_stage4_report_<YYYY-MM-DD>.md`:
- Stage 3 input record counts confirmed
- Anonymization mapping size + collisions check
- D-10 judges_config.json restoration verified
- Stage 4 launch + completion timestamps; total wall clock
- Per-judge call count, token usage, attested cost
- Stage 4 IRR table (per-pair κ, per-outcome α)
- PROCEED or HALT verdict
- Per-system means table (9 systems × 5 outcomes)
- v1-vs-v2 delta on Cond-X (the schema-mismatch quantification number)
- Cond-A vs Cond-B by domain (the DomainProfile effect quantification)
- Anomalies (incomplete records, retry-layer activity, provider weather)
- Cumulative v2 spend snapshot

Commit message:
```
HANDOFF_20 Stage 4 complete: full-coverage v2 grading per D-10 (Opus restored, 20% IRR). 12,000 records graded across 9 system conditions. Per-pair κ + per-outcome α reported; halt-or-PROCEED verdict per PROTOCOL_LOCK §8. v1-vs-v2 Cond-X delta quantified for Finding 6. Cond-A vs Cond-B DomainProfile contrast quantified for Finding 7.
```

## What Stage 4 unblocks

- **Stage 5 analysis** populates Empirical Evidence Supplemental Section 5.4 and Section 4.6/4.7 with the v2 numbers.
- **Stage 6 (HANDOFF_21)** O5 perturbation runs + grading can fire in parallel with Stage 5 since they don't share inputs.
- **v2 deposit packaging** assembles the canonical-MANDATE Cond-A/B runs + re-graded baselines + v2 IRR under `mandate-eval-primary-2026q2-v2` tag.

## If Stage 4 hits the κ halt

The HALT path produces a methodological finding regardless:

- If `mission_intent` is again the lowest-κ outcome under Opus full coverage, the issue is intrinsic judge-rubric ambiguity, not the v1 Sonnet self-grading bias we documented in v1 D-08-amend.
- If a different outcome is the rate-limiter under v2 (e.g., `fabrication_count`), the diagnosis is that v2's shape-neutral rubric tightened semantic match on coverages but introduced new ambiguity elsewhere.
- Either outcome is publishable as Finding 8: "LLM-judge ensembles disagree systematically on subjective MANDATE outcomes regardless of rubric design under SME-skip ground truth."

The v2 deposit ships in the HALT case with the diagnostic finding instead of cross-system numerical comparison; the substantive 5+ content-tripwire findings carry the paper.
