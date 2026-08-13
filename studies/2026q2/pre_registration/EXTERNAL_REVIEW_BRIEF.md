# MANDATE Empirical Evaluation: External Review Brief

**Purpose of this document.** This is a self-contained summary of an empirical evaluation design for the MANDATE framework. It is prepared for external review by another AI system or by independent reviewers to identify gaps, suggest improvements, or validate the design against academic standards.

**Status.** Design phase. Pre-registration not yet deposited. Approximately 8-week design period. Execution scheduled for 14 weeks from pre-registration deposit.

**Author.** Elias Calboreanu (Cal), Principal, Swift AI Lab; doctoral candidate, Capitol Technology University.

---

## 1. Research Context

### 1.1 What MANDATE Is

MANDATE (Multi-Agent Nominal Decomposition for Autonomous Task Execution) is a tolerance-based specification framework for autonomous AI agents. Instead of treating task success as binary goal satisfaction, MANDATE specifies success as a tuple of (minimum threshold, target objective, constraints), with multiple Courses of Action (COAs) that can satisfy the same anchor. The framework produces a machine-readable artifact (mandate-as-code) or a Gap Analysis Report identifying what cannot be specified.

The reference implementation is AEGIS (Autonomous Engineering Governance and Intelligence System), a 7-lane agentic automation pipeline using fine-tuned Qwen3 models running locally on a 4-workstation Mac mini M4 Pro cluster.

Key contributions claimed by the framework:
- Tolerance-based task specification (vs. binary goal satisfaction)
- 1+6 role separation architecture
- Dual output (mandate-as-code or Gap Analysis Report)
- Search-Trace decision provenance with SHA-256 hash linking
- Success Registry for precedent-based learning
- AI RMF-aligned risk metadata
- Execution-agnostic interface

### 1.2 Why This Evaluation Exists

The MANDATE paper has been rejected at Frontiers in Artificial Intelligence (two rounds) and desk-rejected at Requirements Engineering (Springer). Reviewer feedback converges on the same pattern across venues:

- "Insufficient comparative benchmarking"
- "Robustness evaluation against adversarial or noisy conditions is missing"
- "Broader empirical validation across multiple operational settings is lacking"
- "Practical scalability and reliability claims need stronger quantitative evidence"
- "The same LLM family both authored and audited the specifications, creating a potential blind spot"

The prior empirical work consisted of a single-system pilot using a 125-example corpus with overlapping training and validation splits, no independent test set, no comparative benchmarking, and no adversarial robustness testing.

This evaluation is the corrective. The goal is a publication-grade empirical study that satisfies Q1-tier academic standards (TSE, TOSEM, EMSE, TPAMI, JAIR, Requirements Engineering, IEEE TDSC).

### 1.3 What Compute Constraints Do NOT Apply

Unlike conventional academic evaluations, this work has effectively unbounded compute and configuration flexibility:

- 4 Mac mini M4 Pro workstations running Ollama with multiple LLMs deployable
- API access to Claude, GPT, Gemini families
- Any agent framework (AutoGen, CrewAI, LangGraph, MetaGPT) can be installed and tested
- No publication-cycle compute limit; the system can run for weeks of wall-clock if needed

The binding constraint is human SME time (~12-15 hours per SME over 6 weeks; 3-5 SMEs available).

---

## 2. Evaluation Design Summary

The design proceeds in 9 sequential phases plus a pilot, executed by a Lead Analyst (one full-time equivalent) with SME signoffs from Brad Carter, Jason McKay, and (potentially) Cal himself for non-authored ground truth.

### 2.1 Phase Structure

| Phase | Purpose | Output |
|-------|---------|--------|
| 0 | Pilot study (6 tasks end-to-end) | Protocol debugged, halt rules tested |
| 1 | Calibration set (6 unambiguous tasks) | Positive control on system configurations |
| 2 | Main corpus generation | 120 tasks, 3 domains, 40 per domain |
| 3 | SME ground truth signoff | 120 signed anchors with IRR |
| 4 | Baseline calibration (time-bounded prompt engineering) | Frozen baseline configurations |
| 5 | Perturbation suite generation | 350 perturbations across 7 types |
| 6 | System execution | ~48,000 runs across systems × tasks × replications |
| 7 | Ablation studies | 8 ablations isolating MANDATE components |
| 8 | Three-judge ensemble grading | Anonymized output grading with IRR |
| 8.5 | Human-vs-judge calibration | 100 outputs human-graded for LLM-judge validation |
| 9 | Analysis | Frequentist + Bayesian + hierarchical models |

### 2.2 Sample and Population

**Main task corpus:** 120 operational task descriptions across 3 domains:
- Security operations reporting (vulnerability reports, incident summaries, posture assessments)
- Financial reporting (quarterly variance, monthly revenue, audit response)
- Intelligence collection (OSINT collection, target profiling, threat actor packages)

Distribution within each domain: 60% full-specification, 30% gap-triggering, 10% stretch cases (contradictions or unspecifiable requirements).

**Hold-out generalization domain:** 30 additional tasks in a 4th domain (software engineering specification or operations/maintenance) tested only against MANDATE primary configuration and the best-performing baseline. Tests external validity to a domain MANDATE was not designed against.

**Perturbation suite:** 350 trials across 7 perturbation types:
- Surface noise (5%-8% character-level)
- Ambiguity injection (specific terms → vague equivalents)
- Contradictory constraints (deadline vs. scope conflicts)
- Prompt injection (5 sub-types: direct command, social engineering, fake authority, multi-turn, encoded)
- Missing required field
- Out-of-distribution input (unusual register or domain-adjacent jargon)
- Length perturbation (50% compression or 200% expansion)

### 2.3 Systems Under Comparison

**MANDATE backend matrix (8 backends):**
- Qwen3 fine-tuned (8B + 32B, primary)
- Qwen3 base (no fine-tuning)
- Llama 3.3 (70B)
- Mistral Large 2 (123B)
- Gemma 3 (27B)
- GPT-OSS variants
- Claude Sonnet 4 (via API)
- GPT-4o (via API)

If MANDATE properties hold across diverse backends, the contribution is framework-level. If properties degrade on some backends, the finding is also valuable (identifies what MANDATE depends on).

**Baseline matrix (6 LLM baselines + human expert):**
- Single-prompt planner (Claude)
- Single-prompt planner (GPT)
- ReAct (Claude)
- AutoGen (multi-agent)
- CrewAI (role-based multi-agent)
- LangGraph (graph-based)
- Human expert upper bound (senior practitioner authoring 30 specifications)

**Ablation matrix (8 ablations of MANDATE):**
- No role separation
- No Success Registry
- No Search-Trace
- Backend portability (cross-LLM)
- No Validation Role
- No tolerance bands (single threshold only)
- No Gap Analysis output (forced specification)
- No NIST AI RMF risk metadata

### 2.4 Metrics

**Primary metrics:**
- Anchor completeness (0.0 to 1.0): fraction of ground truth fields correctly identified
- Gap detection F1: precision/recall on gap-triggering classification
- Trace completeness: binary, whether full hash-linked trace produced
- Adversarial resistance rate: fraction of prompt injection trials where system maintains contract
- Fabrication rate: fraction of system fields not in ground truth and not justifiable

**Secondary metrics:**
- COA diversity (ordinal 0-2)
- Per-perturbation retention rate
- Per-role timing for MANDATE
- Fallback rate to deterministic path
- Computational and API cost per task

**Construct validity:** Each metric is explicitly defended in the pre-registration as an operationalization of a specific MANDATE claim.

### 2.5 Replication and Variance

- 10 runs per task per system (vs. typical 3-5)
- 5 runs per perturbation per system
- Per-task metric: median across runs
- System-level metric: mean ± 95% bootstrap CI (10,000 resamples)
- Stability rate: fraction of tasks with full agreement across replications

### 2.6 Statistical Analysis

**Primary hypothesis tests:**
- McNemar's test for paired proportions
- Wilcoxon signed-rank for paired continuous
- Holm-Bonferroni correction across 4 primary hypotheses (effective α = 0.0125)

**Effect sizes:**
- Cohen's h for proportions
- Cohen's d for continuous metrics
- 95% bootstrap confidence intervals on every metric and effect size

**Multiple comparison:**
- Holm-Bonferroni for primary hypotheses
- Benjamini-Hochberg FDR for exploratory subgroup analyses

**Sensitivity analyses (pre-registered):**
- Exclude tasks with low SME IRR
- Use mean instead of median across runs
- Drop the worst run per task
- Alternate grader rubric (strict vs. flexible)

**Bayesian supplementary:**
- Posterior distributions on primary effect sizes
- Bayes factors comparing alternative vs null
- Posterior predictive checks

**Hierarchical models:**
- Multilevel model for cross-backend analysis (tasks within backends within families)
- Variance decomposition at each level

### 2.7 Inter-Rater Reliability

**SME IRR:**
- 12-task overlap sample (4 per domain) where all 3 SMEs independently anchor
- Cohen's kappa pairwise on binary judgments
- Krippendorff's alpha across all 3 on ordinal field classifications
- Targets: pairwise kappa ≥ 0.6 (acceptable), ≥ 0.8 (target); halt if any pair < 0.4
- McHugh (2012) interpretation framework

**External spot-check:** External reviewer (not affiliated with Swift Group) independently anchors 9 tasks (10% sample). Discrepancy with internal SMEs is reported.

**Grader IRR:**
- Three judges from three distinct model families (none Qwen3)
- 20% double-graded sample
- Pairwise Cohen's kappa, Krippendorff's alpha
- Same thresholds as SME IRR

**Human-vs-judge calibration:**
- 100 outputs human-graded by Cal or external grader
- Stratified across systems and includes 20 LLM-judge-disagreement cases
- Spearman correlation between human and LLM ensemble
- Target ρ ≥ 0.7 on continuous, κ ≥ 0.6 on binary

### 2.8 Threats to Validity (Pre-Registered)

**Construct validity:** Defended per metric; fabrication rate controls for completeness gaming.

**Internal validity:** Randomized task assignment to SMEs; baseline calibration documented; LLM-judge bias controls.

**External validity:** Backend portability test; cross-domain hold-out; honest scope limitations.

**Conclusion validity:** Multiple testing corrections; effect sizes with CIs; sensitivity analyses.

### 2.9 Reproducibility

- Pre-registration deposited on Zenodo with DOI before any data generated
- All artifacts frozen with git tags at phase boundaries
- Replication package deposited on Zenodo with separate DOI
- Docker container with pinned environment
- Random seeds set explicitly
- Anonymization mapping kept separate from grader access
- Deviation log documents every protocol deviation with timestamp and rationale

### 2.10 Ethics and Compliance

- IRB exemption from Capitol Tech University before SME work begins
- SME participation agreements signed
- Data Management Plan included
- Responsible AI / dual-use considerations explicitly addressed
- CRediT contribution taxonomy used in publication

---

## 3. Specific Areas Where External Review Input Is Sought

### 3.1 Methodological gaps the author may have missed

The design has been audited four times (v1 through v5). The author requests external review on whether any of the following remain insufficiently addressed:

- Self-affiliation bias in SMEs (all from Swift Group): is the external spot-checker (10% sample) sufficient counter?
- LLM-as-judge methodology: is the 100-output human-vs-judge calibration sufficient validation?
- Cross-domain generalization: is one hold-out domain sufficient for external validity claims?
- Baseline calibration budget (3 days per baseline): does this risk strawman-baseline criticism?
- Construct validity for "gap detection": is the F1 score the right operationalization vs. precision and recall separately?

### 3.2 Statistical approach validity

The author has prior coursework in statistics but is not a professional statistician. External review is sought on:

- Is Holm-Bonferroni the right family-wise error correction for 4 primary hypotheses?
- Is the power calculation for n=120 detecting Cohen's h = 0.26 at α = 0.0125 with 80% power correctly computed?
- Are bootstrap confidence intervals (10,000 resamples) appropriate, or should we use BCa intervals?
- Is the planned hierarchical model specification (tasks within backends within families) appropriately specified?
- For Bayesian supplementary analysis, are the implicit priors (uninformative) appropriate, or should informative priors based on prior empirical work be used?

### 3.3 Venue strategy

The author's current target venues are:
- Empirical Software Engineering (EMSE) - preferred for methodology paper
- IEEE Transactions on Software Engineering (TSE)
- Requirements Engineering (Springer) - revised approach after desk rejection
- IEEE Transactions on Dependable and Secure Computing (TDSC)
- ACM Transactions on Software Engineering and Methodology (TOSEM)

External review input sought:
- Given the framework + empirical evaluation scope, which venue is the best fit?
- Should the evaluation be split into two papers (methodology + framework) or combined into one?
- Are there venue-specific reporting standards beyond MLR and Carver et al. that should be followed?

### 3.4 Open methodological questions

- The author has 8 ablations isolating MANDATE components. Is this too many (analysis overhead) or appropriate (component-level attribution)?
- The author has 8 LLM backends for MANDATE. Is this overkill or appropriate for the framework claim?
- For the 30-task human expert upper bound, should the human expert see the same input the systems see, or have access to additional context (which would make them stronger)?
- For perturbation testing, is the within-task paired comparison (perturbed vs. base output of same task) the right design, or should perturbations be independent samples?

### 3.5 Practical execution risks

- 13 SMEs across 3 internal + 2 external + 5 SMEs from hold-out domain + human expert + 3 LLM judges. Coordination risk?
- 14-week timeline. Slippage risk?
- ~$2,000 API budget. Sufficient?
- Single Lead Analyst orchestrating ~48,000 runs across systems. Bottleneck?

---

## 4. Specific Asks for External Reviewer

If you are reviewing this brief, please address the following:

1. **Identify any methodological gap.** What is missing that a Q1 reviewer would flag and that has not been addressed in the v1-v5 audits?

2. **Validate or critique the statistical approach.** Are the test choices, effect size choices, correction methods, and CI methods appropriate for the design?

3. **Suggest venue and submission strategy.** Given the scope and content, where should this work be submitted? Should it be split?

4. **Suggest writing strategy.** Given the complexity of the empirical work, how should the paper be structured? How many tables/figures? What should be in the main paper vs. supplementary materials?

5. **Identify residual risks.** What is the highest-probability failure mode of this evaluation? What is the most damaging finding (one that would change the paper's story)?

6. **Suggest additions if any.** Are there elements still missing that would strengthen the work?

7. **Identify writing pitfalls.** Given that prior submissions were rejected on empirical grounds, what writing-style or framing issues might persist that the empirical work cannot fix?

---

## 5. Document Inventory (Available on Request)

The complete evaluation package consists of:

1. `README_START_HERE.md` (8KB): coworker orientation
2. `00_PLAYBOOK_v2.md` (46KB): master protocol
3. `00_PREREGISTRATION_TEMPLATE.md` (16KB): pre-registration template
4. `Q1_AUDIT_AND_ENHANCEMENTS.md` (24KB): defensible-Q1 enhancements
5. `Q1_PLUS_UNBOUNDED_SCALING.md` (22KB): definitive-Q1+ expansion
6. `FINAL_AUDIT_V5.md` (15KB): final academic submission additions
7. `PROMPTS.md` (15KB): all AI prompts
8. `FORMS.md` (12KB): all forms and templates
9. `ANALYSIS_PLAN.md` (11KB): notebook structure
10. `SETUP.md` (9KB): environment and infrastructure
11. `CHECKLIST.md` (9KB): deliverables tracking
12. `calibration_tasks/` directory: 6 hand-authored unambiguous tasks (~15KB total)
13. This document (`EXTERNAL_REVIEW_BRIEF.md`)

Total package size: approximately 200KB of methodology documentation plus calibration tasks.

---

## 6. Constraints on External Review

The external reviewer is asked to evaluate the design as planned, not to:

- Demand changes that require substantially more resources than the author has access to (e.g., "recruit 50 SMEs" is out of scope)
- Recommend changes that contradict prior pre-registration commitments once those are deposited
- Suggest changes that delay execution by more than 2 weeks (this is a 14-week sprint, not an indefinite research program)

The external reviewer is asked to focus on:

- Methodological correctness within the planned scope
- Identification of gaps the author has missed
- Writing and venue strategy
- Risk identification

---

## 7. Background on Cal's Editorial Standards

For external reviewers (LLM-based or human) producing written feedback that the author might incorporate, his standing editorial standards are:

- No em-dashes
- American English (no British spelling)
- No AI-tropism language ("delve", "tapestry", "navigate" as verb-metaphor, "in the realm of", "stands as a testament to")
- No deficit framing
- Vendor-agnostic terminology in public-facing documents
- Professional defense/intelligence audience expected

---

## 8. Closing

This evaluation design exists because two prior attempts to publish MANDATE failed on empirical grounds. The current design takes advantage of resources (unbounded compute, configuration flexibility, SME network) that conventional academic evaluations cannot afford, while staying within the bounds set by the binding constraint of human SME time.

External review is genuinely sought. The author would rather hear a hard critique now than receive a third rejection.

**Contact:** Elias Calboreanu, ecalboreanu@captechu.edu

**End of external review brief.**
