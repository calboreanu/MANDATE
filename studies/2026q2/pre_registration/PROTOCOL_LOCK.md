# PROTOCOL LOCK

**Status:** Canonical reference for the MANDATE empirical evaluation. Every other document in the package defers to this file. Conflicts between this file and another document resolve in favor of this file.

**Version:** 1.0
**Date locked:** [TO BE FILLED AT PRE-REGISTRATION DEPOSIT]
**Supersedes for numbers:** All prior version statements in v1 through v5 documents.

**Origin:** Created in response to external review identifying version drift across the v1-v5 documents. This file consolidates the final design and incorporates substantive corrections to the statistical specification.

---

## 1. Final Sample Specification

| Element | Count | Source/Method |
|---------|-------|---------------|
| Main corpus tasks | 120 | 40 per domain × 3 domains, AI-generated and SME-ratified |
| Pilot tasks | 6 | Used in Phase 0 protocol debug, separate from corpus |
| Calibration tasks | 6 | Hand-authored by PI, used as positive control |
| Hold-out generalization domain tasks | 30 | 4th domain, MANDATE-primary and best-baseline only |
| Perturbations | 350 | 7 types × 50 trials each |
| Ablation subset | 30 tasks | Stratified subset from main corpus (10 per domain) |
| Human expert upper bound | 30 specifications | Authored by senior practitioner, single pass |
| Human-vs-judge calibration sample | 100 outputs | Stratified across systems and conditions |

## 2. System Matrix

### 2.1 Primary system

**One frozen MANDATE configuration is the primary comparator.** All headline statistical tests use this configuration.

- **MANDATE-primary:** AEGIS (Autonomous Engineering Governance and Intelligence System) reference implementation with fine-tuned Qwen3-8B (Intake, Procedure roles) and Qwen3-32B (Interpreter, Decomposition, Binding, Validation roles), running locally on Mac mini M4 Pro cluster via Ollama, model versions and git tags pinned in pre-registration.

### 2.2 Comparator baselines (primary statistical comparisons)

The headline comparison is MANDATE-primary against **one** designated strongest baseline, pre-specified before unblinding. To pre-specify "strongest baseline":

- Run all baseline calibration on the 6 calibration tasks
- Define "strongest baseline" as the baseline achieving highest mean anchor completeness on the calibration set
- Lock this selection rule in the pre-registration

Candidate baselines (6 total):

| ID | System | Family | Type |
|----|--------|--------|------|
| B1 | Single-prompt planner | Claude (Anthropic) | LLM only |
| B2 | Single-prompt planner | GPT (OpenAI) | LLM only |
| B3 | ReAct | Claude | Reasoning + Acting |
| B4 | AutoGen | Claude/GPT, multi-agent | Multi-agent framework |
| B5 | CrewAI | Claude/GPT, role-based | Multi-agent framework |
| B6 | LangGraph | Claude/GPT, graph-based | State machine agent |

All six baselines run on all 120 tasks; primary statistical test uses MANDATE vs designated strongest baseline. Comparisons against the other five baselines are pre-registered exploratory.

### 2.3 Human expert upper bound

A single senior domain practitioner (not affiliated with the SME ground-truth pool) authors specifications for 30 tasks under the same input conditions as the systems (same input text, no additional context). Used as upper-bound reference, not a primary statistical comparator.

### 2.4 MANDATE backend portability (robustness, not ablation)

Re-categorized per external review: backend portability is a robustness/external-validity analysis, not an ablation.

**Backends to test:** MANDATE-primary plus 5 alternative LLM backends (6 total backends): Qwen3 base (no fine-tuning), Llama 3.3 70B, Mistral Large 2, Gemma 3, and Claude Sonnet 4 via API. Tested on the 30-task ablation subset only (not the full 120) to bound execution cost.

### 2.5 Ablations (tiered)

**Primary ablations (3 theory-critical):**

| ID | Removes | Tests claim |
|----|---------|-------------|
| A1 | Role separation | Does role isolation contribute to specification quality? |
| A2 | Tolerance bands (single threshold only) | Does threshold/target separation matter, or only threshold? |
| A3 | Gap Analysis output (forced specification) | Does gap reporting reduce fabrication? |

**Secondary ablations (4 supporting):**

| ID | Removes | Tests claim |
|----|---------|-------------|
| A4 | Validation Role | Does independent verification matter? |
| A5 | Success Registry | Does precedent reuse matter? |
| A6 | Search-Trace recording (decision-level, not just output) | Does trace recording influence decisions? |
| A7 | NIST AI RMF risk metadata | Does explicit risk assessment improve outcomes? |

Each ablation runs on the 30-task subset with 10 runs per condition.

## 3. Replication

| Condition | Runs per task per system |
|-----------|--------------------------|
| Main corpus tasks | 10 |
| Perturbations | 5 |
| Ablation tasks | 10 |
| Hold-out domain tasks | 10 |
| Human expert tasks | 1 (no replication; one expert, one pass) |

**Unit of analysis: task.** Per-task metrics computed as median across runs. The 10-run replication supports stability analysis and confidence intervals around per-task estimates; it does not multiply the statistical sample size.

## 4. Primary Outcomes (Corrected)

Five primary outcomes. Per external review, gap detection is decomposed (not just F1) and schema validity is elevated to primary.

| ID | Metric | Type | Operationalization |
|----|--------|------|-------------------|
| O1 | Anchor completeness | Bounded continuous (0-1) | Fraction of ground-truth fields correctly identified |
| O2a | Gap detection recall | Bounded continuous (0-1) | TP / (TP + FN) on gap-triggering tasks. Headline focus given FN are operationally worse |
| O2b | Gap detection precision | Bounded continuous (0-1) | TP / (TP + FP) on gap-triggering tasks |
| O3 | Fabrication rate | Count or rate | Number of unsupported fields per task |
| O4 | Schema validity rate | Binary per task | Percentage of mandate-as-code outputs that parse and validate against schema and can be consumed by a downstream runner without manual repair. **For baselines:** percentage of outputs that parse against an equivalent specification schema (defined per-baseline in calibration phase) |
| O5 | Adversarial resistance rate | Binary per perturbation | Fraction of prompt injection trials where system maintains specification contract |

### 4.1 Trace completeness (re-categorized)

Per external review: trace completeness is removed from primary comparative metrics because it is MANDATE-native and baselines cannot produce equivalent traces by construction. Reclassified as a **within-MANDATE reliability metric** reported in the methods section.

A separate exploratory analysis tests whether baselines can be wrapped to produce provenance artifacts and compared on equivalent auditability terms. This is not a primary contribution.

## 5. Primary Hypotheses (Sharpened)

Per external review: one central question, supporting claims as secondary.

**Central question:** Does the MANDATE specification framework produce more complete, less fabricated, more robust, and more parseable autonomous-agent task specifications than the strongest non-MANDATE baseline across operational task domains?

**Primary hypotheses:**

- **H1.** MANDATE-primary achieves higher mean anchor completeness (O1) than the designated strongest baseline.
- **H2a.** MANDATE-primary achieves higher mean gap detection recall (O2a) than the designated strongest baseline.
- **H3.** MANDATE-primary achieves lower mean fabrication rate (O3) than the designated strongest baseline.
- **H4.** MANDATE-primary achieves higher schema validity rate (O4) than the designated strongest baseline.
- **H5.** MANDATE-primary maintains higher adversarial resistance (O5) than the designated strongest baseline on prompt-injection perturbations.

**Secondary pre-registered:** Gap detection precision (O2b); per-domain analyses; per-perturbation-type analyses; primary ablations (A1, A2, A3); MANDATE-primary vs each non-strongest baseline pairwise.

**Exploratory:** Secondary ablations (A4-A7); backend portability; hold-out generalization; cost-effectiveness; failure mode analysis.

## 6. Statistical Specification (Corrected)

### 6.1 Primary analysis: mixed-effects models

Per external review correction.

For each primary outcome, fit a mixed-effects model on task-level aggregates:

**Continuous bounded outcomes (O1, O2a, O3 as rate):** Use beta regression or fractional logistic regression on task-level median scores. Fixed effects: system, domain, task_type, system × domain. Random effects: (1 | task_id). For cross-backend analyses: add (1 | backend_family).

**Binary outcomes (O4 schema validity, O5 adversarial resistance):** Logistic mixed-effects model. Fixed effects: system, domain, task_type. Random effects: (1 | task_id).

**Tasks are crossed with systems (every system attempts every task), not nested.** The random effect on task_id captures within-task correlation across systems.

### 6.2 Robustness checks: nonparametric paired tests

Wilcoxon signed-rank test as a model-free robustness check for continuous outcomes. McNemar's test for binary outcomes only (O4, O5). Reported alongside the primary mixed-effects estimates.

### 6.3 Repeated runs

The 10 runs per condition support stability analysis. **Primary unit of analysis is task, not run.** Per-task metrics: median across runs.

Sensitivity analyses repeat the primary tests using: mean across runs, best-of-10, worst-of-10, and a run-level mixed model with (1 | run_id) nested in (1 | task_id).

### 6.4 Multiple testing correction

**Family-wise error control for the five primary hypotheses (H1, H2a, H3, H4, H5):** Holm-Bonferroni applied sequentially. The first (smallest) p-value is tested at α = 0.01; subsequent thresholds increase per Holm's rule. **The "effective alpha" is not constant at 0.01**; Holm sequentially relaxes the threshold.

**For exploratory comparisons:** Benjamini-Hochberg FDR at q = 0.05.

### 6.5 Power analysis (simulation-based)

Per external review correction: formula-based power analysis using Cohen's h alone is insufficient for paired designs with task-level random effects. Pre-registered power analysis uses simulation:

1. Simulate task-level outcomes under assumed effect sizes (h = 0.20, 0.25, 0.30 for proportion outcomes; d = 0.4, 0.5, 0.6 for continuous)
2. Simulate the actual design: 120 tasks, 3 domains, paired systems, 10 runs per condition collapsed to task-level medians
3. Run the planned mixed-effects tests on each simulated dataset
4. Compute empirical power across 5,000 simulations per effect-size scenario
5. Report the minimum detectable effect (MDE) at 80% power as the design's power statement

If MDE exceeds practically meaningful effect sizes for any primary outcome, consider expanding sample or re-specifying that outcome before deposit.

### 6.6 Effect sizes and confidence intervals

- Continuous outcomes: standardized mean difference (Cohen's d) with 95% bootstrap CI
- Proportions: Cohen's h with 95% bootstrap CI; risk difference with 95% CI
- Mixed-effects model coefficients: 95% profile likelihood CI or 95% bootstrap CI
- Bootstrap procedure: 10,000 resamples, stratified by domain

### 6.7 Bayesian supplementary

For each primary hypothesis, fit a Bayesian model with weakly informative priors. Report posterior distribution, 95% credible interval, and Bayes factor against the null. Bayesian results are supplementary to the frequentist primary analyses, not replacements.

Priors are pre-registered. For effect sizes, use a weakly informative normal prior centered at zero with standard deviation 1 (on the standardized scale). For variance components, half-normal or half-Cauchy with scale 1.

## 7. Operational Significance Thresholds

Pre-registered before unblinding. A finding clears both bars to support adoption recommendation.

| Outcome | Statistical bar | Operational bar |
|---------|-----------------|-----------------|
| Anchor completeness | p (Holm) < 0.05 AND Cohen's d ≥ 0.4 | At least 10 percentage points absolute improvement |
| Gap recall | p (Holm) < 0.05 AND Cohen's h ≥ 0.3 | At least 15 percentage points absolute improvement |
| Fabrication rate | p (Holm) < 0.05 AND Cohen's d ≥ 0.4 | At least 50% relative reduction |
| Schema validity | p (Holm) < 0.05 AND Cohen's h ≥ 0.4 | At least 90% parseable |
| Adversarial resistance | p (Holm) < 0.05 AND Cohen's h ≥ 0.4 | At least 30 percentage points absolute resistance advantage |

Findings clearing only the statistical bar are reported as "statistically significant, operationally marginal."

## 8. Ground Truth Protocol

### 8.1 Sample

- 120 main corpus tasks: SME-signed ground truth
- 30 hold-out domain tasks: 1-2 external SMEs from hold-out domain
- 30 ablation subset tasks: subset of the 120 main corpus tasks; ground truth already established

### 8.2 SME pool

- Three primary SMEs: Brad Carter, Jason McKay, and the PI (Cal)
- **Cal is excluded from ground-truth signoff on tasks he authored, scaffolded, or had any pre-execution awareness of.** Cal signs off only on tasks Brad or Jason cannot cover, and only after blinded review.
- One to two external SMEs from the hold-out domain

### 8.3 Independence requirements

- SME forms independent mental anchor BEFORE reading AI-scaffolded candidate
- Independence statement signed on every signoff form
- 12-task IRR overlap sample (4 per domain)
- Pairwise Cohen's kappa ≥ 0.6 acceptable; ≥ 0.8 target; halt if < 0.4

### 8.4 External adjudication (expanded per external review)

Per external review: random 10% external check is insufficient. Replaced with stratified external review:

**24 tasks (20% of corpus)** independently anchored by an external reviewer not affiliated with Swift Group. Selection stratified to include:

- 8 tasks from each domain (proportional)
- All tasks where internal SMEs disagreed at first pass
- 6 gap-triggering tasks
- 4 stretch cases
- 6 highest-ambiguity tasks (selected by realism audit ratings)

Agreement between external and internal ground truth reported separately from internal SME IRR.

## 9. Data Leakage Audit

Per external review addition.

Before main run begins:

1. Verify the 120 main corpus tasks (and 30 hold-out tasks) do not appear in:
   - The Qwen3 fine-tuning training set (102 examples + 21 validation from the prior 125-example corpus)
   - The Success Registry as seeded examples
   - Any prompt examples or in-context examples shown to MANDATE or baselines
   - The 6 calibration tasks
   - The 6 pilot tasks
2. Compute embedding similarity (cosine) between evaluation tasks and any potentially overlapping examples; flag any similarity > 0.85 for review
3. Document the audit in the pre-registration appendix
4. If overlap is found, either exclude the overlapping task or substitute a fresh AI-generated task before corpus freeze

## 10. Model and Configuration Pinning

Per external review addition.

For every system, the pre-registration locks:

- Exact model version string (e.g., `claude-sonnet-4-20250514`, `qwen3-32b-ft-2026q1-v1.2`)
- Decoding parameters: temperature (default 0 for MANDATE internal; baselines per their calibration), top_p, max_tokens, presence_penalty, frequency_penalty
- Random seeds where seed control is available
- System fingerprints (for API providers that expose them)
- Local model file hashes (SHA-256) for all Ollama-served models
- Sampling parameters per agent framework (AutoGen, CrewAI, LangGraph configurations)

These are committed before execution and reported in the methods section. Any unavoidable change during execution is logged in the deviation log.

## 11. Baseline Fairness Safeguards

Per external review addition.

- All baselines receive the same input text as MANDATE; no hidden context
- All baselines required to produce output to a defined schema; baseline-specific schemas pre-registered
- Baselines have comparable tool/retrieval access where the comparison is meaningful (ReAct/AutoGen/CrewAI/LangGraph have tool sets; single-prompt baselines do not by design)
- Calibration uses the 6 calibration tasks ONLY; the calibration tasks are NOT used as positive control AND as baseline tuning target simultaneously; if calibration tuning saturates, a separate development set of 6 fresh AI-generated tasks (not in main corpus) is used for additional tuning
- All baseline prompts and configurations published in replication package
- Decision rule for "strongest baseline" (used in primary test) pre-registered as: highest mean anchor completeness on the 6 calibration tasks

## 12. Execution Constraints

- Lead Analyst: one full-time equivalent for 15-16 weeks (revised from 13-14 to absorb the additional rigor)
- SME pool: 3 internal + 1-2 external (hold-out domain) + 1 external spot-checker (24-task review)
- Human expert: 1 senior practitioner for the upper-bound baseline
- Human grader: 1-2 humans for the 100-output human-vs-judge calibration (NOT the PI or affiliated SMEs)
- API budget: approximately $2,500 (revised upward for 6 baselines)
- Compute: lab cluster + API access

## 13. Halt Rules

Per Playbook §16 with one modification:

- **Halt if data leakage audit (§9) detects >5% overlap.** Pause for corpus regeneration.
- **Halt if simulation-based power analysis (§6.5) shows MDE exceeds operational significance threshold for any primary outcome.** Either expand sample or re-specify outcome before deposit.
- All other halt rules retained from Playbook §16.

## 14. Reporting Constraints

Per external review writing pitfalls:

- Do NOT use language like "definitive Q1+", "publication-grade," "kills the strawman accusation"
- Use neutral language: "the protocol is designed to satisfy empirical standards at top venues in software engineering" if needed at all; preferably let the design speak for itself
- Do not overemphasize "unbounded compute" in the paper; report the actual compute used, briefly
- Do not frame prior reviewers as obstacles; frame the present study as a response to legitimate empirical validity concerns
- Generalization claims limited to "initial evidence across selected operational domains"

## 15. Document Reconciliation

The following documents must be updated to reflect this PROTOCOL_LOCK:

| Document | Updates needed |
|----------|----------------|
| `00_PLAYBOOK_v2.md` | Sample numbers, statistical methods, metric definitions |
| `00_PREREGISTRATION_TEMPLATE.md` | All numbers, hypothesis structure, statistical plan, power analysis approach |
| `Q1_AUDIT_AND_ENHANCEMENTS.md` | Marked as superseded by PROTOCOL_LOCK on numbers; methodology recommendations retained |
| `Q1_PLUS_UNBOUNDED_SCALING.md` | Marked as superseded by PROTOCOL_LOCK on numbers; conceptual framing retained |
| `FINAL_AUDIT_V5.md` | High-priority items integrated; medium and low items remain optional |
| `ANALYSIS_PLAN.md` | Notebook structure updated for corrected statistical models |
| `CHECKLIST.md` | All numbers reconciled |
| `PROMPTS.md` | New prompts for added perturbation types; schema validity check prompt |
| `FORMS.md` | Updated human grader form |
| `SETUP.md` | Additional package requirements for beta regression, mixed-effects models, simulation-based power |

The Lead Analyst's first task is to perform this reconciliation. No file in the package should contradict this PROTOCOL_LOCK after reconciliation is complete.

---

## Change Log

| Date | Change | Source |
|------|--------|--------|
| [DATE] | Initial protocol lock | Created in response to external review identifying version drift |
| [DATE] | Incorporated external review corrections | Specifically: corrected statistical methods, elevated schema validity to primary, decomposed gap detection, reclassified trace completeness, stratified external adjudication, added data leakage audit, added model pinning, added baseline fairness safeguards |

---

**End of PROTOCOL LOCK.**

This file is the authoritative source for the evaluation design. All ambiguity resolves in favor of this file.
