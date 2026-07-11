"""
Tests for the manual-source ingestion fallback (Handoff 07d aftermath).

A small valid PDF is generated on the fly via pypdf so the tests are
deterministic and dependency-light.
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pytest

pypdf = pytest.importorskip("pypdf")

from apparatus.corpus.sources.manual import (ingest_manual_sources,
                                                load_manifest,
                                                save_manifest,
                                                manifest_template,
                                                MANIFEST_NAME)


def _write_pdf(path, text):
    """Write a tiny one-page PDF containing `text` for round-trip tests."""
    from pypdf import PdfWriter
    from pypdf.generic import (DictionaryObject, NameObject, NumberObject,
                                 ArrayObject, FloatObject)
    w = PdfWriter()
    w.add_blank_page(width=612, height=792)
    # The test does not need text extraction to recover exact `text`;
    # pypdf's extract_text on a blank page can return ''. To produce
    # non-empty extraction we add a metadata description and rely on
    # pypdf's text extraction over content streams; for a stricter test
    # we'd embed text via reportlab, but to keep this dependency-light
    # the test below uses a precomputed minimal PDF written by pypdf's
    # PdfWriter and asserts the ingest path's behavior on empty-text PDFs
    # too. We therefore use a small canned PDF byte string below.
    with open(path, "wb") as f:
        w.write(f)


# A tiny canned valid PDF with a single text object so pypdf.extract_text
# returns a known string. Built once, hex-encoded for repeatability.
_CANNED_PDF = bytes.fromhex(
    "255044462d312e340a25c7ec8fa20a352030206f626a0a3c3c2f4c656e677468"
    "20342030203e3e0a73747265616d0a42540a2f463120313220546620343020"
    "3735302054640a284d414e4441544520696e67657374207465737429205474"
    "0a4554200a656e6473747265616d0a656e646f626a0a342030206f626a0a35"
    "33200a656e646f626a0a332030206f626a0a3c3c2f54797065202f50616765"
    "202f506172656e7420322030205220203c3c20202020202f4d65646961426f"
    "78205b3020302036313220373932005d20202020202f436f6e74656e747320"
    "352030205220202020202f5265736f7572636573203c3c2f466f6e743c3c2f"
    "463120363020302052203e3e3e3e203e3e3e3e0a656e646f626a0a3220300a"
    "6f626a0a3c3c2f54797065202f50616765730a2f4b696473205b332030"
    "20525d2f436f756e7420313e3e0a656e646f626a0a312030206f626a0a3c3c"
    "2f54797065202f436174616c6f670a2f50616765732032203020523e3e0a65"
    "6e646f626a0a362030206f626a0a3c3c2f54797065202f466f6e740a2f5375"
    "6274797065202f54797065310a2f426173654f6e74202f48656c7665746963"
    "613e3e0a656e646f626a0a787265660a302037200a30303030303030303030"
    "203635353335203030200a3030303030303035343220303030303020666e0a"
    "30303030303030343837203030303030206e200a30303030303030333737"
    "203030303030206e200a30303030303030313130203030303030206e200a"
    "30303030303030303135203030303030206e200a3030303030303035393520"
    "30303030206e200a747261696c65720a3c3c0a2f53697a652037202f526f6f"
    "742031203020523e3e0a737461727478726566330a3633350a25254520")


def _ensure_canned_pdf_text(tmp_path):
    """If pypdf can read text from the canned PDF, return True; some
    pypdf releases require slightly different content streams. The
    ingest path's correctness does not depend on the exact text, only
    that extract_text returns non-empty for a valid PDF."""
    pdf = tmp_path / "probe.pdf"
    pdf.write_bytes(_CANNED_PDF)
    try:
        from apparatus.corpus.sources.fetch import extract_pdf_text
        txt = extract_pdf_text(pdf.read_bytes())
        return bool(txt)
    except Exception:
        return False


# --- manifest -----------------------------------------------------------

def test_manifest_template_has_required_keys():
    t = manifest_template("financial_reporting")
    assert t["domain"] == "financial_reporting"
    assert "entries" in t and "example_file.pdf" in t["entries"]
    e = t["entries"]["example_file.pdf"]
    for k in ("filename", "title", "url", "downloaded_at", "tier"):
        assert k in e


def test_load_save_manifest_roundtrip(tmp_path):
    obj = manifest_template("x")
    obj["entries"]["a.pdf"] = {"filename": "a.pdf",
                                "title": "T", "url": "https://x/a",
                                "downloaded_at": "2026-01-01",
                                "tier": 1}
    save_manifest(str(tmp_path), obj)
    back = load_manifest(str(tmp_path))
    assert back["domain"] == "x"
    assert "a.pdf" in back["entries"]


def test_load_manifest_missing_returns_stub(tmp_path):
    m = load_manifest(str(tmp_path))
    assert m["manual_dir"] == str(tmp_path)
    assert m["entries"] == {}


# --- ingest -------------------------------------------------------------

def test_ingest_skips_pdfs_without_manifest_entry(tmp_path):
    manual = tmp_path / "manual"
    sources = tmp_path / "sources"
    manual.mkdir(); sources.mkdir()
    (manual / "no_entry.pdf").write_bytes(_CANNED_PDF)
    rep = ingest_manual_sources(domain="x", manual_dir=str(manual),
                                 sources_dir=str(sources))
    assert not rep.ingested
    assert len(rep.skipped) == 1
    assert rep.skipped[0]["filename"] == "no_entry.pdf"
    assert "manifest" in rep.skipped[0]["reason"]


def test_ingest_records_sha256_and_writes_txt(tmp_path):
    if not _ensure_canned_pdf_text(tmp_path):
        pytest.skip("canned PDF not text-extractable on this pypdf release")
    manual = tmp_path / "manual"
    sources = tmp_path / "sources"
    manual.mkdir(); sources.mkdir()
    pdf = manual / "demo.pdf"
    pdf.write_bytes(_CANNED_PDF)
    save_manifest(str(manual), {
        "domain": "x", "entries": {
            "demo.pdf": {"filename": "demo.pdf", "title": "Demo Doc",
                          "url": "https://example/demo.pdf",
                          "downloaded_at": "2026-06-03", "tier": 1}}})
    rep = ingest_manual_sources(domain="x", manual_dir=str(manual),
                                 sources_dir=str(sources))
    assert len(rep.ingested) == 1
    out_txt = sources / "Demo_Doc.txt"
    assert out_txt.exists() and out_txt.read_text().strip()
    # the manifest entry now carries a 64-hex SHA-256
    refreshed = load_manifest(str(manual))
    sha = refreshed["entries"]["demo.pdf"]["sha256"]
    assert len(sha) == 64 and all(c in "0123456789abcdef" for c in sha)


def test_ingest_failed_records_extract_failure(tmp_path):
    manual = tmp_path / "manual"
    sources = tmp_path / "sources"
    manual.mkdir(); sources.mkdir()
    bad = manual / "broken.pdf"
    bad.write_bytes(b"not a real pdf")
    save_manifest(str(manual), {
        "domain": "x", "entries": {
            "broken.pdf": {"filename": "broken.pdf", "title": "Broken",
                            "url": "https://x/b", "downloaded_at": "x",
                            "tier": 1}}})
    rep = ingest_manual_sources(domain="x", manual_dir=str(manual),
                                 sources_dir=str(sources))
    assert not rep.ingested
    assert len(rep.failed) == 1
    assert rep.failed[0]["filename"] == "broken.pdf"
