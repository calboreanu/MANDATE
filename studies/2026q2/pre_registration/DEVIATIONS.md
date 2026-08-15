# Pre-registration deviations

PROTOCOL_LOCK §13 states the study's deviation policy. This file preserves
long-form narratives for four major deviations; it is not an exhaustive log of
every difference between the locked plan and execution. The separate
`DEVIATION_LEDGER.md` enumerates all 13 keyed entries (D-01–D-13), while other
plan-to-execution differences were disclosed without D-numbers. None of these
records retroactively changes the locked protocol document.

---

## 2026-06-04 — SME realism audit skipped; ground truth = Claude Opus 4.6 anchor scaffolds direct

**PI decision.** Cal directed the evaluation to skip the SME realism audit step (FORMS Section 4 / `apparatus.corpus.cli realism-form` + `realism-aggregate` flow) and to use the PROMPTS Section 2 anchor scaffolds produced by HANDOFF_06 (pilot, 6 tasks) and HANDOFF_09 (main, 120 tasks) and the upcoming hold-out scaffolds as the direct ground truth, with no human-rater review.

**Why.** The PI wants to focus on proving the apparatus runs end-to-end and produces gradable artifacts across all six baselines plus MANDATE-primary. The SME coordination loop is multi-day and is outside the scope of this exercise. The realism question becomes an acknowledged open caveat rather than a pre-grading precondition.

**What changes for the formal study.**

- `corpus_freeze_v1` tag is cut once the three selection files (`03_corpus/main/main_selection.json`, `03_corpus/holdout/holdout_selection.json`, `03_corpus/pilot/pilot_selection.json`) are in place and the candidates have been materialized into `04_ground_truth/*_tasks.jsonl`. The realism-audit gate is lifted from this tag's precondition.
- `gt_freeze_v1` tag is cut after the anchor scaffolds for all three pools (pilot, main, hold-out) land at `04_ground_truth/{pilot_scaffolds,main_scaffolds,holdout_scaffolds}/anchor_scaffolds.jsonl`. The SME accept/edit/reject step is skipped. The scaffold output is the ground truth verbatim.
- `baseline_freeze_v1` tag is cut once B1 through B6 have their calibration RunRecords on disk (already complete except for any future re-runs); SME involvement was never part of this tag.

**What this means for the comparative analysis.**

- The three-judge grading ensemble (Phase 8) still runs as protocol-defined. Each judge is an LLM (per the Decisions memo Section 4), not an SME, in this exercise.
- The five primary outcomes (O1 anchor completeness, O2a/O2b gap detection, O3 fabrication, O4 schema validity, O5 adversarial resistance) all still grade against the ground truth defined above. O1 in particular is now measuring system-vs-Claude-Opus-4.6-scaffold rather than system-vs-SME-accepted-anchor; this is a real methodological caveat that needs to be cited in any write-up.
- The Krippendorff α inter-rater reliability is undefined for this run, because there are no human raters. Any analysis that requires α (e.g. reliability of the realism audit) cannot run; analyses that require only the grading ensemble's agreement (e.g. ensemble-vs-ground-truth) still run.
- Any external reviewer who asks "is the corpus realistic?" cannot be answered with "the SMEs accepted it at α > 0.6". The answer is "the corpus is the source-conditioned output of Claude Opus 4.6 against curated public-source chunks; realism was not adjudicated by SMEs in this exercise."

**Implications for the deposit.**

If this state becomes the final deposited study, the deposit must explicitly cite this deviation. A future re-run with SME involvement would be a separate, layered evaluation, not a replacement of this one.

**Reversibility.** This deviation is forward-compatible with re-introducing SMEs later. The `realism-form` and `realism-aggregate` CLI subcommands are unchanged. If SMEs are added in a follow-up, the existing scaffolds become candidate anchors for SME review, and `gt_freeze_v2` can be cut on top of the SME-reviewed pool. The Phase 6 outputs already on disk would need to be re-graded against the new ground truth, but the run-time data does not need to be regenerated.

---

## 2026-06-10 — Phase 6 watchdog refinement: ok=False records are data, not contamination

**Context.** HANDOFF_23 and HANDOFF_24 deployed a fast-fallback watchdog with the rule: halt if any record has `wall_clock_ms < 60_000` OR all six roles have `llm_used=False`. The rule was designed to catch Ollama-crash-induced contamination (when Ollama dies mid-run, every role silently falls back to deterministic mode, producing records that look superficially valid but carry no LLM signal).

The rule was too coarse. It conflates two distinct fast-wall-clock patterns:

- **Pattern A (Ollama crash contamination):** wall_clock under ~5s, all six roles `llm_used=False`. Genuine measurement contamination.
- **Pattern B (legitimate fast failure):** wall_clock 30-50s, Intake or another single role ran the LLM and then `_fail`'d on validation (Intake's `Invalid constraint syntax`, Decomposition's no-COAs branch, etc). Genuine Phase 6 measurement data.

The HANDOFF_24 watchdog quarantined both. Pattern B records should have been recorded as Phase 6 data; they characterize MANDATE-primary failure modes under content-tripwire conditions.

**Correction.** HANDOFF_25 refines the watchdog rule to halt only on the Pattern A signature: `wall_clock_ms < 60_000` AND every role has `llm_used=False`. Pattern B records (one or more roles ran the LLM before a downstream failure) pass through as legitimate ok=False data. The 2 quarantined SEC-038 records from HANDOFF_24 (Intake content-tripwire failures, see below) are restored from `/tmp/handoff24_postreboot_quarantine_20260610_1172/` to the canonical output directory.

**Implications.** Phase 6 O4 (schema validity) and O3 (fabrication) measurement integrity is improved. The Intake-failure rate on the content-tripwire tasks becomes part of the formal dataset rather than being suppressed.

---

## 2026-06-10 — Substantive finding: Intake role content-tripwire on natural-language constraint mentions

**Discovery.** During HANDOFF_24 main matrix execution, `TASK-MAIN-SEC-038` (stretch_case, NIST SP 800-115 derivation) and `TASK-MAIN-SEC-040` both produced `mandate-intake` outputs containing a constraint string that failed `validate_constraint()` ("Invalid constraint syntax"). The pipeline halted at role 1.

Both tasks contain the natural-language phrase "Here's the constraint:" followed by complex requirements in plain English. The fine-tuned Intake role apparently treats this phrase as a directive to emit a constraint into `MissionInput.constraints`, generating the following English sentence as the constraint value. `mandate.constraints.validate_constraint()` requires `field operator value` grammar (operators `==`, `!=`, `<`, `<=`, `>`, `>=`, `IN`, `CONTAINS`), so the English text is rejected at the post-LLM validation step in `Intake.execute()` (line 134-140 of `AEGIS-eval/src/mandate/roles/intake.py`).

**Significance.** This is the fifth content-tripwire failure mode characterized across the six MANDATE roles. With Decomposition (single-COA prior), Interpreter (mode flip), Validation (gap-acknowledgment instability), Binding (structured refusal), and now Intake (constraint-syntax tripwire) all showing content-sensitive behavior, only Procedure remains uncharacterized. The cross-role pattern strengthens the upstream-team note's principal message: chunk-shape and surface-pattern diversity in the training data, not just request-paragraph diversity.

**Phase 6 data implication.** The two tasks' 20 runs total (10 each) are expected to produce 20 ok=False Intake-failure records. These are legitimate Phase 6 data measuring the Intake fine-tune's failure rate on this content pattern. With the refined watchdog they land in the canonical dataset alongside the successful runs.

**Mitigation options for v2 candidate.** Three potential apparatus-side patches, each with different protocol-violation implications, are noted but NOT applied to the v1 study:

1. Make `Intake.execute()` log invalid constraints as a metric instead of failing the role. (Would change observed Intake failure rate.)
2. Patch the Intake LLM prompt to be explicit that "the constraint" in user text is not a directive to emit one. (Requires changing the locked Section 1 prompt — protocol violation under v1.)
3. Replace SEC-038 and SEC-040 with alternative stretch_case candidates from the unused 142-candidate residue of the original 262-candidate main corpus pool. (Would require a `corpus_freeze_v1_patched` tag and a documented deviation.)

The v1 study runs with the failure mode observed. Any of these mitigations becomes a v2 candidate evaluation question.

---

## 2026-06-13 — HANDOFF_11b-ii MP hold-out contamination: 300 records invalid, regenerated under HANDOFF_26

**What happened.** HANDOFF_11b-ii produced 9000 RunRecords, was reported PROCEED, and `outputs_freeze_v1` was cut. Post-hoc analysis surfaced that all 300 MANDATE-primary hold-out records were contaminated: every role on every record reported `llm_fallback=True` with reason `Ollama backend failed after 3 attempt(s): Ollama connection error: [Errno 61] Connection refused`. Wall clock per "run" was ~2 seconds instead of the expected ~370 seconds. The 300 records measured the deterministic-fallback path, not MANDATE-primary v1.

Root cause is likely Ollama dying between Task 1 (baselines, ~50-80 hours of API-only work) and Task 2 (hold-out, requires Ollama for MP). Either idle timeout, RAM pressure during the long baseline run, or a clean process exit not detected by Codex. When MP hold-out attempted to call Ollama on `localhost:11434`, every request hit Connection refused, and the apparatus's `llm_fallback=True` was set silently per role.

**Why Codex did not halt.** HANDOFF_11b-ii's decision boundary read: *"You may NOT treat as a halt (Phase 6 data): any_llm_fallback=True on MANDATE-primary hold-out runs."* I wrote that rule expecting some legitimate Binding refusals on the out-of-domain hold-out (per the demo finding of probabilistic Binding refusal). But I did not include a check for the contamination signature — every role on every record carrying `llm_fallback=True`. The HANDOFF_25 refined watchdog rule (all roles `llm_fallback=True` = contamination) was applied only to the MP main matrix in 11b-i resume, not propagated to 11b-ii's hold-out leg.

**Detection signature, corrected.** The right contamination check for Ollama-backed systems (MANDATE-primary, ablation variants): `if rts and all(t.get('llm_fallback') for t in rts): contaminated`. The earlier check `all(not t.get('llm_used') for t in rts)` missed this because the apparatus sets `llm_used=True` before attempting the call, then `llm_fallback=True` after the call fails. Both flags are True on a contaminated record.

**Correction.** HANDOFF_26 quarantines the 300 contaminated MP hold-out records, re-runs MP hold-out fresh against the patched apparatus and a restarted Ollama, re-anonymizes the full output tree (the previous anonymization included the 300 contaminated records and the mapping no longer corresponds), and cuts `outputs_freeze_v1_1` as the corrected freeze. The original `outputs_freeze_v1` tag is left in place as historical record. The 1200 MP main matrix records and the 7500 API-bound baseline records are unaffected and are not regenerated.

**Cost.** API: $0 (re-run is Ollama only). Ollama wall clock: ~31 hours for 300 fresh MP hold-out runs. No additional baseline spend.

---
