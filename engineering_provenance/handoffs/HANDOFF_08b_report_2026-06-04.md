# Handoff 08b Report: Hold-out corpus (software_engineering_specification)

**Codex session:** desktop session
**Eval host:** lattice-ws01
**Date:** 2026-06-04
**Wall clock:** ~20 minutes

## Verdict

PROCEED

## Evidence

- registry gap closed (precondition):       yes
- SE-domain URLs fetched / failed:          7/2
- candidates generated per (category):      15/15/15
- dedup kept / in / dropped:                44/45/1
- leakage threshold:                        0.85
- leakage overlap rate:                     0.00%
- leakage halt triggered:                   no
- every candidate has derived_from:         yes
- Anthropic model used:                     claude-opus-4-6
- Anthropic input tokens (total):           not recorded by current `source-generate` output
- Anthropic output tokens (total):          not recorded by current `source-generate` output
- estimated API cost (USD):                 not recorded by current `source-generate` output

## Failed URLs

- `https://www.gao.gov/products/gao-21-105313` — `fetch failed: <HTTPError 404: 'Not Found'>`
- `https://insights.sei.cmu.edu/library/architecture-centric-engineering/` — `fetch failed: <HTTPError 404: 'Not Found'>`

## Anything the PI must decide before proceeding

- Review the deduped pool at `03_corpus/holdout/candidates_holdout.jsonl` and select 30 candidates for the hold-out task set.

## Deviations from this handoff

- The two 404 fetch failures were not retried because they were persistent client-side not-found responses, not transient HTTP/5xx errors.
- Token usage and API cost are unavailable because `apparatus.corpus.cli source-generate` discards the `LLMResponse` usage fields returned by the Anthropic client instead of persisting them into candidate files or reports.
- The registry-fix files (`apparatus/corpus/prompts.py`, `apparatus/corpus/tests/test_corpus.py`) are included in this handoff commit so the precondition remains reproducible from the project record.
