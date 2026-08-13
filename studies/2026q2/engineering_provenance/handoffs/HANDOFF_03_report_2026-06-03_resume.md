# Handoff 03 Report: Main Corpus Authoring Resume

**Codex session:** Handoff 03 resume after Anthropic credit replenishment
**Eval host:** lattice-ws01
**Date:** 2026-06-03
**Wall clock:** 55 minutes

## Verdict

PROCEED

## Evidence

- per-domain URLs fetched / failed:      sec=7/0, fin=8/1, int=3/7 (Task 2 source-build skipped by PI directive; intel failures documented from Handoffs 07/07b/07d)
- per-domain failure rate:               sec=0.00%, fin=11.11%, int=70.00% (intel threshold explicitly overridden for this session)
- per-domain chunks indexed:             sec=2512, fin=1228, int=211
- candidates generated per (dom x cat):  9 files, totals fin_full=30, fin_gap=30, fin_stretch=30, int_full=30, int_gap=30, int_stretch=30, sec_full=30, sec_gap=30, sec_stretch=30
- dedup kept / in / dropped:             262/270/8
- per-domain kept:                       sec=87, fin=89, int=86
- leakage threshold:                     0.85
- leakage overlap rate:                  0.00%
- leakage halt triggered:                no
- every candidate has derived_from:      yes
- Anthropic model used:                  claude-opus-4-6
- Anthropic input tokens (total):        199872
- Anthropic output tokens (total):       71338
- estimated API cost (USD):              $2.78

## Documented limitation

Intel-domain candidates are derived from three IC-specific primary sources (ODNI Annual Threat Assessment 2024 and 2025; intelligence.gov "How the IC Works"). Seven additional intel URLs (JCS Joint Publications 2-0, 2-01, 2-01.3; CIA Tradecraft Primer and Psychology of Intelligence Analysis; intelligence.gov "What the IC Does"; GAO IC information-sharing report) returned 403 or 404 from the eval host's network across Handoff 07, 07b, and 07d, with both the academic-identifying and the bare Chrome User-Agent. The manual-ingest pathway is available in the apparatus (apparatus.corpus.cli ingest-manual) for future expansion via PI-downloaded PDFs; the main corpus proceeds without it. Reviewer-visible note required in the methods section.

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

- review the main candidate pool at 03_corpus/main/candidates_main.jsonl
- select 40 per domain (approximately 14 per category) and write 03_corpus/main/main_selection.json
- run the SME realism audit on the selected 120 tasks
- after the realism audit passes, tag corpus_freeze_v1

## Deviations from this handoff

- Resumed from Handoff 03 HALT commit `e8bb2a4`; did not regenerate the five completed 30-candidate files already present in `03_corpus/candidates_source_first_main/`.
- Skipped Tasks 1 and 2 per the PI's Handoff 03 resumption directive: the open precondition was closed by Option A, and source-build was not run.
- The 30%-failure-per-domain escalation rule was explicitly overridden for the intel domain by PI directive. The 70% intel source-fetch limitation remains reviewer-visible.
- Ran only the four missing source-generation calls with the original seed sequence: `financial_reporting/stretch_case` seed `20260608`, `intelligence_collection_tasking/full_specification` seed `20260609`, `intelligence_collection_tasking/gap_triggering` seed `20260610`, and `intelligence_collection_tasking/stretch_case` seed `20260611`.
- The corpus CLI records `source_model` and `derived_from` but does not persist Anthropic response usage. Token totals were reconstructed with Anthropic `messages.count_tokens` from the deterministic source-conditioned prompts and saved candidate text; estimated cost uses Claude Opus 4.6 base pricing.
- Did not run PI selection, SME realism audit, `corpus_freeze_v1` tagging, baseline calibration, perturbation generation, or system runs on study data.
