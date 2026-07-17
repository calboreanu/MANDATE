# Exclusions — Promised Paths Not Present in This Deposit

Added 2026-07-17 (pre-push fix D6). The deposit-planning documents
(`GITHUB_DEPOSIT_PLAN.md`, `DEPOSIT_MAPPING.md`) promise a small number of
paths that are not in the repository as planned. This file enumerates each
one, where it was promised, and its actual status, so a reviewer following
the plan documents is never left guessing. Nothing here affects the frozen
evidence or any quantitative claim.

| # | Promised path | Promised where | Status |
|---|---|---|---|
| 1 | `pre_registration/02_strongest_baseline_selection_rule.md` | `GITHUB_DEPOSIT_PLAN.md` (pre_registration tree listing) · `DEPOSIT_MAPPING.md` T1 table ("The locked rule for pre-specifying strongest baseline against the calibration set", routed GH) | **Superseded by `pre_registration/PROTOCOL_LOCK.md`.** The locked selection rule was never a standalone file in the deposit; it is carried verbatim inside the locked protocol: PROTOCOL_LOCK "Baselines" section ("Define 'strongest baseline' as the baseline achieving highest mean anchor completeness on the calibration set") and its pre-registered decision-rule list ("Decision rule for 'strongest baseline' (used in primary test) pre-registered as: highest mean anchor completeness on the 6 calibration tasks"). |
| 2 | `replication_package/v0_5_pilot/authorized_lab/` (the 6-case pentest corpus) | `GITHUB_DEPOSIT_PLAN.md` (v0_5_pilot tree, "# 6-case pentest corpus") · `DEPOSIT_MAPPING.md` T3 table ("Required to replicate the pilot. Mirror as `replication_package/v0_5_pilot/authorized_lab/`") | **Not deposited; available on request.** The corpus is part of the proprietary upstream AEGIS evaluation tree, which this deposit does not redistribute (`replication_package/v0_pilot/README.md`: "the AEGIS reference implementation itself is proprietary and is not redistributed; these artifacts are its evaluation outputs"). The pilot's raw outputs — the 15 `authorized_lab_eval_*` cross-profile logs and the AUTHLAB-RUN-001 run logs — *are* deposited under `replication_package/v0_5_pilot/logs/` and are the source of every §6.7 aggregate. Re-running the pilot (as opposed to verifying its outputs) requires the corpus and apparatus on request, like mlt-stack (see `docs/REPLICATION_INSTRUCTIONS.md`, "Acquiring mlt-stack"). |
| 3 | `replication_package/v0_5_pilot/ab_evaluation.py` ("the script that emits the 5/6 ok pattern") | `GITHUB_DEPOSIT_PLAN.md` (v0_5_pilot tree listing) | **Not deposited; available on request.** The script belongs to the proprietary upstream AEGIS apparatus (`replication_package/v1_main/findings_extracted/v1_pilot_cross_profile/findings.md` records it as `~/Desktop/AEGIS/scripts/ab_evaluation.py`, run with `--profiles deterministic,base,tuned`) and was not extracted into the deposit for the same non-redistribution reason as item 2. Its outputs (the 15 logs) and the deterministically extracted aggregates (item 4) are deposited, so the 5/6 ok pattern is verifiable without it. |
| 4 | `replication_package/v0_5_pilot/profile_aggregates.json` ("extracted aggregates from 15 logs") | `GITHUB_DEPOSIT_PLAN.md` (v0_5_pilot tree listing) | **Superseded by (deposited at) `replication_package/v1_main/findings_extracted/v1_pilot_cross_profile/profile_aggregates.json`.** The file exists in the deposit, one directory over from the planned location: the aggregates were routed with the other finding extracts under `v1_main/findings_extracted/` rather than into `v0_5_pilot/`. Companion narrative: `v1_pilot_cross_profile/findings.md`. |

Related, for completeness: the `GITHUB_DEPOSIT_PLAN.md` v0_5_pilot tree also
sketches `adapter_manifests/` and `authlab_run_001/` as subdirectories; those
files were deposited flat inside `replication_package/v0_5_pilot/logs/`
(`adapter_manifest_*.json`, `AUTHLAB-RUN-001_*.json`) rather than in
subdirectories — present, just not at the sketched paths (see
`replication_package/v0_5_pilot/README.md`).

Broader "what cannot be replicated at all" boundaries (SME pool, upstream
ablation builds, etc.) are in `docs/KNOWN_GAPS.md`; frozen-artifact label
errata are in `docs/ERRATA.md`.
