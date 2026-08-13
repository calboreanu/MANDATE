"""
Per-domain authoritative source URL list (PROMPTS Section 1.1).

Every URL points to a real public document. The `tier` field records the
authority bucket:

  1: government primary source (NIST, SEC, ODNI, DoD, govinfo.gov, CISA)
  2: standards body (MITRE, PCAOB, FASB public summaries, ISO public refs)
  3: regulator interpretation / guidance (OECD, COSO, OMB)

The default per-domain set is sized so `apparatus.corpus.sources.fetch`
builds a chunk pool sufficient to support the PROMPTS Section 1
source-conditioned run frequency (one generation per chunk).

`security_operations_reporting` is the special case: the AEGIS MITRE
ATT&CK index already exists at `AEGIS-eval/rag/embeddings/enterprise-attack.jsonl`
and is the canonical primary-source index for the domain; the additional
URLs here augment it. The corpus build leaves the MITRE index untouched
and writes the augmenting chunks to `rag/embeddings/security_operations_reporting.jsonl`.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceSpec:
    title: str
    url: str
    media: str          # "html" | "pdf" | "docx" | "pptx"
    tier: int           # 1 / 2 / 3 (see module docstring)
    note: str = ""


CURATED_SOURCES = {
    "security_operations_reporting": [
        SourceSpec("NIST SP 800-61 Rev. 2 (Computer Security Incident "
                    "Handling Guide)",
                    "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/"
                    "NIST.SP.800-61r2.pdf", "pdf", 1),
        SourceSpec("NIST SP 800-53 Rev. 5 (Security and Privacy Controls)",
                    "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/"
                    "NIST.SP.800-53r5.pdf", "pdf", 1),
        SourceSpec("NIST SP 800-137 (Continuous Monitoring)",
                    "https://nvlpubs.nist.gov/nistpubs/Legacy/SP/"
                    "nistspecialpublication800-137.pdf", "pdf", 1),
        SourceSpec("NIST SP 800-92 (Computer Security Log Management)",
                    "https://nvlpubs.nist.gov/nistpubs/Legacy/SP/"
                    "nistspecialpublication800-92.pdf", "pdf", 1),
        SourceSpec("NIST SP 800-115 (Technical Guide to Information "
                    "Security Testing and Assessment)",
                    "https://nvlpubs.nist.gov/nistpubs/Legacy/SP/"
                    "nistspecialpublication800-115.pdf", "pdf", 1),
        SourceSpec("CISA Cybersecurity Advisories index (HTML)",
                    "https://www.cisa.gov/news-events/cybersecurity-advisories",
                    "html", 1,
                    note="The advisories listing; individual advisories "
                          "are linked from this page and can be added "
                          "incrementally."),
        SourceSpec("MITRE D3FEND public knowledge graph (HTML)",
                    "https://d3fend.mitre.org/", "html", 2),
    ],

    "financial_reporting": [
        SourceSpec("Sarbanes-Oxley Act of 2002, full text",
                    "https://www.govinfo.gov/content/pkg/PLAW-107publ204/"
                    "pdf/PLAW-107publ204.pdf", "pdf", 1),
        SourceSpec("PCAOB AS 2110 (Identifying and Assessing Risks of "
                    "Material Misstatement)",
                    "https://pcaobus.org/oversight/standards/"
                    "auditing-standards/details/AS2110", "html", 2),
        SourceSpec("PCAOB AS 2201 (Audit of Internal Control Over "
                    "Financial Reporting)",
                    "https://pcaobus.org/oversight/standards/"
                    "auditing-standards/details/AS2201", "html", 2),
        SourceSpec("PCAOB AS 2410 (Related Parties)",
                    "https://pcaobus.org/oversight/standards/"
                    "auditing-standards/details/AS2410", "html", 2),
        SourceSpec("SEC Form 10-K General Instructions",
                    "https://www.sec.gov/files/form10-k.pdf", "pdf", 1),
        SourceSpec("OMB Circular A-123 (Management's Responsibility for "
                    "Enterprise Risk Management and Internal Control)",
                    "https://www.whitehouse.gov/wp-content/uploads/legacy_"
                    "drupal_files/omb/memoranda/2016/m-16-17.pdf",
                    "pdf", 3),
        SourceSpec("COSO Internal Control Integrated Framework "
                    "(executive summary)",
                    "https://www.coso.org/_files/ugd/3059fc_"
                    "1df7d5dd38074006bce8fdf621a942cf.pdf", "pdf", 3),
        SourceSpec("FASB Topic 606 Revenue from Contracts with Customers "
                    "(public summary)",
                    "https://fasb.org/page/showpdf?path=ASU2014-09.pdf",
                    "pdf", 2),
        SourceSpec("NIST SP 800-37 Rev. 2 (Risk Management Framework)",
                    "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/"
                    "NIST.SP.800-37r2.pdf", "pdf", 1),
    ],

    "intelligence_collection_tasking": [
        # Doctrine: Joint Publications via JCS.mil (the irp.fas.org mirror
        # was unfetchable in the 2026-06-03 build; JCS hosts the authoritative
        # current copies).
        SourceSpec("DoD Joint Publication 2-0 (Joint Intelligence)",
                    "https://www.jcs.mil/Portals/36/Documents/Doctrine/pubs/"
                    "jp2_0.pdf", "pdf", 1),
        SourceSpec("DoD Joint Publication 2-01 (Joint and National "
                    "Intelligence Support to Military Operations)",
                    "https://www.jcs.mil/Portals/36/Documents/Doctrine/pubs/"
                    "jp2_01.pdf", "pdf", 1),
        SourceSpec("DoD Joint Publication 2-01.3 (Joint Intelligence "
                    "Preparation of the Operational Environment)",
                    "https://www.jcs.mil/Portals/36/Documents/Doctrine/pubs/"
                    "jp2_01_3.pdf", "pdf", 1),
        # CIA analytic-tradecraft canon. The CIA CDN uses hashed paths
        # that have proven stable across years for these specific
        # publications.
        SourceSpec("CIA: A Tradecraft Primer (Structured Analytic "
                    "Techniques for Improving Intelligence Analysis)",
                    "https://www.cia.gov/static/"
                    "Tradecraft-Primer-apr09.pdf", "pdf", 1),
        SourceSpec("CIA: Psychology of Intelligence Analysis (Richards "
                    "J. Heuer)",
                    "https://www.cia.gov/static/"
                    "9a5f1162fd0932c29bfed1c030edf4ae/"
                    "Pyschology-of-Intelligence-Analysis.pdf", "pdf", 1,
                    note="Filename retains the historical typo "
                          "'Pyschology' as published on cia.gov."),
        # ODNI primary-source oversight document. The Annual Threat
        # Assessment is published unclassified every year at a stable
        # filename pattern.
        SourceSpec("ODNI Annual Threat Assessment 2024 (Unclassified)",
                    "https://www.dni.gov/files/ODNI/documents/assessments/"
                    "ATA-2024-Unclassified-Report.pdf", "pdf", 1),
        SourceSpec("ODNI Annual Threat Assessment 2025 (Unclassified)",
                    "https://www.dni.gov/files/ODNI/documents/assessments/"
                    "ATA-2025-Unclassified-Report.pdf", "pdf", 1,
                    note="If the 2025 PDF is not yet at this canonical "
                          "path, the 2024 entry above is the substantive "
                          "primary source."),
        # IC public-facing HTML reference (intelligence.gov is the
        # designated public portal for ODNI; HTML is more fetch-reliable
        # than the dni.gov/files PDFs that 404'd in the 2026-06-03 build).
        SourceSpec("ODNI intelligence.gov: How the IC Works (HTML)",
                    "https://www.intelligence.gov/how-the-ic-works",
                    "html", 1),
        SourceSpec("ODNI intelligence.gov: What the IC Does (HTML)",
                    "https://www.intelligence.gov/what-the-ic-does",
                    "html", 1),
        # GAO oversight report on IC information sharing, HTML so it does
        # not depend on PDF extraction.
        SourceSpec("GAO Report: Intelligence Community Information Sharing",
                    "https://www.gao.gov/products/gao-21-104450",
                    "html", 1),
    ],

    # Hold-out 4th domain (PROTOCOL_LOCK Section 1, Decisions memo Section 1
    # recommendation). Software engineering specification is the
    # recommended hold-out: outside the four MANDATE training corpus
    # domains (cyber, legal, financial, intel) and outside the three main
    # evaluation domains, so a hold-out evaluation here is a clean
    # generalization signal. Curated public primary sources only.
    "software_engineering_specification": [
        SourceSpec("NIST SP 800-160 Vol. 1 (Systems Security Engineering)",
                    "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/"
                    "NIST.SP.800-160v1.pdf", "pdf", 1),
        SourceSpec("NIST SP 800-218 (Secure Software Development Framework)",
                    "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/"
                    "NIST.SP.800-218.pdf", "pdf", 1),
        SourceSpec("NIST SP 800-64 Rev. 2 (Security Considerations in the "
                    "SDLC)",
                    "https://nvlpubs.nist.gov/nistpubs/Legacy/SP/"
                    "nistspecialpublication800-64r2.pdf", "pdf", 1),
        SourceSpec("Agile Manifesto (HTML)",
                    "https://agilemanifesto.org/", "html", 2),
        SourceSpec("Twelve-Factor App methodology (HTML)",
                    "https://12factor.net/", "html", 2),
        SourceSpec("NASA NPR 7150.2D (Software Engineering Requirements)",
                    "https://nodis3.gsfc.nasa.gov/displayDir.cfm?"
                    "t=NPR&c=7150&s=2D", "html", 1),
        SourceSpec("GAO Report: DoD Software Acquisition (HTML)",
                    "https://www.gao.gov/products/gao-21-105313", "html", 1),
        SourceSpec("UK Government Digital Service Manual: Service Standard",
                    "https://www.gov.uk/service-manual/service-standard",
                    "html", 1),
        SourceSpec("CMU SEI: Architecture-Centric Engineering (HTML)",
                    "https://insights.sei.cmu.edu/library/"
                    "architecture-centric-engineering/", "html", 2),
    ],
}

# Hold-out 4th-domain reconciliation note (2026-06-03):
# Added `software_engineering_specification` per Decisions memo Section 1
# recommendation. Free, primary-source URLs prioritized; PDF and HTML mix.
# Same network-brittleness caveats as the intel domain (see Handoff 07b/
# 07d) may apply; the manual-ingest pathway is available if any of these
# URLs fail on the eval host.

# Reconciliation note (2026-06-03, intel-domain fix):
# The first source-first build (Handoff 07) lost 7 of 8 intel URLs to 404,
# 403, and empty-PDF responses, leaving the intel pool derived almost
# entirely from NIST SP 800-53 chunks (a security-controls document
# tagged as also-relevant-to-IC). That bias is now resolved by replacing
# the intel list with intel-specific primary sources only:
#   - DoD Joint Publications via JCS.mil (replacing the irp.fas.org
#     mirror that served empty PDFs);
#   - CIA analytic-tradecraft canon at cia.gov/static (Tradecraft Primer
#     and Heuer's Psychology of Intelligence Analysis);
#   - ODNI Annual Threat Assessments (replacing the ICDs that 404'd at
#     dni.gov/files/documents/ICD and the National Intelligence Strategy
#     that 404'd at dni.gov/files/ODNI/documents);
#   - ODNI public-facing intelligence.gov HTML pages as fetch-reliable
#     IC references;
#   - GAO oversight report (HTML) replacing the CRS PDF that 403'd at
#     crsreports.congress.gov.
# NIST SP 800-53 is intentionally removed from the intel list so its
# chunks no longer dominate intel-domain candidate derivation. It remains
# in the security list, where it belongs.


def get_sources(domain: str) -> list:
    """Return the SourceSpec list for a domain."""
    if domain not in CURATED_SOURCES:
        raise KeyError("unknown domain: %r (one of %s)"
                       % (domain, ", ".join(CURATED_SOURCES)))
    return list(CURATED_SOURCES[domain])
