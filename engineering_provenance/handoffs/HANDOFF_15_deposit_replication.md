# Codex Handoff 15: Final Report and Replication Package Deposit

**For:** Codex (eval host) + PI manual steps
**From:** Lead Analyst
**Date:** 2026-06-03
**Estimated wall clock:** 4 to 8 hours (mostly PI manuscript work; the package build is minutes).
**Blocked on:** Phase 9 PROCEED, final report draft accepted, PI sign-off.

## Mission

Assemble the deposited replication package per PROTOCOL_LOCK Section 16: every freeze tag, every result JSON, every figure, every notebook in its executed state, the deviation log, the run ledgers, the anonymization mapping (sealed and unreleased until deposit), the corpus and ground truth at their frozen tags, the apparatus source at its commit. Deposit on Zenodo. Submit the final paper.

**Definition of done.** A `11_replication_package/` directory tarball deposited on Zenodo with its DOI captured in `_package/PREREGISTRATION_TEMPLATE.md`. Final report markdown finalized. Deviation log signed. Every TO_FILL row RESOLVED.

## Tasks (apparatus side)

```zsh
cd "$HOME/Desktop/MANDATE Evaluation/mandate_eval_2026Q2"
source .venv/bin/activate

mkdir -p 11_replication_package
# Assemble: the apparatus source at its commit, the executed notebooks,
# the result JSONs, the deviation log, the corpus and ground truth at
# their frozen tags. The seed_corpus from AEGIS-eval is included as
# provenance. The anonymization mapping is INCLUDED post-deposit because
# the protocol's anonymization sealed period is the grading phase only.

cp -r 03_corpus 04_ground_truth 06_perturbations 09_analysis \
      10_report _package handoffs setup apparatus \
      11_replication_package/
cp 00_preregistration/provenance_evidence.md \
   00_preregistration/provenance_pip_freeze.txt \
   11_replication_package/
cp AEGIS-eval/_AEGIS_EVAL_README.txt 11_replication_package/AEGIS_EVAL_PROVENANCE.txt

# A small README naming the deposit
cat > 11_replication_package/README.md <<'EOF'
# MANDATE 2026Q2 Empirical Evaluation: Replication Package

Frozen artifacts, scripts, and notebooks supporting the deposited paper.
See `_package/PREREGISTRATION_TEMPLATE.md` for the pre-registration record
and `10_report/deviation_log.md` for every departure from the deposited
protocol. The AEGIS source under evaluation is at git tag
`mandate-eval-primary-2026q2-v1` (commit 4f8af83); recreate with the
recipe in `setup/recreate_aegis_eval.sh`.
EOF

tar czf 11_replication_package_v1.tar.gz 11_replication_package/
shasum -a 256 11_replication_package_v1.tar.gz > \
  11_replication_package_v1.sha256
```

## PI manual steps

Deposit `11_replication_package_v1.tar.gz` on Zenodo. Capture the DOI. Update `_package/PREREGISTRATION_TEMPLATE.md` header with the deposit DOI and date. Sign the deviation log. Submit the paper to its target venue.

## Report

`handoffs/HANDOFF_15_report_<YYYY-MM-DD>.md` with: Zenodo DOI, replication package SHA-256, final TO_FILL state, deviation log row count, paper submission status. Final commit `Handoff 15: deposit and paper submission`. Tag the repo at `study_deposit_v1`.
