# Originator Deliverable Matrix

This matrix tracks the 16 final deliverables specified in section 11 of the follow-on authorization.

| # | Required deliverable | Final location | State |
|---:|---|---|---|
| 1 | Core commit hash and patch | `code/COMMITS.md`, `code/mlt_patches/` | Complete |
| 2 | Apparatus commit hash and patch | `code/COMMITS.md`, `code/apparatus_patches/` | Complete |
| 3 | Strict analyzer source and adversarial tests | Apparatus patch series; source hashes in `preflight/preflight_manifest.json` | Complete |
| 4 | Clean-worktree/provenance manifest | `preflight/preflight_manifest.json`, `campaign/full_campaign/provenance/` | Complete |
| 5 | Complete core and apparatus test logs | `preflight/logs/` | Complete |
| 6 | Replacement smoke records and analysis | `paid_smoke/` | Complete |
| 7 | Replacement smoke cost ledger | `paid_smoke/api_cost_ledger.jsonl` | Complete |
| 8 | All four full-campaign shards | `campaign/full_campaign/cond_a_main`, `cond_a_holdout`, `cond_b_main`, `cond_b_holdout` | Complete |
| 9 | Full shared cost ledger | `campaign/full_campaign/api_cost_ledger.jsonl` | Complete |
| 10 | Consolidated Cond-A and Cond-B JSONL | `campaign/full_campaign/cond_a_rerun.jsonl`, `cond_b_rerun.jsonl` | Complete |
| 11 | Final rerun manifest and SHA-256 inventory | `campaign/full_campaign/rerun_manifest.json`, `provenance/file_hashes.sha256`, package `SHA256SUMS.txt` | Complete |
| 12 | V1-versus-V3 tables | `campaign/full_campaign/analysis/rerun_routing_summary.csv` and `.tex`; final JSON includes V1 summary | Complete |
| 13 | Fallback/retry/cost/trace reports | `campaign/full_campaign/analysis/` | Complete |
| 14 | Exact total spend | `$191.388447` in final analysis, summary, and ledger | Complete |
| 15 | Final paper language and limitations | `00_READ_ME_FIRST.md`, `06_FINAL_RESULTS_AND_LIMITATIONS.md` | Complete |
| 16 | Secret-scan results | `campaign/full_campaign/analysis/secret_scan_report.json`; package-level verification | Complete |

All requested deliverables are present. `SHA256SUMS.txt` is the portable, relative-path integrity manifest for this return package.

