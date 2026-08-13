# MANDATE study release manifest — 2026.08.13

This is one study result and one release. Historical path and tag names remain
unchanged for provenance and hash continuity; they do not denote separately
published results.

## Pinned state

- Release identifier: `2026.08.13`; the published Git tag is
  `study-release-2026.08.13`.
- Frozen focused-check evidence commit:
  `f5019da050bfa87e8f72005820f059eee465aeb8` (historical evidence tag
  `v3_validation_20260812`).
- Unified retained-judge reconciliation commit:
  `e02f88cffbe80af3a62e51488e7e9b18199a6cd4`.
- Corrected-core campaign commit: `c0b58fb38b3c72ab6ece72f7576425892234976c`.

Private reviewer and local recovery bundles are deliberately excluded from the
public repository. Their hashes belong in the private handoff inventory, not
in this public data manifest.

## Release gates

From a full checkout (not a sparse worktree):

```bash
python3 code/scripts/verify_study_release.py
cd replication_package/v3_corrected_routing
sha256sum -c EVIDENCE_SHA256SUMS.txt
```

The focused routing-purpose test contains 3,000 records. Its measured denominator
is 2,999 signal-carrying records, with zero executable-with-blocking violations,
18,000 trace entries, and USD 191.388447 ledger-settled cost. The test determines
whether the successor implementation routes blocking or insufficient
specifications to non-executable states; it is not a second comparative study.

## Upload shape

- 3,023 tracked files in the prepared release.
- Checkout size: approximately 682 MiB before GitHub-side packing.
- The retained-stream component contains 82,155 grading records in nine
  deterministic gzip streams, including all 36,000 per-judge records behind
  the 12,000 full-coverage ensemble results.
- No tracked blob is 100 MB or larger.
- One tracked blob is larger than GitHub's 50 MB warning threshold:
  `replication_package/v2_complete/perturbations_mandate/mandate_primary_perturbations.jsonl`
  at 61,511,310 bytes. It remains ordinary Git content so a standard clone is
  self-contained; no Git LFS dependency is introduced.

The release is designed for a standard GitHub checkout with no Git LFS
dependency. Do not upload private corrected-core or local recovery bundles to
the public data repository.
