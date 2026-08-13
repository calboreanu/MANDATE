# Authoritative Code Revisions

## MLT

- Repository: `/Users/ws01admin/Desktop/MLT-Governance-Stack-v3-local-exec`
- Base: `52e54e4d5aa69dc18a3ddedae4caf2ab42d11ea9`
- Campaign commit: `c0b58fb38b3c72ab6ece72f7576425892234976c`
- Commit subject: `Add fail-closed MANDATE result envelope contract`

The MLT patch series is in `mlt_patches/`.

## Apparatus

- Repository: `/Users/ws01admin/Desktop/mandate-eval-v3-local-exec`
- Base: `ab64056c9464f9ab294696698423c4167a703071`
- Campaign commit: `74c62b02856254656905269d2bff9851dbfb1800`

Commit series:

1. `58e16fc3d47f005a344a903e99c34ff54423d6fc` - Add corrected routing rerun gates and provenance
2. `af471dc753570a6f0b9bba4ae4716d9dd8cae731` - Fix rerun paid-path ledger and analyzer gates
3. `9413b78beb7a6be7970c548ed873c2a2069e8ce7` - Accept frozen corpus text field in rerun analyzer
4. `15a7cca4651e43c22d3b765f334105884b47947e` - Fix paid retry and recovered cost evidence
5. `74c62b02856254656905269d2bff9851dbfb1800` - Add local V3 preflight gates

The apparatus patch series is in `apparatus_patches/`.

## Operational Script

The resume script is operational evidence, not campaign source code. It lives outside the tracked source revision so the clean-worktree gate remains truthful.

- Packaged path: `campaign/operations/resume_existing_campaign_20260806T231117Z_from_env.sh`
- SHA-256: `cb2bfd8619406d68b4059d35f228b71dfc4e04a82ee7712331b72c81d6570b5e`

It must not be represented as part of either pinned commit.

After campaign completion, its finalization block was corrected to write the campaign summary before the hash inventory, exclude the inventory from self-hashing, atomically replace it, and verify every listed hash. This operational reporting fix did not change the pinned campaign source or any result record.
