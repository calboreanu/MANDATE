# MANDATE v2 Release Status

MANDATE 2.0.4 is the publication release represented by this repository.

## Included

- mandate-as-code, gap-report, trace-entry, and result-envelope schemas;
- an explicit fail-closed execution-state contract;
- a six-stage reference pipeline;
- constraint parsing and Rego/Cedar translation;
- RFC 8785 canonicalization and hash verification;
- evaluation, metrics, and success-registry utilities;
- examples, tests, and command-line tools; and
- the 2026Q2 empirical evidence and verification package.

## Validation

The framework test suite is run with `pytest`. The deposited empirical evidence
is checked with:

```bash
python3 studies/2026q2/code/scripts/verify_study_release.py
```

## Boundaries

This release does not provide a tool-execution runtime, downstream policy
enforcement, runtime monitoring, the proprietary campaign model-serving stack,
or the locally fine-tuned models used by one evaluated condition. These
boundaries are described in the study replication documentation.

Future work is tracked through GitHub issues rather than embedded planning
notes in the publication release.
