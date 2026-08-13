# MANDATE V3 Final Originator Return

Date completed: 2026-08-12

Status: **FINAL CAMPAIGN PASS**

This directory is the authoritative return for the MANDATE V3 corrected-routing campaign requested in the original handoff and follow-on authorization. Earlier Desktop bundles are historical and should not be sent as competing handoffs.

## Final Result

The strict analyzer passed with no issues:

- total records: 3,000;
- Cond-A: 1,500 records, all `NON_EXECUTABLE_GAPS`;
- Cond-B: 1,500 records, 1 `EXECUTABLE` and 1,499 `NON_EXECUTABLE_GAPS`;
- primary blocking/insufficient denominator `N`: 2,999;
- blocking/insufficient records marked `EXECUTABLE`: **0**;
- measured rate: `0.0`;
- zero-event upper 95% bound: `0.0009984116497422368`;
- fallback records: 157, all Cond-B and all `NON_EXECUTABLE_GAPS`;
- final cost: `$191.388447` under conservative-upper-bound accounting;
- authorized campaign cap: `$299.250033`;
- unused cap: `$107.861586`.

All four shards passed strict validation with zero issues. The ledger contains 10,513 reservations, 10,513 settlements, 3,000 record summaries, and no active reservation. Consolidation produced 1,500-line Cond-A and Cond-B JSONL files. All 3,000 records contain artifacts and chain hashes, with 18,000 validated trace entries.

## Paper-Facing Statement

> In a generation-only corrective validation on the committed 1.0.3-derived prompt stack, using the frozen 150-task corpus and original 10-run seed schedule, the repaired contract routed all 2,999 records carrying unresolved blocking or insufficient-for-automation signals to explicit non-executable states; zero such records were marked executable.

The single `EXECUTABLE` V3 record was outside the primary blocking/insufficient denominator.

## Authoritative Revisions

- MLT: `c0b58fb38b3c72ab6ece72f7576425892234976c`
- Apparatus: `74c62b02856254656905269d2bff9851dbfb1800`
- Preflight manifest SHA-256: `09425f3d725d6f7192aa13a5bf3287b75e8eb0afc56d062074d432c5bc6d0067`
- Final operational resume script SHA-256: `cb2bfd8619406d68b4059d35f228b71dfc4e04a82ee7712331b72c81d6570b5e`

## Primary Evidence

- `campaign/full_campaign/cond_a_main/` - 1,200 records;
- `campaign/full_campaign/cond_a_holdout/` - 300 records;
- `campaign/full_campaign/cond_b_main/` - 1,200 records;
- `campaign/full_campaign/cond_b_holdout/` - 300 records;
- `campaign/full_campaign/api_cost_ledger.jsonl` - shared campaign ledger;
- `campaign/full_campaign/cond_a_rerun.jsonl` and `cond_b_rerun.jsonl` - consolidated outputs;
- `campaign/full_campaign/rerun_manifest.json` - deterministic consolidation manifest;
- `campaign/full_campaign/analysis/final_analysis.json` - strict machine-readable result;
- `campaign/full_campaign/analysis/` - CSV, LaTeX, fallback, retry, cost, trace, secret-scan, and shard reports;
- `campaign/full_campaign/provenance/file_hashes.sha256` - verified campaign inventory;
- `SHA256SUMS.txt` - relative checksum manifest for the complete transfer package.

## Required Limitations

- Use the label **Corrective validation on the mlt-stack 1.0.3-derived prompt stack**.
- Do not call this an exact same-prompt rerun. The original rc1 prompt source was not recovered and hash-matched.
- Cost mode is `conservative_upper_bound` because three interrupted attempts were conservatively settled.
- Disclose 157 Cond-B fallback records and report their stratified outcome.
- Preserve the invalid-key quarantine and repair audits as incident evidence. The quarantined authentication failures are not part of the 3,000 valid generation observations.

See `06_FINAL_RESULTS_AND_LIMITATIONS.md` for the complete result narrative and `01_DELIVERABLE_MATRIX.md` for the final 16-item handoff index.

