# Deliverables Checklist and Quick Reference

This is the single document the Lead Analyst uses to track progress. Check off items as completed; add notes where deviations occur.

---

## Phase Gates and Deliverables

### Phase 0: Setup and Pre-Registration (Weeks 1-2)

- [ ] Project directory structure created per SETUP.md
- [ ] Python environment provisioned and verified
- [ ] API access for all model families confirmed
- [ ] AEGIS (Autonomous Engineering Governance and Intelligence System) reference implementation accessible
- [ ] SME briefings completed (Brad, Jason, Cal)
- [ ] External spot-checker identified and onboarded
- [ ] Pre-registration document complete (every placeholder filled)
- [ ] Pre-registration approved by Cal in writing
- [ ] Pre-registration deposited on Zenodo; DOI captured
- [ ] **GATE: No data generation begins before this gate**

### Phase 0 (continued): Pilot Study (Week 2)

- [ ] 6 pilot tasks generated (2 per domain)
- [ ] AI scaffolds produced for all 6
- [ ] SMEs complete signoffs (2 each)
- [ ] 3-task overlap sample IRR computed
- [ ] Perturbation generated (5 perturbations on one task)
- [ ] MANDATE executed on all pilot tasks + perturbations
- [ ] Both baselines executed
- [ ] Three-judge ensemble grading completed
- [ ] Grader IRR computed on pilot
- [ ] Pilot findings memo drafted and submitted to Cal
- [ ] **GATE: Pilot approval before Phase 1 begins**
- [ ] Protocol v1.1 deposited if updates were required

### Phase 1: Calibration (Week 3)

- [ ] 6 calibration tasks loaded from package
- [ ] MANDATE executed on all 6
- [ ] Baseline 1 executed on all 6
- [ ] Baseline 2 executed on all 6
- [ ] All systems pass calibration (extract anchors correctly)
- [ ] Calibration pass report produced
- [ ] **GATE: Any system failure here halts and triggers config review**

### Phase 2: Corpus Generation (Week 4)

- [ ] Generation prompts run per domain × category
- [ ] Approximately 225 candidate tasks generated (75 per domain)
- [ ] Lead Analyst selects 30 per domain optimizing for diversity
- [ ] Diversity dimensions verified
- [ ] Deduplication run with 0.85 cosine threshold
- [ ] Deduplication validated on calibration pair set (known-distinct, known-paraphrase)
- [ ] Realism audit distributed to SMEs (10 tasks each, distinct from their signoff assignment)
- [ ] Realism audit results computed
- [ ] Tasks below 2.5 mean realism reworked or replaced
- [ ] Corpus frozen as `corpus_freeze_v1`
- [ ] **GATE: Maximum 10% exclusion rate maintained**

### Phase 3: Ground Truth Construction (Weeks 5-6)

- [ ] AI scaffolds produced for all 90 corpus tasks
- [ ] Signoff packets distributed to SMEs (30 each)
- [ ] SME briefing reinforces independence statement protocol
- [ ] Overlap sample identified (12 tasks, 4 per domain)
- [ ] All 3 SMEs author overlap sample independently
- [ ] Pairwise Cohen's kappa computed across 3 SME pairs
- [ ] Krippendorff's alpha computed across all 3 SMEs
- [ ] If kappa < 0.4 on any pair, calibration session held and overlap redone
- [ ] If kappa < 0.4 after calibration, halt
- [ ] Each SME completes 30 task signoffs
- [ ] Independence statements signed on every form
- [ ] External spot-checker authors 9 task anchors independently
- [ ] External agreement computed against SME-signed ground truth
- [ ] Ground truth frozen as `gt_freeze_v1`
- [ ] **GATE: All SMEs complete; kappa acceptable; external agreement reported**

### Phase 4: Baseline Calibration (Week 7)

- [ ] Baseline 1 prompt engineering on 6 calibration tasks (3-day budget)
- [ ] Baseline 1 calibration log captured
- [ ] Baseline 1 frozen configuration
- [ ] Baseline 2 prompt and tool engineering (3-day budget)
- [ ] Baseline 2 calibration log captured
- [ ] Baseline 2 frozen configuration
- [ ] Frozen as `baseline_freeze_v1`
- [ ] **GATE: Both baselines reach working state within budget**

### Phase 5: Perturbation Generation (Week 8)

- [ ] 30 base tasks sampled (10 per domain) from corpus
- [ ] 30 surface noise perturbations generated
- [ ] 30 ambiguity injection perturbations generated
- [ ] 30 contradictory constraint perturbations generated
- [ ] 30 prompt injection perturbations (10 each sub-type)
- [ ] 30 missing field perturbations generated
- [ ] 30% spot-checked by Lead Analyst
- [ ] Perturbations frozen as `perturbation_freeze_v1`

### Phase 6: System Execution (Week 8)

- [ ] MANDATE × 90 tasks × 3 runs (270 runs)
- [ ] MANDATE × 150 perturbations × 3 runs (450 runs)
- [ ] Baseline 1 × 90 tasks × 3 runs (270 runs)
- [ ] Baseline 1 × 150 perturbations × 3 runs (450 runs)
- [ ] Baseline 2 × 90 tasks × 3 runs (270 runs)
- [ ] Baseline 2 × 150 perturbations × 3 runs (450 runs)
- [ ] Total: 2,160 runs captured with metadata
- [ ] All outputs anonymized
- [ ] Anonymization mapping stored separately (NOT accessible to graders)
- [ ] Outputs frozen as `outputs_freeze_v1`

### Phase 7: Ablation Studies (Week 9)

- [ ] 20-task ablation subset identified
- [ ] Ablation 1 (no role separation) executed
- [ ] Ablation 2 (no Success Registry) executed
- [ ] Ablation 3 (no Search-Trace) executed
- [ ] Ablation outputs anonymized and added to grading queue

### Phase 8: Three-Judge Ensemble Grading (Week 10)

- [ ] Judge 1 (GPT-4o) graded all outputs
- [ ] Judge 2 (Claude Opus 4) graded all outputs
- [ ] Judge 3 (Gemini 2.5 Pro) graded all outputs
- [ ] 20% double-graded sample completed
- [ ] Pairwise grader Cohen's kappa computed
- [ ] Krippendorff's alpha across graders computed
- [ ] If grader kappa < 0.4, rubric revised and re-grade
- [ ] Ensemble aggregation completed (majority vote / median)
- [ ] Disagreement cases logged

### Phase 9: Analysis (Week 11)

- [ ] Notebook 1: Corpus and signoff summary
- [ ] Notebook 2: System outputs summary
- [ ] Notebook 3: Primary hypothesis tests
- [ ] Notebook 4: Exploratory subgroup analyses
- [ ] Notebook 5: Sensitivity analyses
- [ ] Notebook 6: Ablation results
- [ ] Notebook 7: Failure mode coding and analysis
- [ ] Notebook 8: Final tables and figures
- [ ] All headline findings documented with effect sizes and CIs
- [ ] Sensitivity stability assessed

### Phase 10: Final Report (Week 12)

- [ ] Failure mode coding completed for every failed run
- [ ] Final report drafted
- [ ] Limitations section honest and complete
- [ ] Deviation log finalized
- [ ] Executive summary drafted
- [ ] Cal reviews and provides feedback
- [ ] Report revised
- [ ] Replication package assembled
- [ ] Replication package deposited on Zenodo with separate DOI
- [ ] **FINAL DELIVERY: Report + DOIs handed off to Cal**

---

## Quick Reference: Critical Numbers

| Quantity | Value | Source |
|----------|-------|--------|
| Main corpus tasks | 90 (30 per domain) | Playbook §8.1 |
| Pilot tasks | 6 | Playbook §6 |
| Calibration tasks | 6 | Playbook §7 |
| Perturbations total | 150 (30 per type × 5) | Playbook §11.1 |
| Ablation subset | 20 tasks | Playbook §13.2 |
| SME overlap sample | 12 tasks | Playbook §9.6.1 |
| External spot-check sample | 9 tasks (10%) | Playbook §9.7 |
| Runs per task per system | 3 | Playbook §12.1 |
| Total system runs | 2,160 | Calculation |
| Maximum exclusion rate | 10% | Playbook §5.3 |
| Minimum SME kappa | 0.4 (halt below) | Playbook §9.6.2 |
| Target SME kappa | 0.6 | Playbook §9.6.2 |
| Minimum grader kappa | 0.4 (halt below) | Playbook §14.5 |
| Family-wise α | 0.05 (Holm-Bonferroni) | Playbook §5.3 |
| Bootstrap resamples | 10,000 | Playbook §5.3 |
| Embedding similarity threshold | 0.85 | Playbook §8.6 |

---

## Critical Don'ts

These will compromise the evaluation. Do not:

- Generate any data before pre-registration is deposited
- Let an SME read AI scaffold before forming independent judgment
- Edit any artifact after its freeze tag
- Give graders access to the anonymization mapping
- Use Qwen3-family models for any role outside MANDATE
- Run a single judge instead of the three-judge ensemble
- Skip the pilot phase
- Change a metric definition mid-analysis without documenting in deviation log
- Cherry-pick which subgroups to report
- Hide an unfavorable finding

If any of the above is unavoidable due to circumstances, document in deviation log immediately and escalate to Cal.

---

## Critical Do's

- Read the playbook fully before starting
- Schedule the pilot kickoff first
- Brief SMEs on the independence protocol before they touch a signoff form
- Document every deviation in real time, not retroactively
- Send weekly status reports every Monday by 1700 ET
- Tag every freeze in git
- Verify backups daily
- Surface problems early; Cal would rather know in week 1 than week 11

---

**End of checklist.**
