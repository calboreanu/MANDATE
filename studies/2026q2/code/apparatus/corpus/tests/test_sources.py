"""
Tests for the source-first corpus authoring pipeline (Workstream C2 post-
reconciliation): apparatus/corpus/sources/* and source_conditioned.py.

Mock-driven so no network or live LLM is required. The fetch HTTP layer is
injected; the LLM is the existing MockLLMClient.
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pytest

from apparatus.baselines.llm_client import MockLLMClient
from apparatus.corpus.sources.curated_sources import (CURATED_SOURCES,
                                                       SourceSpec,
                                                       get_sources)
from apparatus.corpus.sources.fetch import (extract_html_text, fetch_one,
                                              fetch_all,
                                              SourceFetchResult,
                                              DEFAULT_USER_AGENT,
                                              DEFAULT_ACCEPT,
                                              DEFAULT_ACCEPT_LANGUAGE)
from apparatus.corpus.source_conditioned import (
    render_source_conditioned_prompt, load_chunks, sample_chunks,
    SourceConditionedGenerator, candidate_to_record,
    SOURCE_CONDITIONED_PROMPT)


# --- curated sources --------------------------------------------------------

def test_curated_sources_present_for_all_domains():
    """Three main-corpus domains + the hold-out 4th."""
    assert set(CURATED_SOURCES) == {
        "security_operations_reporting", "financial_reporting",
        "intelligence_collection_tasking",
        "software_engineering_specification"}
    for d, specs in CURATED_SOURCES.items():
        assert len(specs) >= 7, "%s has only %d sources" % (d, len(specs))
        for s in specs:
            assert isinstance(s, SourceSpec)
            assert s.url.startswith(("http://", "https://"))
            assert s.media in ("html", "pdf", "docx", "pptx")
            assert s.tier in (1, 2, 3)


def test_get_sources_rejects_unknown_domain():
    with pytest.raises(KeyError):
        get_sources("quantum_widgets")


# --- HTML extraction --------------------------------------------------------

def test_extract_html_strips_script_and_tags_and_decodes_entities():
    raw = b"""
    <html><head><title>x</title><script>alert(1)</script></head>
    <body><h1>Hello &amp; goodbye</h1>
    <p>This is <b>real</b> text.</p></body></html>"""
    out = extract_html_text(raw)
    assert "Hello & goodbye" in out
    assert "This is real text." in out
    assert "alert(1)" not in out
    assert "<" not in out and ">" not in out


def test_default_user_agent_is_identifying_academic_string():
    """The fetcher's default UA names itself an academic crawler. The
    2026-06-03 Handoff 07d diagnostic showed that a bare Chrome UA
    without supporting headers does WORSE than this string on the .gov
    hosts we fetch, so the identifying string is the documented
    canonical UA. The build_report.json records exactly what is sent."""
    ua = DEFAULT_USER_AGENT
    assert ua.startswith("Mozilla/5.0")
    assert "MANDATE-eval" in ua
    assert "replication package" in ua


def test_default_accept_headers_include_html_and_pdf():
    assert "text/html" in DEFAULT_ACCEPT
    assert "application/pdf" in DEFAULT_ACCEPT
    assert "en" in DEFAULT_ACCEPT_LANGUAGE


def test_extract_html_handles_latin1_bytes():
    raw = "<p>cafe\xe9</p>".encode("latin-1")
    out = extract_html_text(raw)
    assert "cafe" in out


# --- fetch_one with injected getter -----------------------------------------

class _FakeGetter:
    def __init__(self, by_url):
        self.by_url = by_url
        self.calls = []

    def __call__(self, url, timeout=None):
        self.calls.append(url)
        v = self.by_url.get(url)
        if v is None:
            raise RuntimeError("unknown url: %s" % url)
        if isinstance(v, Exception):
            raise v
        return v


def test_fetch_one_html_success_writes_text_file(tmp_path):
    spec = SourceSpec("Demo HTML",
                       "https://example.invalid/x",
                       "html", 1)
    getter = _FakeGetter({spec.url: b"<p>hello world</p>"})
    res = fetch_one(spec, out_dir=str(tmp_path), http_getter=getter)
    assert res.ok is True
    assert res.bytes_text > 0
    saved = (tmp_path / "Demo_HTML.txt").read_text()
    assert "hello world" in saved


def test_fetch_one_records_http_failure_without_writing(tmp_path):
    spec = SourceSpec("Demo failing",
                       "https://example.invalid/y",
                       "html", 1)
    getter = _FakeGetter({spec.url: RuntimeError("boom")})
    res = fetch_one(spec, out_dir=str(tmp_path), http_getter=getter)
    assert res.ok is False
    assert "fetch failed" in res.error
    assert not (tmp_path / "Demo_failing.txt").exists()


def test_fetch_one_records_empty_extract(tmp_path):
    spec = SourceSpec("only tags",
                       "https://example.invalid/z",
                       "html", 1)
    getter = _FakeGetter({spec.url: b"<html><head></head></html>"})
    res = fetch_one(spec, out_dir=str(tmp_path), http_getter=getter)
    assert res.ok is False
    assert "empty" in res.error


def test_fetch_all_separates_fetched_and_failed(tmp_path):
    specs = [
        SourceSpec("ok1", "https://example.invalid/a", "html", 1),
        SourceSpec("bad", "https://example.invalid/b", "html", 1),
        SourceSpec("ok2", "https://example.invalid/c", "html", 1),
    ]
    getter = _FakeGetter({
        specs[0].url: b"<p>alpha</p>",
        specs[1].url: RuntimeError("404"),
        specs[2].url: b"<p>gamma</p>",
    })
    fetched, failed = fetch_all(specs, out_dir=str(tmp_path),
                                  http_getter=getter, sleep_between_s=0)
    assert [r.spec.title for r in fetched] == ["ok1", "ok2"]
    assert [r.spec.title for r in failed] == ["bad"]


# --- source-conditioned prompt ----------------------------------------------

def test_source_conditioned_prompt_has_required_anchors():
    for tok in ("{DOMAIN}", "{CATEGORY}", "{SOURCE_TITLE}",
                "{SOURCE_REFERENCE_ID}", "{SOURCE_CONTENT_CHUNK}"):
        assert tok in SOURCE_CONDITIONED_PROMPT


def test_render_source_conditioned_fills_every_anchor():
    out = render_source_conditioned_prompt(
        domain="financial_reporting", category="full_specification",
        source_title="SOX Act of 2002",
        source_reference_id="FIN-SOX-001",
        source_content="Section 404 requires management to assess.")
    for tok in ("{DOMAIN}", "{CATEGORY}", "{SOURCE_TITLE}",
                "{SOURCE_REFERENCE_ID}", "{SOURCE_CONTENT_CHUNK}"):
        assert tok not in out
    assert "financial_reporting" in out
    assert "SOX Act of 2002" in out
    assert "Section 404 requires management" in out


def test_render_rejects_unknown_domain_or_category():
    with pytest.raises(ValueError):
        render_source_conditioned_prompt(
            domain="quantum", category="full_specification",
            source_title="x", source_reference_id="y", source_content="z")
    with pytest.raises(ValueError):
        render_source_conditioned_prompt(
            domain="financial_reporting", category="something_else",
            source_title="x", source_reference_id="y", source_content="z")


# --- chunk sampling and load ------------------------------------------------

def test_load_chunks_reads_jsonl(tmp_path):
    p = tmp_path / "idx.jsonl"
    p.write_text("\n".join(json.dumps({
        "reference_id": "X-%03d" % i, "source": "X",
        "name": "x.txt", "content": "chunk %d" % i}) for i in range(5)))
    chunks = load_chunks(str(p))
    assert len(chunks) == 5
    assert chunks[0]["reference_id"] == "X-000"


def test_load_chunks_skips_empty_content(tmp_path):
    p = tmp_path / "idx.jsonl"
    p.write_text("\n".join([
        json.dumps({"reference_id": "X-0", "content": "ok"}),
        json.dumps({"reference_id": "X-1", "content": ""}),
        json.dumps({"reference_id": "X-2", "content": "ok2"}),
    ]))
    assert [c["reference_id"] for c in load_chunks(str(p))] == ["X-0", "X-2"]


def test_sample_chunks_is_deterministic_under_seed():
    pool = [{"reference_id": "X-%03d" % i, "content": "c"}
            for i in range(20)]
    a = sample_chunks(pool, n=5, seed=42)
    b = sample_chunks(pool, n=5, seed=42)
    c = sample_chunks(pool, n=5, seed=43)
    assert a == b
    assert a != c
    assert len(a) == 5


def test_sample_chunks_caps_at_pool_size():
    pool = [{"reference_id": "X-1", "content": "c"}]
    assert len(sample_chunks(pool, n=5)) == 1


# --- source-conditioned generator -------------------------------------------

def test_generator_emits_one_candidate_per_chunk_with_derived_from():
    mock = MockLLMClient(responses=[
        "Hi team, this is the request derived from SOX 404.",
        "Senior analyst here: the next collection package needs to ground.",
    ], default="other text")
    gen = SourceConditionedGenerator(client=mock, model="mock-model")
    chunks = [
        {"reference_id": "FIN-SOX-001", "source": "FIN",
         "name": "SOX.txt", "content": "Section 404 requires..."},
        {"reference_id": "INT-ICD-203-005", "source": "INT",
         "name": "ICD-203.txt",
         "content": "Analytic standards require objectivity..."},
    ]
    out = gen.generate_batch(domain="financial_reporting",
                              category="full_specification",
                              chunks=chunks)
    assert len(out) == 2
    # both candidates received the source-conditioned prompt
    assert any("SOX 404" in c.text for c in out)
    # candidate_idx progresses
    assert [c.candidate_idx for c in out] == [1, 2]
    # the notes field records the derivation
    assert "FIN-SOX-001" in out[0].notes
    assert "INT-ICD-203-005" in out[1].notes


def test_candidate_to_record_attaches_derived_from():
    mock = MockLLMClient(default="any text")
    gen = SourceConditionedGenerator(client=mock, model="m")
    chunk = {"reference_id": "FIN-SOX-001", "source": "FIN",
             "name": "SOX.txt", "content": "Section 404 requires..."}
    cand = gen.generate_one(domain="financial_reporting",
                             category="full_specification", chunk=chunk)
    rec = candidate_to_record(cand, chunk=chunk)
    assert rec["derived_from"]["reference_id"] == "FIN-SOX-001"
    assert rec["derived_from"]["source"] == "FIN"
    assert rec["derived_from"]["name"] == "SOX.txt"
    assert "Section 404" in rec["derived_from"]["content_preview"]
