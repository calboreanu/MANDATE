# Errata — Label Discrepancies in Frozen Artifacts

Added 2026-07-17 (pre-push fix D8). Frozen evidence files are deliberately
preserved byte-for-byte as executed; where a frozen label is misleading, the
correction is documented here instead of rewriting the artifact.

## E-1: v1 Anthropic judge is labeled "Opus" but executed as Claude Sonnet 4.6

**The discrepancy.** Three places label the v1 grading cycle's Anthropic
judge as Opus:

1. `replication_package/v1_main/grading/v1_sampled/judges_config.json` —
   `"claude": "claude-opus-4-6"`.
2. The judge identifier string `judge_2_claude_opus`, carried on every v1
   grading artifact: `v1_sampled/ensemble_scores.jsonl` (`judge_ids`, all 700
   records), `v1_sampled/v1_irr_report.json` (pairwise-κ keys, e.g.
   `mission_intent_match:judge_1_gpt4o|judge_2_claude_opus`), and
   `v1_sampled/double_grade/pass{1,2}_scores.jsonl` (`judge_scores[].judge_id`).
   (Upstream, the eval-host directory was likewise named
   `08_grading/judge_2_claude_opus/`.)
3. `docs/CLAIM_TO_DATA_MAP.md` row 5, which reads the v1 κ-halt statistic as
   "(0.2964, mission_intent_match, opus|gemini)".

**The proof of what actually ran.** The per-judge score records embed the
executed model identifier: in
`replication_package/v1_main/grading/v1_sampled/double_grade/pass1_scores.jsonl`
and `pass2_scores.jsonl`, every `judge_scores[]` entry with
`judge_id = "judge_2_claude_opus"` carries **`"model": "claude-sonnet-4-6"`**
(verified exhaustively across both passes, 2026-07-17; the other two judges
read `gpt-4o-2024-11-20` and `gemini-2.5-pro` exactly as labeled). The salvage
audit recorded the same conflict on the eval host:
`engineering_provenance/handoffs/v2_salvage_audit.md` — "Judges:
gpt-4o-2024-11-20, claude-sonnet-4-6 (note: dir-name says opus, config says
sonnet)".

**The correct reading** (consistent with the README status disclosure and the
deviation record):

- `judges_config.json` records the **pre-registered** ensemble (Opus). It is
  frozen pre-registration/configuration evidence, not an execution log.
- The **v1 sampled cycle** (N=700 + the 70-record double-grade; the cycle that
  engaged the PROTOCOL_LOCK §8 κ halt at 0.296) executed its Anthropic judge
  as **Claude Sonnet 4.6**, substituted under **Deviation D-08**. The
  `judge_2_claude_opus` identifier was kept as a stable slot name.
- The **v2 full-coverage cycle** (12,000 records;
  `v1_main/grading/v2_full_coverage/ensemble_scores.jsonl`, the comparative
  table's source of record) **restored Claude Opus 4.6 per Deviation D-10** —
  there the same `judge_2_claude_opus` identifier matches the executed model
  (see `docs/ENVIRONMENT.md`: "Claude Opus 4.6 + GPT-4o + Gemini 2.5 Pro
  three-judge ensemble"; CHANGELOG v2-closeout entry, D-09/D-10).
- Cost corollary (already disclosed): grading projections were Sonnet-priced;
  D-10's Opus restoration raised per-grade cost ~5× (cost-ledger closeout
  addendum; `docs/CLAIM_TO_DATA_MAP.md` row 15).

**What was not changed.** `judges_config.json`, the score/IRR artifacts, and
the claim map's frozen row text are preserved unmodified; long-form deviation
narratives are in `pre_registration/DEVIATIONS.md` and the 13-row structured
deviation table is §9 of the Empirical Evidence Supplemental
(`supplement_pdfs/`). Anyone re-grading v1 for comparison should judge with
Claude Sonnet 4.6, not Opus, to match the v1 artifacts.
