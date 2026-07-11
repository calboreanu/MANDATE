# Handoff 07 Report: Source-First Corpus Authoring

**Codex session:** Handoff 07 source-first corpus authoring
**Eval host:** lattice-ws01
**Date:** 2026-06-03
**Wall clock:** 105 minutes

## Verdict

PROCEED

## Evidence

- pypdf installed:                       6.12.2
- per-domain URLs fetched / failed:      sec=7/0, fin=8/1, int=1/7
- per-domain chunks indexed:             sec=2512, fin=1228, int=1551
- candidates generated per (dom x cat):  9 files, totals fin_full=25, fin_gap=25, fin_stretch=25, int_full=25, int_gap=25, int_stretch=25, sec_full=25, sec_gap=25, sec_stretch=25
- dedup kept / in / dropped:             189/225/36
- leakage threshold:                     0.85
- leakage overlap rate:                  0.00%
- leakage halt triggered:                no
- every candidate has derived_from:      yes
- Anthropic model used:                  claude-opus-4-6
- Anthropic input tokens (total):        169293
- Anthropic output tokens (total):       58244
- estimated API cost (USD):              $2.30

## Failed URLs

- {url: "https://fasb.org/page/showpdf?path=ASU2014-09.pdf", reason: "financial_reporting / FASB Topic 606 Revenue from Contracts with Customers (public summary): fetch failed: <HTTPError 403: 'Forbidden'>"}
- {url: "https://www.dni.gov/files/documents/ICD/ICD%20203%20Analytic%20Standards.pdf", reason: "intelligence_collection_tasking / ODNI ICD 203 (Analytic Standards): fetch failed: <HTTPError 404: 'Not Found'>"}
- {url: "https://www.dni.gov/files/documents/ICD/ICD%20204%20National%20Intelligence%20Priorities%20Framework.pdf", reason: "intelligence_collection_tasking / ODNI ICD 204 (National Intelligence Priorities Framework): fetch failed: <HTTPError 404: 'Not Found'>"}
- {url: "https://www.dni.gov/files/documents/ICD/ICD%20208%20-%20Maximizing%20the%20Utility%20of%20Analytic%20Products.pdf", reason: "intelligence_collection_tasking / ODNI ICD 208 (Maximizing the Utility of Analytic Products): fetch failed: <HTTPError 404: 'Not Found'>"}
- {url: "https://irp.fas.org/doddir/dod/jp2_0.pdf", reason: "intelligence_collection_tasking / DoD Joint Publication 2-0 (Joint Intelligence): extract failed: EmptyFileError('Cannot read an empty file')"}
- {url: "https://irp.fas.org/doddir/dod/jp2_01.pdf", reason: "intelligence_collection_tasking / DoD Joint Publication 2-01 (Joint and National Intelligence Support to Military Operations): extract failed: EmptyFileError('Cannot read an empty file')"}
- {url: "https://crsreports.congress.gov/product/pdf/R/R45175", reason: "intelligence_collection_tasking / CRS Report on the Intelligence Community: fetch failed: <HTTPError 403: 'Forbidden'>"}
- {url: "https://www.dni.gov/files/ODNI/documents/National_Intelligence_Strategy_2023.pdf", reason: "intelligence_collection_tasking / ODNI National Intelligence Strategy: fetch failed: <HTTPError 404: 'Not Found'>"}

## Anything the PI must decide before proceeding

- review the source-first deduped pool at 03_corpus/pilot/candidates_with_sources.jsonl
- select 6 candidates (2 per domain) and write 03_corpus/pilot/pilot_selection.json (Handoff 06 then runs)
- review the failed URL list and confirm the reduced intelligence-source coverage is acceptable for pilot selection

## Deviations from this handoff

- Cleaned only generated output files under `rag/sources/<domain>/`, the three domain indexes, and `rag/embeddings/build_report.json` before rerunning Task 2, because stale `.txt` files already present in those generated-output directories would otherwise have been indexed alongside the curated source fetches.
- The corpus CLI records `source_model` and `derived_from` but does not persist Anthropic response usage. Token totals were reconstructed with Anthropic `messages.count_tokens` from the exact deterministic source-conditioned prompts and saved candidate text; estimated cost uses Claude Opus 4.6 base pricing.
