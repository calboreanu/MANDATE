# Codex Handoff 05: Five AEGIS-variant Ablations (upstream MANDATE work)

**For:** the upstream MANDATE team (Lattice / AEGIS), not Codex on the eval host
**From:** Lead Analyst, MANDATE 2026Q2 empirical evaluation
**Date:** 2026-06-01
**Estimated effort:** 2 to 3 engineer-weeks across the five variants.
**Blocks on:** nothing. Can start in parallel with eval-host work.

---

## Mission

Build the five MANDATE ablation variants the PROTOCOL_LOCK evaluation calls for but the apparatus cannot express as `PipelineConfig` switches: A1 (no role separation), A2 (no tolerance bands), A4 (no Validation role), A6 (no search-trace), A7 (no NIST AI RMF metadata). Two of the seven ablations, A3 (no gap-report output) and A5 (no Success Registry), are config switches and run today from the frozen MANDATE source; this handoff covers the five that need MANDATE source changes.

**Definition of done.** Each of the five variants is a separate AEGIS git tag layered on top of the primary tag, each runs end-to-end from a clean checkout, and each is hashed into `provenance_evidence.md` alongside MANDATE-primary. The apparatus loads the variants by ref; nothing in the apparatus changes after the refs are set.

**Why this matters.** PROTOCOL_LOCK §5 names A1, A2, A3 as primary ablations (main paper) and A4-A7 as secondary. Without the five variants the evaluation runs MANDATE-primary against the strongest baseline (H1-H5, the headline) and reports an ablation table with two of seven cells filled. With the variants the ablation analysis is complete and the paper carries the protocol's intended scope.

## Audience and posture

This is a handoff to the MANDATE team, who own the source code under evaluation. The Lead Analyst does not modify AEGIS (SETUP §6). The variants are MANDATE work, tagged for the study, frozen, and pinned. After tagging, the Lead Analyst sets each `aegis_ref` in `apparatus/ablations/manifest.py` and the harness picks them up.

## Decision boundary

The MANDATE team decides:

- Per-variant implementation details, as long as the variant satisfies the per-variant acceptance criteria below.
- Tag exact name within the naming convention (one-line suggestion below).
- Whether a variant is implemented on a branch off `mandate-eval-primary-2026q2-v1` or as a standalone branch off `main`. The pinned ref is what matters; the branch shape is a workflow choice.
- For A2 specifically: the canonical mapping that collapses the three-band anchor (minimum, target, constraints) to a single threshold per field, because that mapping is also what the SME ground truth has to use for the A2 grading.

The MANDATE team should escalate to the PI (Cal):

- Any change that affects MANDATE-primary's behavior outside the ablation. The variants must isolate one component change each.
- A2's collapsed-band mapping when a clean one is not obvious. The Lead Analyst then helps the PI write a deviation note describing the rule.
- Anything that would make the variant indistinguishable from MANDATE-primary on the calibration tasks. An ablation that does not change behavior is not an ablation.

The MANDATE team may not:

- Modify the MANDATE-primary tag `mandate-eval-primary-2026q2-v1` (commit `4f8af83`) for any reason. Variants are layered above, never replace.
- Skip producing the variant tag because "the ablation is logically equivalent to a config." The apparatus has already drawn the line between config switches and AEGIS variants; A3 and A5 are the only config switches.
- Modify the mandate-as-code schema for any variant other than A2. The schema is part of the system contract being evaluated.

---

## Shared acceptance criteria (every variant)

Every variant must:

1. **Tag and freeze.** Tagged as `mandate-eval-ablation-<id>-2026q2-v1` (suggested), on a commit pinned the same way the primary is. The tag is annotated and signed if the project signs other tags.
2. **Read from `AEGIS-eval`-style extraction.** A clean `git archive <tag> | tar -x -C variant_src` produces a complete, self-contained source tree that the apparatus can import from. No assumed sibling directories, no editable installs.
3. **Same input contract.** The variant accepts the same `MissionInput` (or, via the apparatus, the same raw `request_text` through the thinnest adapter). No new required arguments.
4. **Same RunRecord shape.** The pipeline produces the same `role_results`, `metrics`, `trace_entries`, `artifact`, `gap_reports` structure the apparatus reads. The apparatus does not branch on ablation; only the recorded `system_id` and `code_ref` differ.
5. **Output type contract.** All variants except A2 produce a `MANDATE_AS_CODE` artifact validating against the locked `mandate-as-code.schema.json`. A2 produces a variant schema described below.
6. **Six calibration tasks run end-to-end** in Ollama mode from a clean variant checkout: 6 ok, 6 role timings (or fewer where the variant removes roles), no silent fallback on the model side.
7. **Variant behavior is real.** On the six calibration tasks the variant's anchor differs from MANDATE-primary's anchor in the dimension the ablation removes. A bit-identical variant is rejected.
8. **Documented.** A short `CHANGELOG-ablation-<id>.md` in the variant tree describes: what was removed, the exact files changed, why the change isolates the targeted component, and any caveat the analyst should know.

---

## Per-variant specification

### A1: no role separation

**What is removed.** The 1+6-role pipeline. A single LLM call ingests the request and produces the full mandate-as-code output. The 1 (Intake) plus 6 (Interpreter, Decomposition, Procedure, Binding, Validation) becomes one combined prompt.

**Expected change.** A new pipeline class or a configurable single-role mode in `src/mandate/pipeline.py` that, in this variant only, replaces the role list with a single combined role. The combined role's system prompt is the concatenation (or an equivalent merge) of the six per-role prompts in `configs/system-prompts/`, ordered to flow as MANDATE-primary's roles would. The Ollama model used is the base model the six roles share their family with (Qwen3-32B) on the same Ollama endpoint, or, if the team prefers, the largest of the six `mandate-*` models. The choice is recorded in the variant's CHANGELOG.

**Why this isolates the component.** Single-call removes the role decomposition while keeping the model family, the schema, and the fine-tuning substrate constant. If H1-H5 hold for A1 relative to MANDATE-primary, the decomposition is doing work the single call cannot reproduce.

**Acceptance check.** On a calibration task the variant produces only one entry in `role_results` (the combined call), the trace records one role, and the anchor differs from MANDATE-primary's.

### A2: no tolerance bands

**What is removed.** The minimum / target / constraints three-band anchor structure, collapsed to a single threshold per field.

**Expected change.** `src/mandate/models.py` (`MissionInput`, `AnchorSpec`) loses the band fields and carries a single `threshold` plus the `dimension` and `rationale`. The mandate-as-code schema gets a sibling `mandate-as-code-singleband.schema.json`. Intake and Interpreter prompts are revised so the fine-tunes do not emit band structure. The Validation role is updated to validate against the single-band schema.

**Collapsed-band mapping (PI-decided).** The Lead Analyst proposes this mapping and the PI approves: for fields that have a `minimum` and a `target`, the collapsed threshold is the `minimum` (the harder bar). For fields that have only a `target`, the collapsed threshold is the `target`. Constraints stay attached as constraints because they are not thresholds. Other rules may be defensible; pick one and document it.

**Why this isolates the component.** Tolerance bands are the only structural addition over a single-threshold specification. If H1-H5 hold for A2, the bands carry information beyond a single bar.

**Acceptance check.** On a calibration task the variant's anchor has no `target` field on dimensions that had one, and the threshold value matches the PI-approved mapping. The ground truth for A2 is the same SME-signed primary ground truth, mechanically collapsed by the same rule.

### A4: no Validation role

**What is removed.** The Validation role. The pipeline ends at Binding.

**Expected change.** `src/mandate/pipeline.py` is the only file: the role list construction drops `ValidationRole(self.config)`. The artifact assembly that the Validation role does internally moves into a thin post-pipeline step that produces the same artifact structure without the Validation role's checks. Trace assembly continues; the Validation role is not the only writer.

**Why this isolates the component.** Removing Validation tests whether the explicit Validation role catches errors the other five roles miss, especially fabrications and constraint inconsistencies.

**Acceptance check.** Five role timings on the calibration tasks, not six. The artifact remains schema-valid. The fabrication count, scored downstream by the apparatus, differs from MANDATE-primary's on at least one calibration task.

### A6: no search-trace

**What is removed.** The cryptographic search trace. `_make_trace_entry` in `roles/base.py` returns an empty record (or is short-circuited at the call sites), and the Validation role's trace assembly is bypassed.

**Expected change.** A configuration flag on `PipelineConfig` would be the cleanest expression (`emit_trace=False`), but inspection shows the trace is hard-wired into every role. The variant adds a single boolean on `PipelineConfig`, defaults it to `True` (so MANDATE-primary at the primary tag stays unchanged behaviorally; the new field becomes part of the variant's pinned config), and reads it inside `_make_trace_entry`. Validation skips trace assembly when the flag is False.

**Why this isolates the component.** Trace completeness is not a comparative outcome (PROTOCOL_LOCK §4.1) but A6 lets the analysis test whether the trace's presence influences the other outcomes (for example by affecting Validation's behavior). A near-zero effect would be a useful null result.

**Acceptance check.** On a calibration task `state.trace_entries` is empty and the recorded artifact does not carry a trace block. Everything else runs.

### A7: no NIST AI RMF metadata

**What is removed.** The `nist_rmf` metadata woven into the artifact and the associated compliance hooks.

**Expected change.** `src/mandate/nist_rmf.py` is the entry point; the call sites that annotate the artifact with RMF metadata become no-ops in this variant, and the schema field becomes optional in the variant's schema. The fine-tuned roles are not retrained for the variant; their output passes through with the RMF annotation step removed.

**Why this isolates the component.** RMF annotation is compliance-oriented and sits alongside the substantive anchor. A near-zero effect on the primary outcomes is the expected, reportable, useful result.

**Acceptance check.** The artifact has no `nist_rmf` block (or the field is null), and on a calibration task the rest of the artifact is bit-identical to MANDATE-primary except for the RMF block. (If "bit-identical except for RMF" is not achievable because the RMF step also affected downstream serialization, the CHANGELOG explains what else changed.)

---

## Integration with the apparatus

When a variant tag exists, the Lead Analyst does one edit:

```python
# apparatus/ablations/manifest.py
ABLATIONS["A1"].aegis_ref = "mandate-eval-ablation-a1-2026q2-v1"
# and similarly for A2, A4, A6, A7
```

The harness then runs each variant via `AblationSystem(ablation_id="A1", variant_src_path="./AEGIS-eval-a1")`, where the variant_src_path comes from a sibling extraction the eval host will produce by re-running `setup/recreate_aegis_eval.sh --aegis ~/Desktop/AEGIS --tag mandate-eval-ablation-a1-2026q2-v1` per variant. No apparatus code changes after that.

The apparatus already refuses to run a variant whose `aegis_ref` is empty (it raises `AblationNotReadyError`), so until a tag is set the eval safely declines to substitute MANDATE-primary.

## Tag naming convention (suggested)

```
mandate-eval-ablation-a1-2026q2-v1
mandate-eval-ablation-a2-2026q2-v1
mandate-eval-ablation-a4-2026q2-v1
mandate-eval-ablation-a6-2026q2-v1
mandate-eval-ablation-a7-2026q2-v1
```

Each tag is annotated with a one-paragraph message naming the ablation and the variant's distinguishing change. If you prefer a different scheme, write it on the deliverable below; the Lead Analyst writes it into the manifest.

## Deliverable

A single short report, `handoffs/HANDOFF_05_report_<YYYY-MM-DD>.md`, listing per variant:

```markdown
## A<id>

- Tag:                    <full tag name>
- Commit:                 <40-char sha>
- Files changed (counts): <n added, n modified, n removed>
- Calibration runs:       6 ok, <n> role timings per run, fallback: <list or none>
- Anchor differs from primary: <yes/no, with the calibration task id that
                                shows the difference>
- CHANGELOG path inside the variant: <relative path>
- Caveats for the analyst: <one or two lines, empty if none>
```

When the report is in, the Lead Analyst (a) re-runs A1 verification against each variant in turn (a per-variant A1, cheap, six calibration tasks), (b) updates the manifest, and (c) marks TO_FILL_TRACKER row D11 RESOLVED. From there the variants are part of Phase 6 and Phase 7 like any other system.
