# Handoff 07b Report: Source-First Corpus Authoring

**Codex session:** Handoff 07b intel-domain source replacement and rerun
**Eval host:** lattice-ws01
**Date:** 2026-06-03
**Wall clock:** 18 minutes

## Verdict

HALT

## Evidence

- pypdf installed:                       6.12.2
- per-domain URLs fetched / failed:      int=3/7
- per-domain chunks indexed:             int=208
- candidates generated per (dom x cat):  not run; stopped after intel source-build failure threshold
- dedup kept / in / dropped:             not run
- leakage threshold:                     0.85
- leakage overlap rate:                  not run
- leakage halt triggered:                no
- every candidate has derived_from:      not run
- Anthropic model used:                  not run
- Anthropic input tokens (total):        0
- Anthropic output tokens (total):       0
- estimated API cost (USD):              $0.00

## Failed URLs

- {url: "https://www.jcs.mil/Portals/36/Documents/Doctrine/pubs/jp2_0.pdf", reason: "DoD Joint Publication 2-0 (Joint Intelligence): fetch failed: <HTTPError 403: 'Forbidden'>"}
- {url: "https://www.jcs.mil/Portals/36/Documents/Doctrine/pubs/jp2_01.pdf", reason: "DoD Joint Publication 2-01 (Joint and National Intelligence Support to Military Operations): fetch failed: <HTTPError 403: 'Forbidden'>"}
- {url: "https://www.jcs.mil/Portals/36/Documents/Doctrine/pubs/jp2_01_3.pdf", reason: "DoD Joint Publication 2-01.3 (Joint Intelligence Preparation of the Operational Environment): fetch failed: <HTTPError 403: 'Forbidden'>"}
- {url: "https://www.cia.gov/static/Tradecraft-Primer-apr09.pdf", reason: "CIA: A Tradecraft Primer (Structured Analytic Techniques for Improving Intelligence Analysis): fetch failed: <HTTPError 404: 'Not Found'>"}
- {url: "https://www.cia.gov/static/9a5f1162fd0932c29bfed1c030edf4ae/Pyschology-of-Intelligence-Analysis.pdf", reason: "CIA: Psychology of Intelligence Analysis (Richards J. Heuer): fetch failed: <HTTPError 404: 'Not Found'>"}
- {url: "https://www.intelligence.gov/what-the-ic-does", reason: "ODNI intelligence.gov: What the IC Does (HTML): fetch failed: <HTTPError 404: 'Not Found'>"}
- {url: "https://www.gao.gov/products/gao-21-104450", reason: "GAO Report: Intelligence Community Information Sharing: fetch failed: <HTTPError 403: 'Forbidden'>"}

## What changed since Handoff 07

- DoD Joint Publication 2-0 (Joint Intelligence) | https://www.jcs.mil/Portals/36/Documents/Doctrine/pubs/jp2_0.pdf | pdf | tier 1
- DoD Joint Publication 2-01 (Joint and National Intelligence Support to Military Operations) | https://www.jcs.mil/Portals/36/Documents/Doctrine/pubs/jp2_01.pdf | pdf | tier 1
- DoD Joint Publication 2-01.3 (Joint Intelligence Preparation of the Operational Environment) | https://www.jcs.mil/Portals/36/Documents/Doctrine/pubs/jp2_01_3.pdf | pdf | tier 1
- CIA: A Tradecraft Primer (Structured Analytic Techniques for Improving Intelligence Analysis) | https://www.cia.gov/static/Tradecraft-Primer-apr09.pdf | pdf | tier 1
- CIA: Psychology of Intelligence Analysis (Richards J. Heuer) | https://www.cia.gov/static/9a5f1162fd0932c29bfed1c030edf4ae/Pyschology-of-Intelligence-Analysis.pdf | pdf | tier 1
- ODNI Annual Threat Assessment 2024 (Unclassified) | https://www.dni.gov/files/ODNI/documents/assessments/ATA-2024-Unclassified-Report.pdf | pdf | tier 1
- ODNI Annual Threat Assessment 2025 (Unclassified) | https://www.dni.gov/files/ODNI/documents/assessments/ATA-2025-Unclassified-Report.pdf | pdf | tier 1
- ODNI intelligence.gov: How the IC Works (HTML) | https://www.intelligence.gov/how-the-ic-works | html | tier 1
- ODNI intelligence.gov: What the IC Does (HTML) | https://www.intelligence.gov/what-the-ic-does | html | tier 1
- GAO Report: Intelligence Community Information Sharing | https://www.gao.gov/products/gao-21-104450 | html | tier 1
- The prior intel source `NIST SP 800-53 Rev. 5 (control families also relevant to IC systems)` was removed from the intel list before this rerun.

## Anything the PI must decide before proceeding

- More than three of the ten signed-off intel URLs failed (7/10 failed). Decide whether to proceed with the three fetched intel sources or revise the signed-off intel source list and rerun 07b.
- Source-first candidate generation, dedup, leakage, and pilot-pool replacement were not run in this session because the intel source-build failure threshold fired.

## Deviations from this handoff

- Per the 07b scope, skipped Task 1's `pypdf` install and began by removing stale intel generated outputs.
- Stopped after Task 2 because the 07b-specific escalation rule fired: more than three of the ten intel URLs failed.
- The intel-only `source-build` command wrote an intel-only `build_report.json`; I merged the refreshed intel entry into the previously committed security/finance build report entries so the cross-domain report remains intact while leaving security and finance artifacts unchanged.
