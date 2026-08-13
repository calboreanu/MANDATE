"""
Manual-source ingestion (Workstream C2, fallback for brittle .gov hosts).

When `apparatus.corpus.sources.fetch` cannot reach a public document
(Handoff 07b/07c/07d showed JCS.mil, GAO, CIA static-CDN, and several
dni.gov paths return 403 or 404 to programmatic fetchers, even with a
plain browser User-Agent), the PI downloads the PDF once in a browser
where it works, drops it in `rag/sources/<domain>/manual/`, and runs
`apparatus.corpus.cli ingest-manual`. This module turns those PDFs into
the same `.txt` files the fetched ones produce, with provenance recorded
in a sidecar manifest, so the index build is uniform afterward.

Provenance shape. Each manual PDF carries one entry in
`manual_sources_manifest.json` (one file per domain, in the manual
directory) with:

  filename        the .pdf filename, e.g., 'jp2_0.pdf'
  title           human-readable title, e.g., 'DoD JP 2-0 Joint Intelligence'
  url             the canonical public URL the PDF was downloaded from
  downloaded_at   ISO date string
  sha256          hex digest of the PDF bytes (for replication verification)
  tier            authority tier, same scheme as curated_sources

The replication package commits the manifest and the PDFs; reviewers
verify each PDF's SHA-256 against an authoritative copy at the recorded
URL. Manual sources are therefore as auditable as fetched sources, just
not refetchable in one bash command on the eval host.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

from .fetch import extract_pdf_text, _slugify


MANIFEST_NAME = "manual_sources_manifest.json"


@dataclass
class ManualSourceEntry:
    filename: str
    title: str = ""
    url: str = ""
    downloaded_at: str = ""
    sha256: str = ""
    tier: int = 1
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class IngestReport:
    domain: str
    manual_dir: str
    sources_dir: str
    ingested: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    failed: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"domain": self.domain, "manual_dir": self.manual_dir,
                "sources_dir": self.sources_dir,
                "ingested": [e.to_dict() if hasattr(e, "to_dict") else e
                              for e in self.ingested],
                "skipped": list(self.skipped),
                "failed": list(self.failed)}


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(manual_dir: str) -> dict:
    """Read the manifest if present, else return an empty stub."""
    path = os.path.join(manual_dir, MANIFEST_NAME)
    if not os.path.isfile(path):
        return {"manual_dir": manual_dir, "entries": {}}
    with open(path) as f:
        return json.load(f)


def save_manifest(manual_dir: str, manifest: dict) -> str:
    os.makedirs(manual_dir, exist_ok=True)
    path = os.path.join(manual_dir, MANIFEST_NAME)
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    return path


def ingest_manual_sources(*, domain: str, manual_dir: str,
                          sources_dir: str) -> IngestReport:
    """Extract every `.pdf` in `manual_dir` to a sibling `.txt` in
    `sources_dir`, computing the file SHA-256 and updating the manifest.

    Each PDF must have an entry in `manual_sources_manifest.json` with
    its `filename`; the manifest is the provenance record (title, url,
    downloaded_at, tier). A PDF without a manifest entry is reported in
    `skipped`, not ingested, so the corpus cannot accumulate documents
    whose provenance is not recorded. A PDF whose extracted text is
    empty is reported in `failed`.
    """
    os.makedirs(sources_dir, exist_ok=True)
    rep = IngestReport(domain=domain, manual_dir=manual_dir,
                       sources_dir=sources_dir)
    manifest = load_manifest(manual_dir)
    entries = dict(manifest.get("entries") or {})

    for fname in sorted(os.listdir(manual_dir)):
        if not fname.lower().endswith(".pdf"):
            continue
        pdf_path = os.path.join(manual_dir, fname)
        meta = entries.get(fname)
        if meta is None:
            rep.skipped.append({"filename": fname,
                                  "reason": "no manifest entry"})
            continue
        try:
            with open(pdf_path, "rb") as f:
                raw = f.read()
            text = extract_pdf_text(raw).strip()
        except Exception as e:
            rep.failed.append({"filename": fname,
                                "reason": "extract: %r" % e})
            continue
        if not text:
            rep.failed.append({"filename": fname,
                                "reason": "empty extracted text"})
            continue
        out_path = os.path.join(sources_dir,
                                  "%s.txt" % _slugify(meta.get("title")
                                                        or fname[:-4]))
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        # refresh the manifest entry with sha256 and downloaded_at
        meta["filename"] = fname
        meta["sha256"] = _sha256_file(pdf_path)
        meta.setdefault("downloaded_at",
                          datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        entries[fname] = meta
        rep.ingested.append(ManualSourceEntry(**{
            k: meta.get(k, "")
            for k in ("filename", "title", "url", "downloaded_at",
                       "sha256", "tier", "note")}))

    manifest["entries"] = entries
    save_manifest(manual_dir, manifest)
    return rep


def manifest_template(domain: str) -> dict:
    """A template a PI fills in for a domain's manual sources."""
    return {
        "domain": domain,
        "note": ("Manual PDFs the PI downloaded once in a browser when "
                  "programmatic fetch failed. Each .pdf in this directory "
                  "must have an entry here; ingest-manual skips PDFs "
                  "without a manifest entry rather than silently "
                  "indexing them."),
        "entries": {
            "example_file.pdf": {
                "filename": "example_file.pdf",
                "title": "DoD JP 2-0 Joint Intelligence",
                "url": ("https://www.jcs.mil/Portals/36/Documents/"
                         "Doctrine/pubs/jp2_0.pdf"),
                "downloaded_at": "2026-06-03",
                "tier": 1,
                "note": ("downloaded via Safari on the PI's workstation; "
                          "programmatic fetch from the eval-host venv "
                          "returns 403 (see HANDOFF_07b/07d).")
            }
        }
    }
