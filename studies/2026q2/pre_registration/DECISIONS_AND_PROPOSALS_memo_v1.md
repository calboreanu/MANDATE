# Decisions and Proposals Memo, v1

**To:** Cal (PI)
**From:** Lead Analyst
**Date:** 2026-05-23
**Re:** Day-1 decisions that unblock the MANDATE empirical evaluation

---

## 0. Purpose and how to use this memo

PROTOCOL_LOCK and the package README assign the Lead Analyst a short list of Day-1 actions that are explicitly "propose to Cal for approval": the hold-out 4th domain, the external spot-checker, the human expert, and the SME briefings. The execution plan adds a few more decisions that change scope. This memo collects all of them in one place, gives a recommendation and rationale for each, and states what each one unblocks.

None of these decisions block the apparatus engineering, which is proceeding in parallel (see Section 8). They block the **pre-registration deposit**, which is the gate before any data is generated. Treat this memo as the agenda for the kickoff meeting. Approving a recommendation can be as short as "approved" against its number.

---

## 1. Hold-out 4th domain

**Decision needed:** which domain is the held-out generalization domain (30 tasks, MANDATE-primary and strongest baseline only).

**Constraints.** The hold-out domain must not have been used in fine-tuning or rubric calibration. The MANDATE training corpus (125 examples) covers cyber, legal, financial, and intel. The three main evaluation domains are security operations, financial reporting, and intelligence collection. PROTOCOL_LOCK recommends software engineering specification or operations/maintenance reporting.

**Recommendation: software engineering specification.**

Rationale:
- It is cleanly outside all four training-corpus domains and all three evaluation domains. Operations/maintenance reporting is also outside them, but it sits conceptually next to "security operations reporting," which slightly weakens the "held-out" claim a reviewer would scrutinize.
- It speaks directly to the audience that has already engaged MANDATE. The Requirements Engineering venue desk-rejected the prior work; a software-engineering generalization result is the most relevant possible evidence for that readership.
- The practitioner pool is large, which makes recruiting the 1 to 2 hold-out-domain SMEs straightforward.

Acceptable alternative: operations/maintenance reporting, with the adjacency caveat noted in the limitations section.

**Unblocks:** hold-out corpus authoring (30 tasks), hold-out SME recruitment, the PREREGISTRATION_TEMPLATE Section 3.2 placeholder.

---

## 2. Phase 6 execution host

**Decision needed:** confirm the physical host for the main run and where the fine-tuned MANDATE models live.

**What we know.** `configs/runtime/ws01_model_manifest.json` documents the six `mandate-*` Ollama models on a workstation named `lattice-ws01` running Ollama 0.16.2. PROTOCOL_LOCK Section 2.1 names a "Mac mini M4 Pro cluster." These may be the same machine under two names, or not.

**Why it matters.** The execution plan flagged this as a real schedule risk. MANDATE-primary alone is roughly 2,950 runs, each invoking six sequential LLM roles, four of them on a 32B model. On a single Mac mini M4 Pro that is on the order of hundreds of wall-clock hours before the other systems. The package puts Phase 6 in "Week 9." That is realistic only if the cluster is genuinely several machines running in parallel.

**Questions for you:**
1. Is the "cluster" one machine or several? How many nodes?
2. Is `lattice-ws01` one of the Mac mini M4 Pro nodes, or a separate workstation?
3. Are the six fine-tuned Ollama models already resident on the intended eval host, or do they need to be re-registered there?

**Unblocks:** Workstream A1 (verify the fine-tunes run, with no silent fallback), the Phase 6 schedule, and the model SHA-256 pinning.

---

## 3. The request_text to MissionInput adapter

**Decision needed:** how MANDATE receives the natural-language task text.

**Background.** The protocol hands every system the same natural-language `request_text` (a stakeholder memo, as in the six calibration tasks). MANDATE's pipeline consumes a structured `MissionInput`. The AEGIS CLI has a `--from-document` path that runs a deterministic ingestion stack (Pandoc, PDF, OCR, quality checker) on a document file, but the evaluation provides a string, not a file.

**Recommendation: the thinnest possible adapter.** Construct a `MissionInput` that carries the raw `request_text` as its content and leaves the structured fields for the fine-tuned Intake role to populate. Do not pre-structure the text with a heavier pre-processor. The reason is fairness and interpretability: the substantive extraction work should be done by MANDATE's own roles, which is what the study measures, not by a pre-processing step that no baseline gets. Every baseline receives the identical raw `request_text`.

The adapter, once chosen, is part of MANDATE-primary's measured behavior and will be pinned in the pre-registration and frozen with the AEGIS tag.

**Unblocks:** the MANDATE adapter inside the uniform run harness (Workstream B1), and a clean pre-registration description of MANDATE-primary's inputs.

---

## 4. Baseline set and model versions

**Decision needed:** confirm exact model versions for the six baselines, and the model used inside the multi-agent frameworks.

PROTOCOL_LOCK Section 2.2 fixes the six baselines: B1 single-prompt Claude, B2 single-prompt GPT, B3 ReAct Claude, B4 AutoGen, B5 CrewAI, B6 LangGraph. The template leaves every model-version string as a placeholder, and B4 to B6 are listed as "Claude/GPT."

**Recommendation:** use one consistent model inside B4, B5, and B6 so that the agent framework is the variable under test, not the model. Holding the model constant across the three multi-agent baselines isolates "what the framework adds." I recommend Claude for B4 to B6, consistent with B1 and B3, so that B2 is the single clean GPT comparison and the model-family accounting in PREREG Section 5 stays simple. This is your call; the alternative (GPT inside the frameworks) is equally defensible as long as it is consistent and pre-registered.

You will also need to fix the exact version strings (for example `claude-...` and `gpt-4o-...`) at pinning time. Those are tracked in `TO_FILL_TRACKER.md` rows D7 and D8.

**Unblocks:** baseline construction (Workstream B2) and the model-family separation table.

---

## 5. Independent parties to recruit

The protocol's conflict-of-interest mitigations depend on genuinely independent people. They have the longest lead time of anything in the project and they gate the pre-registration deposit and the grading phase. Proposed criteria and slots:

**External spot-checker (1 person).** Authors independent ground-truth anchors for 24 of the 120 tasks. Must not be affiliated with the Swift Group. Should be literate across security operations, financial reporting, and intelligence collection, or comfortable authoring anchors in those domains. Estimated effort: 3 to 5 hours. Needed before Phase 3 ground truth completes.

**Hold-out-domain SMEs (1 to 2 people).** Author ground truth for the 30 hold-out tasks in the chosen 4th domain (software engineering specification, per Section 1). Estimated effort: 3 to 5 hours each. Needed before Phase 3 freeze.

**Human expert (1 person).** A senior practitioner, not in the SME ground-truth pool, who authors specifications for 30 tasks as the upper-bound baseline. Estimated effort: about 6 hours, single pass. Needed before Phase 6.

**Human grader(s) (1 to 2 people).** Apply the grading rubric to 100 outputs for the human-vs-judge calibration. Must not be the PI or any ground-truth SME. A second grader covers a 30-output overlap for inter-human reliability. Needed before Phase 8.5.

**Request:** please name candidates, or delegate the search to me with constraints. These four roles are rows B1 to B4 in `TO_FILL_TRACKER.md`.

---

## 6. SME briefings and kickoff

The package calls for SME briefings in week 2 and a 1-hour kickoff with you. The single most important briefing point is the independence statement: SMEs must form their own anchor before reading the AI scaffold, or the study's defense against "the SMEs rubber-stamped the AI" collapses.

**Request:** confirm availability for a kickoff, and confirm that Brad Carter and Jason McKay are committed and when they can take the independence briefing.

---

## 7. Staffing and timeline

The package frames the work as 15 to 16 weeks for one Lead Analyst. The execution plan's honest assessment is that this is optimistic: the evaluation apparatus (the uniform harness, six baselines, perturbation generator, anonymization, three-judge grading, ten analysis notebooks) is several engineer-months of software work, and the human-coordination phases carry wall-clock latency that staffing cannot remove.

**Request:** confirm who, besides the Lead Analyst, is available to build the apparatus, and whether the 15-to-16-week framing should be replaced with a schedule that reflects the build.

---

## 8. Decoding parameters for MANDATE-primary (added after the apparatus audit)

**Decision needed:** how MANDATE-primary's per-role decoding parameters are pinned, given that the protocol and the AEGIS configuration disagree.

**Background.** PROTOCOL_LOCK Section 10 pins deterministic decoding at temperature 0. The apparatus audit found that the AEGIS canonical configuration, `configs/llm_defaults.json`, assigns each of the six fine-tuned roles its own sampling temperature, and they are not all zero. The MANDATE adapter reads that file because doing so is what makes it faithful to how the AEGIS CLI actually runs MANDATE. The two specifications cannot both hold. This is row D10 in `TO_FILL_TRACKER.md`.

**Recommendation: adopt the AEGIS per-role temperatures (option a).** The construct under test is MANDATE-primary as the framework actually runs. The per-role temperatures are a property of the fine-tuned six-role configuration, not an incidental knob, so overriding them to 0 would evaluate a variant that no real MANDATE deployment uses. Reproducibility does not require a temperature-0 run: it is secured instead by pinning the random seed, recording the resolved `decoding_params` in every RunRecord, and reporting the 10-run stochastic stability in Notebook 02. The pre-registration decoding language should be amended to state that MANDATE-primary uses the per-role decoding parameters in AEGIS `configs/llm_defaults.json` at the pinned tag, captured verbatim in `provenance_evidence.md`; baselines keep their own pinned decoding settings, disclosed the same way. The alternative (force temperature 0, log a deviation) is defensible but trades external validity for a determinism the design does not need.

**Unblocks:** the A1 re-verification configuration on the eval host, and the PREREG Section 4.1 decoding-parameter text.

---

## 9. The O2b gap-precision definition (added after the apparatus audit)

**Decision needed:** confirm how the secondary outcome O2b (gap detection precision) is measured, or accept that it is reported descriptively.

**Background.** PROTOCOL_LOCK Section 4 defines O2b as TP / (TP + FP) on gap-triggering tasks. On a gap-triggering task the ground truth deliberately omits a required field, so it expects a gap. Under the rubric's strict false-positive definition ("system reported a gap and ground truth expected no gap"), a clean false positive cannot arise on that subset, which leaves O2b near-degenerate when measured exactly as written. O2b is a secondary outcome, not one of the five primary, so this does not affect the headline analysis.

**Recommendation: keep O2b as written, report it descriptively, and route false-gap behavior to Notebook 09.** Changing a locked outcome definition is a heavier step than the issue warrants for a secondary metric. O2b stays defined as in the protocol and is reported as a descriptive precision figure among gap reports, without a hypothesis test that its structure cannot support. The behavior people actually care about, a system inventing a gap on a task that has none, is a failure mode; it is already captured by the "false gap" category in the Notebook 09 failure-mode taxonomy, measured across the full corpus where false positives genuinely occur. If you would rather O2b carry a real precision test, the alternative is to re-specify it as precision across the full 120-task corpus, which is a pre-registration amendment.

**Unblocks:** the Notebook 04 and Notebook 09 specifications; no apparatus change either way.

---

## 10. What proceeds now, without waiting on these decisions

To be clear that the project is moving: none of the decisions above block the apparatus engineering. M0 reconciliation, M1 project setup, and Workstream B (the uniform harness, the MANDATE adapter, baselines B1 to B3, the perturbation generator, anonymization, three-judge grading, the power simulation, the O1 to O5 scorers, and the analysis notebooks) are built and unit-tested. The decisions above, and the independent-party recruitment, gate the **pre-registration deposit** and therefore the start of data generation, not the build. The remaining build items that do depend on a decision are the multi-agent baselines B4 to B6 (they need the model choice in Section 4 and live-API development on the eval host) and the A1 re-verification (it needs the decoding-parameter decision in Section 8).

---

## Summary

| # | Decision | Recommendation | Unblocks |
|---|----------|----------------|----------|
| 1 | Hold-out 4th domain | Software engineering specification | Hold-out corpus, hold-out SME recruitment |
| 2 | Phase 6 execution host | Confirm cluster size and model location | Workstream A1, Phase 6 schedule, model pinning |
| 3 | Input adapter | Thinnest `request_text` to `MissionInput` adapter | MANDATE adapter in the run harness |
| 4 | Baseline model versions | One consistent model inside B4 to B6 (recommend Claude) | Baseline construction |
| 5 | Independent parties | Name or delegate spot-checker, hold-out SMEs, human expert, graders | Pre-registration deposit, grading phase |
| 6 | SME briefings + kickoff | Schedule kickoff; confirm Brad and Jason | Phase 3 ground truth |
| 7 | Staffing and timeline | Confirm apparatus builders; revisit the 15-to-16-week framing | Realistic schedule |
| 8 | MANDATE-primary decoding parameters | Adopt the AEGIS per-role temperatures | A1 re-verification, PREREG Section 4.1 |
| 9 | O2b gap-precision definition | Keep as written, report descriptively, route false gaps to Notebook 09 | Notebook 04 and 09 specs |

A short approval against each number is enough to move every one of these forward.
