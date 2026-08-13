# Partial Replication Guide (no cluster required)

Four tiers, cheapest first. Tier 1 requires nothing but this repository.

## Tier 1 — Read-only verification ($0, minutes)
The consolidated JSONL files *are* the evidence. Every quantitative claim maps
to a file via `docs/CLAIM_TO_DATA_MAP.md`; the README Quickstart shows count
verifications. Verbatim failure samples (Intake tripwire, Binding refusals)
are in `replication_package/v1_main/findings_extracted/` for byte-level
comparison against the supplement text.

## Tier 2 — Re-grade frozen outputs (~$50–200 API, hours)
Re-run the three-judge ensemble over the anonymized frozen outputs and compare
against `v1_main/grading/v2_full_coverage/ensemble_scores.jsonl`.
Code: `code/apparatus` (grading modules) with `code/scripts/`. Requires
Anthropic + OpenAI + Google API keys. Judge model versions are pinned in
`v1_main/grading/v1_sampled/judges_config.json`; provider-side model drift is
a documented temporal-validity threat (supplement Threats §), so expect
agreement within tolerance rather than byte-identity.

## Tier 3 — Re-run baselines on the frozen corpus (~$500–2,000 per baseline)
Regenerate B1–B6 RunRecords from `v1_main/corpus/main_tasks.jsonl` using the
baseline shells in `code/apparatus`. Compare structural fields (ok, trace
length, schema validity) against the shipped `baseline_*_main.jsonl`.
Note B4–B6 are implementation-pattern shells sharing one LLM, not literal
framework installations (documented in the supplement and Deviation record).

## Tier 4 — Full replication including fine-tunes (cluster, multi-day)
Reproduce the six LoRA role specialists (manifests in
`replication_package/v0_5_pilot/logs/adapter_manifest_*.json`) and serve via
Ollama per `docs/ENVIRONMENT.md`. This is documented for completeness and is
not the expected reviewer path.

## Resuming Phase B (optional, ~$1,350 at 2026-07 Opus-tier prices)
The paused perturbation grading resumes without regeneration:
`grade-v2 --skip-existing` against the frozen perturbation records on the
evaluation tree (B1–B3 at 3,500 each; B4 partial at 3,021 — available from
the maintainer on request). Completed grades in `v2_complete/grading_v2/`
are stable under resume.
