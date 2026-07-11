# Q1 Audit and Enhancements

**Purpose:** Audit the v2 package against top-quartile journal empirical standards (TSE, TOSEM, EMSE, TPAMI, JAIR, Requirements Engineering) and specify the additional protocol elements required to reach that bar. Since compute is not a constraint (AEGIS (Autonomous Engineering Governance and Intelligence System) is built, lab cluster is operational), every recommended enhancement that strengthens science is included.

---

## Part 1: Audit Against Q1 Standards

### Honest scorecard

| Q1 Requirement | v2 Status | Action |
|----------------|-----------|--------|
| Pre-registration with hypotheses, metrics, sample plan | Present | None |
| Formal sample size justification via power analysis | Present | Expand sample (compute is free) |
| Inter-rater reliability with appropriate metrics (kappa, alpha) | Present | None |
| Effect sizes (Cohen's h, d) with confidence intervals | Present | None |
| Multiple testing correction (Holm-Bonferroni, BH) | Present | None |
| Pilot phase with halt rules | Present | None |
| Calibration set (positive control) | Present | None |
| Ablation studies isolating component contributions | Present | None |
| Sensitivity analyses for headline findings | Present | None |
| Failure mode taxonomy with manual coding | Present | None |
| Replication package | Present | None |
| Cross-family LLM judges with bias controls | Present | None |
| Blinding throughout grading | Present | None |
| **Threats to Validity (TTV) framework** | **MISSING** | **Add as new section** |
| **Construct validity defense for each metric** | **MISSING** | **Add to pre-reg** |
| **Human-vs-LLM-judge calibration** | **MISSING** | **Add sub-phase** |
| **Third baseline (current SOTA multi-agent framework)** | **MISSING** | **Add AutoGen as Baseline 3** |
| **Backend portability test (MANDATE on multiple LLMs)** | **MISSING** | **Add as ablation 4** |
| **Compute and cost transparency** | **MISSING** | **Add to capture protocol** |
| **Corpus test-retest reliability** | **MISSING** | **Add validation step** |
| **Larger sample exploiting available compute** | 90 tasks | **Expand to 120 (40 per domain)** |
| **More runs per condition** | 3 runs | **Expand to 5 runs** |

The v2 protocol is solid for Q2-Q3 venues. The seven items marked MISSING are what separates Q2 from Q1. Each is now specified below as a protocol addition.

---

## Part 2: Q1 Enhancements (Apply to Existing Phases)

### Enhancement 1: Sample Expansion (90 → 120 tasks)

**Rationale.** Compute is free; SMEs are the bottleneck. 120 tasks at 40 per SME is approximately 9-10 hours of work per SME (8-12 minutes per signoff), a meaningful but realistic ask. The expanded sample provides:

- Statistical headroom for Cohen's h = 0.2 detection (currently sized for h = 0.3)
- Larger subgroup sizes (40 per domain enables stronger per-domain claims)
- More tasks available for ablation subset expansion (30 instead of 20)

**Action.**

Update pre-registration Section 3.1: corpus increases from 90 to 120 tasks (40 per domain). Within-domain composition unchanged: 24 full-spec (60%), 12 gap-triggering (30%), 4 stretch cases (10%).

Update SME workload: 40 tasks per SME instead of 30. Confirm with Brad and Jason before pre-reg deposit that this is feasible. If not, fallback to 105 tasks (35 per domain, 35 per SME).

Update power analysis in pre-reg: at n=120 with α=0.0125 (Holm-Bonferroni) and 80% power, detectable Cohen's h drops from 0.30 to 0.26.

### Enhancement 2: Runs Per Task (3 → 5)

**Rationale.** Three runs is the minimum for variance estimation. Five gives meaningfully tighter confidence intervals on stochastic stability metrics and reduces the risk that a single outlier run skews per-task median computation. Cost is purely compute, which is free.

**Action.**

Update Playbook §12.1: each system runs each task five times. Total runs become:

- 3 systems (MANDATE, Baseline 1, Baseline 2) × 120 tasks × 5 runs = 1,800 task runs
- Plus 1 additional system (Baseline 3, see Enhancement 4) = 2,400 task runs
- Plus 4 systems × 150 perturbations × 5 runs = 3,000 perturbation runs
- Plus ablations: 4 ablation variants × 30 tasks × 5 runs = 600 ablation runs
- **Total: ~6,000 runs**

Update Playbook §12.3: per-task metric is now median across 5 runs; stability rate is fraction of tasks with 5/5 equivalent runs. Stability classifications: stable (5/5), mostly stable (4/5), unstable (3/5 or worse).

### Enhancement 3: Threats to Validity Framework

**Rationale.** Every Q1 empirical SE paper has a structured TTV section. Reviewers in 2026 expect coverage of all four validity types (Cook and Campbell tradition). Missing this section produces immediate desk rejection at TSE/TOSEM/EMSE.

**Action: Add Section 13 to pre-registration and Section 7 to final report.**

```markdown
## Threats to Validity

### Construct Validity (are we measuring what we claim?)

**Threat:** Anchor completeness rewards systems that produce many fields,
which may not reflect specification quality.
**Mitigation:** Fabrication rate is reported alongside completeness; a
system that maximizes completeness by inventing fields will show high
fabrication and be penalized.

**Threat:** Gap detection F1 conflates two failure types (silent gap and
false gap) that have different operational consequences.
**Mitigation:** Per-error-type reporting in supplementary analysis;
silent gaps are highlighted as the operationally worse failure.

**Threat:** Trace completeness as a binary measure may overlook trace
quality differences (e.g., useful vs. meaningless trace entries).
**Mitigation:** Trace auditability scored 0-2 by graders captures
quality; the binary completeness measure is reported only as a basic
hygiene check.

**Threat:** Adversarial resistance measured on synthetic injections may
not reflect real-world adversarial behavior.
**Mitigation:** Three sub-types (direct, social engineering, fake
authority) capture varied threat models; honest limitation
acknowledged that real attackers may use techniques not in our suite.

### Internal Validity (are the inferences valid given the design?)

**Threat:** Self-selection bias if SMEs preferentially complete easier
tasks first, leaving harder ones for time-pressured later signoff.
**Mitigation:** Task assignment randomized within each SME's batch;
task completion order recorded; sensitivity check on signoff time
quartiles.

**Threat:** Carryover effects if SMEs see related tasks and develop
implicit anchoring.
**Mitigation:** Tasks assigned to SMEs in randomized order; no
within-task feedback during signoff window.

**Threat:** LLM-as-judge bias inherits from each judge model's training
data, potentially correlated across families.
**Mitigation:** Three judges from three families; double-grading sample;
human-vs-judge calibration (Enhancement 5).

**Threat:** Baseline configurations could be suboptimal, inflating
MANDATE's relative performance.
**Mitigation:** Phase 4 documented baseline calibration with budget;
calibration log published in replication package.

### External Validity (do findings generalize?)

**Threat:** Three operational domains may not generalize to other
operational contexts (clinical, legal, manufacturing).
**Mitigation:** Domain selection (security, financial, intelligence)
spans high-stakes deliverable diversity; honest limitation that
generalization to other domains requires future work.

**Threat:** Task descriptions generated by Claude may exhibit
systematic patterns favoring MANDATE's strengths.
**Mitigation:** Realism audit by SMEs (mean ≥ 2.5); generation model
distinct from MANDATE backend; corpus diversity dimensions enforced;
test-retest reliability check on corpus generation (Enhancement 7).

**Threat:** MANDATE evaluated only with fine-tuned Qwen3 backend; may
not generalize to other LLMs.
**Mitigation:** Backend portability ablation runs MANDATE on at least
one additional LLM backend (Enhancement 6).

**Threat:** Single-organization SME pool reflects Swift Group's
operational perspective.
**Mitigation:** External spot-checker not affiliated with Swift; report
external-vs-internal agreement.

### Conclusion Validity (are the statistical conclusions sound?)

**Threat:** Multiple testing inflation from 4 primary + many secondary
analyses.
**Mitigation:** Holm-Bonferroni on primary family; Benjamini-Hochberg
on exploratory; sensitivity analyses for stability.

**Threat:** Effect size estimates may be unstable on small subgroups.
**Mitigation:** Bootstrap CIs (10,000 resamples); subgroups smaller
than 20 tasks reported as exploratory only.

**Threat:** Null findings on H3 (trace completeness) could result from
inadequate statistical power on the 95% threshold test.
**Mitigation:** Post-hoc power computation reported; if power was low,
acknowledged in limitations.
```

### Enhancement 4: Add Baseline 3 (AutoGen)

**Rationale.** Two baselines is acceptable; three is Q1-typical for novel architecture papers. AutoGen is the most-cited current multi-agent framework (Wu et al. 2023), referenced in the MANDATE paper itself (§2.2). Adding it as Baseline 3 directly addresses Reviewer 3's "lacks comparative benchmarking" complaint at the strongest level.

**Action.**

Update pre-registration §4.1 to add:

```markdown
**Baseline 3: AutoGen multi-agent**
- Framework: AutoGen v[VERSION]
- Model: [Same family as Baselines 1-2 for consistency, e.g., Claude Sonnet 4 or GPT-4]
- Agent configuration: Mirror MANDATE's role structure with AutoGen agents
  for each role (Interpreter, Decomposition, etc.), or use AutoGen's default
  planner-executor pattern, whichever is more faithful to AutoGen's
  intended usage. Document the configuration choice.
- Prompt and configuration frozen at end of Phase 4 calibration
```

Update Phase 4 (Baseline Calibration): 3-day budget for AutoGen calibration in addition to existing budgets for Baselines 1-2. Total Phase 4 extends from 1 week to ~10 days (compressible to 5 working days with parallel calibration tracks).

Update Phase 6 execution counts: includes Baseline 3 (~600 more task runs, ~750 more perturbation runs).

Update all comparative analyses: triple pairwise comparisons (MANDATE vs B1, vs B2, vs B3); apply Holm-Bonferroni across the expanded family.

**Pre-registration hypothesis update:** H2 and H4 expand to require MANDATE to outperform all three baselines (more conservative claim).

### Enhancement 5: Human-vs-Judge Calibration

**Rationale.** LLM-as-judge methodology in 2026 requires validation against human judgment to be defensible. Without this, a reviewer says "your conclusions rest on LLM judges whose accuracy is unknown." A small calibration sample produces strong defense.

**Action: Add as Phase 8.5 (between grading and analysis).**

```markdown
## Phase 8.5: Human-vs-Judge Calibration

### Sample

30 anonymized outputs sampled stratified across:
- 10 from MANDATE
- 10 from Baselines (split across the three)
- 10 from perturbed task runs

### Human Grader

A domain SME (not the same SME who authored ground truth for the
sampled tasks; recommended: Cal or external spot-checker) scores
each output using the identical grader rubric (PROMPTS §4).

### Comparison

For each of the 30 outputs, compare:
- Human score on each rubric dimension
- LLM ensemble score (majority/median) on the same dimension

Compute:
- Per-dimension correlation between human and ensemble (Spearman ρ)
- Per-dimension percent agreement
- Cohen's kappa on binary judgments
- Cases where human and ensemble disagreed substantially (≥2-point
  gap on continuous, opposite classification on categorical)

### Reporting

Human-vs-judge calibration appears in:
- Final report as a methodology validation table
- Pre-registration as a planned calibration phase
- Limitations section if agreement is below threshold

### Threshold

Target: Spearman ρ ≥ 0.7 on continuous dimensions; Cohen's kappa
≥ 0.6 on binary judgments.

If calibration agreement is below threshold, the primary findings
are reported with the caveat "LLM-as-judge methodology showed
moderate agreement with human SME grading; results should be
interpreted accordingly."

Importantly, low agreement does NOT invalidate the comparative
analyses (judges grade all systems with the same potential bias,
which cancels in within-task comparisons), but it does affect
absolute-score interpretation.
```

### Enhancement 6: Backend Portability Test

**Rationale.** A reviewer can say: "MANDATE's results only show that the fine-tuned Qwen3 ensemble works; they don't show that the MANDATE architecture itself contributes." Backend portability testing directly addresses this by running MANDATE on different LLMs and comparing.

**Action: Add as Ablation 4.**

```markdown
**Ablation 4: Backend portability**

Run the MANDATE pipeline (full role separation, registry, trace) on
TWO additional LLM backends besides the primary fine-tuned Qwen3:

- Backend B: Base Qwen3 (no fine-tuning), same Qwen3-8B and 32B variants
- Backend C: Different model family (e.g., Llama 3.1 70B or Mistral
  Large 2), running locally on the lab cluster

Test on the 30-task ablation subset (5 runs each, per Enhancement 2).

Compute the same primary metrics. Report:
- Per-backend performance vs primary Qwen3 fine-tuned
- Whether MANDATE's properties (gap detection, trace completeness)
  hold across backends
- Cost/quality trade-offs across backends

If MANDATE properties degrade substantially on alternative backends,
this is a finding: MANDATE's empirical performance is partially
attributable to fine-tuning, not architecture alone. Report honestly.

If properties hold across backends, this is strong external validity:
MANDATE works as a framework, not just as a specific implementation.
```

### Enhancement 7: Corpus Test-Retest Reliability

**Rationale.** The corpus is the foundation of every other measurement. If different generation seeds produce systematically different corpora, the findings depend on the specific corpus draw, not on the framework being evaluated. Test-retest reliability on corpus generation validates the corpus itself.

**Action: Add to Phase 2 (Corpus Generation).**

```markdown
### Section 8.7: Test-Retest Reliability on Corpus Generation

After the main corpus is finalized, generate a parallel corpus of
30 tasks (10 per domain) using the identical generation prompt but
a different random seed.

Compare the two corpora on:
- Task length distribution (Kolmogorov-Smirnov test for distributional
  similarity)
- Stakeholder type diversity (chi-square goodness-of-fit)
- Category balance (full-spec / gap-triggering / stretch case proportions)
- Domain-specific terminology frequency

Report similarity findings. If the two corpora differ substantially
on key dimensions, this is reported as a corpus-generation
reliability limitation. If they are similar, this is positive
methodological evidence.

The parallel corpus is NOT used in primary analyses; it serves only
as a validation artifact. It is included in the replication package
for transparency.
```

### Enhancement 8: Compute and Cost Transparency

**Rationale.** Reproducibility costs money. Q1 venues increasingly require cost transparency so independent replicators can estimate budget. Cost is also a confound: if MANDATE costs 10x as much as a baseline to run, that affects practical recommendation.

**Action: Add tracking and reporting throughout.**

Update Playbook §12.4 (Output Capture):

```markdown
For every run, capture:
- Wall-clock time, role-by-role for MANDATE; total for baselines
- API cost (for cloud-based baselines): input tokens × input price +
  output tokens × output price, captured per provider's billing
- Local compute cost (for MANDATE on lab cluster): GPU-hours or
  CPU-hours × estimated cost-per-hour for equivalent cloud GPU

Aggregate per system:
- Mean cost per task
- Mean cost per perturbation
- Total study cost per system
- Cost-effectiveness: mean anchor completeness per dollar
```

Add to final report as Table 6:

```markdown
| System | Mean cost / task (USD) | Mean cost / perturbation (USD) | Total study cost (USD) | Anchor completeness per $ |
|--------|------------------------|--------------------------------|------------------------|---------------------------|
| MANDATE | | | | |
| Baseline 1 | | | | |
| Baseline 2 | | | | |
| Baseline 3 | | | | |
```

### Enhancement 9: Construct Validity Defense

**Rationale.** Construct validity is "are we measuring what the framework claims to provide?" Q1 reviewers expect an explicit defense for every metric.

**Action: Add to pre-registration §6 (Metrics) as a new subsection.**

```markdown
### 6.4 Construct Validity for Each Metric

**Anchor Completeness.** MANDATE claims to produce tolerance-based
specifications with minimum, target, and constraint dimensions. Anchor
completeness measures how many of the SME-identified dimensions the
system extracts. This directly operationalizes MANDATE's specification
quality claim. Confounds (e.g., a system that produces many fields by
fabrication) are controlled by Fabrication Rate.

**Gap Detection F1.** MANDATE claims to identify when specifications
are underspecified rather than fabricating completions. Gap F1
measures whether the system correctly classifies tasks as
gap-triggering vs. fully-specifiable, against SME-identified gaps.
This operationalizes MANDATE's automation-readiness diagnostic claim.

**Trace Completeness.** MANDATE claims to produce auditable decision
provenance. Trace completeness measures whether the 6-role pipeline
produces a complete hash-linked trace. This operationalizes MANDATE's
governance-readiness claim. Trace quality (vs. mere presence) is
captured by the separate Trace Auditability rubric scored by judges.

**Adversarial Resistance.** MANDATE claims role separation and
anchor immutability provide robustness against subversion. Adversarial
resistance measures whether the system maintains its specification
contract under prompt injection. This operationalizes MANDATE's
robustness claim.

**Fabrication Rate.** Independent metric that controls for
construct-validity threats on Anchor Completeness (a system maximizing
completeness via fabrication will show high fabrication). Lower is
better; reported alongside completeness.
```

---

## Part 3: Updated Sample Size and Effort Estimate

### Revised numbers

| Element | v2 | v3 (Q1) |
|---------|----|----|
| Main corpus tasks | 90 | 120 |
| Tasks per SME | 30 | 40 |
| Runs per task per system | 3 | 5 |
| Total baselines | 2 | 3 |
| Ablations | 3 | 4 (adds backend portability) |
| Ablation subset size | 20 | 30 |
| Total system runs (tasks + perturbations + ablations) | ~2,200 | ~6,000 |
| Human-vs-judge calibration sample | 0 | 30 outputs |
| Estimated SME hours each | 8 | 10-12 |

### Revised timeline

| Week | Phase | Change from v2 |
|------|-------|----------------|
| 1 | Pre-registration | Includes TTV, construct validity, expanded baselines section |
| 2 | Phase 0 pilot | Same |
| 3 | Phase 1 calibration + corpus generation start | Same |
| 4-5 | Phase 2 corpus (120 tasks) | Adds test-retest corpus + realism audit |
| 6-7 | Phase 3 ground truth (40 per SME) | Slightly longer SME window |
| 8 | Phase 4 baseline calibration (3 baselines) | Extended to 10 days |
| 9 | Phase 5+6 perturbations + execution (5 runs, 4 systems) | Longer compute window |
| 10 | Phase 7 ablations (4 variants, 30 tasks) | Extended |
| 11 | Phase 8 grading + Phase 8.5 human-vs-judge calibration | Adds human grading |
| 12 | Phase 9 analysis | Same |
| 13 | Buffer + final report | Buffer week is now week 13 not week 12 |

Total: 13 weeks instead of 12. The extra week reflects realistic effort for Q1 rigor.

### SME confirmation needed

Before depositing pre-registration with these enhancements, confirm with Brad and Jason:

- Each will commit ~10-12 hours of signoff work spread over weeks 5-7 (40 tasks at ~15 min each)
- Plus ~1 hour realism audit (10 tasks)
- Plus ~30 minutes pilot signoff (2 tasks)
- Plus possible 1 hour human-vs-judge calibration if Cal is unavailable

Total SME commitment: ~12-14 hours over 6 weeks. If this is not feasible, fall back to: 105 main corpus tasks (35 per SME), same enhancements otherwise.

---

## Part 4: Files To Update for Q1 Enhancement

### Update CHECKLIST.md

Add Q1 enhancement items to each phase:

- Phase 0: Confirm SME commitment for 40-task signoff workload
- Phase 2: Add corpus test-retest reliability sub-step (Enhancement 7)
- Phase 4: Calibrate three baselines instead of two (add AutoGen as Baseline 3)
- Phase 6: Capture compute and cost metrics per run (Enhancement 8)
- Phase 7: Add Ablation 4 (backend portability) (Enhancement 6)
- Phase 8: Same
- Phase 8.5 (NEW): Human-vs-judge calibration (Enhancement 5)
- Phase 9: Add Threats to Validity analysis (Enhancement 3); add construct validity table; add cost-effectiveness analysis
- Final report: TTV section, construct validity defense, cost table

### Update Pre-Registration Template

Add the following sections to `00_PREREGISTRATION_TEMPLATE.md`:

- §4.1: Baseline 3 (AutoGen) — definition, version, configuration plan
- §6.4: Construct Validity for Each Metric — defense of each metric (Enhancement 9)
- §13: Threats to Validity — all four validity types with mitigations (Enhancement 3)
- §3.4: Backend Portability Ablation — addition to ablation list (Enhancement 6)
- §3.5: Test-Retest Reliability on Corpus Generation — methodology validation (Enhancement 7)
- §6.5: Compute and Cost Tracking — what is captured per run (Enhancement 8)

### Update Forms

Add to `FORMS.md`:

- Human-vs-judge calibration form: identical to grader prompt rubric, applied by a human grader on the 30-output calibration sample

### Update Setup

Add to `SETUP.md`:

- AutoGen installation and configuration
- Additional LLM backend setup for Ablation 4 (base Qwen3 + a different family)
- Cost tracking integration (API usage logging)

---

## Part 5: What This Buys You

### Closes these specific reviewer objections

| Reviewer Likely Objection | Closed By |
|---------------------------|-----------|
| "Insufficient comparative benchmarking" | 3 baselines + 4 ablations |
| "LLM-as-judge methodology not validated" | Human-vs-judge calibration (Enhancement 5) |
| "Lacks threats to validity discussion" | TTV framework (Enhancement 3) |
| "Construct validity unclear" | Per-metric defense (Enhancement 9) |
| "Doesn't generalize across LLMs" | Backend portability ablation (Enhancement 6) |
| "Corpus may be biased toward MANDATE" | Test-retest reliability (Enhancement 7) |
| "Cost-effectiveness not analyzed" | Compute and cost transparency (Enhancement 8) |
| "Sample too small for subgroup claims" | 120 tasks instead of 90 |
| "Insufficient runs for variance estimate" | 5 runs instead of 3 |

### Estimated reviewer confidence

A reviewer at TSE, TOSEM, EMSE, or Requirements Engineering reading this protocol will not be able to easily reject on empirical grounds. They can still reject on framing, contribution, or scope grounds, but the empirical section will be defensible.

A reviewer at TPAMI or JAIR (ML-leaning) will see strong empirical methodology with the caveat that ML benchmarks often use larger samples (1000+); the 120-task corpus is appropriate for a framework paper but would be small for a pure benchmark paper. This is acknowledged in External Validity.

---

## Part 6: Recommended Decision

The honest recommendation: apply all 9 enhancements. Compute is free, methodology is everything, and you've already been rejected twice on empirical grounds. The marginal cost of going from Q2-quality to Q1-quality methodology is:

- 1 extra week of timeline (12 → 13 weeks)
- 2-4 extra hours per SME
- Additional compute (which you have)
- Additional analysis sections in the final report

The marginal benefit is: substantial improvement in defense against the exact rejection class you have been receiving.

Before applying, get explicit SME commitment from Brad and Jason on the expanded workload. If they cannot commit, fall back to 105-task corpus and accept the small power reduction.

---

**End of Q1 audit and enhancements.**

Apply these enhancements before pre-registration deposit. Once the pre-registration is on Zenodo, the protocol is locked.
