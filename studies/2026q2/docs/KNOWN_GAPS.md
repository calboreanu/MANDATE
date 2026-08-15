# Known Gaps — What This Deposit Cannot Support

Honest boundaries, stated once, in one place. Each is documented in the
supplement (Deviation Table and/or Threats to Validity) and summarized here.

1. **Human-expert upper bound: never measured.** The protocol-specified
   human-expert condition was not executed. No claim in
   the paper or supplement compares MANDATE to human specification quality.

2. **SME ground-truth pool unavailable.** The signed-anchor SME ratification
   process cannot be re-run externally; scaffolds and the answer key ship,
   the human sign-off process does not (documented deviation).

3. **Confidence intervals and significance tests: delivered 2026-07-10.**
   Task-clustered and per-record bootstrap CIs (10,000 resamples, seed
   20260710) plus Holm-corrected paired Wilcoxon tests on the shared
   120-task main corpus now ship in `analysis/bootstrap_contrasts_results.json`
   (script: `code/scripts/bootstrap_contrasts.py`). Small gaps at the
   Cond-A/B3 boundary (clustered CI [+0.004, +0.029]) are input-confounded
   because Cond-A receives pre-extracted structure and must not be read as
   fair raw-input wins.

4. **Executed contrast analysis is post-hoc.** The locked plan specified task
   medians and a domain-stratified bootstrap. The released exploratory script
   uses task means and unstratified task resampling, plus an independent
   per-record bootstrap; the locked analysis was not executed.

5. **Judged semantic outcomes are analysis-set dependent.** Full-coverage
   minimum-coverage reliability is α=0.855 when pooled across systems,
   α=0.618 for the decisive Cond-B/B3 comparison, α=0.446 within Cond-B,
   and α=0.766 within B3. Target coverage (0.586), constraint coverage
   (0.589), mission-intent match (0.536 nominal), gap classification (0.449
   nominal), fabrication count (0.218), and judged trace completeness (0.218
   interval / 0.027 nominal) show additional low or variable agreement. The
   locked protocol specified no Krippendorff-α acceptance cutoff. Semantic
   effect magnitudes are therefore descriptive and paired with the applicable
   reliability estimate. Structural trace-integrity claims instead derive
   from on-disk hash recomputation. The earlier sampled values (trace 0.194;
   fabrication 0.216) are retained only as halt-rule history.

6. **Cross-system semantic adversarial comparison: partial (80.7%).** Grading
   paused under budget Deviation D-13; baseline_4 generation halted at
   86.3% (3,021/3,500 on the frozen evaluation tree; the closeout status
   JSON snapshot reads 2,993 because it was written while the generator
   drained); baselines 5–6 scoped out under D-12 with baseline_4 as the
   multi-agent-shell class representative. Resumable; not claimable today.

7. **Source-level ablations A1/A2/A4/A6/A7: not run at full scale.**
   Upstream-blocked at the variant-build level. The auxiliary `ablation_mvp/`
   demonstrates all seven ablations end-to-end at 150-task scale but does not
   substitute for the protocol-specified full-scale runs.

8. **Single-lab provenance.** All results come from one author-controlled
   environment. Independent-lab replication has not been attempted; this
   repository exists to enable it.

9. **Judge-authoring overlap.** The same vendor families that power judges
   also power some baselines and the ground-truth scaffolding; mitigations
   (anonymization, three-vendor ensemble, shape-neutral rubric) are
   documented in the supplement's Threats section.

10. **Evaluated-build Cond-B generation cost is unlogged** (`api_cost_usd = null`
   by design on all 1,500 records); the original cost ledger carries this as a
   flagged estimate. The focused successor-routing check is ledgered at
   USD 191.388447 (USD 192.138414 cumulative including prior smoke/probes).

11. **Provider temporal drift.** Judge and baseline model versions are pinned
    by identifier, but hosted-model behavior drifts; byte-identical re-grades
    are not expected (temporal-validity threat).

12. **The successor routing-contract check is not an exact same-prompt replay.** The
    original `1.0.0rc1` prompt implementation was not recovered and
    hash-matched. The focused check uses the same frozen 150 tasks, recorded
    ten-run schedule, and two canonical conditions on a committed
    1.0.3-derived prompt stack. It establishes observed routing conformance on
    this corpus, not prompt-level identity or causal isolation.
