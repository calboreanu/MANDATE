# Final Package Verification

Verification performed: 2026-08-12

## Structural Checks

- Payload files excluding the package checksum manifest: 3,495.
- JSON files parsed: 3,363.
- JSON parse errors: 0.
- `.DS_Store`, `.git`, `__pycache__`, `.pytest_cache`, and `.pyc` artifacts: 0.
- Live-looking Anthropic keys, bearer tokens, or populated Anthropic key assignments: 0.

The package-level secret scan covered the complete final folder, including all records, ledgers, logs, instructions, patches, historical repair evidence, and analysis outputs.

## Source-Copy Equivalence

A checksum-mode `rsync` comparison between the authoritative completed campaign root and `campaign/full_campaign/` produced no differences. The final transfer copy therefore matches the source campaign after excluding only `.DS_Store`, Python caches, and `.pyc` files.

## Campaign Integrity

- Four shard checks: all `ok=true`, zero issues.
- Records: 3,000; record summaries: 3,000.
- Reservations: 10,513; settlements: 10,513; active reservations: 0.
- Consolidated JSONL: 1,500 Cond-A records and 1,500 Cond-B records.
- Final analyzer: `ok=true`, `N=2,999`, executable-with-blocking count `0`, no issues.
- Campaign secret scan: `ok=true`, zero hits.
- Campaign inventory: 3,384 listed files, all hashes verified.

The generated campaign inventory initially included itself and therefore had one unavoidable self-hash mismatch. The operational finalization script was corrected to write the summary first, exclude the inventory and temporary file, atomically install the inventory, and verify it. The regenerated inventory passes in full. No record, ledger row, or scientific result changed.

## Patch Reproduction

Both patch series were applied to temporary detached worktrees at the documented base revisions. Resulting tree objects matched the campaign commits exactly:

- Apparatus patch tree and campaign tree: `20576459a4ad6bdfa737709da5cc2713162ac9bf`.
- MLT patch tree and campaign tree: `436683db0f9b017cd21fd08cbc993d009a5ccc39`.

## Included Test Gates

- MLT: `2384 passed, 31 skipped, 4 xfailed`.
- Apparatus: `371 passed, 3 skipped`.
- Focused regressions: `39 passed`.
- No-network production smoke V3: ordinary success, fail-once retry, and recovered-stale-success scenarios passed strict analysis.
- Accepted paid smoke: `ok=true`, `N=2`, zero issues, exact settled cost `$0.108858`.

## Transfer Verification

`SHA256SUMS.txt` is generated with paths relative to this final package and verified before ZIP creation. The ZIP is tested with `unzip -t`, and its external SHA-256 is stored alongside it in `MANDATE_ORIGINATOR_RETURN_20260812_FINAL.zip.sha256`.

