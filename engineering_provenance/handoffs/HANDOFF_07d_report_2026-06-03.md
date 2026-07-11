# Handoff 07d Report: Source-First Corpus Authoring

**Codex session:** Handoff 07d User-Agent diagnostic intel source-build
**Eval host:** lattice-ws01
**Date:** 2026-06-03
**Wall clock:** 8 minutes

## Verdict

HALT

## Evidence

- pypdf installed:                       6.12.2
- per-domain URLs fetched / failed:      int=0/10
- per-domain chunks indexed:             int=0
- candidates generated per (dom x cat):  not run; diagnostic source-build only
- dedup kept / in / dropped:             not run
- leakage threshold:                     0.85
- leakage overlap rate:                  not run
- leakage halt triggered:                no
- every candidate has derived_from:      not run
- Anthropic model used:                  not run
- Anthropic input tokens (total):        0
- Anthropic output tokens (total):       0
- estimated API cost (USD):              $0.00
- User-Agent change effect:              newly-successful=0; still-failing=7; previously-successful-now-failing=3; working-source diff versus 07b: 3 -> 0 (-3)

## Per-URL Fetch Outcomes

- {url: "https://www.jcs.mil/Portals/36/Documents/Doctrine/pubs/jp2_0.pdf", status: "failed", reason: "DoD Joint Publication 2-0 (Joint Intelligence): fetch failed: <HTTPError 403: 'Forbidden'>"}
- {url: "https://www.jcs.mil/Portals/36/Documents/Doctrine/pubs/jp2_01.pdf", status: "failed", reason: "DoD Joint Publication 2-01 (Joint and National Intelligence Support to Military Operations): fetch failed: <HTTPError 403: 'Forbidden'>"}
- {url: "https://www.jcs.mil/Portals/36/Documents/Doctrine/pubs/jp2_01_3.pdf", status: "failed", reason: "DoD Joint Publication 2-01.3 (Joint Intelligence Preparation of the Operational Environment): fetch failed: <HTTPError 403: 'Forbidden'>"}
- {url: "https://www.cia.gov/static/Tradecraft-Primer-apr09.pdf", status: "failed", reason: "CIA: A Tradecraft Primer (Structured Analytic Techniques for Improving Intelligence Analysis): fetch failed: <HTTPError 404: 'Not Found'>"}
- {url: "https://www.cia.gov/static/9a5f1162fd0932c29bfed1c030edf4ae/Pyschology-of-Intelligence-Analysis.pdf", status: "failed", reason: "CIA: Psychology of Intelligence Analysis (Richards J. Heuer): fetch failed: <HTTPError 404: 'Not Found'>"}
- {url: "https://www.dni.gov/files/ODNI/documents/assessments/ATA-2024-Unclassified-Report.pdf", status: "failed", reason: "ODNI Annual Threat Assessment 2024 (Unclassified): fetch failed: <HTTPError 403: 'Forbidden'>"}
- {url: "https://www.dni.gov/files/ODNI/documents/assessments/ATA-2025-Unclassified-Report.pdf", status: "failed", reason: "ODNI Annual Threat Assessment 2025 (Unclassified): fetch failed: <HTTPError 403: 'Forbidden'>"}
- {url: "https://www.intelligence.gov/how-the-ic-works", status: "failed", reason: "ODNI intelligence.gov: How the IC Works (HTML): fetch failed: <HTTPError 403: 'Forbidden'>"}
- {url: "https://www.intelligence.gov/what-the-ic-does", status: "failed", reason: "ODNI intelligence.gov: What the IC Does (HTML): fetch failed: <HTTPError 403: 'Forbidden'>"}
- {url: "https://www.gao.gov/products/gao-21-104450", status: "failed", reason: "GAO Report: Intelligence Community Information Sharing: fetch failed: <HTTPError 403: 'Forbidden'>"}

## Failed URLs

- {url: "https://www.jcs.mil/Portals/36/Documents/Doctrine/pubs/jp2_0.pdf", reason: "DoD Joint Publication 2-0 (Joint Intelligence): fetch failed: <HTTPError 403: 'Forbidden'>"}
- {url: "https://www.jcs.mil/Portals/36/Documents/Doctrine/pubs/jp2_01.pdf", reason: "DoD Joint Publication 2-01 (Joint and National Intelligence Support to Military Operations): fetch failed: <HTTPError 403: 'Forbidden'>"}
- {url: "https://www.jcs.mil/Portals/36/Documents/Doctrine/pubs/jp2_01_3.pdf", reason: "DoD Joint Publication 2-01.3 (Joint Intelligence Preparation of the Operational Environment): fetch failed: <HTTPError 403: 'Forbidden'>"}
- {url: "https://www.cia.gov/static/Tradecraft-Primer-apr09.pdf", reason: "CIA: A Tradecraft Primer (Structured Analytic Techniques for Improving Intelligence Analysis): fetch failed: <HTTPError 404: 'Not Found'>"}
- {url: "https://www.cia.gov/static/9a5f1162fd0932c29bfed1c030edf4ae/Pyschology-of-Intelligence-Analysis.pdf", reason: "CIA: Psychology of Intelligence Analysis (Richards J. Heuer): fetch failed: <HTTPError 404: 'Not Found'>"}
- {url: "https://www.dni.gov/files/ODNI/documents/assessments/ATA-2024-Unclassified-Report.pdf", reason: "ODNI Annual Threat Assessment 2024 (Unclassified): fetch failed: <HTTPError 403: 'Forbidden'>"}
- {url: "https://www.dni.gov/files/ODNI/documents/assessments/ATA-2025-Unclassified-Report.pdf", reason: "ODNI Annual Threat Assessment 2025 (Unclassified): fetch failed: <HTTPError 403: 'Forbidden'>"}
- {url: "https://www.intelligence.gov/how-the-ic-works", reason: "ODNI intelligence.gov: How the IC Works (HTML): fetch failed: <HTTPError 403: 'Forbidden'>"}
- {url: "https://www.intelligence.gov/what-the-ic-does", reason: "ODNI intelligence.gov: What the IC Does (HTML): fetch failed: <HTTPError 403: 'Forbidden'>"}
- {url: "https://www.gao.gov/products/gao-21-104450", reason: "GAO Report: Intelligence Community Information Sharing: fetch failed: <HTTPError 403: 'Forbidden'>"}

## Anything the PI must decide before proceeding

- HANDOFF_03 remains blocked: intel coverage is now 0 working sources under the Chrome 120 User-Agent diagnostic, below the six-source threshold.
- Decide whether to revert the User-Agent behavior, use the 07c three-source PI override state, or approve a different intel source access strategy.

## Deviations from this handoff

- Skipped Task 1 per 07d scope; preconditions were already satisfied.
- Ran Task 2 only for `intelligence_collection_tasking`; did not run source generation, dedup/leakage, pilot replacement, main corpus authoring, or system runs.
- The intel-only `source-build` command wrote an intel-only `build_report.json`; I merged the refreshed intel entry into the previously committed security/finance entries so the cross-domain report remains intact while reflecting the 07d intel diagnostic result.
