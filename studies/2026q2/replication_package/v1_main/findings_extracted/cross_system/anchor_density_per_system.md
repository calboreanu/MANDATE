# Cross-System Anchor Density Comparison

Records counted: ok=True only. MANDATE-primary uses the mandate-as-code schema where anchor.minimum is a single structured object; baselines use baseline_specification schema where minimum is an array of `{dimension, threshold, rationale}` objects.

| System | n | Schema-valid | Min (med) | Min (mean) | Target (med) | Constraints (med) | Gaps (med) | Gaps (max) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mandate_primary | 1180 | n/a | 1.0 | 1.00 | 1.0 | 0.0 | 0.0 | 0 |
| baseline_1 | 1206 | 1201/1206 | 8.0 | 8.23 | 4.0 | 6.0 | 9.0 | 13 |
| baseline_2 | 1206 | 1205/1206 | 3.0 | 3.16 | 1.0 | 2.0 | 2.0 | 5 |
| baseline_3 | 1205 | 0/1205 | 8.0 | 8.67 | 6.0 | 6.0 | 10.0 | 25 |
| baseline_4 | 1206 | 1195/1206 | 8.0 | 8.22 | 4.0 | 6.0 | 10.0 | 15 |
| baseline_5 | 1206 | 1196/1206 | 7.0 | 7.28 | 5.0 | 7.0 | 10.0 | 15 |
| baseline_6 | 1206 | 1197/1206 | 8.0 | 8.24 | 4.0 | 6.0 | 9.0 | 14 |
