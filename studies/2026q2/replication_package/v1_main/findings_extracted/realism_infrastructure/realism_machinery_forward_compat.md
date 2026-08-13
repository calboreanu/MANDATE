# Realism Audit Machinery (Forward Compatibility for v2-with-SMEs)

The realism audit CLI infrastructure (`apparatus.corpus.cli realism-form`,
`apparatus.corpus.cli realism-aggregate`) is built and tested, but unused
in the v1 evaluation per the SME-skip deviation (DEVIATIONS.md
2026-06-04).

## The CLI

- `realism-form --selection <selection.json> --pool <candidates.jsonl>
   --rater-id <id>` produces a per-rater CSV template for an SME to fill
  in with realism ratings for each candidate.
- `realism-aggregate` consumes the filled-in CSVs across multiple raters
  and produces the audit report including Krippendorff's α inter-rater
  reliability and the halt list (candidates flagged below the threshold).

## Forward-Compatibility Statement

For any future v2 evaluation that adds SME involvement, the existing
deposit artifacts feed cleanly into the realism audit:

1. The 156 PROMPTS Section 2 scaffolds in
   `04_ground_truth/{pilot,main,holdout}_scaffolds/anchor_scaffolds.jsonl`
   become candidate anchors for SME accept/edit/reject review.
2. The realism audit CSV produced by `realism-form` can be sent to SMEs
   for the 120 main-corpus tasks.
3. `realism-aggregate` consumes the filled CSVs to compute α and the halt
   list, gating a `corpus_freeze_v2_with_sme` tag.
4. The existing Phase 6 RunRecords at `outputs_freeze_v1_1` are re-graded
   against the SME-revised ground truth without regenerating the
   run-time data.

The CC BY 4.0 license on this deposit permits independent re-grading
work without permission. Independent SME teams can produce a v2 gt_freeze
on top of this v1 deposit and report differences in O1-O4 outcomes
attributable to SME revision.
