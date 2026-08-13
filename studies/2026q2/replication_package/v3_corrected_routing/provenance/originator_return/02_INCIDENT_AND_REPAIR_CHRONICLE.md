# Incident and Repair Chronicle

This record makes the restart and repair history explicit so the originator receives one coherent chain of custody rather than several unexplained archives.

## Preflight Correction Chain

1. The first returned smoke demonstrated the result-envelope idea but had incomplete code provenance and permissive analyzer/budget gates.
2. Follow-on repairs committed the MLT contract and apparatus routing, provenance, ledger, analyzer, and recovery behavior.
3. Two independent no-go audits identified remaining production retry and recovered-cost evidence defects. Those defects were corrected before the accepted paid smoke.
4. The final local clean preflight passed at the exact revisions recorded in `code/COMMITS.md`.

## Accepted Paid Smoke

The first local paid smoke attempt at `20260806T225847Z` failed strict analysis and is excluded from the accepted evidence set. It remains in the local worktree as historical evidence.

The replacement at `20260806T225913Z` passed:

- records: 2;
- primary denominator `N`: 2;
- execution state: `NON_EXECUTABLE_GAPS` for both;
- executable-with-blocking: 0;
- cost mode: exact;
- settled cost: `$0.108858`;
- analyzer issues: none.

Only the accepted replacement smoke is included under `paid_smoke/`.

## Campaign Restarts

The full campaign was interrupted by an intentional stop, a later process failure, and a power loss. Per-record checkpoints, `--skip-existing`, the shared ledger, pinned commits, and the original campaign root preserved completed observations. Resume operations continued in the same root rather than creating a mixed or duplicate campaign.

The hardened resume script now:

- verifies both pinned commits and the clean tracked worktrees;
- validates checkpoints and ledger state before requesting an API key;
- reconciles stale reservations;
- repairs stale shard ledgers from active checkpoints, preserving timestamped backups;
- selects only incomplete task IDs and handles empty task arrays;
- probes provider authentication before paid work;
- resumes with `--skip-existing`, the shared ledger, original manifest, and original cap;
- runs consolidation, final analysis, secret scanning, and checksum inventory after all shards pass.

## Cost-Evidence Repairs

Three Cond-B main records acquired duplicated role-attempt evidence during resume enrichment. The duplicated evidence did not represent new provider calls. Each affected record was backed up, repaired against the reservation IDs in the authoritative ledger, and revalidated. Audit files are included under `campaign/repair_audits/`.

Affected records:

- `cond_b__TASK-MAIN-INT-007__r04` (`Binding`);
- `cond_b__TASK-MAIN-SEC-010__r03` (`Decomposition`);
- `cond_b__TASK-MAIN-SEC-022__r10` (`Interpreter`).

After repair, the Cond-B main strict shard check returned zero issues for all 1,200 records.

## Invalid-Key Holdout Quarantine

On 2026-08-12, Cond-B holdout was invoked with an invalid Anthropic key. The system produced 300 failed checkpoints containing only authentication failures and conservatively settled 1,800 reservations at reserved bounds. These are not valid generation observations.

The failed checkpoints and their ledger rows were quarantined, not silently discarded:

- 300 invalid holdout files moved under the campaign repair provenance directory;
- 5,700 associated ledger rows preserved in a removed-rows evidence file;
- conservative reserved-bound total recorded as `$131.578020`;
- the active campaign ledger rebuilt without those non-observations;
- the full pre/post hashes and row counts recorded in `quarantine_audit.json`.

This amount was conservative reservation accounting for failed authentication, not a valid generation cost. The final originator report must retain this incident disclosure and distinguish the quarantined accounting from the active campaign's exact/conservative settled total.

## Holdout Shard-Ledger Repair

After the first valid holdout record completed, the shard-local ledger still contained run IDs from the quarantined invalid-key attempt and rejected the valid checkpoint as a duplicate. The stale local ledger was backed up and rebuilt from active checkpoint JSON. The missing shared-ledger record summary for the valid record was added from its existing settlements. The repair audit records the before/after hashes and counts.

## Current Evidentiary State

At the package snapshot, all pre-resume gates had passed, three full shards were complete, and valid Cond-B holdout generation was progressing. No temporary API key is stored in this package.

