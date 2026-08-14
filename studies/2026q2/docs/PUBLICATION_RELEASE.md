# MANDATE v2.0.1 Publication Evidence

The 2026Q2 study snapshot is included in the single MANDATE v2.0.1 publication
release at repository path `studies/2026q2/`.

## Release identity

- Repository: `https://github.com/calboreanu/MANDATE`
- Publication tag: `v2.0.1`
- Framework version: `2.0.1`
- Study snapshot: `2026.08.13.1`

Historical study tags and commits remain available as provenance anchors. They
do not denote additional current releases.

## Verification gates

From a full checkout at `v2.0.1`:

```bash
cd studies/2026q2
python3 code/scripts/verify_study_release.py
python3 code/scripts/check_claim_map_paths.py
```

The verifier checks the comparative record counts, all 36,000 retained
full-coverage judge records, ensemble reconciliation, measured reliability,
the 3,000-record routing-purpose test, and whole-deposit trace hashes.

## Scope

The public tree supports evidence verification and partial replication. Exact
regeneration of campaign records requires the proprietary components listed in
`docs/EXCLUSIONS.md`. Private reviewer bundles and local recovery archives are
not part of the public release.
