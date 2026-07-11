# MANDATE Empirical Evaluation: Coworker Package

**Welcome.** This package contains everything you need to execute the MANDATE empirical evaluation. The protocol is rigorous because the paper has been rejected twice on empirical grounds; this is the corrective. Do not improvise.

---

## Read these in this order

1. **This README** (you are here). 10 minutes.
2. **00_PLAYBOOK_v2.md** (the master protocol). Read it in full before you do anything. About 90 minutes.
3. **CHECKLIST.md** (the deliverables list). Use it to track progress.
4. **Phase-specific artifacts** as you reach each phase.

If you have not read the playbook in full, stop and read it. Skimming will cause errors that compound.

---

## Quick orientation

**What this evaluation does.** It tests MANDATE against two baseline systems on 90 operational tasks across three domains, with 150 perturbation trials, three ablation studies, three-judge ensemble grading, and full pre-registration. The output is a publication-grade evaluation suitable for the next MANDATE submission.

**Why the rigor.** MANDATE has been rejected at Frontiers in AI (twice) and desk-rejected at Requirements Engineering. Reviewers converge on the same complaint: empirical work is preliminary, self-referential, and lacks comparison. Every step here exists to close a specific reviewer objection.

**Your role.** You are the Lead Analyst. You own end-to-end execution. You do NOT contribute to ground truth signoff (you would compromise blinding). Cal is the Principal Investigator and adjudicates ambiguity. Brad Carter and Jason McKay are SMEs. An external spot-checker (to be assigned) provides independence.

**What success looks like.** At week 12, you hand Cal: a Zenodo-deposited pre-registration with DOI, a frozen 90-task corpus with SME-signed ground truth, frozen baseline configurations, 2,160 system runs across 3 systems, three-judge ensemble grading with disagreement statistics, ablation results, failure-mode-coded findings, primary statistical analyses with effect sizes and confidence intervals, a final report with limitations and deviation log, and a complete Zenodo replication package.

---

## File inventory

| File | Purpose | When to use |
|------|---------|-------------|
| `00_PLAYBOOK_v2.md` | Master protocol | Read first; reference throughout |
| `00_PREREGISTRATION_TEMPLATE.md` | Pre-registration doc to fill in | Week 1, before any data is generated |
| `calibration_tasks/` | 6 hand-authored unambiguous tasks | Phase 1, week 3 |
| `PROMPTS.md` | All AI prompts (generation, scaffolding, grading, perturbation) | Reference throughout |
| `FORMS.md` | All form templates (SME signoff, realism audit, spot-check, failure coding, pilot memo, status report, deviation log) | As each form is needed |
| `ANALYSIS_PLAN.md` | Statistical analysis plan with notebook outlines | Phase 9, weeks 9-11 |
| `SETUP.md` | Folder structure and environment setup | Day 1 |
| `CHECKLIST.md` | Final deliverables checklist | Reference throughout; final handoff |

---

## Day 1 actions

Do these in this exact order on day 1.

1. Read this README in full.
2. Read `00_PLAYBOOK_v2.md` in full. Take notes on questions; do not start work yet.
3. Schedule a 1-hour kickoff meeting with Cal to walk through your questions.
4. Read `SETUP.md` and create the project directory structure under wherever the project will live (recommended: `/work/mandate_eval_2026Q2/`).
5. Schedule SME briefings with Brad and Jason for week 2 (before Phase 0 pilot signoffs).
6. Identify candidates for the external spot-checker and propose to Cal for approval.

Do NOT begin Phase 0 until pre-registration is deposited on Zenodo and Cal has approved the protocol in writing.

---

## Escalation paths

**Page Cal immediately if any of:**

- Any halt condition in Playbook Section 16.1 triggers
- A prompt injection succeeds against MANDATE (treat as a finding, not an emergency, but flag immediately)
- SME availability collapses (illness, departure, etc.)
- Infrastructure failure persists more than 24 hours
- You discover a methodological flaw in the protocol mid-execution
- Any data is accidentally edited after freeze

**Wait until weekly sync to discuss:**

- Workflow inefficiencies that don't affect data
- Minor rubric interpretations (note them; we'll batch)
- Schedule slippage less than 3 days

**Proceed independently:**

- Anything explicitly within your authority per the playbook
- Routine administrative coordination with SMEs
- Tool selection within constraints (model versions specified in pre-reg are fixed; choice of embedding model for dedup, choice of analysis library, etc. are yours)

---

## Common pitfalls

These are the ways evaluations fail. Avoid them.

**Skipping the pilot.** Phase 0 exists because protocol bugs surface in execution, not in design. Skipping the pilot to "save time" turns a 1-week debug into a multi-week recovery.

**Letting SMEs read AI scaffold first.** The independence statement in the signoff form is your defense against "SMEs rubber-stamped AI proposals." If an SME reads the scaffold before forming their own judgment, the entire ground truth becomes suspect. Brief them on this before they touch the form.

**Editing frozen artifacts.** Once a git tag is applied to a freeze (corpus_freeze_v1, gt_freeze_v1, etc.), the files are immutable. If you find an error, you document it in the deviation log and create a new version, never edit in place.

**Cherry-picking metrics.** The pre-registration commits to specific metrics with specific definitions. If during analysis you discover a different metric would tell a better story, you may report it as exploratory but the pre-registered metric stays headlined. This is the price of pre-registration credibility.

**Hiding failures.** If MANDATE underperforms on a metric, report it. Reviewers respect honest reporting and punish concealment when they find it (and they find it). Section 16.2 of the playbook explicitly says this.

**Compromising blinding.** The output anonymization step before grading is critical. If a grader can tell which output came from MANDATE, the grading is compromised. Maintain the identifier mapping in a file the graders cannot access.

**Late-stage protocol changes without documentation.** Every deviation goes in the deviation log with timestamp and rationale. Undocumented changes look like p-hacking.

---

## Useful background on Cal's preferences

These are Cal's standing editorial standards across all his work. Match them in any writing you do for this project.

- No em-dashes
- American English (no British spelling)
- No AI-sounding language (avoid "delve", "tapestry", "navigate" as verb metaphors, "in the realm of", etc.)
- No deficit framing (frame things as opportunities, capabilities, and observations rather than gaps, problems, and failures, except where the methodology specifically requires gap language)
- Vendor-agnostic terminology in public-facing documents
- Cal signs informal communications as "Cal" and formal documents as "Elias Calboreanu"

If you produce writing that goes into the final report, run it past these standards before submitting.

---

## Status reporting

Send Cal a weekly status report every Monday by 1700 ET using the template in `FORMS.md`. If schedule is slipping, flag it in week 1 of slippage, not week 3. Cal would rather know early.

---

## If you're stuck

In order of escalation:

1. Re-read the relevant playbook section
2. Check `FORMS.md` and `PROMPTS.md` for templates
3. Search prior conversations or notes for related decisions
4. Slack Cal with a specific question (not an open-ended one)
5. Schedule a 15-minute focused call

Avoid open-ended "can we talk about Phase X" requests. Come with the specific question and your proposed answer; Cal will react faster.

---

**You have everything you need in this package. Read the playbook, set up the structure, get the pre-registration approved, and start.**

Good luck.

Cal
