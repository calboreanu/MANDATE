# Handoff 07c Report: Source-First Corpus Authoring

**Codex session:** Handoff 07c intel candidate generation under PI override
**Eval host:** lattice-ws01
**Date:** 2026-06-03
**Wall clock:** 40 minutes

## Verdict

PROCEED

## Evidence

- pypdf installed:                       6.12.2
- per-domain URLs fetched / failed:      sec=7/0, fin=8/1, int=3/7
- per-domain chunks indexed:             sec=2512, fin=1228, int=208
- candidates generated per (dom x cat):  9 files, totals fin_full=25, fin_gap=25, fin_stretch=25, int_full=25, int_gap=25, int_stretch=25, sec_full=25, sec_gap=25, sec_stretch=25
- dedup kept / in / dropped:             183/225/42
- leakage threshold:                     0.85
- leakage overlap rate:                  0.00%
- leakage halt triggered:                no
- every candidate has derived_from:      yes
- Anthropic model used:                  claude-opus-4-6
- Anthropic input tokens (total):        54886
- Anthropic output tokens (total):       19581
- estimated API cost (USD):              $0.76

## Failed URLs

- {url: "https://fasb.org/page/showpdf?path=ASU2014-09.pdf", reason: "financial_reporting / FASB Topic 606 Revenue from Contracts with Customers (public summary): fetch failed: <HTTPError 403: 'Forbidden'>"}
- {url: "https://www.jcs.mil/Portals/36/Documents/Doctrine/pubs/jp2_0.pdf", reason: "intelligence_collection_tasking / DoD Joint Publication 2-0 (Joint Intelligence): fetch failed: <HTTPError 403: 'Forbidden'>"}
- {url: "https://www.jcs.mil/Portals/36/Documents/Doctrine/pubs/jp2_01.pdf", reason: "intelligence_collection_tasking / DoD Joint Publication 2-01 (Joint and National Intelligence Support to Military Operations): fetch failed: <HTTPError 403: 'Forbidden'>"}
- {url: "https://www.jcs.mil/Portals/36/Documents/Doctrine/pubs/jp2_01_3.pdf", reason: "intelligence_collection_tasking / DoD Joint Publication 2-01.3 (Joint Intelligence Preparation of the Operational Environment): fetch failed: <HTTPError 403: 'Forbidden'>"}
- {url: "https://www.cia.gov/static/Tradecraft-Primer-apr09.pdf", reason: "intelligence_collection_tasking / CIA: A Tradecraft Primer (Structured Analytic Techniques for Improving Intelligence Analysis): fetch failed: <HTTPError 404: 'Not Found'>"}
- {url: "https://www.cia.gov/static/9a5f1162fd0932c29bfed1c030edf4ae/Pyschology-of-Intelligence-Analysis.pdf", reason: "intelligence_collection_tasking / CIA: Psychology of Intelligence Analysis (Richards J. Heuer): fetch failed: <HTTPError 404: 'Not Found'>"}
- {url: "https://www.intelligence.gov/what-the-ic-does", reason: "intelligence_collection_tasking / ODNI intelligence.gov: What the IC Does (HTML): fetch failed: <HTTPError 404: 'Not Found'>"}
- {url: "https://www.gao.gov/products/gao-21-104450", reason: "intelligence_collection_tasking / GAO Report: Intelligence Community Information Sharing: fetch failed: <HTTPError 403: 'Forbidden'>"}

## Anything the PI must decide before proceeding

- review the source-first deduped pool at 03_corpus/pilot/candidates_with_sources.jsonl
- select 6 candidates (2 per domain) and write 03_corpus/pilot/pilot_selection.json (Handoff 06 then runs)

## Deviations from this handoff

- Skipped Tasks 1 and 2 per 07c scope; resumed from the 208-chunk intel index built in 07b.
- Resumed from 07b under PI override: used `ODNI Annual Threat Assessment 2024 (Unclassified)`, `ODNI Annual Threat Assessment 2025 (Unclassified)`, and `ODNI intelligence.gov: How the IC Works (HTML)` as the three intel sources.
- Removed stale `03_corpus/candidates_source_first/candidates_deduped.jsonl` before Task 4 so dedup read the intended nine source files only.
- Anthropic token totals and cost are for the 07c intel generation only; security and finance candidates were unchanged from Handoff 07. The corpus CLI does not persist response usage, so token totals were reconstructed with Anthropic `messages.count_tokens` from the exact deterministic source-conditioned prompts and saved candidate text.
