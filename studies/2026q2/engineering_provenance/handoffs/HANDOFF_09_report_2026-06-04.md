# Handoff 09 Report: Main Anchor Scaffolds

**Codex session:** desktop session
**Eval host:** lattice-ws01
**Date:** 2026-06-04
**Wall clock:** ~91 minutes

## Verdict

PROCEED

## Evidence

- main_selection.json shape OK: yes
- corpus_freeze_v1 tag present: yes
- patched scaffolder present: yes
- resolved main tasks: 120/120
- scaffolds produced: 120/120
- scaffolds parsed_ok: 120/120
- scaffolds with derived_from: 120/120
- raw_json captured: 120/120
- Anthropic model used: `claude-opus-4-6`
- Anthropic max_tokens: 4096
- Anthropic input tokens (total): not serialized by `apparatus.corpus.cli scaffold`
- Anthropic output tokens (total): not serialized by `apparatus.corpus.cli scaffold`
- estimated API cost (USD): exact cost unavailable from persisted artifact

## Verification Command

```text
merged derived_from into 120 scaffolds
scaffolds: 120 parsed_ok: 120 with derived_from: 120
```

## Output Locations

- `04_ground_truth/main_scaffolds/main_tasks_resolved.jsonl`
- `04_ground_truth/main_scaffolds/anchor_scaffolds.jsonl`

## Anything the PI must decide before proceeding

- None for Handoff 09. Under the SME-skip deviation in `00_preregistration/DEVIATIONS.md`, these 120 scaffolds are ready for the `gt_freeze_v1` path as main-corpus ground truth.

## Deviations from this handoff

- None. Runtime exceeded the handoff estimate, but the command completed successfully without retry.
