# Contributing

Thanks for contributing to MANDATE.

## Ways to contribute

- File issues for schema defects, edge cases, or paper-to-repository mismatches.
- Add example mandates, gap reports, and canonicalization test vectors.
- Improve validation, policy translation, and trace-integrity tooling.
- Add interoperable integrations without changing the fail-closed result
  contract.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Pull request guidelines

- Add or adjust tests for behavior changes.
- Keep schemas backward-compatible when possible; otherwise bump the semantic
  version and document the migration.
- Record user-visible changes in `CHANGELOG.md`.
