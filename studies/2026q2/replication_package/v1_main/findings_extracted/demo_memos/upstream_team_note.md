# Note to the upstream MANDATE team: Decomposition role single-COA bias

**From:** Lead Analyst, MANDATE 2026Q2 empirical evaluation
**Date:** 2026-06-03
**Tag under evaluation:** `mandate-eval-primary-2026q2-v1` (commit `4f8af83`)
**Status:** Pre-deposit demonstration finding. Not formal study evidence; the formal Phase 6 study will quantify this against a 120-task corpus and the three-judge ensemble. Sharing now because the finding is clean enough to fold into the next training run if the team wants to.

## What we saw

Three real-world stakeholder specification requests across two domains, ingested through the apparatus, run through MANDATE-primary's six fine-tuned role pipeline on the eval host's Ollama:

1. **Volt Typhoon** (security operations; CISA AA23-144A and AA24-038A; 12 source files; CISO request for defense capability stand-up; 238.5 s wall clock).
2. **CrowdStrike outage** (security operations; CrowdStrike Channel File 291 RCA, NIST CSF DOCX/PPTX, SEC 8-K filings; 13 source files; CIO request explicitly demanding *three distinct strategic options* for endpoint security architecture; 212.0 s wall clock).
3. **Silicon Valley Bank collapse** (financial reporting; Federal Reserve SVB Review PDF, Senate Banking testimony, NIST DOCX deltas, NIST CSF PPTX; 11 source files; CFO request explicitly demanding *three distinct strategic options* for ERM and treasury overhaul; 195.8 s wall clock).

In all three runs every fine-tuned role fired (`llm_used=True` on Intake, Interpreter, Decomposition, Procedure, Binding, Validation; `any_llm_fallback=False`). RAG was wired into the Procedure role and queried the per-scenario index each time. Per-role temperatures matched the frozen `configs/llm_defaults.json` exactly. The artifacts are schema-valid mandate-as-code with the full field set populated.

## The behavior worth flagging

**On the CrowdStrike run the anchor's `minimum` correctly captured the multi-option requirement:**

> "Three distinct strategic options for endpoint security architecture with (a) operational and capex implications, (b) residual risk profile after one year, (c) vendor-relationship and contractual changes, and (d) implementation timeline."

That is the Interpreter role doing real work; the four-part requirement is lifted accurately from the CIO's paragraph.

**The Decomposition role still produced exactly one COA**, with a two-node task DAG (Manual Assessment → Results Documentation), risk score LOW, primary_factor `execution_uncertainty`. The same single-COA shape appeared on the Volt Typhoon run (CISO request, did not explicitly demand alternatives) and on the SVB run (CFO request, financial domain, did explicitly demand three options). Three scenarios, two domains, every Ollama run converges on the same COA-1 name and the same two-step DAG. The shape is cross-domain and consistent across the deterministic-vs-Ollama paths.

**The Validation role detected the CrowdStrike gap and recorded it in the recommendation rationale** verbatim:

> "However, its low confidence in execution and potential insufficiency in delivering three distinct strategic options necessitate close monitoring and possible adjustments."

So the validator is self-aware about the upstream Decomposition output not satisfying the anchor's minimum; it just cannot fix it from its pipeline position. On the SVB run, with a structurally similar three-options demand from the CFO, the validator's rationale dropped the gap acknowledgment and read instead: "COA-1 chosen for resource efficiency despite low confidence; aligns with minimal assessment requirements while acknowledging execution risks." So the gap-detection is real but not reliably triggered across scenarios.

**A second observation that surfaced on the SVB run.** The Interpreter role's anchor distillation was substantially weaker on SVB than on the two security-domain runs. CrowdStrike got "Three distinct strategic options for endpoint security architecture..." and "Strategy memo deliverable by next quarterly review..." as cleanly distilled minimum and target. Volt Typhoon got a similarly distilled target. SVB got the deterministic-prefix shape ("Minimally satisfy: Team, this is the CFO..." and "Fully achieve: Team, this is the CFO...") with the CFO's paragraph echoed rather than distilled, while all six roles still reported `llm_used=True`. The financial-domain fine-tunes appear to be producing anchor output that mimics the deterministic prefix pattern. Possibly the financial-domain training data was thin; possibly the prompt template behaves differently when the domain context is less familiar. Worth investigating alongside the COA-count question.

## Independent baseline comparison on the same input

A single-prompt Claude Sonnet 4.6 (Baseline 1, the protocol's `baseline_1`) was run on the identical task file and produced a much denser anchor on the same request:

| Anchor dimension | MANDATE-primary | Single-prompt Claude |
|---|---:|---:|
| `minimum` entries | 1 (paragraph) | 9 (each with dimension + threshold) |
| `target` entries | 1 (paragraph) | 5 (each with dimension + objective) |
| `constraints` entries | 0 | 6 (including `options_count == 3` and `nist_csf_alignment == maintained`) |
| `suspected_gaps` | n/a (mandate-as-code schema) | 8 (named: `next_quarterly_review_date`, `organization_exposure_magnitude`, `current_vendor_relationships`, …) |

Single-prompt Claude does not produce courses_of_action (no Decomposition role; baseline schema only carries the anchor). What it does is encode the "three options" requirement as a machine-readable constraint, where MANDATE-primary captured the same requirement in free-text paragraph form.

## What this suggests about the training corpus

The Decomposition fine-tune appears to have a strong single-COA prior independent of the anchor's minimum field. Two scenarios is not statistical evidence, but the consistency of the single-COA shape across very different requests, and the validator's ability to *detect* the mismatch without being able to *correct* it, is what someone iterating on the training data would want to know now rather than after the formal Phase 6 study runs.

Possible directions, in the team's hands not mine:

- Audit the training data balance for the Decomposition role. If the seed corpus is dominated by examples whose anchors carry one operational goal, the fine-tune will reflect that.
- Add training examples whose anchors carry explicit multi-option requirements (a CISO request asking for three strategy variants is a common operational shape) and check whether the Decomposition output fans to N COAs when the anchor requires N.
- Consider whether the Decomposition prompt template explicitly receives the anchor's minimum cardinality requirement. If the prompt summarizes the anchor before passing it forward, that summary may be lossy with respect to the "N distinct options" signal.
- Evaluate whether a downstream pass — the Validation role asking the Decomposition role to expand — is worth adding. The current pipeline is one-shot; the validator's gap detection is information that the Decomposition role does not receive.

## What does not need fixing

The apparatus side is verified: every role fires through Ollama, the RAG retriever is wired, the schema validates, the trace chains hash correctly, the per-role temperatures pin to the frozen config, the Procedure role consumes the scenario-specific RAG index. The apparatus audit's RAG fix (the original work that prompted AEGIS-eval) is operationally confirmed on two real scenarios. The substantive question is purely about model behavior, not pipeline integrity.

## What the formal study will measure

The five pre-registered primary outcomes operationalize this question directly. O1 anchor completeness will quantify the anchor-density gap against SME ground truth on 120 main-corpus tasks; the three-judge ensemble grades against ground truth, not against subjective preference. O2a/O2b will measure whether MANDATE-primary's gap detection beats the baselines' suspected_gaps field on the gap-triggering subset. O3 will count fabrications. O4 will measure schema validity (where MANDATE-primary's mandate-as-code schema is strictly more demanding than the baseline schema, which is a real advantage worth surfacing). O5 will measure adversarial resistance under prompt injection. Whether the Decomposition single-COA behavior shows up as a depressed anchor completeness in the formal data, or whether the COA structure plus the trace chain wins out elsewhere, is the substantive question Phase 6 will answer.

## Update from the 2026-06-04 binary-sourced re-run (HANDOFF_16b)

After this note was first drafted, the three scenarios were re-run end to end against fresh RAG indexes built from the original PDF/DOCX/PPTX/HTML binaries (extracted through the apparatus's `pypdf` / `python-docx` / `python-pptx` extractors instead of the prior `mcp web_fetch` text-mode rendering). Volt Typhoon and CrowdStrike came through with no fallbacks; SVB's Binding role fell back after 3 schema-validation failures on `decision_summary`. The full evidence is in `demo/MANDATE_DEMO_FINDINGS.md`. Four additions to this note follow.

**Decomposition single-COA prior: REAFFIRMED.** All three from-binaries runs produced `n_coas=1` with the same `COA-1: Minimal manual assessment approach` name and the same two-node DAG. Across the six runs total (three with web_fetch chunks, three with extractor-built chunks, two domains), Decomposition emitted one COA every time. The prior is robust to the upstream chunk-content variation that the formal study will not control.

**Interpreter anchor distillation: content-tripwire behavior in BOTH directions.** The CrowdStrike Interpreter, which I cited in this note as the cleanest example of the role doing real work, regressed on the from-binaries run to the deterministic-prefix paragraph echo on both `minimum` and `target`. Symmetrically, the SVB Interpreter, which I cited as showing the deterministic-prefix shape, distilled cleanly on the from-binaries run: `minimum` came out as "Three distinct strategic options with operational/capex implications, residual risk profiles modeled against SVB-class deposit outflow, contractual/personnel changes, and implementation timelines aligned with next SOX 404 cycle." The Interpreter is not domain-bound; it has two output modes and the chunk content (not the user-facing request paragraph) controls which mode it enters. Audit the Interpreter's training set for examples that mix clean-distillation and deterministic-prefix output on the same input domain.

**Validation gap-acknowledgment: also content-tripwire.** The CrowdStrike validator rationale lost the "potential insufficiency in delivering three distinct strategic options" gap-flag on the from-binaries run. Same scenario, same input request, same fine-tune; only the upstream chunks differed. The validator's gap-detection appears to be surface-pattern driven rather than constraint-count driven.

**Binding fine-tune: NOT a defect. The HANDOFF_16c diagnostic showed it is refusing to bind contradictory inputs and explaining why, in clean structured JSON.** All three of the SVB Binding model's parse-failure attempts emitted exactly one field: `error`. The three error messages, verbatim:

> *Attempt 1:* "The provided JSON data does not contain the necessary information to make a recommendation. The 'coas' array is empty, and there is only one COA available (COA-1), which may not meet the requirement for three distinct strategic options as mentioned in the mission intent."

> *Attempt 2:* "The provided JSON data does not contain the necessary information to make a recommendation. There is only one COA (COA-1) available, but no alternative options to consider for a fallback sequence. Additionally, there is no risk tolerance specified in the anchor to guide the recommendation."

> *Attempt 3:* "The provided content does not meet the requirements outlined in the mission intent. Specifically, there is only one COA (COA-1) presented, while the mission explicitly requests three distinct strategic options. Additionally, the provided COA lacks the necessary details regarding operational/capex implications, residual risk profiles, contractual/personnel changes, and implementation timelines as required."

This is exactly the Decomposition single-COA contradiction surfacing one step downstream. The Binding fine-tune correctly noticed that the sharply distilled SVB anchor ("Three distinct strategic options with operational/capex implications, residual risk profiles modeled against SVB-class deposit outflow...") was incompatible with the single COA Decomposition emitted, and emitted a structured refusal rather than fabricating a `decision_summary` over the mismatch. The prior SVB run did not see this refusal because the Interpreter on that path emitted a vague deterministic-prefix anchor that Binding could write *some* `decision_summary` over.

Two takeaways:

First, the Binding training data does not need additional financial-domain examples to fix this. The model's structured-refusal behavior is correct and well-explained. If anything, this is positive evidence that the Binding fine-tune has learned to be honest about input contradictions.

Second, the contradiction Binding refuses to bind is the same Decomposition single-COA prior this note already names. The strongest reading of the HANDOFF_16c finding is that the Decomposition-prior story is the principal upstream-team finding, and the Binding role's downstream structured refusal is supporting evidence that the contradiction is detectable post-Decomposition without additional training. The apparatus-side handling of these `{"error": "..."}` payloads (currently parsed as a `decision_summary`-missing failure and discarded after 3 retries) is a separate concern that AEGIS-eval can fix without upstream model changes; it is being captured as a candidate apparatus patch, not raised here.

The combined message is now: the Decomposition single-COA prior is the principal upstream-team finding. The Interpreter shows content-tripwire behavior in both directions across extraction paths (clean distillation and deterministic-prefix echo are both reachable from the same fine-tune; chunk shape selects between them). The Validation role's gap-acknowledgment is surface-pattern driven rather than constraint-count driven. The Binding role is correctly refusing to bind the Decomposition contradiction when the anchor is sharp enough to make it visible. Training-data audits should look at chunk-shape diversity, not just request-paragraph diversity. The two extraction paths produce request-paragraph-identical inputs but chunk-shape-different ones, and that is enough to swing three of the four roles' behavior in measurable ways.

## Update from the 2026-06-10 Phase 6 main matrix: fifth content-tripwire (Intake role)

During the HANDOFF_24 MANDATE-primary main matrix run (Phase 6, v1 frozen tag), two tasks (`TASK-MAIN-SEC-038` and `TASK-MAIN-SEC-040`, both stretch_case category, both derived from NIST SP 800-115) failed at the Intake role with `Invalid constraint syntax`. The pipeline halted at role 1 with `ok=False`. The shared trigger between both tasks is the natural-language phrase "Here's the constraint:" followed by complex English requirements.

The `mandate-intake` fine-tune appears to treat that phrase as a directive: it emits a constraint string into `MissionInput.constraints` containing the subsequent English sentence. `mandate.constraints.validate_constraint()` requires `field operator value` grammar with operators `==`, `!=`, `<`, `<=`, `>`, `>=`, `IN`, `CONTAINS`. The natural-language sentence fails the grammar check at line 134-140 of `AEGIS-eval/src/mandate/roles/intake.py`, and `Intake.execute()` returns `_fail`.

This is the **fifth content-tripwire failure mode** characterized across the six MANDATE roles. The combined picture is now:

- **Intake** content-tripwire: emits invalid-grammar constraints on natural-language "constraint" directives in user text.
- **Interpreter** content-tripwire: flips between clean distillation and deterministic-prefix paragraph echo on chunk-shape changes.
- **Decomposition** single-COA prior: emits exactly one COA regardless of anchor minimum cardinality.
- **Procedure**: only role currently uncharacterized for content-tripwire failures. Phase 6 data will measure.
- **Binding** structured refusal: emits `{"error": "..."}` when upstream inputs are contradictory.
- **Validation** gap-acknowledgment instability: surface-pattern driven rather than constraint-count driven.

Five of six fine-tuned roles show content-sensitive failure modes detectable in v1 ground-truth-grounded evaluation. The training-data audit recommendation strengthens: chunk-shape diversity AND surface-pattern diversity (including phrasings like "Here's the constraint:") need to be represented in the role training sets, not just request-paragraph diversity.

The Intake fix path is analogous to the Binding refusal patch: an apparatus-side patch that treats `validate_constraint()` failures as soft (log + drop the bad constraint, continue) rather than hard (fail the role). That's a v2 candidate, not a v1 modification. The v1 study runs with the failure mode observed at the Phase 6 measured rate (expected 20 of 1200 main runs, ~1.7%).

**Observed SVB Binding refusal rate at temperature 0.1.** HANDOFF_17c ran five additional SVB v2 full-pipeline attempts and observed zero refusals. Combined with HANDOFF_16b's 1 refusal in 1 attempt and HANDOFF_17b's 0 refusals in 1 attempt, the full-pipeline refusal rate is 1 of 7 (~14%). HANDOFF_16c's separate 3-of-3 refusal rate was measured on direct Ollama calls against a single captured prompt, which bypassed the upstream pipeline. The roughly five-fold difference between direct-call (100% refusal) and full-pipeline (~14% refusal) means the refusal is not a simple function of the user-facing request paragraph. The upstream pipeline (Decomposition output content, Procedure RAG chunk selection, Interpreter anchor distillation shape) varies stochastically per call, and the Binding role's noticing-of-contradiction is sensitive to that variation. The contradiction is always present in principle when Decomposition emits one COA against a three-options anchor, but Binding only emits the structured refusal when the upstream pipeline assembles the inputs in a particular shape. The upstream team may want to consider this when audit-sampling: a single SVB-class scenario run may not surface the refusal, but the refusal is reproducibly elicitable by holding the Binding-role prompt fixed.

**Apparatus-side patch status.** The candidate v2 patch (`feature/binding-refusal-as-gap-sideload` in this project) is verified at the unit-test level (1443 AEGIS-eval tests passing including 5 new refusal-specific cases) and at the deterministic-replay level (Lane 3 of HANDOFF_17c: feeds the HANDOFF_16c captured refusal payload through the patched apparatus end-to-end via a stub adapter, confirms the gap-report is emitted and the rationale carries the `[binding refused]` prefix). The patch does not over-fire on non-refusal scenarios (Lane 1: Volt and CrowdStrike v2 both clean). The patch is ready to migrate to upstream AEGIS (Autonomous Engineering Governance and Intelligence System) once the `~/Desktop/AEGIS` working tree is clean; the v1 tag remains untouched and the formal Phase 6 study still imports from the v1 baseline.

## Artifacts

- Volt Typhoon RunRecord (Ollama, web_fetch chunks): `demo/volt_typhoon/output_ollama/mandate_primary__TASK-DEMO-VOLT-001__r01.json`
- Volt Typhoon RunRecord (Ollama, from-binaries chunks): `demo/volt_typhoon/output_ollama_from_binaries/mandate_primary__TASK-DEMO-VOLT-001__r01.json`
- CrowdStrike RunRecord (Ollama, web_fetch chunks): `demo/crowdstrike_outage/output_ollama/mandate_primary__TASK-DEMO-CRWD-001__r01.json`
- CrowdStrike RunRecord (Ollama, from-binaries chunks): `demo/crowdstrike_outage/output_ollama_from_binaries/mandate_primary__TASK-DEMO-CRWD-001__r01.json`
- SVB RunRecord (Ollama, web_fetch chunks): `demo/svb_collapse/output_ollama/mandate_primary__TASK-DEMO-SVB-001__r01.json`
- SVB RunRecord (Ollama, from-binaries chunks, Binding fallback): `demo/svb_collapse/output_ollama_from_binaries/mandate_primary__TASK-DEMO-SVB-001__r01.json`
- Baseline 1 RunRecord on CrowdStrike: `demo/crowdstrike_outage/baseline_outputs/baseline_1/baseline_1__TASK-DEMO-CRWD-001__r01.json`
- Full findings memo: `demo/MANDATE_DEMO_FINDINGS.md`
- HANDOFF_16b Codex report: `handoffs/HANDOFF_16b_report_2026-06-04.md`
- HANDOFF_16c SVB Binding raw-response diagnostic: `demo/svb_collapse/diagnostics/svb_binding_raw_responses_2026-06-04.json`
- HANDOFF_16c Codex report: `handoffs/HANDOFF_16c_report_2026-06-04.md`
- HANDOFF_17b Codex report (patch applied via Path B side-load): `handoffs/HANDOFF_17b_report_2026-06-04.md`
- HANDOFF_17c Codex report (patch verified end to end): `handoffs/HANDOFF_17c_report_2026-06-04.md`
- v2 candidate patch branch: `feature/binding-refusal-as-gap-sideload` in this project

The eval-host commands that produced each are in `demo/<scenario>/eval_host_run.md` and `demo/RERUN_FROM_BINARIES.md`. Anyone with the eval host and the six `mandate-*` Ollama models can reproduce all six Ollama runs.
