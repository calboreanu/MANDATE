# Final Results and Limitations

## Decision

The corrected-routing campaign passed every final structural and contract gate. The strict analyzer returned `ok=true`, no issues, and zero executable-with-blocking observations.

## Results

| Measure | Result |
|---|---:|
| Total V3 records | 3,000 |
| Primary blocking/insufficient denominator | 2,999 |
| Executable with blocking/insufficient signal | 0 |
| Measured rate | 0.0 |
| Zero-event upper 95% bound | 0.0009984116497422368 |
| Cond-A records | 1,500 |
| Cond-B records | 1,500 |
| V3 `NON_EXECUTABLE_GAPS` | 2,999 |
| V3 `EXECUTABLE` | 1 |
| Cond-B fallback records | 157 |
| Final settled campaign cost | `$191.388447` |

Cond-A cost was `$40.286970`; Cond-B cost was `$151.101477`. Cost accounting is labeled `conservative_upper_bound` because three interrupted attempts were conservatively settled. The ledger closed with 10,513 reservations, 10,513 settlements, 3,000 record summaries, and no active reservations.

All 157 fallback records were routed to `NON_EXECUTABLE_GAPS`. The one `EXECUTABLE` record was a non-fallback Cond-B record and did not carry an unresolved blocking or insufficient-for-automation signal.

Trace integrity passed for all 3,000 records: 3,000 artifacts, 3,000 chain hashes, and 18,000 trace entries validated with `mlt.mandate.validator.validate_obj`.

The frozen V1 comparison set contains 3,000 records, all labeled `MANDATE_AS_CODE` with `ok=true`, while all 3,000 carried a blocking or insufficient signal under the corrected analysis.

## Paper-Facing Language

> In a generation-only corrective validation on the committed 1.0.3-derived prompt stack, using the frozen 150-task corpus and original 10-run seed schedule, the repaired contract routed all 2,999 records carrying unresolved blocking or insufficient-for-automation signals to explicit non-executable states; zero such records were marked executable.

Report the single non-blocking `EXECUTABLE` record separately so readers can reconcile the 3,000 total with the primary denominator of 2,999.

## Limitations and Incident Disclosure

1. The original rc1 prompt implementation was not recovered and hash-verified. This is a corrective validation on the committed 1.0.3-derived prompt stack, not an exact same-prompt rerun.
2. Three interrupted paid attempts use conservative upper-bound settlement. Exact provider-call and record evidence otherwise reconciles; the analyzer found no cost issue.
3. Cond-B produced 157 fallback records. All were explicit non-executable outcomes, but fallback stratification must accompany the headline result.
4. An invalid Anthropic key previously generated 300 authentication-failure checkpoints and 1,800 reserved-bound settlements. Those non-observations and 5,700 associated ledger rows were quarantined with pre/post hashes and are not included in the 3,000 valid campaign records or `$191.388447` active ledger total.
5. Three resumed Cond-B main records acquired duplicated role-attempt evidence during skip-existing enrichment. Each original record was backed up, the duplicate evidence was removed against authoritative reservation IDs, and the repaired 1,200-record shard passed strict validation with zero issues.
6. The first valid holdout checkpoint encountered a stale shard-local ledger left by the quarantined run. That ledger was backed up and rebuilt from active checkpoints; the shared summary was reconciled from existing settlements. The final holdout shard passed all gates.

## Verification

- MLT test suite: `2384 passed, 31 skipped, 4 xfailed`.
- Apparatus test suite: `371 passed, 3 skipped`.
- Focused phase-two regressions: `39 passed`.
- No-network production smoke: ordinary success, fail-once retry, and recovered-stale-success all passed.
- Paid replacement smoke: 2 records, `N=2`, zero executable-with-blocking, exact cost `$0.108858`.
- Four final shard checks: all `ok=true`, zero issues.
- Final analyzer: `PASS: N=2999, executable_with_blocking=0`.
- Campaign secret scan: `ok=true`, zero hits.
- Campaign hash inventory: 3,384 listed files, all verified after excluding the inventory from self-hashing.

The operational script in `campaign/operations/` was corrected after completion so future finalization writes the summary before inventory generation, excludes the inventory and temporary file from hashing, atomically installs the inventory, and verifies it immediately. This reporting fix did not alter campaign records, ledger entries, or analysis results.

