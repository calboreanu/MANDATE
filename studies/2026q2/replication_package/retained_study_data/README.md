# Retained study data

This directory is part of MANDATE study release `2026.08.13`. It restores raw
testing depth that remained in the cloud-optimized source evaluation tree but
was omitted from the earlier curated repository package.

It is not a separate result or a separate study phase. Its components include:

- the three retained per-judge streams for the 12,000-record full-coverage
  grading campaign;
- the retained sampled grading streams and double-grade evidence;
- retained partial perturbation-judge streams.

The source tree also retains per-record and anonymized grading inputs plus
baseline perturbation outputs omitted from the earlier curated deposit. Those
directory-backed cloud placeholders are enumerated in
`code/scripts/package_retained_study_data.py`; they are not claimed present in
this component until materialization and packaging complete.

`manifest.json` records the source-relative path, record count, byte count, and
SHA-256 of every packaged stream. Directory-sourced records additionally carry
their original source-relative path and source-file SHA-256 inside each JSONL
envelope. The packager is `code/scripts/package_retained_study_data.py`.

The historical `v1`, `v2`, and `v3` strings in source paths are immutable
provenance labels. Public reporting treats the repository as one study release
and uses component purpose and implementation version instead.
