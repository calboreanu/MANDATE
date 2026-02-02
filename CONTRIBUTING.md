# Contributing

Thanks for contributing to MANDATE.

## Ways to contribute
- File issues for schema improvements, edge cases, or paper-repo mismatches
- Add example mandates/gap reports and test vectors
- Implement schema-to-policy translators (OPA/Rego, Cedar)
- Improve the hashing + trace integrity tooling

## Development setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Pull request guidelines
- Add/adjust tests for any behavior changes
- Keep schemas backwards compatible when possible (or bump `version`)
- Document changes in `CHANGELOG.md`
