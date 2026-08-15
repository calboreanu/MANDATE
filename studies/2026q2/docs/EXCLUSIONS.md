# Replication Exclusions

The publication release contains the evidence required to verify the reported
results, but it does not contain every component required to regenerate every
record. These boundaries do not alter the deposited quantitative evidence.

| Excluded component | Status and consequence |
|---|---|
| Standalone strongest-baseline rule file | No standalone file was executed. The rule is carried in `pre_registration/PROTOCOL_LOCK.md`. |
| Six-case `authorized_lab` pilot corpus | Proprietary upstream AEGIS input, available to reviewers on request. The 15 raw cross-profile output logs and extracted aggregates are deposited. |
| Upstream `ab_evaluation.py` pilot script | Proprietary AEGIS apparatus, available on request. Its output logs and deterministic aggregate extract are deposited. |
| Exact evaluated `mlt-stack 1.0.0rc1` | Proprietary campaign core, available to reviewers on request. It is required for byte-faithful Cond-A/Cond-B regeneration. |
| MANDATE-primary AEGIS tree and six local fine-tunes | Proprietary campaign assets, available to reviewers on request. They are required to regenerate MANDATE-primary records. |
| Corrected core at `c0b58fb…` | Available to reviewers on request. The public deposit includes its patch provenance, tests, outputs, and analyzer results. |
| Raw per-judge records beyond the retained streams | Not claimed. The release contains all 36,000 full-coverage judge records and the retained partial perturbation streams listed in `replication_package/retained_study_data/`. |
| Rejected task candidates and final accept/reject rationale | The release contains the selected 120/30 corpus, source-balance counts, and selection code, but not the complete 262/44 candidate pools or an auditable author decision log. Final author selection cannot be reconstructed. |

The cross-profile aggregate file is deposited at
`replication_package/v1_main/findings_extracted/v1_pilot_cross_profile/profile_aggregates.json`.
The corresponding raw logs are under `replication_package/v0_5_pilot/logs/`.

See `docs/KNOWN_GAPS.md` for methodological limitations and `docs/ERRATA.md`
for frozen-artifact label corrections.
