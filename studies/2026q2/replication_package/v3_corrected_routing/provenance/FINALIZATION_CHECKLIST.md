# Finalization Record

Completed: 2026-08-12

- [x] Campaign runner and `caffeinate` process exited.
- [x] Counts reached 1,200 Cond-A main, 300 Cond-A holdout, 1,200 Cond-B main, and 300 Cond-B holdout.
- [x] All four strict shard checks returned `ok=true` with zero issues.
- [x] Shared ledger closed with no active reservation, 10,513 matched reservations/settlements, 3,000 record summaries, and `$191.388447` settled below the `$299.250033` cap.
- [x] Deterministic consolidation produced `cond_a_rerun.jsonl`, `cond_b_rerun.jsonl`, and `rerun_manifest.json`.
- [x] Strict final analysis passed against V3, frozen V1, both corpora, exact schema, shared ledger, and pinned commits.
- [x] Final analysis reported `N=2,999` and zero executable-with-blocking records.
- [x] Publication CSV, LaTeX, fallback, retry/cost, trace, and provenance outputs were generated.
- [x] Final result language, limitations, fallback count, incident disclosure, and exact spend were recorded.
- [x] Campaign and final-package secret scans reported zero live-looking secret hits.
- [x] Campaign and package checksum inventories were generated and verified.
- [x] Final ZIP was archive-tested and assigned an external SHA-256.

Required paper language is recorded in `00_READ_ME_FIRST.md` and `06_FINAL_RESULTS_AND_LIMITATIONS.md`.

