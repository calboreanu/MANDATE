# Desktop Cleanup Inventory

No source worktree or historical evidence was deleted while the paid campaign was active. This inventory separates the two live roots from safe post-finalization cleanup candidates.

## Preserve Until Final Bundle Verification

- `/Users/ws01admin/Desktop/mandate-eval-v3-local-exec` - active apparatus worktree and authoritative campaign root, about 2.2 GB.
- `/Users/ws01admin/Desktop/MLT-Governance-Stack-v3-local-exec` - pinned MLT worktree used by the campaign.
- `/Users/ws01admin/Desktop/MANDATE_ORIGINATOR_RETURN_20260812_FINAL` - final consolidated return package.

Do not move or rename either live worktree while the resume script or campaign process is running. Their absolute paths are embedded in the preflight and campaign provenance.

## Historical Worktrees

These are superseded execution worktrees, each about 469 MB:

- `mandate-eval-v3-exec`
- `mandate-eval-v3-nogo-exec`
- `mandate-eval-v3-nogo2-exec`
- `mandate-eval-v3-nogo3-exec`

After the final originator ZIP verifies, remove these through the owning repository's `git worktree` commands rather than moving or deleting them in Finder. That keeps Git's worktree registry consistent.

The same rule applies to these superseded MLT worktrees, all at the earlier `5ed09e9...` contract commit:

- `MLT-Governance-Stack-v3-exec`
- `MLT-Governance-Stack-v3-nogo-exec`
- `MLT-Governance-Stack-v3-nogo3-exec`

Their owning repository is `/Users/ws01admin/Desktop/MLT-Governance-Stack`. They are clean and contain no unique untracked evidence.

## Historical Bundles

The following are superseded by this consolidated package but should remain until the final ZIP is verified:

- `rerun_codex_handoff_bundle_20260806_090051/` and ZIP;
- `rerun_codex_followon_bundle_20260806_1349/` and its four overlapping ZIP variants;
- `rerun_codex_no_go_replacement_preflight_bundle_20260806/`;
- `rerun_codex_no_go_replacement_preflight_bundle_20260806_v2/` and ZIP variants;
- `rerun_codex_no_go2_replacement_preflight_bundle_20260806/` and ZIP;
- `mandate-local-rebuild.AGmdUV/`;
- `mandate_local_exec_paths_20260806.env`.
- `WINGMAN_ACTIVE_MLT_RUN_GUARD_2026-08-07.md`.

These files contain audit history, but the originator should receive the selected authoritative documents in this package rather than every duplicate archive.

The guard file is associated but stale: its opening stopped-run state predates the current resume. A historical copy is included in `historical/cross_project/`; it is not current operating guidance.

The complete association analysis and exact duplicate ZIP hashes are recorded in `05_DESKTOP_ASSOCIATION_AUDIT.md`.

## Cleanup Gate

The campaign and final package now satisfy all six cleanup gates below. Cleanup is authorized from an evidence-preservation perspective, but no historical worktree or bundle has been removed automatically.

1. Cond-B holdout reaches 300 valid records.
2. All four strict shard checks pass.
3. Consolidation and strict final analysis pass.
4. The final secret scan reports no live secret.
5. The final checksum manifest and external ZIP checksum verify.
6. The final ZIP has been copied to its intended transfer location.
