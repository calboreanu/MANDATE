# Desktop Association Audit

Audit date: 2026-08-12

Scope: top-level Desktop items created by, copied for, or directly governing the August 2026 MANDATE V3 corrected-routing Codex rerun. Name matches were checked against file contents, Git ownership, commit reachability, and untracked evidence.

## Summary

- Total associated footprint before cleanup: about 4.077 GiB.
- Required active footprint: the local apparatus campaign root, pinned local MLT repository, and this consolidated return package.
- Superseded footprint recoverable after final verification: about 1.875 GiB (2.013 decimal GB).
- No item was moved or deleted while the paid campaign was active.
- Four small files unique to the first failed no-go worktree were copied into `historical/superseded_no_go_attempt/` before that worktree was marked removable.

## Active and Required

| Desktop item | Size | Reason |
|---|---:|---|
| `mandate-eval-v3-local-exec` | about 2.2 GB | Active process, venv, corpus, checkpoints, shared ledger, analysis, and restart scripts |
| `MLT-Governance-Stack-v3-local-exec` | about 25 MB | Pinned MLT source at campaign commit `c0b58fb...` |
| `MANDATE_ORIGINATOR_RETURN_20260812_FINAL/` | about 693 MB after finalization | Final consolidated handoff and complete campaign evidence |
| `MANDATE_ORIGINATOR_RETURN_20260812_FINAL.zip` and checksum | Generated after final verification | Authoritative transfer archive |

Do not move or rename the two local execution repositories. Absolute paths are recorded in the preflight manifest and campaign records.

## Superseded Apparatus Worktrees

The following are detached Git worktrees owned by `/Users/ws01admin/Documents/Research & Publications/MANDATE/mandate-eval-primary-2026q2`:

- `mandate-eval-v3-exec` at `d3810c3205db...`;
- `mandate-eval-v3-nogo-exec` at `7a07b8e738ad...`;
- `mandate-eval-v3-nogo2-exec` at `69adee1a575d...`;
- `mandate-eval-v3-nogo3-exec` at `9ab2c2923ba2...`.

Each is about 469 MB because each worktree carries another copy of the approximately 463 MB replication package. The detached commits are reachable through the preserved `codex/corrected-routing-apparatus-v1` history.

Their untracked preflight artifacts were hash-compared with the historical bundles and this consolidated package. All were duplicated except four files from `mandate-eval-v3-nogo-exec`; those four are now preserved under `historical/superseded_no_go_attempt/`.

After the final campaign ZIP verifies, remove these with `git worktree remove` from the owning repository. Do not delete the directories directly.

## Superseded MLT Worktrees

The following detached worktrees are owned by `/Users/ws01admin/Desktop/MLT-Governance-Stack` and all point to the earlier contract commit `5ed09e920eb4...`:

- `MLT-Governance-Stack-v3-exec`;
- `MLT-Governance-Stack-v3-nogo-exec`;
- `MLT-Governance-Stack-v3-nogo3-exec`.

They are clean, contain no unique untracked evidence, and the commit remains reachable from `codex/corrected-routing-contract-v1`. They can be removed with the parent repository's `git worktree remove` command after final verification.

## Superseded Bundles and Temporary Files

The following are associated historical outputs:

- all top-level `rerun_codex_*` directories and ZIPs;
- `mandate-local-rebuild.AGmdUV/`;
- `mandate_local_exec_paths_20260806.env`;
- `WINGMAN_ACTIVE_MLT_RUN_GUARD_2026-08-07.md`.

The temporary rebuild directory mirrors the no-go replacement bundles. The local path file contains paths only. The WINGMAN guard belongs to this campaign but its opening stopped-run state is stale after later resumes; it is preserved under `historical/cross_project/` and must not be treated as current status.

Two ZIP pairs are byte-identical:

- `rerun_codex_followon_bundle_20260806_1349_clean2.zip` and `rerun_codex_followon_preflight_bundle_20260806.zip`: SHA-256 `ada148aa483d090dc66cd13aaeb1e35a181fa474673379d2e6d6ec389fc59174`;
- `rerun_codex_no_go_replacement_preflight_bundle_20260806_FINAL.zip` and `rerun_codex_no_go_replacement_preflight_bundle_20260806_v2.zip`: SHA-256 `fe853a0755b65187bf32ad984117b96a19e6e383060be6c7d25f85452b8a5615`.

The authoritative instructions, audits, final patch series, current preflight evidence, accepted smoke, and repair history have been selected into this consolidated package. The historical bundles should remain until the final originator ZIP passes its checksums, then they may be archived or removed as one reviewed group.

## Associated Repositories That Are Not Cleanup Targets

- `/Users/ws01admin/Desktop/MLT-Governance-Stack` is the owning source repository, not a rerun artifact.
- `/Users/ws01admin/Documents/Research & Publications/MANDATE/mandate-eval-primary-2026q2` is the owning apparatus repository, not a Desktop artifact.
- `/Users/ws01admin/Desktop/Repos/MANDATE` and `/Users/ws01admin/Desktop/SWIFT/MANDATE` are separate project copies and were not created by this corrected-routing run.
- `/Users/ws01admin/Desktop/MLT-WINGMAN-INTEGRATION` is a separate WINGMAN integration worktree.

## Name or Content False Positives

The following mention MANDATE but are not part of the corrected-routing handoff or cleanup set:

- `_Archive_Review_2026-05-20/Round_3/mandate_duplicates/` contains older May publication/evaluation archives;
- `WINGMAN_ALPHA_HARDENING_HANDOFF_TO_CODEX_2026-08-09.md` is a WINGMAN hardening handoff;
- `Safeguards_Controls_WINGMAN_SLIDE.pptx` is presentation material;
- other WINGMAN decks, screenshots, authorization files, and worktrees are independent.

## Cleanup Decision

The current review supports a later Git-aware cleanup of the seven superseded worktrees plus the historical rerun bundles, temporary rebuild directory, path map, and stale guard. The safe cleanup gate remains final campaign completion, strict analysis PASS, final secret scan PASS, and verified final ZIP transfer.
