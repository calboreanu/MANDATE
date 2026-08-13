# HANDOFF_19 Stage 3 Cond-A Report

## Verdict

PROCEED

## Scope

Stage 3 Cond-A only: source-grounded structured extraction into canonical MLT MANDATE deterministic planning.

Cond-A main resumed from the 68-record checkpoint created by the prior throughput halt. Cond-A holdout then ran as the separate 300-record holdout leg. Cond-B remains pending and should run with `--domain-profile-mode auto` per HANDOFF_19d.

## Code Changes Applied Before Completion

- Commit `5adb04b6`: `run-cond-a` and `run-cond-b` now honor `--max-workers` with bounded per-record concurrency while preserving per-record checkpointing.
- Commit `dafbdfcf`: opt-in `--domain-profile-mode {default,auto}` added. Default mode preserves pre-HANDOFF_19d behavior. Auto mode maps `INT -> defense_intel`, `SEC -> incident_response`, and `FIN -> None`.
- Tests: `305 passed, 1 skipped`.

## Cond-A Main Results

- Output directory: `07_system_outputs/cond_a/`
- Records: `1200`
- Unique run IDs: `1200`
- Ok: `1200`
- Not ok: `0`
- Any LLM fallback: `0`
- Domain split: `FIN=400`, `INT=400`, `SEC=400`
- API cost: `$32.135550`
- Mean wall clock per record: `27414 ms`
- Max wall clock: `97432 ms`
- Ledger normalized to active records: `1200` lines

COA count distribution:

- `1 COA`: `255`
- `2 COAs`: `925`
- `3 COAs`: `20`

Approach text distribution across all main COAs:

- `1200`: `Aggressive multi-vector approach with parallel execution`
- `945`: `Conservative reconnaissance and scanning without exploitation`
- `20`: `Moderate approach with targeted exploitation of confirmed vulnerabilities`

## Cond-A Holdout Results

- Output directory: `07_system_outputs/cond_a/holdout/`
- Records: `300`
- Unique run IDs: `300`
- Ok: `300`
- Not ok: `0`
- Any LLM fallback: `0`
- Domain split: `SES=300`
- API cost: `$8.239410`
- Mean wall clock per record: `33960 ms`
- Max wall clock: `379309 ms`
- Ledger: `300` lines

COA count distribution:

- `1 COA`: `62`
- `2 COAs`: `217`
- `3 COAs`: `21`

Approach text distribution across all holdout COAs:

- `300`: `Aggressive multi-vector approach with parallel execution`
- `238`: `Conservative reconnaissance and scanning without exploitation`
- `21`: `Moderate approach with targeted exploitation of confirmed vulnerabilities`

## DomainProfile Selection

Cond-A domain profile selection: `default` (canonical `None` / pentest-flavored fallback). The HANDOFF_19d patch added opt-in `--domain-profile-mode auto` mapping for use in subsequent conditions.

The Cond-A main and holdout records were generated under coherent default-DomainProfile behavior. The profile metadata fields introduced by HANDOFF_19d are absent from these already-running default-mode records because the Cond-A processes were launched before the patch loaded.

## Throughput Gate

The prior false-positive throughput halt was corrected by making `--max-workers 5` real. The resumed main run cleared the revised catastrophic-only gate decisively:

- Starting checkpoint: `68` records
- At approximately 27 minutes: `383` records total, `315` new records since checkpoint
- Revised gate: fewer than `30` new records after `30` minutes

No Cond-A cost ceiling fired. Combined main + holdout Cond-A API cost was `$40.374960`, below the `$50` Cond-A escalation threshold.

## Deviations

- The executable throughput gate was not present in apparatus code; it was a handoff/operator threshold. No code patch was needed for that threshold beyond documenting the revised interpretation here.
- The Cond-A records intentionally remain on default DomainProfile behavior to avoid mixing profile-selection logic within a condition. HANDOFF_19d enables `auto` only for Cond-B and future v2.1 comparisons.

## Next Step

Run Cond-B main and holdout with `--domain-profile-mode auto`, `--max-workers 5`, and `--skip-existing`, after an Anthropic probe passes.
