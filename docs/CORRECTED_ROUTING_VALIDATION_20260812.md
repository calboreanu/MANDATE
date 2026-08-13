# Successor implementation routing-contract check — 2026-08-12

This is a focused component of study release `2026.08.13`, not a separate
result or release. Historical source paths and identifiers are retained below
where necessary for exact provenance.

## Decision

The 3,000-record focused check passes its contract requirements. Its purpose is
to determine whether the committed `1.0.3`-derived successor implementation
routes blocking or insufficient-for-automation specifications to explicit
non-executable states. It is not evidence of an exact same-prompt replay of the
evaluated `1.0.0rc1` implementation.

## Independent validation

The originator return ZIP tested clean, and all 3,495 entries in its package
checksum manifest verified. The six evaluated-build corpus files already in this
repository match the preflight hashes exactly. Independent inspection then
confirmed:

- exactly 1,200 main and 300 holdout records per condition;
- exact task, run-number, and recorded schedule identity between the evaluated
  build and the successor check;
- runs 1–10 and seeds `20260624`–`20260633` for every task;
- 2,999 raw gap sets carrying a blocking or insufficient signal;
- zero executable observations among those 2,999 records;
- 3,000 artifacts and 18,000 trace entries, with entry, parent, chain,
  anchor, and artifact-output hashes intact;
- all 10,513 reservation IDs matched exactly once between record evidence
  and ledger settlements;
- 157 fallback observations, all in Cond-B and all non-executable;
- zero live-looking Anthropic keys in the delivered archive.

The single executable record,
`cond_b__TASK-MAIN-FIN-003__r07`, has 19 nonblocking gap reports. It is outside
the primary denominator by the committed predicate and must be disclosed
separately.

## Cost and attempt corrections

The as-received documentation labels USD 191.388447 as the exact total in one
deliverable table. That value is the full-campaign ledger total. Cumulative
authorized accounting is:

| Component | USD |
|---|---:|
| Prior smoke/probe accounting | 0.749967 |
| Full campaign | 191.388447 |
| Cumulative | 192.138414 |
| Remaining under USD 300 | 107.861586 |

The analyzer's `provider_call_count=10503` is also a response-object count,
not an attempt count. Ledger evidence establishes 10,510 response-received
attempts plus three dispatch-uncertain conservative settlements. The thirteen
attempts beyond the nominal schedule cost USD 0.421476 and are already
included in the campaign ledger.

These are reporting corrections. They do not change any routing outcome,
denominator, cost debit, or record.

## Claim boundary

Purpose-bounded reporting language:

> In a generation-only contract-conformance check of the committed
> 1.0.3-derived successor implementation, using the frozen 150-task corpus and
> original recorded 10-run schedule, all 2,999 records carrying unresolved
> blocking or insufficient-for-automation signals routed to explicit
> non-executable states; zero such records were marked executable.

Do not say that every record with any gap was non-executable, that all 3,000
records were non-executable, or that the run used a recovered and hash-matched
copy of the original rc1 prompts.
