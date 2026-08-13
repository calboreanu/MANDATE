# engineering_provenance/ — Internal Record

**Reviewers can skip this directory.** Nothing here is required to verify or
replicate the results; it exists for engineering transparency.

- `handoffs/` — the full 119-file handoff chronology between the lead analyst
  and the evaluation host (specs, reports, status JSONs) from corpus authoring
  through the 2026-07-08 closeout. The chronology is the audit trail for how
  every deviation (D-01–D-13) arose and was executed. Key closeout artifacts:
  `HANDOFF_24_phase_b_status.json` (final state machine),
  HANDOFF_24b/24c (Phase B parallelization + baseline 5/6 scope-out).
- `cost_log/` — per-phase and per-handoff API cost attestation
  (`cost_ledger.md` + machine-readable CSV/JSON), including the 2026-07-08
  closeout addendum documenting the Sonnet-priced projection error, the ~5×
  Opus per-grade correction, record-summed generation actuals ($648.29
  logged for Phase B generation), and the D-12/D-13 budget decisions.

Additional working audits and review documents that predate the deposit's
curated audit set are archived outside the repository (see
DEPOSIT_MAPPING.md consolidation addendum).

The 2026-08-12 corrected-routing campaign has a self-contained provenance
surface at `replication_package/v3_corrected_routing/provenance/`. It includes
the preflight manifest, source-verification report, apparatus and external
mlt-stack patches, test evidence, repair audits, cost authorization, and final
status. The complete return package is preserved byte-for-byte in the adjacent
`archive/` directory.
