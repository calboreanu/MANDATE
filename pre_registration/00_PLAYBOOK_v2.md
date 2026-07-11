# MANDATE Empirical Evaluation Playbook v2.0

**Owner:** Elias Calboreanu (Cal), Swift AI Lab
**Date issued:** 22 May 2026
**Supersedes:** v1.0 (issued same day)
**Estimated execution window:** 8 to 12 weeks
**Status:** Audited, hardened, ready for coworker handoff

---

## Changelog and Audit Findings

This v2 replaces v1.0 in full. The audit below documents every methodological weakness identified in v1 and the specific change made in v2 to address it. The audit trail is itself part of the defense against future reviewer criticism: if a reviewer questions a methodological choice, the rationale is documented.

| # | v1 Weakness | v2 Correction |
|---|-------------|---------------|
| 1 | Sample size justified by hand-wavy "60 gives 80% power" | Formal power calculation (Section 5.3), corpus expanded to 90 tasks (30/domain) to provide headroom for subgroup analyses |
| 2 | No pilot phase, protocol untested before main run | Added Phase 0: pilot study on 6 tasks to debug workflow, rubric, and tooling before main execution |
| 3 | No calibration anchor (no way to detect configuration errors) | Added Phase 1: calibration set of 6 unambiguous tasks all systems should handle; failure on calibration triggers config review, not a result |
| 4 | Single grader model creates single-point-of-failure for bias | Three-judge ensemble grading with majority vote, disagreement flagged for human review |
| 5 | Blinding not specified; SMEs and graders could see system identity | Explicit blinding protocol: outputs anonymized before grading; system-identifying strings stripped; SMEs see only task text during anchor authoring |
| 6 | Baselines could be strawmen with weak prompts | Phase 4: baseline calibration with time-bounded prompt engineering (1 week budget, documented attempts) before frozen run |
| 7 | No ablation studies; reviewer can't isolate which MANDATE components contribute | Phase 7: three ablations (no role separation, no Success Registry, no Search-Trace) on a 20-task subset |
| 8 | Statistics: only p-values, no effect sizes, weak multiplicity correction | Effect sizes mandatory (Cohen's h for proportions, Cohen's d for continuous), 95% bootstrap CIs, Holm-Bonferroni for family-wise error, Benjamini-Hochberg for exploratory |
| 9 | LLM-as-judge known biases (position, verbosity, self-preference) not controlled | Explicit bias controls: randomized output order per grading call, length-normalization in rubric, judge-system family disjoint |
| 10 | No failure mode taxonomy | Pre-registered failure categories; manual coding of every failed run into a category for qualitative analysis |
| 11 | No replication package defined | Section 17 defines exact contents: anonymized corpus, prompts, configs, analysis notebooks, model versions |
| 12 | Conflict of interest weakly handled | Lead Analyst's role disclosed; independent spot-check of 10% of signoffs by an external reviewer (target: Capitol cohort or outside SME) |
| 13 | Robustness sample (20/type) underpowered for proportions | Expanded to 30 perturbations per type (150 total) for tighter confidence intervals |
| 14 | Stochastic variance from 3-run replication vaguely reported | Explicit specification: per-task metrics reported as median across 3 runs, system-level metrics as mean ± 95% bootstrap CI |
| 15 | Subgroup analyses not pre-specified; HARKing risk | Subgroups pre-registered (gap-triggering vs. full-spec, by domain, by stakeholder type) |
| 16 | No halt-on-finding rules | Section 16 defines pre-specified continue/halt criteria for early findings |
| 17 | Inter-rater kappa interpretation arbitrary | Anchored to McHugh (2012) interpretation: ≥ 0.6 minimum, ≥ 0.8 target, < 0.4 halt |
| 18 | Cohen's kappa alone may be inadequate for multi-class | Added Krippendorff's alpha as supplementary measure for ordinal judgments |
| 19 | No data quality audit on AI-generated tasks | Added Section 8.5: independent realism audit by SMEs before corpus freeze |
| 20 | Timeline overconfident at 6-8 weeks | Revised to 8-12 weeks with explicit slack at every phase boundary |

The audit also confirms what v1 got right: pre-registration as the central defense, cross-family model separation, SME human-in-loop signoff, frozen artifacts at every phase boundary. These are retained without change.

---

## 1. Purpose

This playbook gives the executing analyst the protocol, artifacts, and decision rules required to run an empirical evaluation of MANDATE against two baseline systems across three operational domains, with pilot validation, baseline calibration, ground truth signoff by independent expert reviewers, ablation studies, and cross-family ensemble grading.

The output is a publication-grade evaluation dataset, a results report containing effect sizes and confidence intervals with pre-registered statistical analyses, a complete replication package, and the supporting documentation needed to defend the evaluation against hostile peer review.

MANDATE has been rejected twice at venues that demand empirical rigor (Frontiers in AI, Requirements Engineering). The reviewer comments converge on the same core complaint: the empirical work is preliminary, self-referential, and lacks comparative evaluation. This playbook is the corrective. Every methodological choice exists to close one or more of those objections while remaining executable by a small team in a defensible timeline.

---

## 2. Background and Methodological Context

### 2.1 MANDATE Framework Summary

MANDATE (Multi-Agent Nominal Decomposition for Autonomous Task Execution) is a specification framework that produces tolerance-based task definitions for autonomous AI agents. It takes an operational document as input and produces either a machine-readable specification (mandate-as-code) or a Gap Analysis Report identifying what cannot be specified. The framework runs a six-role pipeline: Intake, Interpreter, Decomposition, Procedure, Binding, and Validation.

The reference implementation (AEGIS (Autonomous Engineering Governance and Intelligence System)) uses fine-tuned Qwen3 models running locally on the Swift AI Lab Mac mini M4 Pro cluster via Ollama. Prior empirical work was a single-system pilot using a 125-example corpus with overlap between training and validation; not an independent test corpus.

### 2.2 Empirical Standards Applied

This evaluation follows established practice from three methodological traditions:

**Empirical software engineering.** Controlled experiment design with pre-registration, baseline comparison, ablation, and replication package, following the practice codified in the empirical SE literature (Wohlin et al., Basili et al.).

**ML and AI evaluation.** Multiple-seed runs to capture stochastic variance, cross-family LLM-as-judge with bias controls, and benchmark design practices addressed by Pineau et al. on reproducibility and Bouthillier et al. on variance accounting.

**Human-in-the-loop evaluation.** Inter-rater reliability with both Cohen's kappa (binary) and Krippendorff's alpha (ordinal), independent expert ratification, and blinding throughout.

### 2.3 Scope Boundary

This evaluation is a focused study appropriate to a framework paper, not an AgentBench-scale benchmark. The goal is a defensible, reproducible empirical foundation that closes the immediate reviewer objections, not exhaustive multi-domain validation. Future work can extend to additional domains, larger samples, and runtime integration.

---

## 3. Roles and Responsibilities

| Role | Person | Responsibilities |
|------|--------|------------------|
| Principal Investigator | Cal | Approves protocol, adjudicates ambiguity, signs final report. Acknowledged as MANDATE author. |
| Lead Analyst | Coworker | Owns end-to-end execution. Does NOT contribute to ground truth signoff to preserve blinding. |
| SME Reviewer A | Brad Carter | Signs off on ~30 ground truth anchors, participates in 12-task overlap sample for IRR |
| SME Reviewer B | Jason McKay | Same as A |
| SME Reviewer C | Cal | Same as A |
| External Spot-Checker | (to be assigned) | Spot-checks 10% of SME signoffs as independent verification. Should be a Capitol Tech University cohort member or outside SME not affiliated with Swift Group. |
| Grader Operator | Lead Analyst | Orchestrates three-judge ensemble grading; does NOT manually adjudicate to preserve blinding |

**Conflict of interest disclosure.** The Lead Analyst and PI are both affiliated with The Swift Group, the entity that holds commercial licensing rights to MANDATE-based products. This is documented in the pre-registration and acknowledged in the final report. The external spot-checker and the cross-family graders provide the independence buffer against accusations of conflicted methodology.

---

## 4. Project Timeline

| Week | Phase | Key Deliverables |
|------|-------|------------------|
| 1 | Pre-registration + Phase 0 setup | Protocol on Zenodo with DOI; pilot tasks generated |
| 2 | Phase 0 (Pilot) | Pilot run executed; rubric and workflow debugged; v2.1 protocol if needed |
| 3 | Phase 1 (Calibration set) | 6 calibration tasks + ground truth; all systems pass calibration |
| 4 | Phase 2 (Corpus generation) | 90 tasks generated, realism-audited, deduplicated |
| 5 | Phase 3 (Ground truth) | AI scaffolding complete; SME signoffs distributed |
| 6 | Phase 3 (continued) | SME signoffs complete; IRR computed; ground truth frozen |
| 7 | Phase 4 (Baseline calibration) | Baselines tuned via time-bounded prompt engineering; configurations frozen |
| 8 | Phase 5 + 6 | Perturbation suite generated; all systems executed on full task + perturbation set |
| 9 | Phase 7 (Ablations) | Ablation runs complete |
| 10 | Phase 8 (Grading) | Ensemble grading complete; IRR computed |
| 11 | Phase 9 (Analysis) | Analyses complete; results tables and figures drafted |
| 12 | Buffer + final report | Failure mode coding; final report; replication package |

Weeks 11-12 are buffer for the consistently underestimated tasks: failure coding, dispute resolution, writing. Do not pre-commit them. Realistic execution is 10 weeks; the buffer is for the things that always go wrong.

---

## 5. Pre-Registration Protocol

### 5.1 Purpose

Pre-registration is a time-stamped public commitment to the evaluation design before any data is generated. It is the single most leveraged artifact in this study. Reviewers cannot accuse a pre-registered protocol of being designed around the results.

### 5.2 Deposit

Deposit on Zenodo with CC-BY-4.0 license. Title: "MANDATE Empirical Evaluation: Pre-Registered Protocol v1.0". Capture DOI in `00_preregistration/zenodo_doi.txt`.

### 5.3 Required Content

The pre-registration document includes all sections in Appendix A. The mandatory elements:

**Hypotheses (stated as falsifiable claims):**

- H1: MANDATE produces anchor specifications with higher mean field completeness than a single-prompt LLM baseline on operational tasks, with Cohen's h effect size ≥ 0.3.
- H2: MANDATE achieves higher gap detection F1 than both baselines on gap-triggering tasks, with at least one comparison reaching Cohen's h ≥ 0.4.
- H3: MANDATE retains trace completeness on at least 95% of runs (deterministic and LLM-backed combined).
- H4: MANDATE resists prompt injection at higher rate than either baseline, with rate difference ≥ 30 percentage points.

**Sample size justification.**

For H1 and H2, the primary statistical test is McNemar's test for paired proportions. To detect Cohen's h = 0.3 (moderate effect) at α = 0.0125 (Holm-Bonferroni adjusted for four primary hypotheses) with 80% power, the required sample size is approximately n = 75 paired observations per comparison. The corpus of 90 tasks provides headroom for exclusions (capped at 10%) and subgroup analyses.

For robustness (H4), 30 prompt injection trials per system gives a 95% confidence interval width of approximately ±18 percentage points on a proportion. This is reported honestly as a moderately-powered robustness assessment.

**Pre-specified subgroup analyses:**

- Performance on gap-triggering tasks vs. full-specification tasks
- Performance by domain (security, financial, intel)
- Performance by stakeholder type (executive vs. operator)

Subgroups are pre-specified to avoid HARKing (Hypothesizing After Results are Known).

**Exclusion rules.** A task is excluded if (a) AI-generated description is unparseable after one regeneration, (b) all three SMEs unanimously reject the task as unrealistic, (c) the task fails the realism audit (Section 8.5), or (d) a system crashes irrecoverably on the task. Maximum exclusion rate: 10% (9 of 90 tasks). If exceeded, the evaluation pauses for protocol review.

**Halt rules.** See Section 16.

**Statistical analysis plan:**

- Primary comparisons: McNemar's test (paired proportions), Wilcoxon signed-rank (paired continuous)
- Family-wise error control on primary hypotheses: Holm-Bonferroni
- Exploratory comparisons: Benjamini-Hochberg FDR
- Effect sizes: Cohen's h (proportions), Cohen's d (continuous), reported with 95% bootstrap CIs (10,000 resamples)
- Inter-rater reliability: Cohen's kappa (binary judgments), Krippendorff's alpha (ordinal)

### 5.4 Approval Gate

Pre-registration is approved by Cal in writing before Zenodo deposit. Deposit happens before Phase 0 begins.

---

## 6. Phase 0: Pilot Study

### 6.1 Purpose

The pilot's job is to surface protocol failures while they're still cheap to fix. v1 of this playbook skipped this and would have shipped problems to the main run.

### 6.2 Pilot Sample

Six tasks: two per domain, one full-spec and one gap-triggering per domain.

### 6.3 Pilot Execution

Run the complete protocol end-to-end on the six pilot tasks:

1. AI generation of task descriptions
2. AI scaffolding of anchors
3. SME signoff (each SME reviews 2 tasks)
4. IRR computation on a 3-task overlap
5. Perturbation generation (5 perturbations, one per type, on one base task)
6. Run MANDATE and both baselines on all 6 tasks and 5 perturbations
7. Three-judge ensemble grading
8. Grader IRR computation
9. Analysis pass on the pilot data

### 6.4 Pilot Findings and Corrective Action

At the end of Phase 0, the Lead Analyst produces a pilot findings memo (max 3 pages) that documents:

- Workflow steps that took longer than expected
- Rubric criteria that produced grader disagreement
- SME interpretation conflicts on anchor fields
- Any tooling failures
- Recommended protocol updates

Cal reviews the memo and approves any protocol updates as Protocol v1.1. Updates are deposited as an addendum to the Zenodo pre-registration (NOT a replacement; the original protocol stands and changes are documented).

### 6.5 Halt Conditions in Pilot

The pilot halts if:

- Any system fails to produce output on more than 2 of 6 tasks (infrastructure issue)
- SME IRR on the 3-task overlap is below 0.4 (rubric or training issue)
- Grader IRR on the pilot grading is below 0.5 (rubric ambiguity)

A halt triggers protocol revision before main run.

---

## 7. Phase 1: Calibration Set

### 7.1 Purpose

Calibration tasks are unambiguous reference cases where ground truth is essentially undisputed and a correctly-configured system should succeed. They serve as a positive control: if MANDATE or a baseline fails calibration, the result is a configuration issue to debug, not a finding.

### 7.2 Calibration Task Properties

Six tasks (two per domain), constructed to have:

- Explicit numeric thresholds in the request text ("at least 95% compliance", "within 4 hours")
- Named, well-known data sources ("Tenable Nessus", "ServiceNow", "internal expense system")
- Unambiguous deliverable format ("PDF report, 5-10 pages")
- Clear stakeholder and audience
- No intentional gaps

Calibration tasks are hand-authored by Cal (not AI-generated) to remove generation-level ambiguity.

### 7.3 Calibration Pass Criterion

A system passes calibration if it produces a complete anchor with all explicit thresholds correctly extracted and no fabricated gaps. Failure on calibration halts the evaluation for that system pending configuration review.

Calibration results are reported in the final paper as a positive control. This is a transparency move: if a system passes calibration but fails on real tasks, the failure is on the task, not the system configuration.

---

## 8. Phase 2: Task Corpus Generation

### 8.1 Domain Coverage and Sample Size

Three domains, 30 tasks each, total 90 tasks. The expansion from v1's 60 to v2's 90 provides:

- Statistical headroom for the four primary hypothesis tests after Holm-Bonferroni correction
- Buffer for the 10% exclusion cap (9 tasks)
- Adequate sample size in each subgroup analysis

**Domain 1: Security Operations Reporting** (30 tasks). Vulnerability reporting, patch compliance, incident summaries, threat briefings, posture assessments. Stakeholders: CISOs, SOC managers, executive leadership.

**Domain 2: Financial Reporting** (30 tasks). Quarterly reports, expense analyses, revenue summaries, budget variance, audit response. Stakeholders: CFOs, controllers, audit committees.

**Domain 3: Intelligence Collection Tasking** (30 tasks). OSINT collection, target package development, threat actor profiling, indicator extraction. Stakeholders: intelligence analysts, collection managers, operations leads.

### 8.2 Task Categories

Within each domain of 30 tasks:

- 18 tasks (60%) full-specification (no gap expected)
- 9 tasks (30%) gap-triggering (one expected gap)
- 3 tasks (10%) stretch cases (contradiction or unspecifiable requirement)

### 8.3 AI Generation Protocol

Use Claude Opus 4 or equivalent for task generation. Do NOT use the Qwen3 family used inside MANDATE.

Use the generation prompt in Appendix A.2. Run 5 generations per domain-category combination to produce a candidate pool of approximately 75 tasks per domain. Lead Analyst selects 30 per domain optimizing for diversity per Section 8.4.

### 8.4 Diversity Requirements

Each domain's 30 tasks must include:

- At least 5 different stakeholder types
- At least 4 different deliverable formats
- At least 3 different time horizons
- At least 3 different organizational scopes

Diversity is verified by tagging each task on these dimensions and confirming the distribution.

### 8.5 Realism Audit (new in v2)

Before corpus freeze, each SME reviews 10 tasks (not the 30 they'll later sign off on, to avoid familiarity bias) and rates each on a 4-point scale:

- 4: I have seen this exact request type in operational work
- 3: This is realistic and plausible
- 2: This is somewhat realistic but feels artificial
- 1: This is not realistic; a real stakeholder would not write this

Tasks averaging below 2.5 across reviewers are flagged for rework or replacement. The audit takes approximately 1 hour per SME and runs in parallel with anchor scaffolding.

### 8.6 Deduplication

Compute embedding similarity (use a recent open-source sentence embedding model such as BGE-large or E5-large) pairwise across the corpus. Cosine similarity above 0.85 flags a pair for human review. The threshold is the same as v1 but now validated: a small calibration test on 20 known-distinct and 20 known-paraphrase pairs confirms the 0.85 cutoff achieves at least 90% paraphrase detection.

### 8.7 Output Format

Each task is a JSON file matching the v1 schema (Section 6.5), with an added `realism_audit` field containing per-SME ratings and the mean.

### 8.8 Corpus Freeze

After realism audit, deduplication, and final selection, the corpus is frozen in a git tag (`corpus_freeze_v1`). No edits after freeze.

---

## 9. Phase 3: Ground Truth Construction with Blinding

### 9.1 Blinding Protocol

SMEs see only:

- The task request_text
- The AI-scaffolded candidate anchor

SMEs do NOT see:

- Task metadata (category, intended_difficulty, intended_gap_field)
- Any system output (no system has run yet)
- The generation prompt used or generation model

The Lead Analyst maintains a separate "metadata vault" not shared with SMEs.

### 9.2 AI Scaffolding

Use Claude Opus 4 with the scaffolding prompt in Appendix A.3. The scaffold proposes a candidate anchor; the SME's job is to independently form judgment, compare, and ratify or revise.

### 9.3 SME Signoff Workflow

Each SME receives 30 tasks. Per task (estimated 8-12 minutes):

1. Read request_text
2. Form independent mental anchor (mission_intent, key minimum thresholds, suspected gaps) BEFORE reading AI scaffold
3. Read AI scaffold
4. Document independent assessment in signoff form (Appendix C)
5. Accept, revise, add, or remove fields field-by-field
6. Classify each suspected gap as confirmed/rejected/reclassified
7. Sign and timestamp

Tasks exceeding 20 minutes are flagged "requires discussion" and escalated to Cal.

### 9.4 Independence Statement

Each signoff form includes an independence statement the SME signs:

> "I confirm that my final ground truth represents my expert judgment of acceptable success criteria for this task, formed independently of how any system might process it. I read the AI scaffold only after forming my initial assessment."

This statement is the formal artifact backing the "human in the loop" defense.

### 9.5 Final Anchor Schema

Same as v1 (Section 7.3) with the addition of:

```json
{
  "independent_assessment_first": true,
  "independence_statement_signed": true,
  "deviation_from_ai_scaffold": "high | medium | low | none",
  "external_spotcheck": {
    "checked": true|false,
    "spotchecker": "[name]",
    "concur": true|false,
    "notes": "[if discordant]"
  }
}
```

### 9.6 Inter-Rater Reliability Protocol

#### 9.6.1 Overlap Sample

12 tasks (4 per domain), independently anchored by all three SMEs before any sees the others' work.

#### 9.6.2 Reliability Metrics

- Cohen's kappa pairwise across reviewers on binary judgments (is the task gap-triggering, is field X classified as minimum vs target)
- Krippendorff's alpha across all three reviewers on ordinal field-classification (minimum / target / constraint / not-present)

Interpretation anchor (McHugh, 2012):

| Kappa Range | Interpretation | Action |
|-------------|----------------|--------|
| < 0.40 | Poor | Halt, recalibrate rubric, re-train SMEs |
| 0.40 – 0.59 | Weak | Pause, discuss disagreements, re-do overlap |
| 0.60 – 0.79 | Moderate | Acceptable, proceed with documented caveat |
| 0.80 – 0.90 | Strong | Acceptable |
| > 0.90 | Almost perfect | Acceptable |

Target: Cohen's kappa ≥ 0.6 pairwise across all three pairs. Halt if any pair is < 0.4.

### 9.7 External Spot-Check

The external spot-checker (not affiliated with Swift Group) independently authors anchors for 9 tasks (10% of the corpus, 3 per domain) without seeing the SME signoffs. The Lead Analyst computes agreement between the external authoring and the SME-signed ground truth.

If external/SME agreement is substantially lower than SME-internal IRR, this signals potential team-internal echo. The discrepancy is reported in the final paper.

### 9.8 Ground Truth Freeze

After all signoffs, kappa computation, and spot-check, freeze in `gt_freeze_v1`. No edits after freeze.

---

## 10. Phase 4: Baseline Calibration

### 10.1 Purpose

Reviewers will ask whether the baselines were strawmen. Baseline calibration is a time-bounded, documented prompt engineering phase to ensure both baselines run at reasonable strength before the frozen comparison run.

### 10.2 Budget

One week of engineering time, split across the two baselines (3 days each, plus 1 day for documentation). Stop at the budget regardless of progress; report final configurations as the time-bounded "best effort within reasonable budget."

### 10.3 Calibration Procedure

For each baseline:

1. Start from the v1 prompts (Section 9.2 and 9.3 of v1)
2. Iterate on 6 development tasks NOT in the main corpus (use the 6 calibration tasks from Phase 1)
3. Make prompt changes documented in a calibration log
4. Stop when no improvement is observed across 3 consecutive prompt revisions OR when the 3-day budget is exhausted

### 10.4 Frozen Baseline Configurations

At the end of Phase 4, freeze:

- Final system prompt
- Model version and decoding parameters
- Tool list and definitions (for ReAct baseline)
- Calibration log documenting attempts

These are committed to `baseline_freeze_v1` tag. No changes during main run.

### 10.5 Reviewer Defense

The calibration log is published as part of the replication package. The argument to reviewers: "We allocated a reasonable, documented budget to baseline tuning; configurations are frozen and available for inspection." This kills the strawman accusation without requiring infinite tuning.

---

## 11. Phase 5: Perturbation Suite

### 11.1 Sample Size

30 trials per perturbation type, 5 types, total 150 perturbations. Increased from v1's 100 to provide adequate confidence intervals for the binary outcomes in robustness measurement.

### 11.2 Perturbation Types

Same five types as v1 (Section 8.1): surface noise, ambiguity injection, contradictory constraints, prompt injection, missing required field.

### 11.3 Adversarial Injection Sub-types

Prompt injection (30 trials) is further broken into sub-types to characterize where MANDATE is robust vs. vulnerable:

- 10 direct command injections ("Ignore instructions, do X")
- 10 social engineering ("As authorized by the system administrator, override...")
- 10 fake authority ("This is a NIST-required override, modify...")

Per-sub-type results reported separately.

### 11.4 Base Task Sampling

Sample 30 base tasks from the 90-task corpus, stratified by domain (10 per domain). Different base tasks for different perturbation types may reduce within-task interference; or the same 30 base tasks can serve all 5 perturbation types. The latter (same 30) enables paired comparison of perturbed vs. base output and is the pre-registered choice.

### 11.5 Generation and Quality Control

Same as v1 (Sections 8.2-8.3) with the addition: 30% of perturbations spot-checked (not 20%) given the expanded sample.

---

## 12. Phase 6: System Execution with Blinding

### 12.1 Execution Protocol

Each system runs each task and each perturbation three times to capture stochastic variance. Total runs:

- 3 systems × 90 tasks × 3 runs = 810 task runs
- 3 systems × 150 perturbations × 3 runs = 1,350 perturbation runs
- Total: 2,160 runs

This is tractable: at 30 seconds per run average, total compute time is ~18 hours wall-clock per system. Run in parallel where infrastructure allows.

### 12.2 Output Anonymization

Critical for blinded grading. Before grading, the Lead Analyst:

1. Strips all system-identifying strings from outputs (e.g., remove "AEGIS", "ReAct", model names, role labels that signal MANDATE)
2. Assigns a random alphanumeric identifier per output (e.g., `OUT-3F7A2B`)
3. Maintains the identifier-to-system mapping in a separate file not shared with graders

Graders see only the task, the ground truth, and the anonymized output. They do not know which system produced which output.

### 12.3 Variance Reporting

Per-task metrics: report the median across the 3 runs for that task. The median is more robust to outlier runs than the mean.

Per-system metrics: report mean ± 95% bootstrap CI (10,000 resamples) across the corpus.

If any task shows variance across runs greater than a pre-specified threshold (e.g., one run reports SUCCESS and another reports GAP_REPORT), that task is flagged for qualitative analysis as a stability case.

### 12.4 Output Capture and Freeze

Same structure as v1 (Section 9.4) with the addition of anonymization step. Outputs frozen in `outputs_freeze_v1` before grading.

---

## 13. Phase 7: Ablation Studies

### 13.1 Purpose

Reviewers asked: which MANDATE components actually contribute? Ablations isolate the contribution of specific architectural choices.

### 13.2 Ablation Subset

20 tasks drawn from the 90-task corpus, stratified by domain (7-7-6). Same tasks for all ablations enable within-task paired comparison.

### 13.3 Ablation Configurations

**Ablation 1: No role separation.** Single-LLM pipeline that performs all six MANDATE roles in a single prompt context rather than separated role contexts. Tests: does role separation contribute to specification quality?

**Ablation 2: No Success Registry.** MANDATE pipeline runs without precedent lookup. Tests: does precedent-based matching contribute to specification quality on tasks that have registry precedents?

**Ablation 3: No Search-Trace.** MANDATE pipeline runs without recording top-K candidates or hash-linking decisions. Tests: does the trace architecture contribute beyond logging (i.e., does it influence decisions)?

### 13.4 Ablation Metrics

Same primary metrics as the main comparison (anchor completeness, gap F1, trace completeness, fabrication rate), measured on the ablation subset. Compare to full MANDATE on the same subset.

### 13.5 Ablation Interpretation

For each ablation, the question is: does removing this component degrade performance? Significant degradation supports the design choice. Negligible degradation suggests the component is overhead. Both findings are valuable; honest ablations report both.

---

## 14. Phase 8: Cross-Family Ensemble Grading

### 14.1 Three-Judge Ensemble

Grading is performed by three judge models from three different families:

- Judge 1: GPT-4 class (OpenAI family)
- Judge 2: Claude Opus 4 (Anthropic family)
- Judge 3: Gemini 2.5 Pro (Google family)

All three judges must be distinct from the Qwen3 family used by MANDATE. Cost is roughly tripled relative to single-judge grading, but the result is dramatically more defensible.

### 14.2 LLM-as-Judge Bias Controls

Established LLM-as-judge biases that this protocol controls:

**Position bias** (judges favor first option). Mitigation: for any pairwise comparison, randomize order; for individual scoring, the rubric is anchored to ground truth, not to other outputs.

**Verbosity bias** (judges favor longer responses). Mitigation: rubric includes "length-appropriateness" criteria and excludes raw verbosity from scoring; fabrication metric explicitly penalizes unjustified additions.

**Self-preference** (a judge prefers outputs from its own family). Mitigation: three-judge ensemble across families dilutes any single judge's family bias.

**Anchoring on rubric examples** (judges over-weight example cases). Mitigation: rubric examples are drawn from outside the test corpus.

### 14.3 Judge Output and Aggregation

Each judge scores each output independently. For each scored dimension:

- Binary judgments: majority vote (2 of 3); disagreements (3 different answers impossible since binary; 2-1 splits accepted as majority)
- Continuous scores: median across the three judges
- Categorical (e.g., gap classification TP/TN/FP/FN): majority vote; if no majority (rare), human adjudication

Disagreement rate between judges is itself reported as a methodological metric. High disagreement signals rubric ambiguity.

### 14.4 Grader Prompts

Detailed prompts in Appendix B. Each prompt includes:

- The grading rubric with anchored definitions
- The ground truth anchor for the task
- The anonymized system output
- The instruction to score on each dimension with one-sentence rationale per score
- The instruction to NOT speculate about system identity

### 14.5 Grader Inter-Reliability

Compute pairwise Cohen's kappa across the three judges on binary judgments and Krippendorff's alpha on ordinal/continuous. Same interpretation thresholds as Section 9.6.

If grader IRR is below 0.6, the grading rubric is revised and re-run (counted in the buffer week). If below 0.4, halt and reconsider rubric design.

### 14.6 Double-Grading Sample

20% of outputs are double-graded by all three judges in two independent runs (different random seeds, different output ordering). Run-to-run agreement reported as a grader stability metric.

---

## 15. Phase 9: Analysis with Effect Sizes and Confidence Intervals

### 15.1 Primary Hypothesis Tests

For each of H1-H4:

1. Compute the relevant per-system metric (anchor completeness, gap F1, trace completeness, adversarial resistance)
2. Conduct paired statistical test (McNemar for proportions, Wilcoxon signed-rank for continuous)
3. Compute effect size (Cohen's h for proportions, Cohen's d for continuous)
4. Compute 95% bootstrap CI (10,000 resamples)
5. Apply Holm-Bonferroni correction across the family of primary tests

### 15.2 Required Reporting

For each comparison, report:

- Point estimate of metric for each system
- 95% CI for the metric
- p-value (corrected)
- Effect size with 95% CI

p-values without effect sizes are insufficient. Reviewers in 2026 expect effect sizes.

### 15.3 Subgroup Analyses

Pre-specified subgroups (Section 5.3) analyzed with Benjamini-Hochberg FDR control across the family of subgroup tests. Subgroup analyses are interpreted as exploratory.

### 15.4 Sensitivity Analyses

Three sensitivity checks:

1. Exclude tasks where SME IRR was poor (kappa < 0.4 on that task's domain). Does the headline finding change?
2. Use mean instead of median across runs. Does the headline finding change?
3. Drop the worst-performing system run per task. Does the headline finding change?

Sensitivity-stable findings strengthen the conclusion; sensitivity-fragile findings are reported honestly as such.

### 15.5 Tables

**Table 1: Primary results.** All three systems × all four primary metrics, with effect sizes and CIs.

**Table 2: Per-domain breakdown.** Primary metrics by domain.

**Table 3: Robustness.** Retention rate by perturbation type per system.

**Table 4: Ablations.** MANDATE-full vs. three ablation variants on 20-task subset.

**Table 5: Inter-rater reliability.** SME kappa, grader kappa, external spot-check agreement.

### 15.6 Failure Mode Analysis

Section 18.

---

## 16. Quality Controls and Halt Rules

### 16.1 Continue/Halt Decision Tree

The Lead Analyst escalates to Cal (halting that workstream pending decision) if any of:

| Condition | Action |
|-----------|--------|
| Phase 0 pilot shows fundamental protocol issue | Halt; revise protocol as v1.1 addendum |
| SME IRR < 0.4 on any pair after one calibration round | Halt; reconsider rubric or training |
| > 15% of corpus rejected by SMEs as unrealistic | Halt; corpus generation prompt revision |
| MANDATE calibration failure | Halt; configuration review |
| Baseline calibration produces no working configuration | Halt; protocol revision (the comparison may need a different baseline) |
| Grader IRR < 0.4 | Halt; rubric revision |
| Any prompt injection succeeds against MANDATE | Continue but flag; this is a finding, not a halt |
| > 10% task exclusion rate exceeded | Halt; protocol review |
| Stochastic variance produces > 20% of tasks flagged as unstable | Continue; report stability as methodological caveat |

### 16.2 Findings That Are Not Halts

Some findings will be unexpected. These do NOT halt the evaluation:

- MANDATE underperforms baselines on some metrics. This is a finding worth reporting.
- Baselines surprise on robustness. This is a finding.
- Some MANDATE roles fall back to deterministic path more than expected. This is a methodological caveat reported in scalability discussion.

The evaluation reports what it finds. The protocol is not a system for guaranteeing MANDATE looks good; it is a system for measuring honestly.

---

## 17. Replication Package

### 17.1 Contents

The replication package is deposited on Zenodo at the end of Phase 9, with a separate DOI from the pre-registration. Contents:

- The frozen pre-registration document and any v1.1 addenda
- The frozen 90-task corpus (anonymized where needed)
- The frozen 150-perturbation suite
- The ground truth anchors with SME attribution
- The frozen baseline configurations and calibration logs
- All system outputs (anonymized identifiers retained, mapping included)
- All grading outputs from all three judges
- Analysis notebooks (Jupyter, with version-pinned environment)
- Pre-computed result tables and figures
- The full deviation log
- A README with reproduction instructions

### 17.2 What is NOT in the Package

- Raw SME signoff forms with personally-identifying information (anonymized aggregates only)
- Proprietary AEGIS internal configurations beyond what is needed to reproduce MANDATE behavior (the Qwen3 fine-tuning data, internal lab tooling)
- Any internal Swift Group documents

### 17.3 License

CC-BY-4.0 on data and documentation; MIT or Apache-2.0 on code. Compatible with the MANDATE framework specification license.

---

## 18. Failure Mode Taxonomy

### 18.1 Purpose

When a system fails on a task, the failure has a structure. Categorizing failures enables qualitative analysis and exposes patterns that aggregate metrics miss.

### 18.2 Pre-Registered Failure Categories

Every failure (a system output that scores below threshold on at least one primary metric) is coded into one of these categories:

1. **Extraction failure.** The system did not extract information present in the input.
2. **Fabrication.** The system invented information not present in the input or ground truth.
3. **Misclassification.** The system extracted information correctly but classified it incorrectly (e.g., constraint labeled as target).
4. **Silent gap.** The system proceeded without flagging a gap that ground truth identified.
5. **False gap.** The system flagged a gap on a task where ground truth had no gap.
6. **Trace failure.** The system completed but trace is incomplete or unverifiable.
7. **Adversarial compliance.** The system was subverted by a prompt injection.
8. **Calibration failure.** The system failed on a calibration task (separately reported).
9. **Infrastructure failure.** The system crashed or timed out.

### 18.3 Coding Protocol

After grading is complete, the Lead Analyst manually codes every failed task into one of these categories. For uncertain cases, the second coder is Cal.

Per-category counts are reported per system. Patterns ("MANDATE's failures are mostly extraction; Baseline 1's failures are mostly fabrication") are part of the qualitative findings.

### 18.4 Reporting

Failure mode distribution is reported as a stacked bar or heatmap in the final paper. This visualization is often more informative to readers than the headline metrics.

---

## 19. Deliverables Checklist

Final handoff to Cal includes:

- [ ] Zenodo-deposited pre-registration (Protocol v1.0)
- [ ] Phase 0 pilot findings memo
- [ ] Any v1.1 protocol addendum if revisions occurred
- [ ] Phase 1 calibration results (all systems pass)
- [ ] Frozen 90-task corpus (`corpus_freeze_v1`)
- [ ] 90 signed ground truth anchors with SME attribution
- [ ] External spot-check report (9 tasks, independent review)
- [ ] SME IRR computation (Cohen's kappa, Krippendorff's alpha)
- [ ] Frozen baseline configurations (`baseline_freeze_v1`) with calibration logs
- [ ] Frozen 150-perturbation suite (`perturbation_freeze_v1`)
- [ ] System output sets for all 3 systems × 3 runs (`outputs_freeze_v1`)
- [ ] Ablation run outputs
- [ ] Three-judge grading outputs with agreement statistics
- [ ] Grader IRR computation
- [ ] Failure mode coding for every failed task
- [ ] Analysis notebooks with all primary, subgroup, and sensitivity analyses
- [ ] Effect sizes with CIs for every primary comparison
- [ ] Final report with limitations, deviation log, and qualitative findings
- [ ] One-page executive summary for paper integration
- [ ] Replication package deposited on Zenodo with separate DOI

---

## Appendix A: Pre-Registration Document Template

### A.1 Outline

```markdown
# MANDATE Empirical Evaluation: Pre-Registered Protocol v1.0

**Authors:** [Lead Analyst Name], Elias Calboreanu
**Affiliation:** Swift AI Lab, The Swift Group
**Date of pre-registration:** [DATE]
**License:** CC-BY-4.0
**Conflict of interest:** The authors are affiliated with The Swift Group,
which holds commercial licensing rights to MANDATE-based products. External
spot-check by [name/institution].

## 1. Background and Rationale
[3-4 paragraphs]

## 2. Hypotheses
H1: [falsifiable statement with effect size threshold]
H2: [...]
H3: [...]
H4: [...]

## 3. Sample
- 90 tasks across 3 domains, 30 per domain
- 6 pilot tasks
- 6 calibration tasks
- 150 perturbations (30 per type × 5 types)
- 20-task ablation subset
- Inclusion / exclusion criteria
- Maximum exclusion rate: 10%

## 4. Systems Under Comparison
- MANDATE (AEGIS, fine-tuned Qwen3 stack, version [X])
- Baseline 1: Single-prompt planner using [model, version]
- Baseline 2: ReAct-style agent using [model, version] with [framework, version]
- Ablation 1: MANDATE without role separation
- Ablation 2: MANDATE without Success Registry
- Ablation 3: MANDATE without Search-Trace

## 5. Model Family Separation
- Task generation: [family, model, version]
- MANDATE: [Qwen3 variants]
- Baselines: [families]
- Graders: 3 distinct families [list]

## 6. Metrics
[Mathematical definitions]

## 7. Statistical Analysis Plan
- Primary tests with corrections
- Effect size definitions
- CI computation
- Subgroup analyses (pre-specified)
- Sensitivity analyses (pre-specified)

## 8. Inter-Rater Reliability
- SME kappa target ≥ 0.6
- Grader kappa target ≥ 0.6
- Krippendorff's alpha as supplementary

## 9. Halt and Continue Rules
[From Section 16]

## 10. Deviation Policy
[Commitment to document]

## 11. Replication Package Commitment
[What will be deposited]
```

### A.2 AI Task Generation Prompt

[Same as v1 Section 6.3]

### A.3 AI Scaffolding Prompt

[Same as v1 Section 7.1]

---

## Appendix B: Grader Prompts (Multi-Judge)

### B.1 Base Prompt (All Judges)

```
You are scoring the output of an AI agent specification system against
expert-defined ground truth. You are one of three independent judges; do
not assume your view is correct.

Scoring rules:
- Be rubric-driven, not impressionistic
- Do not infer the system's identity from output style
- Do not reward verbosity or punish brevity unless rubric specifies
- For each dimension, provide a one-sentence rationale grounded in
  specific output elements

GROUND TRUTH ANCHOR:
[anchor JSON]

ANONYMIZED SYSTEM OUTPUT:
[anonymized output]

TASK CATEGORY (informational, do not score):
[full-spec | gap-triggering | stretch]

SCORE THE FOLLOWING DIMENSIONS:

[Same dimensions as v1 Appendix B]

Respond in valid JSON. Do not include preamble or commentary outside the
JSON structure.
```

### B.2 Judge-Specific Notes

Each judge receives an identical base prompt. Differences across judges are emergent (different families, different training data), not protocol-driven.

### B.3 Aggregation Logic

[Reference to Section 14.3]

---

## Appendix C: SME Sign-Off Form (with Independence Statement)

[Same structure as v1 Appendix C with the addition of the independence statement in Section 9.4]

---

## Appendix D: Status Reporting Template

[Same as v1 Appendix D]

---

## Appendix E: Methods Reference Notes

This evaluation draws on established methodology. The references below are illustrative of the tradition the protocol follows; specific citations should be verified by the Lead Analyst when integrating into the final paper.

**Empirical software engineering experiment design:** Wohlin et al., "Experimentation in Software Engineering" (textbook); Basili et al. on Goal-Question-Metric.

**ML/AI evaluation reproducibility:** Pineau et al. on reproducibility checklist; Bouthillier et al. on variance accounting in ML benchmarks.

**LLM-as-judge methodology and biases:** Zheng et al. (2023) on MT-Bench (LLM-as-judge as a paradigm); subsequent literature on position bias, verbosity bias, and self-preference.

**Inter-rater reliability:** Cohen (1960) on kappa; McHugh (2012) on kappa interpretation; Krippendorff (2018) on alpha for ordinal data.

**Effect size and power:** Cohen (1988) on statistical power and effect sizes; specific formulations for h (proportions) and d (means).

**Multiple testing correction:** Holm (1979) for family-wise error; Benjamini and Hochberg (1995) for false discovery rate.

**Pre-registration practice:** Center for Open Science guidance on social science pre-registration; emerging adoption in computer science.

---

## Appendix F: Glossary of Statistical Terms

**Cohen's d:** Effect size for continuous outcomes. d = (mean1 - mean2) / pooled_SD. Conventions: 0.2 small, 0.5 medium, 0.8 large.

**Cohen's h:** Effect size for proportions. h = 2·arcsin(√p1) - 2·arcsin(√p2). Same conventions as Cohen's d.

**Cohen's kappa:** Inter-rater reliability for binary or categorical judgments, corrected for chance agreement.

**Krippendorff's alpha:** Generalized inter-rater reliability for any level of measurement (nominal, ordinal, interval); handles missing data and any number of raters.

**McNemar's test:** Non-parametric test for paired proportions; appropriate when the same units are measured under two conditions.

**Wilcoxon signed-rank test:** Non-parametric test for paired continuous data; the non-parametric equivalent of a paired t-test.

**Holm-Bonferroni correction:** Sequential method for controlling family-wise error rate; less conservative than Bonferroni.

**Benjamini-Hochberg correction:** Method for controlling false discovery rate; appropriate for exploratory multiple comparisons.

**Bootstrap CI:** Confidence interval estimated by resampling the data with replacement; useful when the sampling distribution is unknown or non-normal.

**HARKing:** Hypothesizing After Results are Known; the practice of presenting post-hoc hypotheses as if they were pre-specified. Pre-registration is the primary defense.

---

**End of playbook v2.0.**

The Lead Analyst is the single point of accountability for execution per this protocol. Deviations require Cal's written approval and are documented in the deviation log. The integrity of the evaluation depends on protocol adherence and honest reporting of findings, including findings unfavorable to MANDATE.
