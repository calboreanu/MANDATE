# MANDATE study release manifest — 2026.08.13

This is one study result and one release. Historical path and tag names remain
unchanged for provenance and hash continuity; they do not denote separately
published results.

## Pinned state

- Deposit commit: `f5019da050bfa87e8f72005820f059eee465aeb8` plus the release-hygiene commit prepared after it.
- Evidence tag: `v3_validation_20260812` (points to the frozen evidence commit above).
- Corrected-core campaign commit: `c0b58fb38b3c72ab6ece72f7576425892234976c`.
- Corrected-core private reviewer bundle SHA-256:
  `54c3979904a5378cdcd4eb606e14b9f8619593602a04261e6373758b8e20d3e1`.
- Evaluation integration delta bundle SHA-256:
  `fabf71df41224c261b830ebcbb8fc2dda25850c111879675f616003e656e2113`.

## Release gates

From a full checkout (not a sparse worktree):

```bash
python3 code/scripts/verify_v3_corrected_routing.py
cd replication_package/v3_corrected_routing
sha256sum -c EVIDENCE_SHA256SUMS.txt
```

The focused routing-purpose test contains 3,000 records. Its measured denominator
is 2,999 signal-carrying records, with zero executable-with-blocking violations,
18,000 trace entries, and USD 191.388447 ledger-settled cost. The test determines
whether the successor implementation routes blocking or insufficient
specifications to non-executable states; it is not a second comparative study.

## Upload shape

- 3,007 evidence-commit files before release-hygiene and retained-source additions.
- Evidence tree size: 656,640,977 bytes (626.22 MiB uncompressed).
- Simulated Git pack: approximately 198 MiB.
- No tracked blob is 100 MB or larger.
- One tracked blob is larger than GitHub's 50 MB warning threshold:
  `replication_package/v2_complete/perturbations_mandate/mandate_primary_perturbations.jsonl`
  at 61,511,310 bytes. It remains ordinary Git content so a standard clone is
  self-contained; no Git LFS dependency is introduced.

The public evaluation repository did not yet exist when this manifest was
prepared. Create it as an empty repository, push the prepared release branch,
run CI, then make `main` public only after the private reviewer/package boundary
has been checked. Do not upload the private corrected-core bundle to the public
data repository.
