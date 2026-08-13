"""
Per-domain authoritative source corpus build (Workstream C2, source-first).

`fetch` pulls real public documents from a curated URL list, extracts text
(HTML directly, PDF via pypdf), persists them as `.txt`, and builds a
per-domain Jaccard chunk index in the AEGIS RAG format so MANDATE-primary
can also use the same index at runtime. `curated_sources` holds the URL
list per domain as PROMPTS Section 1.1 specifies.

The pre-deposit reconciliation that moved PROMPTS Section 1 from synthetic
to source-conditioned generation is in `_package/RECONCILIATION_LOG.md`
Change 9.
"""
from .curated_sources import CURATED_SOURCES, SourceSpec, get_sources
from .fetch import (fetch_one, fetch_all, build_domain_index,
                    SourceFetchResult, BuildReport, extract_pdf_text,
                    extract_html_text, extract_docx_text,
                    extract_pptx_text)
from .manual import (ManualSourceEntry, IngestReport, MANIFEST_NAME,
                      ingest_manual_sources, load_manifest, save_manifest,
                      manifest_template)

__all__ = ["CURATED_SOURCES", "SourceSpec", "get_sources",
           "fetch_one", "fetch_all", "build_domain_index",
           "SourceFetchResult", "BuildReport",
           "extract_pdf_text", "extract_html_text",
           "ManualSourceEntry", "IngestReport", "MANIFEST_NAME",
           "ingest_manual_sources", "load_manifest", "save_manifest",
           "manifest_template"]
