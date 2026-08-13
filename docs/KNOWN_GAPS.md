# Known Gaps — What This Deposit Cannot Support

Honest boundaries, stated once, in one place. Each is documented in the
supplement (Deviation Table and/or Threats to Validity) and summarized here.

1. **Human-expert baseline: never measured.** The pre-registered
   human-authored workflow-template comparator was not executed. No claim in
   the paper or supplement compares MANDATE to human specification quality.

2. **SME ground-truth pool unavailable.** The signed-anchor SME ratification
   process cannot be re-run externally; scaffolds and the answer key ship,
   the human sign-off process does not (documented deviation).

3. **Confidence intervals and significance tests: delivered 2026-07-10.**
   Task-clustered and per-record bootstrap CIs (10,000 resamples, seed
   20260710) plus Holm-corrected paired Wilcoxon tests on the shared
   120-task main corpus now ship in `analysis/bootstrap_contrasts_results.json`
   (script: `code/scripts/bootstrap_contrasts.py`). Small gaps at the
   Cond-A/B3 boundary (clustered CI [+0.004, +0.029]) remain below the
   pre-registered minimum detectable effect and must not be read as wins.

4. **Subjective judge outcomes are unreliable by their own IRR.**
   trace_completeness (α=0.194) and fabrication_count (α=0.216) fell below
   the reliability threshold; structural claims deliberately derive from
   on-disk record inspection instead. Treat those two grade columns as
   descriptive.

5. **Phase B semantic adversarial comparison: partial (80.7%).** Grading
   paused under budget Deviation D-13; baseline_4 generation halted at
   86.3% (3,021/3,500 on the frozen evaluation tree; the closeout status
   JSON snapshot reads 2,993 because it was written while the generator
   drained); baselines 5–6 scoped out under D-12 with baseline_4 as the
   multi-agent-shell class representative. Resumable; not claimable today.

6. **Source-level ablations A1/A2/A4/A6/A7: not run at full scale.**
   Upstream-blocked at the variant-build level. The auxiliary `ablation_mvp/`
   demonstrates all seven ablations end-to-end at 150-task scale but does not
   substitute for the pre-registered full-scale runs.

7. **Single-lab provenance.** All results come from one author-controlled
   environment. Independent-lab replication has not been attempted; this
   repository exists to enable it.

8. **Judge-authoring overlap.** The same vendor families that power judges
   also power some baselines and the ground-truth scaffolding; mitigations
   (anonymization, three-vendor ensemble, shape-neutral rubric) are
   documented in the supplement's Threats section.

9. **Original V1 Cond-B generation cost is unlogged** (`api_cost_usd = null`
   by design on all 1,500 records); the original cost ledger carries this as a
   flagged estimate. The V3 corrective campaign is separately ledgered at
   USD 191.388447 (USD 192.138414 cumulative including prior smoke/probes).

10. **Provider temporal drift.** Judge and baseline model versions are pinned
    by identifier, but hosted-model behavior drifts; byte-identical re-grades
    are not expected (temporal-validity threat).

11. **The corrective validation is not an exact same-prompt replay.** The
    original `1.0.0rc1` prompt implementation was not recovered and
    hash-matched. V3 uses the same frozen 150 tasks, ten-run seed schedule,
    and two canonical conditions on a committed 1.0.3-derived prompt stack.
    It supports a repaired-contract claim, not prompt-level identity.
