# Forms and Templates

All forms used in the evaluation. Copy the relevant section, fill in, save with the naming convention shown.

---

## 1. SME Signoff Form

**Usage:** Each SME fills this in for every assigned task during Phase 3. One form per task.
**File naming:** `signoff_TASK-{ID}_{REVIEWER_INITIALS}_{YYYYMMDD}.md`
**Estimated time:** 8 to 12 minutes per task.

```markdown
# Ground Truth Signoff: TASK-[ID]

**Reviewer:** ____________________
**Date and time started:** _______________________
**Time spent (minutes):** _______

## 1. Task Description

[Paste the request_text from the corpus task here. Do NOT include any
metadata such as category or intended_gap_field.]

## 2. Independent Assessment (FILL IN BEFORE READING AI SCAFFOLD)

Before reading the AI scaffolded anchor below, capture your independent
sense of the task:

- **Mission intent (in your own words):**

- **Critical minimum threshold(s) that come to mind:**

- **Is this task gap-triggering? (Y / N):**

- **If gap-triggering, what is missing:**

[Stop here. Read the AI scaffold below ONLY after writing the above.]

---

## 3. AI Scaffolded Anchor (For Comparison Only)

[Paste the AI-scaffolded JSON here.]

---

## 4. Field-by-Field Review

For each field in the AI scaffolded anchor, mark Accept, Revise, or Remove.
Add fields the AI missed.

### Mission Intent
- AI proposal: ________________
- Action: Accept / Revise / Remove
- If revised, your version: ________________

### Minimum Dimensions

| AI dimension | AI threshold | Action | Your value (if revised) | Rationale |
|--------------|--------------|--------|-------------------------|-----------|
| | | A/R/X | | |
| | | A/R/X | | |
| | | A/R/X | | |

Additional minimum dimensions not in AI scaffold:
- Dimension: __________, Threshold: __________, Rationale: __________

### Target Dimensions

| AI dimension | AI objective | Action | Your value (if revised) | Rationale |
|--------------|--------------|--------|-------------------------|-----------|
| | | A/R/X | | |

### Constraints

| AI predicate | Action | Your version (if revised) | Rationale |
|--------------|--------|---------------------------|-----------|
| | A/R/X | | |

## 5. Gap Assessment

Suspected gaps from AI scaffold:

| Gap field | Confirmed / Rejected / Reclassified | If reclassified, to what gap_type |
|-----------|--------------------------------------|----------------------------------|
| | | |

Additional gaps not flagged by AI:
- Field: __________, Reason: __________

## 6. Final Ground Truth Anchor

[Reviewer pastes the final agreed anchor JSON here, in the schema from
Playbook Section 9.5.]

## 7. Independence Statement

I confirm that the above represents my expert judgment of acceptable
success criteria for this task, formed independently of how any system
might process it. I read the AI scaffold only after forming my initial
assessment in Section 2.

**Signature:** ____________________
**Timestamp:** ____________________

## 8. Notes for Lead Analyst (Optional)

[Any concerns, questions, or items requiring discussion]
```

---

## 2. Realism Audit Form

**Usage:** Each SME rates 10 tasks for realism before corpus freeze (Phase 2, Section 8.5).
**File naming:** `realism_audit_{REVIEWER_INITIALS}_{YYYYMMDD}.md`
**Estimated time:** 1 hour per SME total.

```markdown
# Realism Audit

**Reviewer:** ____________________
**Date:** ____________________

For each task below, rate operational realism on a 4-point scale:
- 4: I have seen this exact request type in operational work
- 3: This is realistic and plausible
- 2: This is somewhat realistic but feels artificial
- 1: This is not realistic; a real stakeholder would not write this

Tasks averaging below 2.5 will be flagged for rework or replacement.

## Task TASK-[ID-1]

**Task text:**
[Paste full request_text]

**Rating (1-4):** _____
**Comment (optional):** ____________________

## Task TASK-[ID-2]
...

[Repeat for all 10 assigned tasks]
```

---

## 3. External Spot-Check Form

**Usage:** External spot-checker independently authors anchors for 9 tasks (10% sample).
**File naming:** `spotcheck_TASK-{ID}_external_{YYYYMMDD}.md`

```markdown
# External Spot-Check: TASK-[ID]

**External Reviewer:** ____________________
**Affiliation:** ____________________
**Date:** ____________________

## Task Description

[Paste the request_text only. Do not include any SME signoff or
internal metadata.]

## Your Independent Ground Truth

[Author your version of the anchor independently. Use the same schema
as the SME signoff: mission_intent, minimum, target, constraints,
expected_gaps.]

## Confidence Statement

I have authored this ground truth independently, without prior knowledge
of the internal team's signoff. I have no commercial or affiliation
relationship with The Swift Group, LLC.

**Signature:** ____________________
**Timestamp:** ____________________
```

---

## 4. Failure Mode Coding Sheet

**Usage:** Lead Analyst codes every failed run (a run that scores below threshold on at least one primary metric) into one of the 9 pre-registered categories.
**File naming:** `failure_coding_master.csv` (one master sheet, append rows)

```csv
run_id,task_id,system,run_number,failure_category,description,evidence,coder
RUN-00001,TASK-SEC-007,MANDATE,2,extraction_failure,"Failed to extract the 95% compliance threshold from the request","Ground truth had threshold=0.95; output omitted","Lead Analyst"
```

**Categories (from Playbook Section 18.2):**

| Code | Category | Definition |
|------|----------|------------|
| extraction_failure | Extraction failure | System did not extract information present in input |
| fabrication | Fabrication | System invented information not in input or ground truth |
| misclassification | Misclassification | Information extracted but classified wrongly (e.g., constraint as target) |
| silent_gap | Silent gap | System proceeded without flagging an expected gap |
| false_gap | False gap | System flagged a gap where ground truth had none |
| trace_failure | Trace failure | Output complete but trace incomplete or unverifiable |
| adversarial_compliance | Adversarial compliance | System complied with prompt injection |
| calibration_failure | Calibration failure | Failed on a calibration task (config issue) |
| infrastructure_failure | Infrastructure failure | System crashed or timed out |

For each failure, the coder enters a one-sentence description and a one-sentence pointer to the evidence (which output element, which ground truth field).

Ambiguous cases (multiple categories could apply) escalate to Cal for adjudication.

---

## 5. Pilot Findings Memo Template

**Usage:** End of Phase 0. Lead Analyst summarizes pilot learnings for Cal's review.
**File naming:** `pilot_findings_memo_v1.md`
**Length:** Maximum 3 pages.

```markdown
# Pilot Findings Memo

**Date:** ____________________
**Author:** [Lead Analyst Name]
**Recipient:** Cal

## 1. Executive Summary

[2 to 3 sentences: did the pilot succeed, what should change before
main run, are we ready to proceed.]

## 2. Pilot Execution Summary

- Tasks executed: 6
- AI generations attempted: __
- Successful generations: __
- SME signoffs completed: __
- IRR on 3-task overlap: kappa = __
- System runs attempted: __
- System runs completed: __
- Grading runs completed: __
- Grader IRR: kappa = __

## 3. What Worked

[List 3 to 5 protocol elements that executed cleanly.]

## 4. What Did Not Work

[List every protocol element that failed, timed out, or produced
ambiguous results. Be specific about which playbook section is affected.]

## 5. Recommended Protocol Updates

For each recommendation, cite the playbook section, describe the proposed
change, and the rationale.

| Section | Current | Proposed Change | Rationale |
|---------|---------|-----------------|-----------|
| | | | |

## 6. Tooling Issues

[Infrastructure, model API, scripting issues encountered.]

## 7. Time Estimate Update

If the pilot exposed timing issues, update the timeline estimate for
the main run here.

## 8. Decision Requested from Cal

- Approve protocol as-is and proceed to Phase 1
- Approve protocol with the proposed updates (as v1.1 addendum)
- Halt and revise protocol substantially before proceeding
```

---

## 6. Weekly Status Report Template

**Usage:** Lead Analyst sends to Cal every Monday by 1700 ET.
**File naming:** `status_week{N}_{YYYYMMDD}.md`

```markdown
# MANDATE Eval Status: Week [N]

**Date:** ____________________
**Phase:** [current phase per playbook]
**Schedule status:** On track / Slipping by X days / Recovered

## Completed This Week

-
-
-

## In Progress

-
-

## Blockers

-

## SME Status

- Brad: [tasks completed / total assigned, any concerns]
- Jason: [tasks completed / total assigned, any concerns]
- Cal: [tasks completed / total assigned, any concerns]

## Decisions Needed from Cal

-

## Next Week Plan

-
-

## Risks Surfacing

-
```

---

## 7. Deviation Log

**Usage:** A running log of every deviation from the pre-registered protocol. Append-only.
**File naming:** `deviation_log.md` (single file, growing)

```markdown
# Deviation Log

## Format

Each entry includes: timestamp, phase, deviation description, rationale,
impact assessment, Cal approval (if required).

## Entries

### Entry 001

**Date:** ____________________
**Phase:** ____________________
**Deviation:** ____________________
**Rationale:** ____________________
**Impact on results:** [None / Minor / Material]
**Cal approval (if required):** [Y/N], [Date]
**Pre-registration section affected:** ____________________

### Entry 002

...
```

The deviation log is published as part of the final report and replication package. It is one of the most important defensive artifacts: reviewers respect honest deviation reporting more than they would respect a falsely clean protocol.

---

## 8. Final Report Template

**Usage:** End of Phase 9. The publication-ready empirical section.
**File naming:** `final_report_v1.md`

```markdown
# MANDATE Empirical Evaluation: Final Report

**Authors:** [Lead Analyst Name], Elias Calboreanu
**Date:** ____________________
**Companion to:** [Zenodo pre-registration DOI], [Zenodo replication package DOI]

## 1. Executive Summary

[1 page. The headline finding for each of the 4 primary hypotheses,
with effect sizes and CIs.]

## 2. Methodology Summary

[2 pages. Refer to pre-registration for full protocol; summarize the
key elements: corpus, systems, grading, statistics.]

## 3. Primary Results

### 3.1 Hypothesis-by-Hypothesis Findings

[For each of H1-H4: result, effect size, CI, statistical test, narrative.]

### 3.2 Per-Domain Results

[Table 2 from Playbook Section 15.5.]

### 3.3 Robustness Results

[Table 3.]

### 3.4 Ablation Results

[Table 4.]

## 4. Qualitative Findings

### 4.1 Failure Mode Distribution

[Per-system breakdown of failure categories.]

### 4.2 Stability Across Runs

[Stochastic variance analysis.]

### 4.3 Notable Patterns

[Anything that emerged from the data not captured by primary metrics.]

## 5. Inter-Rater Reliability

[Table 5: SME kappa, grader kappa, external spot-check agreement.]

## 6. Sensitivity Analyses

[Results of the 3 pre-specified sensitivity checks.]

## 7. Limitations

[At minimum: sample size, domain coverage, AI-assisted generation,
SME pool size, conflict of interest acknowledgment.]

## 8. Deviation Log Summary

[Summary of any deviations; full log in appendix.]

## 9. Conclusions

[Tied directly to the hypotheses, not overclaimed.]

## Appendices

- A. Full deviation log
- B. All result tables
- C. All effect size and CI tables
- D. Subgroup analyses
- E. Failure mode coding details
- F. Replication package DOI and contents
```

---

**End of forms reference.**
