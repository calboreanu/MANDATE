# V3 Corrected-Routing Validation

This tier contains the generation-only corrective validation of the two
canonical MANDATE conditions on the fail-closed `1.0.3`-derived contract.
It does not rerun baselines, judges, grading, perturbations, or ablations.

## Result

| Measure | Result |
|---|---:|
| Records | 3,000 |
| Cond-A | 1,500 |
| Cond-B | 1,500 |
| Independently recomputed blocking/insufficient denominator | 2,999 |
| Blocking/insufficient records marked executable | 0 |
| `NON_EXECUTABLE_GAPS` | 2,999 |
| `EXECUTABLE` | 1 |
| Cond-B fallback records | 157 |
| Full-campaign settled cost | USD 191.388447 |
| Cumulative authorized spend including prior smoke/probes | USD 192.138414 |
| Remaining under the USD 300 authorization | USD 107.861586 |

The one executable observation is
`cond_b__TASK-MAIN-FIN-003__r07`. It has nonblocking gap reports but no
signal that meets the committed blocking/insufficient predicate. The result
therefore supports a blocking-routing claim, not a claim that every record
with any gap is non-executable.

## Paper-facing claim

> In a generation-only corrective validation on the committed 1.0.3-derived
> prompt stack, using the frozen 150-task corpus and original 10-run seed
> schedule, the repaired contract routed all 2,999 records carrying unresolved
> blocking or insufficient-for-automation signals to explicit non-executable
> states; zero such records were marked executable.

Do not call this an exact same-prompt rerun. The original `1.0.0rc1` prompt
implementation was not recovered and hash-matched.

## Layout

- `outputs/` contains deterministic gzip streams of the two consolidated
  RunRecord files and shared cost ledger. Use `gzip -dc`; gzip headers omit
  source names and timestamps.
- `analysis/` contains the as-received strict analyzer outputs plus
  `corrected_reporting.json`, which fixes cumulative-cost and provider-attempt
  labels without changing any observation.
- `provenance/` contains the preflight manifest, commits and patches, tests,
  smoke evidence, incident/repair audits, and the originator's documentation.
- `archive/` contains a byte-exact split of the complete originator ZIP. It is
  split only to remain below GitHub's per-file size limit.

The frozen input corpus and V1 comparison records remain in
`../v1_main/{corpus,system_outputs}/`. Their six SHA-256 values match the
preflight manifest exactly.

## Verify

From the repository root:

```bash
python3 code/scripts/verify_v3_corrected_routing.py
```

Reconstruct and test the full originator archive:

```bash
cat replication_package/v3_corrected_routing/archive/MANDATE_ORIGINATOR_RETURN_20260812_FINAL.zip.part-* \
  > /tmp/MANDATE_ORIGINATOR_RETURN_20260812_FINAL.zip
shasum -a 256 /tmp/MANDATE_ORIGINATOR_RETURN_20260812_FINAL.zip
unzip -t /tmp/MANDATE_ORIGINATOR_RETURN_20260812_FINAL.zip
```

Expected archive SHA-256:
`9193189e58b99e8e7655448fbebfc3da5021bca69dc4d43330f051a8040ba0ef`.

## Accounting clarification

`analysis/final_analysis.json` correctly reports the campaign ledger total,
but its `provider_call_count` counts provider-response objects rather than
attempts. The authoritative ledger contains 10,510 response-received attempts
and three additional dispatch-uncertain conservative settlements, for 10,513
reservations. Thirteen attempts exceed the nominal one-call-per-logical-role
schedule: ten authoritative responses costing USD 0.177549 and three
conservative settlements costing USD 0.243927. All are already included in
the USD 191.388447 campaign total.

