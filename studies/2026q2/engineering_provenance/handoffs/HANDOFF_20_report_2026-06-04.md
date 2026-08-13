# Handoff 20 Report: Hold-out Anchor Scaffolds

**Codex session:** desktop session
**Eval host:** lattice-ws01
**Date:** 2026-06-04
**Wall clock:** ~24 minutes

## Verdict

PROCEED

## Evidence

- holdout selection shape OK: yes
- corpus_freeze_v1 tag present: yes
- patched scaffolder present: yes
- resolved holdout tasks: 30/30
- scaffold records produced: 30/30
- scaffold records parsed_ok: 30/30
- unique task_ids: 30/30
- raw_json captured: 30/30
- Anthropic model used: `claude-opus-4-6`
- Anthropic max_tokens: 4096
- Anthropic cost: not serialized by `apparatus.corpus.cli scaffold`; exact cost unavailable from persisted artifact

## Source Distribution

| source | count |
|---|---:|
| NIST_SP_800-160_Vol._1_Systems_Security_Engineering.txt | 21 |
| NIST_SP_800-64_Rev._2_Security_Considerations_in_the_SDLC.txt | 5 |
| NIST_SP_800-218_Secure_Software_Development_Framework.txt | 4 |

## Verification Command

```text
merged derived_from into 30 scaffolds
30 holdout scaffolds, 30 parse_ok, 30 unique task_ids
   21 from NIST_SP_800-160_Vol._1_Systems_Security_Engineering.txt
    5 from NIST_SP_800-64_Rev._2_Security_Considerations_in_the_SDLC.txt
    4 from NIST_SP_800-218_Secure_Software_Development_Framework.txt
```

## Output Locations

- `04_ground_truth/holdout_scaffolds/holdout_tasks_resolved.jsonl`
- `04_ground_truth/holdout_scaffolds/anchor_scaffolds.jsonl`

## Anything the PI must decide before proceeding

- None for Handoff 20. Hold-out scaffolds are parseable and ready for the `gt_freeze_v1` path.

## Deviations from this handoff

- None.
