# Unbounded Compute Scaling: From Defensible to Definitive

**Purpose:** Reframe the evaluation design given that AEGIS (Autonomous Engineering Governance and Intelligence System) can load any LLM, any agent framework, any configuration, with no compute ceiling. This converts the goal from "Q1-defensible" to "Q1+ definitive" by leveraging configuration flexibility that conventional academic evaluations cannot afford.

**Reads alongside:** `00_PLAYBOOK_v2.md` and `Q1_AUDIT_AND_ENHANCEMENTS.md`. This document extends both.

---

## Reframing: What Actually Constrains Us

With unbounded compute and configuration flexibility, the constraints shift:

| Resource | Status | Implication |
|----------|--------|-------------|
| Compute (GPU-hours, API costs) | Unbounded | No reason to limit replications, configurations, or backends |
| Model availability (LLMs, frameworks) | Unbounded | No reason to test only 2-3 system variants |
| SME human time | Bounded (~10-15 hours per SME over 6 weeks) | Determines corpus size ceiling |
| External SME recruitment | Bounded by network and outreach | Determines cross-organizational validity ceiling |
| Calendar time | 13 weeks committed | Determines execution depth |
| Lead Analyst attention | One person, full-time equivalent | Determines orchestration complexity ceiling |

The binding constraint is SMEs. Everything else can scale. The right strategy: keep the corpus at SME-feasible size, then pour the compute headroom into a wide system matrix that tests the framework, not just the implementation.

This is the opposite of how single-system pilots typically scale. Most pilots add tasks (which costs SME time) but stay narrow on systems (which is free). With compute unbounded, the reverse is more defensible: bounded corpus, expansive system matrix.

---

## Expansion 1: MANDATE Backend Matrix

**v3 plan:** MANDATE on fine-tuned Qwen3 + one backend portability variant.
**v4 plan:** MANDATE on 6 to 8 LLM backends.

### Backends to test

| Backend | Family | Size | Rationale |
|---------|--------|------|-----------|
| Qwen3 fine-tuned (primary) | Alibaba | 8B + 32B | The AEGIS reference implementation |
| Qwen3 base (no fine-tuning) | Alibaba | 8B + 32B | Isolates fine-tuning contribution |
| Llama 3.3 | Meta | 70B | Different family, similar size |
| Mistral Large 2 | Mistral AI | 123B | Different family, larger |
| Gemma 3 | Google | 27B | Different family, smaller |
| GPT-OSS variants | OpenAI | varies | Open-weight US frontier model |
| Claude Sonnet 4 (via API) | Anthropic | (proprietary) | Proprietary frontier comparison |
| GPT-4o (via API) | OpenAI | (proprietary) | Proprietary frontier comparison |

Lab has 4 Mac mini M4 Pro workstations running Ollama. All local backends are deployable. API access for Claude and GPT-4o is straightforward.

### What this proves

If MANDATE's specification quality, gap detection accuracy, and trace completeness hold across backends with diverse training data, sizes, and providers, then MANDATE is a framework-level contribution, not a Qwen3-specific artifact. This is the strongest possible external validity claim for an LLM-based framework.

If properties degrade on some backends, the finding is also valuable: it tells us which backend characteristics MANDATE depends on. Either result is publishable.

### Compute scale

8 backends × 120 tasks × 10 runs = 9,600 task runs per backend matrix.
Plus 8 backends × 150 perturbations × 5 runs = 6,000 perturbation runs.
**Backend matrix total: ~15,600 runs.**

### Reviewer effect

Closes the most damaging Q1+ objection: "your results show fine-tuned Qwen3 is good, not that MANDATE is good." With cross-backend validation, this objection becomes incoherent.

---

## Expansion 2: Comprehensive Baseline Matrix

**v3 plan:** 2 baselines (single-prompt + ReAct).
**v4 plan:** 5 to 7 baselines including human expert upper bound.

### Baselines to test

| Baseline | Type | What it tests |
|----------|------|---------------|
| Single-prompt Claude | LLM only | Lower bound: no agent scaffolding |
| Single-prompt GPT-4o | LLM only | Cross-family lower bound |
| ReAct (Claude) | Reasoning + Acting | Standard interleaved agent |
| AutoGen | Multi-agent dialogue | Wu et al. 2023 multi-agent benchmark |
| CrewAI | Role-based multi-agent | Alternative multi-agent framework |
| LangGraph | Graph-based agent | State machine agent paradigm |
| Human expert (gold standard) | Upper bound | What is the best possible? |

The human expert baseline is critical: it answers "how good could anyone do?" If MANDATE is close to human expert performance, that's a strong claim. If MANDATE matches or exceeds human expert speed at comparable quality, that's an even stronger claim.

### Human expert baseline operationalization

For a small subset (30 of 120 tasks, stratified across domains and categories), recruit a senior domain expert (different from the SMEs authoring ground truth) and ask them to write the specification from scratch in the same time budget MANDATE has access to. Their output is graded by the same three-judge ensemble as MANDATE and the LLM baselines.

This gives a small but meaningful comparison: how close does MANDATE come to what a human would produce?

### What this proves

Closes "lacks comparative benchmarking" objection at the maximum strength level. MANDATE compared against the full breadth of current multi-agent frameworks AND against human performance.

### Compute scale

6 LLM baselines × 120 tasks × 10 runs = 7,200 task runs.
Plus 6 LLM baselines × 150 perturbations × 5 runs = 4,500 perturbation runs.
Plus human expert: 30 tasks × 1 expert × 1 run = 30 outputs.
**Baseline matrix total: ~11,700 runs + 30 human-authored specifications.**

### Reviewer effect

A reviewer cannot say "missing comparison to X" when you've compared against six baselines spanning the agent architecture taxonomy. They can quibble about specific baseline configurations but cannot claim the comparison was inadequate.

---

## Expansion 3: Replication Count

**v3 plan:** 5 runs per condition.
**v4 plan:** 10 runs per condition.

### Why 10 not 5

Five runs gives meaningful but moderate CIs on stochastic metrics. Ten runs gives tight CIs that let you confidently distinguish small effects. With unbounded compute, the only reason not to is analysis overhead, which is minor.

At 10 runs per condition, the standard error on a stochastic outcome rate of 0.8 has 95% CI half-width of approximately ±0.12. At 5 runs, it's ±0.18. This matters when reporting per-task stability or per-perturbation retention rates.

### Compute scale impact

Most of the system matrix already accounts for this. Total run count with 10 replications across the expanded matrix: approximately 28,000 task runs plus 11,000 perturbation runs.

If 10 runs per condition becomes a bottleneck somewhere (e.g., human-expert baseline cannot replicate 10x), that condition uses fewer runs and the limitation is reported.

---

## Expansion 4: Cross-Domain Hold-Out Generalization Test

**v3 plan:** 3 corpus domains, all tested against all systems.
**v4 plan:** 3 corpus domains for primary analysis + 1 hold-out domain for generalization test.

### Hold-out domain proposal

After all primary analyses are complete and the protocol is frozen, generate a smaller corpus (30 tasks) in a 4th domain not used during any model fine-tuning, prompt engineering, or rubric calibration. Suggested 4th domain: software engineering specification (e.g., "specify the requirements for a code review automation tool") or operations/maintenance reporting (e.g., "produce the weekly facility safety inspection report").

Test MANDATE primary configuration on this hold-out. Compare against the baseline that performed best on the main corpus.

### What this proves

External validity to a domain MANDATE was not designed against. If MANDATE retains its anchor completeness and gap detection advantage on the hold-out, that's evidence for genuine domain transfer. If it does not, that's a finding: MANDATE's advantage is partly domain-specific tuning, not pure architecture.

### SME requirement

The hold-out domain needs ground truth. Recruit 1 to 2 SMEs from the hold-out domain for ~3 hours each. Brad and Jason may not be qualified for software engineering specifications; this is where external SME recruitment matters.

### Compute scale

30 tasks × (8 MANDATE backends + 6 baselines) × 10 runs = 4,200 hold-out runs.

---

## Expansion 5: Human-vs-Judge Calibration at Scale

**v3 plan:** 30 outputs human-graded for LLM-judge validation.
**v4 plan:** 100 outputs human-graded, stratified across systems and task types.

### Stratification

| Stratum | Count | Rationale |
|---------|-------|-----------|
| MANDATE outputs (across backends) | 30 | Confirm grader handles MANDATE format consistently |
| Baseline outputs | 30 | Confirm grader handles baseline formats |
| Perturbation outputs | 20 | Confirm grader handles edge cases |
| Disagreement cases (judges split 2-1) | 20 | Highest-value human signal: cases where LLM judges disagree |

### Human graders

One primary human grader (Cal or external) reviews all 100. For inter-human reliability, a second human grader reviews a 30-output overlap sample. Pairwise human kappa establishes the upper bound of grading agreement; LLM-judge ensemble agreement with human is then interpreted against that bound.

### What this proves

Establishes the validity of LLM-as-judge methodology at sample size meaningful enough that reviewers cannot say "your validation sample was too small." A 100-output sample gives 95% CI half-width on a correlation of approximately ±0.10.

### Reviewer effect

Closes "LLM-as-judge methodology not validated" objection at maximum strength. The validation sample is itself a publishable methodological contribution.

---

## Expansion 6: Statistical Sophistication

**v3 plan:** Frequentist analyses with effect sizes and CIs.
**v4 plan:** Add Bayesian supplementary, hierarchical models, and pre-registered model specifications.

### Bayesian supplementary

For each primary hypothesis, fit a Bayesian model in addition to the frequentist test:

- Posterior distribution on the effect size
- Bayes factor comparing alternative vs null
- Posterior predictive checks
- 95% credible intervals (interpretable as "the probability the true value lies in this interval")

Bayesian results are reported as supplementary to the pre-registered frequentist tests, not as replacements. They strengthen the conclusion by showing the result is robust to inferential framework.

### Hierarchical model for cross-backend analysis

The backend matrix produces data with natural hierarchical structure: tasks nested within backends, backends nested within model families. Fit a multilevel model:

```
score ~ intercept + system + backend + (1 | task_id) + (1 | family)
```

This isolates system effects from backend-family confounds, gives correct standard errors under the nesting, and provides estimated variance at each level. The presence or absence of significant variance between families is itself a finding.

### Pre-registration of models

Specify both the Bayesian priors and the hierarchical model structures in the pre-registration. This commits to the analyses before seeing the data and prevents post-hoc model selection.

### Reviewer effect

Closes "statistical methods are basic" objection. Q1+ statistical methods are now in play. Reviewers familiar with modern statistics will see this as a strong methodology section.

---

## Expansion 7: Adversarial Robustness at Scale

**v3 plan:** 5 perturbation types × 30 trials = 150 perturbations.
**v4 plan:** 7 perturbation types × 50 trials = 350 perturbations, including new types.

### New perturbation types

**Type 6: Out-of-distribution input.** Tasks deliberately phrased in unusual registers (formal legalese, colloquial speech, mixed-language, technical jargon from adjacent domains). Tests whether MANDATE's gap detection depends on stylistic familiarity.

**Type 7: Length perturbation.** Same task content compressed (50% length) or expanded (200% length). Tests whether MANDATE's extraction is robust to verbose vs. terse phrasings.

### Expanded prompt injection coverage

The original 3 sub-types (direct, social engineering, fake authority) expand to 5:

- Direct command (10)
- Social engineering with fake user context (10)
- Fake authority (NIST, government, internal policy) (10)
- Multi-turn-like injection (instruction embedded as if from a prior conversation) (10)
- Encoded injection (instruction in base64, ROT13, or similar) (10)

Total prompt injection trials: 50.

### Compute scale

7 types × 50 trials = 350 perturbations
× (8 backends + 6 baselines) × 5 runs = ~24,500 perturbation runs

### Reviewer effect

Adversarial robustness suite is now comprehensive enough to address reviewer concerns about narrow threat modeling.

---

## Expansion 8: Ablation Granularity

**v3 plan:** 4 ablations (no role separation, no registry, no trace, backend portability).
**v4 plan:** 8 ablations isolating individual MANDATE components.

### Additional ablations

| Ablation | Removes | Tests |
|----------|---------|-------|
| 1 (existing) | Role separation | Does role isolation matter? |
| 2 (existing) | Success Registry | Does precedent reuse matter? |
| 3 (existing) | Search-Trace | Does trace recording influence decisions? |
| 4 (existing) | Backend portability | Does MANDATE generalize across LLMs? |
| **5 (new)** | Validation Role | Does independent verification matter? |
| **6 (new)** | Tolerance bands | Does threshold/target separation matter or only the threshold? |
| **7 (new)** | Gap Analysis output | Does gap reporting vs. forced output change behavior? |
| **8 (new)** | NIST AI RMF risk metadata | Does explicit risk assessment matter? |

Each ablation runs on the 30-task ablation subset with 10 runs per condition. 240 ablation runs per ablation × 8 ablations = 1,920 ablation runs.

### What this proves

Component-level attribution at fine granularity. Lets the paper claim with precision: "the X component contributes Y percentage points to anchor completeness; the Z component contributes negligibly." Honest reporting of negligible contributions also strengthens the paper.

---

## Total Compute Budget

Aggregating across all expansions:

| Workload | Run Count |
|----------|-----------|
| Backend matrix (8 backends × 120 tasks × 10 runs) | 9,600 |
| Backend matrix perturbations (8 × 150 × 5) | 6,000 |
| Baseline matrix (6 baselines × 120 tasks × 10 runs) | 7,200 |
| Baseline matrix perturbations (6 × 150 × 5) | 4,500 |
| Extended adversarial (14 systems × 200 new perturbations × 5) | 14,000 |
| Hold-out domain generalization | 4,200 |
| Ablations (8 ablations × 30 tasks × 10 runs) | 2,400 |
| Human expert baseline | 30 (one-shot) |
| Human-vs-judge grading | 100 outputs |
| **Approximate total automated runs** | **~48,000** |

At an average of 20 seconds per run (mix of small local and large API), total compute wall-clock is approximately 270 hours per sequential lane. With parallelism across 4 lab workstations and 2 API providers (Claude, GPT), parallelism factor of 6 gives ~45 hours of compute wall-clock. Trivially feasible over the 10-day execution window in Phase 6.

API cost estimate: at $0.005 per typical run for API-based systems (~40% of total), and the rest local at near-zero marginal cost: ~$1,500 to $2,000 total in API costs. Lab budget level, not grant-level.

---

## SME Workload (Unchanged)

The SME workload does NOT scale with the system matrix. SMEs author ground truth, do realism audits, and provide spot-checks. None of these depend on the number of systems evaluated.

| SME activity | Hours |
|--------------|-------|
| Pilot signoffs (2 tasks) | 0.5 |
| Realism audit (10 tasks) | 1 |
| Main signoff (40 tasks) | 8-10 |
| Overlap sample for IRR | 1 |
| Possible human-vs-judge grading | 2 |
| **Total per SME** | **12-15** |

Add 1-2 external SMEs from a different domain for the hold-out generalization test: ~3 hours each.

External spot-checker (independent verification): ~3 hours.

Human expert for upper-bound baseline: ~6 hours for 30 specifications.

**Total external recruitment ask: ~12 hours across 2-3 external participants.**

---

## Timeline (Revised)

| Week | Phase | Notes |
|------|-------|-------|
| 1 | Pre-registration | Expanded scope; multi-day approval |
| 2 | Phase 0 pilot | Same |
| 3 | Phase 1 calibration + Phase 2 corpus generation start | Same |
| 4-5 | Phase 2 corpus | 120 tasks + hold-out domain |
| 6-7 | Phase 3 ground truth | SME signoffs |
| 8 | Phase 4 baseline calibration | 6 baselines in parallel |
| 9 | Phase 5 + 6 | Perturbations generated; backend and baseline matrix executed |
| 10 | Phase 7 | All 8 ablations |
| 11 | Phase 8 | Grading + Phase 8.5 human-vs-judge (100 outputs) |
| 12 | Phase 8 (continued) + analysis start | Hierarchical models, Bayesian supplementary |
| 13 | Phase 9 analysis | Hold-out evaluation |
| 14 | Buffer + final report | Larger report due to expanded scope |

14 weeks instead of 13. The marginal week reflects the expanded analysis complexity, not data collection.

---

## What Defensible Q1+ Looks Like After v4

After applying v4 expansions, the empirical section will support:

- "MANDATE achieves X% higher anchor completeness than the best of 6 baselines across 3 domains, with the effect holding across 8 LLM backends and replicating on a held-out 4th domain."
- "Component ablations isolate that Y component contributes the majority of the gap detection improvement, while Z component contributes negligibly."
- "LLM-as-judge methodology validated against 100 human-graded outputs with Spearman ρ = ___, comparable to inter-human agreement."
- "MANDATE matches/approaches human expert performance on a 30-task gold standard comparison."
- "Adversarial resistance holds across 7 perturbation types with 50 trials each."
- "Bayesian posterior probabilities and hierarchical model variance decomposition independently support the frequentist conclusions."

These are claims a Q1 reviewer cannot easily reject on empirical grounds. The paper will then stand or fall on writing quality, framing, and contribution scope, not on the empirical foundation.

---

## What This Does NOT Solve

Honest acknowledgment of remaining limitations:

- **Single research team execution.** Independent replication by a non-affiliated team would still strengthen the work, but is out of scope.
- **Limited domain coverage.** Even with 4 domains, generalization to medical, legal, scientific research, or other operational contexts remains future work.
- **English-only corpus.** Multi-lingual robustness is not tested.
- **Specification quality vs. specification utility.** This evaluation measures specification quality against expert ground truth; it does not measure whether the specifications lead to better downstream agent execution. Connecting MANDATE to a runtime evaluation is identified as future work in the paper.

These limitations are explicitly stated in Threats to Validity (External Validity section). Reviewers may still flag them; the response is "yes, future work."

---

## Decision Required from Cal

To proceed with v4 expansion, decisions needed:

1. **Backend matrix scope.** Recommend 6 backends to start: Qwen3 fine-tuned, Qwen3 base, Llama 3.3, Mistral Large 2, Claude Sonnet 4 via API, GPT-4o via API. Expand to 8 if Gemma 3 and GPT-OSS are easy to add. **Cal approve?**

2. **Baseline matrix scope.** Recommend 5 LLM baselines plus human expert upper bound. Drop CrewAI and LangGraph if redundant with AutoGen. **Cal approve?**

3. **Hold-out 4th domain.** Software engineering specifications or operations/maintenance? Either works; pick based on SME recruitment feasibility. **Cal decide.**

4. **Human expert recruitment.** Need a senior practitioner from one of the operational domains (CISO, CFO, intelligence operations lead) to author 30 specifications. ~6 hours. **Cal identify candidate.**

5. **External SMEs for hold-out domain.** 1-2 SMEs from the chosen hold-out domain. ~3 hours each. **Cal identify candidates.**

6. **Phase 8.5 grader.** Cal or external? If Cal, then for tasks where Cal did NOT author ground truth, he can serve as the human-vs-judge grader. Recommended approach. **Cal approve.**

7. **Bayesian and hierarchical models.** Adds analytical complexity. Recommend yes, given Q1+ goal. **Cal approve.**

8. **Timeline extension.** 13 weeks → 14 weeks. **Cal approve.**

Decisions 1-2 are gating: they determine the pre-registration content. Decisions 3-5 are recruitment gating: timeline depends on external person availability. Decisions 6-8 are analytical: can be made later.

---

## Files to Update for v4

If v4 is approved, update:

- `00_PREREGISTRATION_TEMPLATE.md`: expand §4.1 baselines, §4.2 ablations, §6 metrics including new types, §7 statistical plan to include Bayesian and hierarchical, §13 Threats to Validity
- `00_PLAYBOOK_v2.md`: revised timeline, expanded Phase 6 execution matrix, expanded Phase 8.5 human-vs-judge, hold-out generalization phase
- `PROMPTS.md`: add 2 new perturbation type prompts (OOD, length); human expert briefing prompt
- `FORMS.md`: add human expert briefing form; expanded human-vs-judge calibration form
- `ANALYSIS_PLAN.md`: add Bayesian notebook section, hierarchical model notebook section, hold-out comparison notebook section
- `CHECKLIST.md`: integrate all v4 phase items
- `SETUP.md`: install all backends (Llama, Mistral, etc.) and frameworks (AutoGen, CrewAI, LangGraph); environment.yml additions for Bayesian (PyMC, ArviZ) and hierarchical modeling (statsmodels mixed effects, or brms/Stan)

---

**Bottom line.** v3 is defensible at Q1. v4 is definitive: a body of evidence that, on its empirical merits, becomes hard to reject. The marginal investment is 1 extra week of timeline, 12 extra hours of external SME recruitment, and roughly $2,000 in API costs. The marginal return is moving from "this paper has a reasonable empirical section" to "this paper sets a new bar for how to evaluate agent specification frameworks."

Given that you have been rejected twice on empirical grounds, the definitive path is the right one.
