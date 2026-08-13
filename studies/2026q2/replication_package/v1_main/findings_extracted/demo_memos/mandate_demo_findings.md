# MANDATE Real-Scenario Demonstration: Findings Memo

**Author:** Lead Analyst (Claude)
**Date:** 2026-06-03
**Status:** Demonstration artifacts; not pre-registered protocol evidence (PROTOCOL_LOCK §13 binds the formal study to the post-deposit protocol). This memo summarizes what MANDATE-primary actually did on two real, multi-source CISO/CIO specification requests, alongside one direct baseline comparison on the same input.

## What was demonstrated

Three independent real-world stakeholder requests across two domains (security operations and financial reporting), grounded in real public source documents, ingested through the apparatus and pushed through MANDATE-primary's six fine-tuned role pipeline on the eval host's Ollama:

| Scenario | Domain | Topic | Sources | Source formats |
|----------|--------|-------|---------|---------------|
| Volt Typhoon | security ops | CISO request for defense capability against PRC state-sponsored intrusion campaign | CISA AA24-038A and AA23-144A joint advisories, MITRE ATT&CK G1017 group page and technique pages, Microsoft Threat Intelligence original disclosure, DOJ KV Botnet press release, FBI search-warrant affidavit, Wikipedia, NIST SP 800-53/61, total 12 files | PDF, HTML |
| CrowdStrike outage | security ops | CIO request explicitly demanding three distinct strategic options for endpoint security architecture after the 19 July 2024 Falcon Sensor outage | CrowdStrike Channel File 291 RCA, Microsoft recovery guidance, CISA advisory, SEC 8-K filings (Delta, United), House Homeland Security testimony, NIST SP 800-218 deltas, NIST CSF v1.1 and Roadmap presentations, total 13 files | PDF, HTML, **DOCX, PPTX** |
| SVB collapse | financial reporting | CFO request explicitly demanding three distinct strategic options for ERM and treasury overhaul after the March 2023 Silicon Valley Bank failure | Federal Reserve SVB Review (April 2023), Senate Banking testimony from Greg Becker, Federal Reserve and FDIC press releases, SEC EDGAR 10-K filings, NIST SP 800-218 / 800-53 DOCX deltas, NIST CSF v1.1 and Roadmap presentations, Wikipedia coverage, total 11 files | PDF, HTML, **DOCX, PPTX** |

The CrowdStrike scenario exercised the new multi-format ingest path (`apparatus.corpus.sources.fetch.extract_docx_text` and `extract_pptx_text` against python-docx and python-pptx, paired with the existing PDF and HTML extractors). Every source URL is logged in each demo's `fetch_report.json` with its HTTP outcome; nothing was substituted for a failed URL.

## What MANDATE-primary did

Both runs PASSED the apparatus's primary integrity gates: every fine-tuned role fired (`llm_used=True`), no role silently fell back to the deterministic path (`any_llm_fallback=False`), and the Procedure role's RAG retriever was correctly wired into each scenario's per-demo Jaccard index (`rag_retriever_wired=True`). The per-role temperatures came through from the frozen `AEGIS-eval/configs/llm_defaults.json` unchanged (Intake 0.0, Interpreter 0.1, Decomposition 0.2, Procedure 0.1, Binding 0.1, Validation 0.0).

| Run | Wall clock | Total roles llm_used | rag_retriever_wired | Output type |
|-----|-----------:|---------------------:|---------------------:|-------------|
| Volt Typhoon, Ollama | 238.5 s | 6/6 | True | MANDATE_AS_CODE |
| CrowdStrike, Ollama | 212.0 s | 6/6 | True | MANDATE_AS_CODE |
| SVB collapse, Ollama | 195.8 s | 6/6 | True | MANDATE_AS_CODE |

The artifacts were schema-valid mandate-as-code with the full field set populated: `mandate_id`, `version`, `generated`, `anchor` (mission_intent + minimum + target + constraints), `courses_of_action`, `recommendation` (with rationale), `trace`, `registry_reference`, `metadata`.

## What the artifacts say substantively

**Anchor interpretation worked.** On the CrowdStrike request, the Interpreter role distilled the CIO's paragraph into a target ("Strategy memo deliverable by next quarterly review, consistent with NIST Cybersecurity Framework alignment and SOX 404 internal control obligations") and the minimum into a precise four-part requirement ("Three distinct strategic options for endpoint security architecture with (a) operational and capex implications, (b) residual risk profile after one year, (c) vendor-relationship and contractual changes, and (d) implementation timeline"). The Interpreter role did real interpretive work; it did not echo the request.

**Decomposition converged on a single COA on all three scenarios**, despite both the CrowdStrike CIO request and the SVB CFO request explicitly demanding "three distinct strategic options." All three runs produced one COA labeled `COA-1: Minimal manual assessment approach` with the same two-node task DAG (Manual Assessment → Results Documentation), the same LOW risk score with `execution_uncertainty` as the primary factor, and the same four off-nominal triggers. The single-COA shape is consistent across two domains (security operations and financial reporting), three scenarios, and the deterministic-versus-Ollama paths. This is cross-domain evidence of a structural tendency in the current Decomposition fine-tune rather than a scenario-dependent artifact.

The Procedure role's RAG context does flow into Decomposition's output. The SVB task DAG node description reads "Manual assessment of COSO ERM framework alignment, NIST SP 800-37 risk management, Federal Reserve supervisory expectations..." — the domain terms from the request and the retrieval are present in the COA's text. What does not vary is the COA count or the DAG shape.

**Validation noticed on CrowdStrike but not on SVB.** On the CrowdStrike run the Recommendation rationale, written by the Validation role, reads in part: "However, its low confidence in execution and potential insufficiency in delivering three distinct strategic options necessitate close monitoring and possible adjustments." The fine-tuned validator is self-aware about the gap between the anchor's minimum (three options) and the upstream Decomposition output (one COA). On the SVB run, with a structurally similar three-options demand, the validator rationale dropped the gap-acknowledgment: "COA-1 chosen for resource efficiency despite low confidence; aligns with minimal assessment requirements while acknowledging execution risks." So the validator's gap-detection is real but not reliably triggered across scenarios. It can detect the gap; it does not always notice; and it cannot fix it from its pipeline position even when it does.

**Anchor distillation also varied across the three runs.** On CrowdStrike the Interpreter role produced a cleanly distilled anchor minimum ("Three distinct strategic options for endpoint security architecture with (a) operational and capex implications, (b) residual risk profile after one year, (c) vendor-relationship and contractual changes, and (d) implementation timeline") and a distilled target ("Strategy memo deliverable by next quarterly review, consistent with NIST Cybersecurity Framework alignment and SOX 404 internal control obligations"). On Volt Typhoon the distillation was similar in quality ("Actionable specification that hardens the environment against specific MITRE ATT&CK techniques..."). On SVB the anchor came out in the deterministic-prefix shape ("Minimally satisfy: Team, this is the CFO..." and "Fully achieve: Team, this is the CFO..."), with the CFO's paragraph echoed rather than distilled, while all six roles still reported `llm_used=True` and `llm_fallback=False`. The financial-domain fine-tune produced anchor output that is less distillative than the security-domain runs on substantively comparable request shapes.

## Direct baseline comparison on the CrowdStrike request

Baseline 1 (single-prompt Claude Sonnet 4.6, no RAG, no role decomposition) was run on the identical task file and produced a baseline-specification output that schema-validated. Its anchor is markedly denser than MANDATE-primary's on the same request:

| Anchor dimension | MANDATE-primary | Baseline 1 (single-prompt Claude) |
|---|---|---|
| `minimum` entries | 1 (paragraph) | **9** (structured, each with dimension + threshold) |
| `target` entries | 1 (paragraph) | **5** (each with dimension + objective) |
| `constraints` entries | 0 | **6** (including literal `options_count == 3` and `nist_csf_alignment == maintained`) |
| `suspected_gaps` | n/a in mandate-as-code schema | **8** (naming concrete missing fields: next_quarterly_review_date, organization_exposure_magnitude, current_vendor_relationships, …) |
| Cost (USD) | ~0 (local Ollama) | $0.033 (API) |
| Wall clock | 212.0 s | 38.2 s |
| Output structure | mandate-as-code with COAs | baseline specification schema (no COAs) |

Baseline 1's mission_intent reads: "Develop a board-ready strategy memo presenting three distinct endpoint security architecture options in response to the CrowdStrike Falcon sensor outage of 19 July 2024, each evaluated across operational, financial, risk, contractual, and timeline dimensions, while maintaining NIST CSF alignment and SOX 404 controls" — a denser distillation of the same paragraph. Baseline 1 does not produce COAs (it has no Decomposition role), so the "three distinct strategic options" question cannot be answered on the B1 side from this output structure; what B1 does is encode "three" as a machine-readable constraint (`options_count == 3`) on the anchor, where MANDATE-primary captured the same requirement in a free-text paragraph.

## Findings, stated plainly

1. **MANDATE-primary's apparatus is verified end to end on three real, source-grounded scenarios across two domains.** Every fine-tuned role fires without silent fallback, RAG retrieval is wired into the Procedure role, the schema-compliant mandate-as-code artifact emits cleanly, and the trace chain is intact.

2. **The Decomposition role currently produces one COA per request, cross-domain.** Three scenarios, two domains (security operations on Volt Typhoon and CrowdStrike, financial reporting on SVB), every Ollama run produces a single COA with the same name and the same two-node DAG, even when the anchor's minimum explicitly demands three. This is a structural tendency in the fine-tune, not a scenario-dependent artifact, and not an apparatus defect.

3. **The Validation role's gap-detection is real but not reliably triggered.** It flagged the COA-count insufficiency on the CrowdStrike run and dropped the acknowledgment on the SVB run, on substantively similar three-options requests. When it does flag, it cannot fix it from its pipeline position.

4. **Anchor-distillation quality varies across domains.** The financial-domain SVB run produced anchor output in the deterministic-prefix shape, while the two security-domain runs produced cleanly distilled anchors on comparable request structures. All three runs had `llm_used=True` on every role, so this is fine-tune behavior, not silent fallback.

5. **A single-prompt Claude baseline extracts a substantially denser, more structured anchor on the same request.** On the CrowdStrike CIO request, Baseline 1 produced 9 minimum fields with explicit thresholds versus MANDATE-primary's 1 free-text paragraph; 6 machine-readable constraints (one of which literally encodes the requested option count) versus 0; 8 explicitly-named suspected gaps versus none. Cost differential is $0.03 per call versus zero, but the structural detail differential is large. Baseline 1 does not produce COAs (no Decomposition role; baseline schema only carries the anchor), so the multi-COA question cannot be answered on the B1 side.

4. **The substantive question the formal Phase 6 study will answer is whether MANDATE-primary's distinctive contribution (the COA structure, the cryptographic trace, the gap-report path) outweighs the apparent anchor-density gap on the comparable dimensions.** That is what the five pre-registered primary outcomes (O1 anchor completeness, O2a gap detection recall, O3 fabrication rate, O4 schema validity, O5 adversarial resistance) operationalize, and what the three-judge ensemble grades against SME ground truth.

## Binary-sourced re-run (HANDOFF_16b, 2026-06-04)

The three scenarios were re-run end to end against fresh Jaccard indexes built from the original PDF, DOCX, PPTX, and HTML binaries on disk (not the prior web_fetch text-mode extracts). The apparatus's production extractors (`apparatus.corpus.sources.fetch.extract_pdf_text` / `extract_docx_text` / `extract_pptx_text` / `extract_html_text`) produced the .txt extracts at `demo/<scenario>/sources/from_binaries/`; the AEGIS (Autonomous Engineering Governance and Intelligence System) Jaccard indexer built the new RAG indexes at `demo/<scenario>/rag/<scenario>__from_binaries.jsonl` with the same `chunk_size=1200, chunk_overlap=200` as the main study. Per-file SHA-256 chain-of-custody is in `demo/<scenario>/sources/FROM_BINARIES_REPORT.json`. The Ollama re-runs used the same six `mandate-*` role models, the same frozen `llm_role_temperatures`, and the same task files; only the chunks fed to the Procedure-role retriever differed.

| Scenario | Roles all LLM | any_llm_fallback | Wall clock | Versus prior |
|---|:-:|:-:|---:|---|
| Volt Typhoon (from-binaries)       | 6/6 | False | 166.7 s | 30% faster than prior 238.5 s |
| CrowdStrike outage (from-binaries) | 6/6 | False | 172.0 s | 19% faster than prior 212.0 s |
| SVB collapse (from-binaries)       | 6/6 | **True (Binding)** | 215.1 s | 10% slower than prior 195.8 s |

The SVB Binding role fell back after 3 schema-validation failures on `decision_summary`; the other five SVB roles ran clean. The Volt and CrowdStrike runs had no fallbacks. RunRecords are at `demo/<scenario>/output_ollama_from_binaries/mandate_primary__TASK-DEMO-<X>-001__r01.json`. HANDOFF_16b's Codex report is `handoffs/HANDOFF_16b_report_2026-06-04.md`.

### What the binary-sourced run shows, role by role

**Decomposition: single-COA cross-domain finding REAFFIRMED under binary-sourced inputs.** All three from-binaries runs produced exactly one COA, named `COA-1: Minimal manual assessment approach`, with the same two-node DAG (Manual Assessment → Results Documentation), the same LOW risk score, the same `execution_uncertainty` primary factor. Five out of six runs across two paths (three with web_fetch chunks, three with python-docx/pptx/pypdf chunks, two domains) produced this exact shape; the SVB from-binaries run also produced n_coas=1 but its DAG description regressed to the generic "Manual assessment of target scope" (its prior run had specific COSO ERM / NIST SP 800-37 / Federal Reserve text). The single-COA shape is robust to the upstream extraction-path variation that the formal study will not control.

**Interpreter: anchor distillation flipped between the two extraction paths in opposite directions.**

On CrowdStrike, the prior run distilled the CIO's paragraph into a structured `minimum` ("Three distinct strategic options for endpoint security architecture with (a) operational and capex implications, (b) residual risk profile after one year, (c) vendor-relationship and contractual changes, and (d) implementation timeline") and a structured `target` ("Strategy memo deliverable by next quarterly review, consistent with NIST Cybersecurity Framework alignment and SOX 404 internal control obligations"). The from-binaries CrowdStrike run regressed to the deterministic-prefix paragraph echo ("Minimally satisfy: Team, this is the CIO..." and "Fully achieve: Team, this is the CIO..."). The cleanest example I had previously cited in the upstream-team note for what the Interpreter is capable of, got worse on a chunk-shape change.

On SVB, the inverse happened. The prior run produced the deterministic-prefix paragraph echo ("Minimally satisfy: Team, this is the CFO..."). The from-binaries SVB run produced the structured distillation we had been wanting on the financial side: `minimum`: "Three distinct strategic options with operational/capex implications, residual risk profiles modeled against SVB-class deposit outflow, contractual/personnel changes, and implementation timelines aligned with next SOX 404 cycle"; `target`: "Strategic options that fully address Federal Reserve supervisory expectations, close identified control gaps through justified new hires if necessary, and demonstrate robust risk mitigation under stress scenarios". This is exactly the shape the upstream-team note flagged as missing on the financial-domain fine-tune. It is here when the chunks come from python-docx and pypdf instead of web_fetch text.

On Volt Typhoon, the `minimum` was identical across the two paths (deterministic-prefix on both), but the `target` regressed: prior had "Actionable specification that hardens the environment against specific MITRE ATT&CK techniques, integrates detection into the SOC workflow, validates and tightens network segmentation between IT and OT, and produces metrics for the audit committee"; from-binaries has "Fully achieve: Team, this is the CISO speaking..." paragraph echo.

The pattern is that the Interpreter has two output modes (structured distillation and deterministic-prefix paragraph echo), and which mode it enters is a function of upstream chunk content, not the input request paragraph (which is identical across the two runs). This is consistent with the Interpreter fine-tune having learned a content-pattern tripwire that is not stable across reasonable extraction-path variations.

**Validation: CrowdStrike gap-acknowledgment vanished on the from-binaries run.** The prior CrowdStrike validator rationale explicitly flagged the gap between the anchor's three-options minimum and the single-COA Decomposition output ("its low confidence in execution and potential insufficiency in delivering three distinct strategic options necessitate close monitoring and possible adjustments"). The from-binaries CrowdStrike validator rationale dropped that specificity: "its minimal approach may not fully address the board's strategic requirements for endpoint security architecture". The validator's gap-detection is not just unreliable across scenarios (as previously noted); it is also unstable across extraction paths for the same scenario.

**Binding: not a fine-tune defect; a structured refusal the apparatus misreads as a parse failure.** The HANDOFF_16c diagnostic (`demo/svb_collapse/diagnostics/svb_binding_raw_responses_2026-06-04.json`) shows what the SVB `mandate-binding` role actually emitted on each of the three failed parse attempts. All three responses are clean valid JSON. All three contain a single field, `error`, with the model explaining in natural language why it is declining to produce a `decision_summary`. The three error messages, verbatim:

> *Attempt 1:* "The provided JSON data does not contain the necessary information to make a recommendation. The 'coas' array is empty, and there is only one COA available (COA-1), which may not meet the requirement for three distinct strategic options as mentioned in the mission intent."

> *Attempt 2:* "The provided JSON data does not contain the necessary information to make a recommendation. There is only one COA (COA-1) available, but no alternative options to consider for a fallback sequence. Additionally, there is no risk tolerance specified in the anchor to guide the recommendation."

> *Attempt 3:* "The provided content does not meet the requirements outlined in the mission intent. Specifically, there is only one COA (COA-1) presented, while the mission explicitly requests three distinct strategic options. Additionally, the provided COA lacks the necessary details regarding operational/capex implications, residual risk profiles, contractual/personnel changes, and implementation timelines as required."

This is exactly the contradiction the Decomposition single-COA prior creates. The Binding fine-tune is doing what a careful binder should do: when the upstream chain has internally contradictory inputs (anchor demands three distinct options; Decomposition emitted one), it refuses to bind and explains why, rather than fabricating a `decision_summary` over the mismatch. The prior SVB run succeeded only because the Interpreter on that path emitted the vague deterministic-prefix anchor ("Minimally satisfy: Team, this is the CFO..."), which Binding could write a coherent `decision_summary` over. On the from-binaries run, the Interpreter distilled the anchor sharply ("Three distinct strategic options with operational/capex implications, residual risk profiles modeled against SVB-class deposit outflow..."), and Binding correctly noticed it could not bind one COA to a three-option requirement.

Two findings follow.

First, this is not a Binding fine-tune defect. Volt and CrowdStrike Binding ran clean across both extraction paths because the upstream chain on those scenarios was internally consistent (their security-domain anchors did not sharpen on the extraction-path change in the same way the SVB financial-domain anchor did). The Binding fine-tune has learned a useful structured-refusal behavior; the upstream-team note should reflect that, not flag it as fragility.

Second, this is an apparatus-level finding. The apparatus's Binding role parser currently retries on `'decision_summary' is a required property`, and after 3 retries it falls back to the deterministic Binding path and drops the model's `error` payload. The model's structured refusal would be much more useful surfaced as a gap report (the `output.gap_reports` array is empty on the failing SVB run; the Binding model's explanation belongs there). Specifically: when `mandate-binding` emits `{"error": "..."}` with no other fields, the apparatus should route the `error` text into `gap_reports` and emit a deterministic-binding stub that carries a `decision_summary` referencing the gap, rather than discarding the model's reasoning and retrying. That is a targeted apparatus patch worth proposing on the AEGIS-eval side, independent of the upstream training-data work.

### What this means for the upstream MANDATE team's training data

The previous version of `demo/UPSTREAM_MANDATE_NOTE_decomposition_bias.md` framed the Decomposition single-COA prior as the principal finding. That finding stands. The binary-sourced re-run adds three more:

1. The Interpreter's anchor-distillation behavior is content-sensitive at the level of chunk shape, not at the level of the user-facing request paragraph. The financial-domain fine-tune is capable of clean structured distillation when the chunks support it (from-binaries SVB), and the security-domain fine-tune is capable of dropping into deterministic-prefix echo when the chunks shift (from-binaries CrowdStrike and Volt target). The hypothesis the upstream team should test is whether the Interpreter's training set has examples of both clean distillation and deterministic-prefix echo close enough in the loss surface that small chunk-content perturbations flip the output mode.

2. The Validation role's gap-acknowledgment is itself content-sensitive: the same anchor/COA-count mismatch on the same scenario triggered the rationale on the web_fetch path and not on the from-binaries path. Validation's gap-detection appears to require specific surface patterns in the upstream content rather than reasoning about the actual constraint count from the anchor's `minimum`.

3. The Binding fine-tune is not defective in the financial domain. The HANDOFF_16c diagnostic showed it is emitting clean JSON with a single `error` field explaining, in natural language, that it cannot bind one COA to a three-option requirement. This is exactly the Decomposition single-COA contradiction surfacing one step downstream. The Binding fine-tune's structured-refusal behavior is well-trained; the apparatus should preserve those error payloads as gap reports rather than discarding them as parse failures. The upstream team can fold this into the gap-detection narrative without changing the Binding training data.

## Apparatus patch verified (HANDOFF_17b + 17c, candidate v2)

A side-loaded patch on `feature/binding-refusal-as-gap-sideload` extends the apparatus to detect Binding's structured refusals and route them to `output.gap_reports` instead of treating them as `'decision_summary' is a required property` parse failures. The patch touches four files inside `AEGIS-eval/src/` (response_parser, llm_support, roles/binding, pipeline) and adds a five-case unit test file. The AEGIS-eval test suite passes (1443 passed, 27 skipped). Project main is unchanged; the formal Phase 6 study still imports from the v1 baseline. The marker at `AEGIS-eval/_AEGIS_EVAL_README.txt` documents the deviation and the rollback path; once upstream `~/Desktop/AEGIS` is clean and writeable, the side-load is intended to migrate to a proper feature branch in upstream AEGIS with a candidate tag `mandate-eval-primary-2026q2-v2-candidate-binding-refusal`.

HANDOFF_17c verified the patch in three lanes. Lane 1 (negative test): Volt and CrowdStrike v2 runs both reported `any_llm_fallback=False` and zero Binding-attributed gap reports, confirming the refusal predicate is narrow enough not to over-fire on non-refusal scenarios. Lane 3 (deterministic): the HANDOFF_16c captured refusal payload was fed through the patched apparatus with a stub adapter, and the patch fired correctly — short-circuit on the first call (no retries), `last_parsed_payload` preserved on the exception, gap report emitted with the verbatim model text, rationale prefixed `[binding refused]`. The patch works as designed under refusal.

Lane 2 (probabilistic) produced a finding worth recording on its own. Five SVB v2 full-pipeline re-runs at temperature 0.1 produced zero refusals. Combined with HANDOFF_16b's 1 refusal in 1 SVB from-binaries run and HANDOFF_17b's 0 refusals in 1 run, the observed full-pipeline refusal rate is 1-of-7 (roughly 14%). HANDOFF_16c's earlier 3-of-3 refusal rate was measured on direct Ollama calls against a frozen captured prompt — that bypassed the upstream pipeline. The roughly five-fold difference between direct-call (100%) and full-pipeline (~14%) refusal rates means the refusal-vs-bind flip is sensitive to upstream pipeline content, not just to the user-facing request paragraph. The Decomposition role's output content, the Procedure role's RAG chunk selection, and the Interpreter's anchor distillation all vary stochastically per pipeline call, and the Binding role's noticing-of-contradiction is sensitive to that variation. The contradiction is always there in principle (anchor demands three options, Decomposition emitted one), but Binding only flags it when the upstream pipeline assembles the inputs in a particular shape.

This adds nuance to the cross-role content-sensitivity story. The Validation role's gap-acknowledgment is content-tripwire driven (HANDOFF_16b showed it dropped the CrowdStrike gap-flag on a chunk-shape change with the same input). The Binding role's refusal behavior is content-tripwire driven AND probabilistic at temperature 0.1. The Decomposition single-COA prior, by contrast, was stable across all 13 runs we now have on record (3 web_fetch + 3 from_binaries + 1 v2 + 5 v2 reruns + 1 v2 sanity).

The combined picture for the upstream team is: the Decomposition single-COA prior remains the principal training-data finding. The Interpreter shows content-tripwire behavior in both directions across extraction paths (clean distillation and deterministic-prefix echo are both reachable from the same fine-tune; chunk shape selects between them). The Validation role's gap-acknowledgment is surface-pattern driven rather than constraint-count driven. The Binding role is doing the right thing under contradictory inputs; the apparatus needs to listen to it. Training-data audits should look at chunk-shape diversity, not just at request-paragraph diversity, since the apparatus's two extraction paths produce request-paragraph-identical inputs but chunk-shape-different ones, and that is enough to swing three of the four roles' behavior.

## Artifacts on disk

- Volt Typhoon: `demo/volt_typhoon/{sources,sources/originals,sources/from_binaries,rag,tasks,output,output_ollama,output_ollama_from_binaries,coas.md,eval_host_run.md}`
- CrowdStrike: `demo/crowdstrike_outage/{sources,sources/originals,sources/from_binaries,rag,tasks,output,output_ollama,output_ollama_from_binaries,baseline_outputs/baseline_1,coas.md,eval_host_run.md}`
- SVB: `demo/svb_collapse/{sources,sources/originals,sources/from_binaries,rag,tasks,output,output_ollama,output_ollama_from_binaries,coas.md,eval_host_run.md}`
- Original source binary inventory: `demo/SOURCE_BINARIES_INVENTORY.md`
- Re-run instructions: `demo/RERUN_FROM_BINARIES.md`
- This memo: `demo/MANDATE_DEMO_FINDINGS.md`
- Upstream-team note: `demo/UPSTREAM_MANDATE_NOTE_decomposition_bias.md`

All artifacts are real; every URL fetch is logged with its actual outcome; nothing was substituted or fabricated. Every binary on disk has a recorded SHA-256.
