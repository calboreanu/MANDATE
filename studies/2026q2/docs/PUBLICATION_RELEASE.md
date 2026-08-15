# MANDATE v2.0.9 Publication Evidence

The 2026Q2 study snapshot is included in the single MANDATE v2.0.9 publication
release at repository path `studies/2026q2/`.

## Release identity

- Repository: `https://github.com/calboreanu/MANDATE`
- Publication tag: `v2.0.9`
- Framework version: `2.0.9`
- Study snapshot: `2026.08.13.1`

Historical study tags and commits remain available as provenance anchors. They
do not denote additional current releases.

## Verification gates

From a full checkout at `v2.0.9`:

```bash
cd studies/2026q2
python3 code/scripts/verify_study_release.py
python3 code/scripts/check_claim_map_paths.py
shasum -a 256 -c EVIDENCE_SHA256SUMS.txt
```

The verifier checks the comparative record counts, all 36,000 retained
full-coverage judge records, ensemble reconciliation, measured reliability,
the evaluated-build gap census, the 3,000-record routing-purpose test,
trace hashes for the declared 2026Q2 source-of-record families, and the
SHA-256 manifest covering every file under
`replication_package/`.

The GitHub Release additionally publishes a deterministic source archive and
its SHA-256 digest. It is constructed from the tagged tree with
`git archive --format=tar --prefix=MANDATE-v2.0.9/ v2.0.9 | gzip -n`; the
digest asset authenticates the downloaded archive with SHA-256 rather than
relying on the repository's SHA-1-format Git object name as a cryptographic
strength claim.

## Scope

The public tree supports evidence verification and partial replication. Exact
regeneration of campaign records requires the proprietary components listed in
`docs/EXCLUSIONS.md`. Private reviewer bundles and local recovery archives are
not part of the public release.
