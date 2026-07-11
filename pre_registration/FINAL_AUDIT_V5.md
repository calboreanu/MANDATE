# Final Audit: Remaining Additions for Complete Academic Submission

**Purpose:** Final pass through the evaluation package identifying methodological elements not yet addressed in v2-v4. These additions address academic requirements beyond pure empirical methodology: ethics, open science, reproducibility infrastructure, practical interpretation, and disciplinary reporting standards.

**Reads alongside:** All prior documents. This is the final layer before the package is academically complete.

---

## Part 1: Audit Findings (What's Still Missing)

### Category A: Ethics and Compliance

| Element | Status | Priority |
|---------|--------|----------|
| IRB exemption letter from Capitol Tech University | Not addressed | HIGH |
| Data Management Plan (NSF/NIH style) | Not addressed | HIGH |
| Responsible AI / dual-use considerations | Brief mention only | HIGH |
| SME participation agreement (informed consent) | Not addressed | HIGH |
| Data anonymization policy for SME-attributed work | Implicit only | MEDIUM |
| Compliance with Capitol Tech research conduct policy | Not addressed | MEDIUM |

### Category B: Open Science and FAIR Principles

| Element | Status | Priority |
|---------|--------|----------|
| FAIR data principles (Findable, Accessible, Interoperable, Reusable) compliance statement | Not addressed | HIGH |
| Open Science Framework (OSF) project registration | Not addressed | MEDIUM |
| Persistent identifiers (DOIs) for every major artifact | Partial (Zenodo for pre-reg and package) | MEDIUM |
| ORCID identifiers on all contributors | Not addressed | LOW |
| Open peer review preprint posting | Not addressed | MEDIUM |
| CRediT contribution taxonomy statement | Not addressed | HIGH |

### Category C: Reproducibility Infrastructure

| Element | Status | Priority |
|---------|--------|----------|
| Docker container with pinned environment | Not addressed | HIGH |
| Continuous integration testing of analysis pipeline | Not addressed | MEDIUM |
| Data versioning beyond git tags (DVC or similar) | Not addressed | MEDIUM |
| Workflow management (Snakemake / Nextflow) | Not addressed | MEDIUM |
| Notebook execution hash pinning | Not addressed | MEDIUM |
| External reproducibility audit (independent team) | Not addressed | MEDIUM |
| Synthetic data smoke test for CI | Not addressed | LOW |

### Category D: Sustainability and Cost Transparency

| Element | Status | Priority |
|---------|--------|----------|
| Carbon footprint estimate (kgCO2eq) | Not addressed | MEDIUM |
| Compute resource breakdown by provider | Partial (Enhancement 8 in Q1 doc) | LOW |
| Energy efficiency reporting | Not addressed | LOW |

### Category E: Practical Interpretation

| Element | Status | Priority |
|---------|--------|----------|
| Operational significance thresholds (not just statistical) | Not addressed | HIGH |
| Risk-tiered interpretation (high-stakes vs. low-stakes contexts) | Not addressed | HIGH |
| Practical deployment guidance from findings | Not addressed | MEDIUM |
| Decision framework: when to use MANDATE vs. baselines | Not addressed | MEDIUM |
| Cost-effectiveness threshold for adoption | Partial | MEDIUM |

### Category F: Methodological Completeness

| Element | Status | Priority |
|---------|--------|----------|
| Negative results commitment in pre-registration | Implicit only | HIGH |
| Confirmatory vs. exploratory hypothesis distinction | Partial | MEDIUM |
| Cross-validation strategies (k-fold, leave-one-domain-out) | Not addressed | MEDIUM |
| Sensitivity to grader rubric (alternate rubric test) | Not addressed | MEDIUM |
| Long-tail failure analysis (hardest 10% of tasks) | Not addressed | MEDIUM |
| Theory-prediction matching (does empirical match theoretical claims?) | Not addressed | MEDIUM |
| Red team adversarial evaluation (human attackers) | Not addressed | LOW |

### Category G: Disciplinary Reporting Standards

| Element | Status | Priority |
|---------|--------|----------|
| MLR (Machine Learning Reproducibility) checklist | Not addressed | HIGH |
| ROSES (Reporting of Studies Examining Synthesis) compliance | Not applicable | N/A |
| Empirical SE reporting checklist (Carver et al. or similar) | Not addressed | HIGH |
| Pre-existing benchmark integration (AgentBench, ToolBench) | Not addressed | MEDIUM |

### Category H: Stakeholder Validation

| Element | Status | Priority |
|---------|--------|----------|
| End-user validation (would deployers find MANDATE output useful?) | Not addressed | MEDIUM |
| Consumer/runtime validation (does mandate-as-code parse correctly downstream?) | Not addressed | MEDIUM |
| Cross-organizational SME validation | Partial (external spot-checker) | MEDIUM |

---

## Part 2: High-Priority Additions

Each item below is a specific addition to be made before pre-registration deposit. These are the items that, if missing, will be flagged by Q1+ academic reviewers.

### Addition 1: IRB Exemption Documentation

**Issue:** Even though no human subjects in a traditional research sense (no interventions, no clinical data), SME work involves humans providing professional judgment. Many institutions classify this as research requiring IRB review even if exempt.

**Action.** Contact Capitol Tech University IRB office. Submit a research description for exempt determination. The submission should include:

- Description of the evaluation as methodology research, not human subjects research
- Description of SME participation (voluntary, professional judgment, no personal data collected)
- Data handling protocol (signoffs are professional artifacts, not personal data)
- Confidentiality protocol (SME identities masked in publications unless explicit consent for attribution)

**Expected outcome.** Exempt determination under 45 CFR 46.104(d)(2) (research involving educational tests, surveys, interviews, or observation of public behavior). Letter on file before SME work begins.

**Documentation.** Include IRB exemption letter or determination notice as an appendix to the final report and in the replication package.

### Addition 2: Data Management Plan

**Issue:** Federal funders (and increasingly journals) require explicit data management plans. Even if not funded externally, having a DMP is a professionalism marker.

**Action.** Produce a 2-page DMP covering:

- Data types generated (corpus, signoffs, system outputs, grading results)
- Storage during research (location, redundancy, access control)
- Sharing policy (Zenodo deposit with CC-BY-4.0)
- Long-term preservation (Zenodo with Capitol Tech archival agreement)
- Data security (encryption at rest for sensitive items)
- PII handling (none collected; SMEs identified only with consent)

### Addition 3: Responsible AI / Dual-Use Statement

**Issue:** MANDATE is potentially deployable in defense and intelligence contexts. Academic venues increasingly ask for explicit dual-use analysis.

**Action.** Add a section to the pre-registration and final report:

```markdown
## Responsible AI and Dual-Use Considerations

The MANDATE framework is a specification methodology that produces
structured task definitions for autonomous agent execution. The
framework itself does not authorize, execute, or perform tasks; it
specifies acceptable success criteria.

### Beneficial applications

- Improving auditability of autonomous agent operations
- Enabling responsible automation by surfacing implicit thresholds
- Supporting governance compliance (NIST AI RMF alignment)
- Facilitating human oversight via gap reporting and escalation
- Enabling safer deployment in high-stakes operational contexts

### Potential dual-use concerns

- MANDATE could specify tasks that, if executed, cause harm. The
  framework does not authorize or prevent harmful tasks.
- Adversarial actors could use MANDATE to specify attacks against
  computer systems. The framework's role separation could improve
  the structure of such attacks.
- Specifications could be used to encode discriminatory or unfair
  criteria into apparently objective machine-readable artifacts.

### Mitigations

- The MANDATE framework operates upstream of execution; it does not
  itself enable any new capability that does not already exist.
- The Gap Analysis output explicitly surfaces ambiguity rather than
  hiding it, supporting human review of specifications before execution.
- Risk metadata aligned with NIST AI RMF supports governance review.
- Distribution under CC-BY-4.0 with explicit responsible use guidance.
- The reference implementation (AEGIS (Autonomous Engineering Governance and Intelligence System)) is proprietary and not
  publicly released; only the methodology is open.

### Future research priorities

- Empirical study of how MANDATE specifications affect downstream
  execution risk under varied operational stakes.
- Study of MANDATE's behavior under adversarial specification
  attempts (e.g., specifications designed to bypass review).
- Cross-cultural study of how tolerance bands are interpreted
  differently across organizational and national contexts.
```

### Addition 4: SME Participation Agreement

**Issue:** SMEs need a written record of what they are participating in, what is expected, and how their contributions will be acknowledged or anonymized.

**Action.** Create a one-page SME Participation Agreement covering:

- Purpose of the research
- SME role and time commitment expected (~12-15 hours over 6 weeks)
- Compensation (if any; if volunteer, stated as such)
- How signoffs will be attributed (anonymized aggregate by default; individual attribution only with explicit consent)
- Data handling (signoffs stored in project repository; aggregate published in replication package)
- Right to withdraw (participation may be discontinued at any time without penalty)
- Acknowledgment in publications (yes, with consent on attribution form)

Brad, Jason, and external SMEs all sign before beginning work.

### Addition 5: FAIR Data Principles Compliance

**Issue:** Open Science practice increasingly requires explicit FAIR compliance.

**Action.** Add a FAIR compliance section to the replication package README:

- **Findable.** Persistent DOIs via Zenodo. Rich metadata. Indexed in OpenAIRE.
- **Accessible.** Open access via Zenodo with no authentication barriers. Repository remains accessible per Zenodo's preservation commitment (CERN-backed).
- **Interoperable.** Data in standard formats (JSON, CSV, Markdown). Schemas published. Use of standard vocabularies where possible (PROV, NIST AI RMF, SHA-256).
- **Reusable.** Clear license (CC-BY-4.0). Provenance via deviation log. Detailed methodology enables reproduction.

### Addition 6: CRediT Contribution Taxonomy

**Issue:** Modern publication standards expect CRediT (Contributor Roles Taxonomy) attribution.

**Action.** In the final report, replace the simple author contribution statement with structured CRediT roles:

```markdown
## Author Contributions (CRediT)

**Elias Calboreanu (Principal Investigator):**
Conceptualization, Methodology, Software (AEGIS reference implementation),
Validation, Formal analysis, Investigation, Resources, Data curation,
Writing - original draft, Writing - review and editing, Visualization,
Supervision, Project administration.

**[Lead Analyst Name]:**
Methodology, Software (evaluation pipeline), Validation, Formal analysis,
Investigation, Data curation, Writing - original draft (methods section),
Writing - review and editing.

**[SME Brad Carter]:**
Investigation (ground truth signoff), Validation (realism audit),
Writing - review and editing.

**[SME Jason McKay]:**
Investigation (ground truth signoff), Validation (realism audit),
Writing - review and editing.

**[External Spot-Checker Name]:**
Validation (independent anchor authoring), Writing - review and editing.
```

### Addition 7: MLR Reproducibility Checklist Compliance

**Issue:** ML venues increasingly require the Machine Learning Reproducibility checklist (Pineau et al.) be completed and included.

**Action.** Complete the MLR checklist as a replication package appendix. Items include:

- Specification of all algorithms used
- Computational environment specification
- Random seed handling
- Data preprocessing steps
- Hyperparameter search procedure
- Number of evaluation runs
- Hardware specifications
- Variance reporting
- Statistical significance testing methodology

The v4 protocol already satisfies most items; the checklist serves as confirmation and explicit documentation.

### Addition 8: Empirical SE Reporting Standards Compliance

**Issue:** Empirical software engineering venues (TSE, TOSEM, EMSE) have specific reporting expectations.

**Action.** Cross-reference the v4 protocol against the Empirical Software Engineering reporting standards (Carver et al. 2014 framework or equivalent):

- Research goals stated as GQM (Goal-Question-Metric)
- Threats to validity discussed structurally (TTV section)
- Replication encouraged via open data
- Statistical methods justified
- Sample size justification
- Effect sizes and confidence intervals

Most items are addressed. The explicit compliance statement is the addition.

### Addition 9: Operational Significance Thresholds

**Issue:** A statistically significant difference of 2 percentage points may not be operationally meaningful. Q1 reviewers ask "what difference would actually matter in practice?"

**Action.** Before unblinding results, the protocol commits to operational significance thresholds:

```markdown
## Operational Significance Thresholds

For each primary metric, the following thresholds are pre-specified as
the minimum effect size that would justify recommending MANDATE adoption
over a baseline in operational deployment:

| Metric | Statistical bar | Operational bar |
|--------|-----------------|-----------------|
| Anchor completeness | p < 0.0125 AND Cohen's h >= 0.2 | At least 10 percentage points absolute improvement |
| Gap detection F1 | p < 0.0125 AND Cohen's h >= 0.3 | At least 15 percentage points absolute improvement on F1 |
| Trace completeness | At least 95% rate | At least 95% rate |
| Adversarial resistance | p < 0.0125 AND difference >= 30pp | At least 30 percentage points absolute resistance advantage |

If a result clears the statistical bar but not the operational bar, it
is reported as "statistically significant but operationally marginal."
This honesty separates findings that should change deployment decisions
from findings that should inform academic discussion only.
```

### Addition 10: Negative Results Commitment

**Issue:** Pre-registration combined with negative results commitment is the strongest defense against file-drawer bias.

**Action.** Add to pre-registration explicitly:

```markdown
## Negative Results Commitment

The authors commit to publishing the results of this evaluation regardless
of whether MANDATE demonstrates statistical or operational advantage over
baselines. Specifically:

- If MANDATE fails any primary hypothesis, the failure is reported as
  the primary finding.
- If MANDATE shows marginal or null effects, the marginality is reported
  honestly, not buried.
- If MANDATE shows statistically significant but operationally marginal
  effects, this distinction is reported prominently.
- The replication package is deposited regardless of result direction.

A null or negative result represents a contribution: it is evidence
that the MANDATE architecture, at least as evaluated, does not deliver
the claimed advantages. This is publishable and methodologically
important.
```

---

## Part 3: Medium-Priority Additions

### Addition 11: Reproducibility Infrastructure (Docker + CI)

**Action.** Produce a Docker container with the complete environment:

```dockerfile
FROM python:3.11-slim
WORKDIR /eval
COPY environment.yml .
RUN conda env create -f environment.yml
COPY . .
CMD ["jupyter", "lab", "--no-browser"]
```

Add GitHub Actions workflow that runs the analysis pipeline on a small synthetic dataset whenever the analysis notebooks are modified. This is a continuous integrity check, not a result check.

### Addition 12: Risk-Tiered Interpretation Framework

**Action.** Add to the final report a section on how MANDATE's performance metrics map to deployment recommendations across operational risk tiers:

| Risk Tier | Example Context | Minimum MANDATE Performance for Recommendation |
|-----------|-----------------|------------------------------------------------|
| Low | Routine internal reporting | Anchor completeness >= 75%, gap detection F1 >= 0.7 |
| Medium | Business decisions, customer-facing | Anchor completeness >= 85%, gap detection F1 >= 0.8, adversarial resistance >= 0.9 |
| High | Safety-critical, regulated | Anchor completeness >= 95%, gap detection F1 >= 0.9, adversarial resistance >= 0.95, plus human review in loop |
| Critical | Defense, medical, infrastructure | MANDATE used only as decision support; no autonomous execution |

Whether MANDATE clears each tier's bar becomes a practical finding from the empirical results.

### Addition 13: Cross-Validation Strategies

**Action.** Add to the analysis plan:

- **K-fold cross-validation** across tasks: 5-fold CV on the 120-task corpus to test stability of findings across task subsets.
- **Leave-one-domain-out generalization**: train (or calibrate) on 2 domains, test on the third. Tests whether MANDATE's advantage is domain-specific or domain-general.
- **Stratified bootstrap**: resampling with replacement within domain strata to compute robust CIs that respect the domain structure.

### Addition 14: Sensitivity to Grader Rubric

**Action.** On a 30-output subset, re-grade with an alternate rubric variant that emphasizes different criteria (e.g., a "strict" rubric that requires exact threshold matches vs. the primary rubric that allows order-of-magnitude matching). Test whether headline findings hold under both rubrics.

This addresses the threat that the chosen rubric coincidentally favors MANDATE.

### Addition 15: Long-Tail Failure Analysis

**Action.** After grading, identify the hardest 12 tasks (worst 10% by mean anchor completeness across all systems). Qualitative deep-dive on these:

- What is hard about them?
- Does any system handle them well?
- Are they pathological cases or genuinely difficult?
- What would a hypothetical "perfect" system look like for them?

This qualitative section is highly valued by Q1 reviewers because it shows engagement with the data beyond summary statistics.

### Addition 16: Theory-Prediction Matching

**Action.** Before unblinding results, the MANDATE paper's theoretical claims are translated into specific empirical predictions:

- "Role separation improves quality" → ablation 1 (no role separation) should show degradation
- "Registry enables precedent reuse" → ablation 2 should degrade on tasks similar to registry entries
- "Trace provenance supports audit" → trace completeness should be near-100% for MANDATE
- "Gap detection prevents fabrication" → fabrication rate should be lower for MANDATE than baselines

Each prediction is tested. Where the empirical result matches the theoretical prediction, the theory is supported. Where it does not, the discrepancy is a finding.

### Addition 17: Pre-Existing Benchmark Integration

**Action.** Evaluate whether MANDATE can be run on an existing public benchmark to add cross-validation evidence:

- **AgentBench** (Liu et al. 2024): Task completion benchmark. MANDATE produces specifications, not executions, so direct comparison is awkward, but anchor quality on AgentBench-derived tasks could be measured.
- **ToolBench**: Tool use benchmark; similar issue.
- **NaturalSpec or related** benchmarks if they exist for natural language specification.

If a suitable benchmark is identified, run a subset of evaluations on it. This adds an external validity arm to the study.

If no suitable benchmark exists, this is itself a methodological finding worth noting (the field lacks specification-quality benchmarks; MANDATE evaluation contributes by demonstrating one).

---

## Part 4: Low-Priority Additions (Nice-to-Have)

### Addition 18: Carbon Footprint Reporting

Use the CodeCarbon Python library (or equivalent) to estimate kgCO2eq for the compute phase. Report in the methods section.

### Addition 19: Red Team Adversarial Evaluation

Beyond automated perturbations, a human red team attempts to craft inputs that break MANDATE. Even a small effort (2-3 hours by 1-2 security professionals) produces qualitative findings on robustness.

### Addition 20: End-User Validation

Beyond SMEs (ground truth) and graders (LLM and human), recruit 3-5 potential users of MANDATE output (e.g., automation engineers who would consume mandate-as-code) and ask them to evaluate sample outputs for downstream usability. Qualitative findings only.

### Addition 21: Workflow Management

Migrate ad hoc analysis scripts to a workflow manager (Snakemake or Nextflow) for true reproducibility. The workflow definition file becomes a documented artifact.

---

## Part 5: Summary

The package now includes:

| Layer | Document | What it provides |
|-------|----------|------------------|
| 1 | `00_PLAYBOOK_v2.md` | Core protocol with all standard methodology |
| 2 | `Q1_AUDIT_AND_ENHANCEMENTS.md` | Closes gaps to defensible-Q1 |
| 3 | `Q1_PLUS_UNBOUNDED_SCALING.md` | Expands to definitive-Q1+ with backend matrix, baseline matrix, replication scale |
| 4 | `FINAL_AUDIT_V5.md` | Closes remaining gaps for academic submission completeness |

Together, these four documents specify an evaluation that meets the highest empirical standards in the field. The marginal cost of the v5 additions is documentation work and modest external coordination (IRB letter, SME agreements), not additional compute or analysis time.

After applying v5, the only honest remaining limitations are those acknowledged in Threats to Validity:

- Single research team execution (independent replication is future work)
- Limited domain coverage (3 primary + 1 hold-out; broader domains are future work)
- English-only corpus (multilingual is future work)
- Specification quality measured, not downstream execution quality (runtime evaluation is future work)

These are honest scope limitations, not methodological gaps. They are publishable as future work directions.

---

**End of final audit.**
