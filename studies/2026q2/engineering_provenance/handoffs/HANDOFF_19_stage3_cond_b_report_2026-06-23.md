# HANDOFF_19 Stage 3 Cond-B Report - 2026-06-23

## Verdict

PROCEED

## Scope

Stage 3 Cond-B only: canonical MANDATE with source-aware LLM extraction wrappers, `--domain-profile-mode auto`, and the HANDOFF_19d domain-profile mapping patch in force.

This report closes the Cond-B main and holdout legs after Cond-A had already completed in `handoffs/HANDOFF_19_stage3_cond_a_report_2026-06-23.md`.

## Apparatus State

- Commit `5adb04b6`: `run-cond-a` and `run-cond-b` honor `--max-workers` through bounded per-record concurrency.
- Commit `dafbdfcf`: `--domain-profile-mode {default,auto}` added for canonical-MANDATE conditions.
- Commit `39d1723b`: Cond-A main and holdout complete under default DomainProfile behavior.
- Commit `ad27cf2c`: Cond-B main complete under auto DomainProfile behavior.
- Full apparatus regression after HANDOFF_19d patch: `305 passed, 1 skipped`.

The stale Stage 2c Cond-B pilot artifacts were moved into `07_system_outputs/cond_b/_stage2c_pilot_pre_domain_profile/` before the Stage 3 main run, so `--skip-existing` did not preserve pre-auto/default-profile pilot records in the top-level Cond-B output directory.

## Cond-B Main Results

- Output directory: `07_system_outputs/cond_b/`
- Records: `1200`
- Unique run IDs: `1200`
- Ledger lines: `1200`
- `ok=True`: `1200`
- `ok=False`: `0`
- `schema_valid=False`: `0`
- Domain split: `FIN=400`, `INT=400`, `SEC=400`
- Top-level `any_llm_fallback=True`: `177`
- Fallback roles: `Procedure=177`
- Fallbacks by domain: `FIN=13`, `INT=57`, `SEC=107`
- Mean wall clock per record: `111248 ms`
- Max wall clock: `329687 ms`
- RunRecord `api_cost_usd` sum: `$0.000000`

## Cond-B Holdout Results

- Output directory: `07_system_outputs/cond_b/holdout/`
- Records: `300`
- Unique run IDs: `300`
- Ledger lines: `300`
- `ok=True`: `300`
- `ok=False`: `0`
- `schema_valid=False`: `0`
- Domain split: `SES=300`
- Top-level `any_llm_fallback=True`: `7`
- Fallback roles: `Procedure=7`
- Fallbacks by domain: `SES=7`
- Mean wall clock per record: `112710 ms`
- Max wall clock: `225588 ms`
- RunRecord `api_cost_usd` sum: `$0.000000`

## DomainProfile Mapping Verification

Auto DomainProfile selection matched the HANDOFF_19d mapping:

- `FIN -> None`: `400` main records.
- `INT -> defense_intel`: `400` main records.
- `SEC -> incident_response`: `400` main records.
- `SES -> None`: `300` holdout records.

The `SES` holdout result is expected. HANDOFF_19d only defined explicit mappings for `INT` and `SEC`, with `FIN` intentionally left at `None`; software-engineering holdout tasks therefore remain at `None` under auto mode.

All `1500` Cond-B Stage 3 records include `domain_profile_mode=auto` in `decoding_params`.

## Provider And Throughput

- Anthropic probe passed before the holdout run.
- `logs/HANDOFF_19_stage3_cond_b_main.stderr`: `0` lines.
- `logs/HANDOFF_19_stage3_cond_b_holdout.stderr`: `0` lines.
- No provider-error quarantine was required for the Cond-B main or holdout legs.

The observed Cond-B mean wall-clock time was about `111-113` seconds per record with `--max-workers 5`. This is slower than Cond-A but produced complete output with no hard failures.

## Measurement Notes

The `184` Procedure fallbacks across Cond-B are recorded as data, not as a halt condition:

- Main: `177 / 1200`
- Holdout: `7 / 300`
- Combined: `184 / 1500`

All records remained `ok=True`; no record was marked schema invalid. The fallback concentration is highest in security operations reporting (`107 / 400`) and lowest in financial reporting (`13 / 400`) on the main matrix.

Cond-B RunRecords report `api_cost_usd=0.000000` despite use of the Anthropic backend. Cost accounting for this condition should therefore not be inferred from RunRecord cost fields.

## Artifacts

- Cond-B main: `07_system_outputs/cond_b/` committed in `ad27cf2c`.
- Cond-B holdout: `07_system_outputs/cond_b/holdout/`.
- Stage 2c quarantine: `07_system_outputs/cond_b/_stage2c_pilot_pre_domain_profile/`.
- This report: `handoffs/HANDOFF_19_stage3_cond_b_report_2026-06-23.md`.

## Escalations

None.

## Next Target

Stage 3 is complete for Cond-A and Cond-B across main and holdout pools. Stage 4 / Framing 2 grading and analysis can proceed from the completed condition outputs.
