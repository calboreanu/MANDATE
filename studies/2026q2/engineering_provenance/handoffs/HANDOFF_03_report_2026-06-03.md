# Handoff 03 Report: Main Corpus Authoring

**Codex session:** Handoff 03 main corpus generation under PI Option A
**Eval host:** lattice-ws01
**Date:** 2026-06-03
**Wall clock:** 30 minutes

## Verdict

HALT

## Evidence

- per-domain URLs fetched / failed:      sec=7/0, fin=8/0, int=3/7 (Task 2 source-build skipped by PI directive; intel failures documented from Handoffs 07/07b/07d)
- per-domain failure rate:               sec=0.00%, fin=0.00%, int=70.00% (intel threshold explicitly overridden for this session)
- per-domain chunks indexed:             sec=2512, fin=1228, int=211
- candidates generated per (dom x cat):  5 files, totals security_operations_reporting/full_specification=30, security_operations_reporting/gap_triggering=30, security_operations_reporting/stretch_case=30, financial_reporting/full_specification=30, financial_reporting/gap_triggering=30; missing financial_reporting/stretch_case, intelligence_collection_tasking/full_specification, intelligence_collection_tasking/gap_triggering, intelligence_collection_tasking/stretch_case
- dedup kept / in / dropped:             not run; Task 3 halted before the nine-file pool existed
- per-domain kept:                       not run
- leakage threshold:                     0.85
- leakage overlap rate:                  not run
- leakage halt triggered:                no
- every candidate has derived_from:      yes for the 150 partial candidates generated before halt; not assessed for a complete pool
- Anthropic model used:                  claude-opus-4-6
- Anthropic input tokens (total):        not computed for partial run
- Anthropic output tokens (total):       not computed for partial run
- estimated API cost (USD):              not computed for partial run

## Documented limitation

Intel-domain candidates are derived from three IC-specific primary sources (ODNI Annual Threat Assessment 2024 and 2025; intelligence.gov "How the IC Works"). Seven additional intel URLs (JCS Joint Publications 2-0, 2-01, 2-01.3; CIA Tradecraft Primer and Psychology of Intelligence Analysis; intelligence.gov "What the IC Does"; GAO IC information-sharing report) returned 403 or 404 from the eval host's network across Handoff 07, 07b, and 07d, with both the academic-identifying and the bare Chrome User-Agent. The manual-ingest pathway is available in the apparatus (apparatus.corpus.cli ingest-manual) for future expansion via PI-downloaded PDFs; the main corpus proceeds without it. Reviewer-visible note required in the methods section.

## Failed URLs

- {url: "https://www.jcs.mil/Portals/36/Documents/Doctrine/pubs/jp2_0.pdf", reason: "DoD Joint Publication 2-0 (Joint Intelligence): 403 from eval host across Handoff 07b/07d; PI Option A override accepted three-source intel limitation"}
- {url: "https://www.jcs.mil/Portals/36/Documents/Doctrine/pubs/jp2_01.pdf", reason: "DoD Joint Publication 2-01 (Joint and National Intelligence Support to Military Operations): 403 from eval host across Handoff 07b/07d; PI Option A override accepted three-source intel limitation"}
- {url: "https://www.jcs.mil/Portals/36/Documents/Doctrine/pubs/jp2_01_3.pdf", reason: "DoD Joint Publication 2-01.3 (Joint Intelligence Preparation of the Operational Environment): 403 from eval host across Handoff 07b/07d; PI Option A override accepted three-source intel limitation"}
- {url: "https://www.cia.gov/static/Tradecraft-Primer-apr09.pdf", reason: "CIA: A Tradecraft Primer (Structured Analytic Techniques for Improving Intelligence Analysis): 404 from eval host across Handoff 07b/07d; PI Option A override accepted three-source intel limitation"}
- {url: "https://www.cia.gov/static/9a5f1162fd0932c29bfed1c030edf4ae/Pyschology-of-Intelligence-Analysis.pdf", reason: "CIA: Psychology of Intelligence Analysis (Richards J. Heuer): 404 from eval host across Handoff 07b/07d; PI Option A override accepted three-source intel limitation"}
- {url: "https://www.intelligence.gov/what-the-ic-does", reason: "ODNI intelligence.gov: What the IC Does (HTML): 404/403 from eval host across Handoff 07b/07d; PI Option A override accepted three-source intel limitation"}
- {url: "https://www.gao.gov/products/gao-21-104450", reason: "GAO Report: Intelligence Community Information Sharing: 403 from eval host across Handoff 07b/07d; PI Option A override accepted three-source intel limitation"}

## Anything the PI must decide before proceeding

- Replenish or otherwise fix the Anthropic account balance for the API key in `.env`. Task 3 halted on persistent `anthropic.BadRequestError` 400 responses: "Your credit balance is too low to access the Anthropic API."
- After credits are restored, rerun Handoff 03 from Task 3. Completed partial files are present for five category files, but the main pool is incomplete and dedup/leakage were not run.
- Failed Task 3 categories and request IDs: `financial_reporting/stretch_case` (`req_011CbgceYJRTwEnnhqRwLew1`), `intelligence_collection_tasking/full_specification` (`req_011Cbgceb3sB8kk2L2Z7Zvvq`), `intelligence_collection_tasking/gap_triggering` (`req_011CbgcedKnm5QmYgMc9x3a5`), `intelligence_collection_tasking/stretch_case` (`req_011CbgcefcxDehqJUx5dGZ6H`).
- Once a complete pool exists, review `03_corpus/main/candidates_main.jsonl`, select 40 per domain (approximately 14 per category), write `03_corpus/main/main_selection.json`, run the SME realism audit on the selected 120 tasks, and tag `corpus_freeze_v1` only after the audit passes.

## Deviations from this handoff

- Skipped Tasks 1 and 2 per the PI's Handoff 03 resumption directive: the open precondition was closed by Option A, and source-build was not run.
- The 30%-failure-per-domain escalation rule was explicitly overridden for the intel domain by PI directive. The 70% intel source-fetch limitation remains reviewer-visible.
- Task 3 was executed with the user-specified incrementing seeds (`20260603` through `20260611`) rather than the static seed shown in the original handoff text.
- The shell loop continued after the first Anthropic balance error because the requested command did not set `set -e`; the remaining three categories also failed immediately with the same persistent API balance error. Dedup, leakage, sanity, PI selection, realism audit, freeze tagging, baseline runs, and system runs were not executed.
- The restored intel index contains 211 chunks: 210 from the three PI-accepted intel source texts plus one chunk named `manual/manual_sources_manifest.json`. It was not rebuilt or edited in this session because Task 2 was explicitly skipped.
