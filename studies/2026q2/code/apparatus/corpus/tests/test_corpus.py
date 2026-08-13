"""
Tests for the corpus-authoring pipeline (Workstream C2).

Dependency-light: the LLM-call steps use the shared MockLLMClient, and the
dedup / leakage tests use HashEmbedder so sentence-transformers is not
required. The eval-host run uses Claude Opus 4 for generation and the
sentence-transformer embedder for dedup / leakage.

Run:  python3 -m pytest apparatus/corpus/tests -q
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import numpy as np
import pytest

from apparatus.baselines.llm_client import MockLLMClient
from apparatus.corpus import (
    TASK_GENERATION_PROMPT, ANCHOR_SCAFFOLD_PROMPT, CATEGORIES,
    DOMAIN_GUIDANCE, render_task_generation_prompt,
    render_anchor_scaffold_prompt,
    TaskGenerator, parse_numbered_tasks, AnchorScaffolder,
    HashEmbedder, cosine_similarity_matrix, cosine_dedup, leakage_audit)


# --- prompts -----------------------------------------------------------------

def test_section1_prompt_is_verbatim_with_required_anchors():
    # the body must carry the locked anchor strings the renderer relies on
    assert "{DOMAIN}" in TASK_GENERATION_PROMPT
    assert ("{full_specification | gap_triggering | stretch_case}"
            in TASK_GENERATION_PROMPT)
    assert "Produce 5 distinct task descriptions." in TASK_GENERATION_PROMPT


def test_section2_prompt_carries_the_json_skeleton_and_constraint_grammar():
    assert '"mission_intent"' in ANCHOR_SCAFFOLD_PROMPT
    assert "MANDATE constraint grammar" in ANCHOR_SCAFFOLD_PROMPT
    assert "{REQUEST_TEXT}" in ANCHOR_SCAFFOLD_PROMPT


def test_render_task_generation_prompt_fills_both_anchors():
    out = render_task_generation_prompt(
        domain="security_operations_reporting",
        category="gap_triggering")
    assert "security_operations_reporting" in out
    assert "gap_triggering" in out
    # the anchors must be gone, not double-substituted
    assert "{DOMAIN}" not in out
    assert "{full_specification | gap_triggering | stretch_case}" not in out


def test_render_task_generation_rejects_unknown_domain_or_category():
    with pytest.raises(ValueError):
        render_task_generation_prompt(domain="quantum_widgets",
                                       category="full_specification")
    with pytest.raises(ValueError):
        render_task_generation_prompt(
            domain="financial_reporting", category="something_else")


def test_render_anchor_scaffold_preserves_json_braces():
    out = render_anchor_scaffold_prompt(request_text="x")
    assert '"mission_intent"' in out
    assert "{REQUEST_TEXT}" not in out


def test_corpus_domains_match_curated_sources():
    """DOMAIN_GUIDANCE must list every domain that CURATED_SOURCES carries.
    The three main-corpus domains plus the hold-out 4th domain
    (software_engineering_specification). If the two registries drift, the
    source-build / source-generate CLI will reject the configured domain
    even though sources are present (HANDOFF_08 2026-06-04 halt)."""
    from apparatus.corpus.sources.curated_sources import CURATED_SOURCES
    assert set(DOMAIN_GUIDANCE) == set(CURATED_SOURCES) == {
        "security_operations_reporting", "financial_reporting",
        "intelligence_collection_tasking",
        "software_engineering_specification"}


# --- output parsing ----------------------------------------------------------

def test_parse_numbered_tasks_dot_separator():
    raw = ("1. First task with some context here.\n"
            "2. Second task that is also reasonable.\n"
            "3. Third one with another stakeholder.")
    parts = parse_numbered_tasks(raw)
    assert len(parts) == 3
    assert parts[0].startswith("First")
    assert parts[2].startswith("Third")


def test_parse_numbered_tasks_paren_separator_and_blank_lines():
    raw = "1) alpha\n\n2) beta\n\n3) gamma\n"
    assert parse_numbered_tasks(raw) == ["alpha", "beta", "gamma"]


def test_parse_numbered_tasks_returns_what_is_there():
    # fewer than 5 numbered items: return them, do not fabricate
    raw = "1. only one"
    assert parse_numbered_tasks(raw) == ["only one"]
    assert parse_numbered_tasks("") == []


# --- TaskGenerator -----------------------------------------------------------

NUMBERED_FIVE = (
    "1. A CISO asks the SOC manager for a vulnerability posture summary by\n"
    "end of week covering all internet-facing assets.\n"
    "2. The director asks for a patch compliance brief that compares this\n"
    "quarter to last across the financial-services subsidiary.\n"
    "3. An incident summary is requested by the leadership team for the\n"
    "ransomware containment last weekend.\n"
    "4. The audit committee wants a threat briefing tailored to the\n"
    "manufacturing operating unit before the board meeting.\n"
    "5. The risk officer asks for a posture assessment focused on third\n"
    "party access since the new vendor onboarding policy went live.")


def test_task_generator_parses_five_candidates():
    mock = MockLLMClient(default=NUMBERED_FIVE)
    gen = TaskGenerator(client=mock, model="mock-model")
    out = gen.generate_run(domain="security_operations_reporting",
                           category="full_specification", run_idx=1)
    assert len(out) == 5
    assert {c.candidate_idx for c in out} == {1, 2, 3, 4, 5}
    assert all(c.domain == "security_operations_reporting" for c in out)
    assert all(c.category == "full_specification" for c in out)
    assert all(c.run_idx == 1 for c in out)
    assert all(c.source_model == "mock-model" for c in out)


def test_task_generator_batch_iterates_all_categories():
    mock = MockLLMClient(default=NUMBERED_FIVE)
    gen = TaskGenerator(client=mock, model="mock-model")
    out = gen.generate_batch(domain="financial_reporting", n_runs=2)
    # 3 categories x 2 runs x up to 5 candidates per run = 30
    assert len(out) == 30
    assert {c.category for c in out} == set(CATEGORIES)


# --- AnchorScaffolder --------------------------------------------------------

SCAFFOLD_JSON = json.dumps({
    "mission_intent": "Summarize ransomware containment.",
    "minimum": [{"dimension": "MTTC", "threshold": None,
                  "rationale": "request says 'by end of week' (vague)"}],
    "target": [{"dimension": "report length", "objective": None,
                 "rationale": "not stated"}],
    "constraints": [{"predicate": "audience == executive",
                      "rationale": "the email goes to the leadership team"}],
    "suspected_gaps": [{"field": "minimum.MTTC",
                         "reason": "no concrete deadline given"}]
})


def test_anchor_scaffolder_parses_json_response():
    mock = MockLLMClient(default=SCAFFOLD_JSON)
    sc = AnchorScaffolder(client=mock, model="mock-model")
    out = sc.scaffold(task_id="TASK-PIL-001",
                      request_text="Hi team, ransomware happened.")
    assert out.parse_ok is True
    assert out.task_id == "TASK-PIL-001"
    assert out.mission_intent.startswith("Summarize")
    assert len(out.suspected_gaps) == 1


def test_anchor_scaffolder_records_parse_failure_cleanly():
    mock = MockLLMClient(default="not JSON")
    sc = AnchorScaffolder(client=mock, model="mock-model")
    out = sc.scaffold(task_id="x", request_text="y")
    assert out.parse_ok is False
    assert out.error                                # non-empty


# --- embeddings and dedup ----------------------------------------------------

def test_hash_embedder_is_deterministic_and_normalized():
    emb = HashEmbedder(dim=64)
    a = emb.embed(["the quick brown fox", "the quick brown fox"])
    assert a.shape == (2, 64)
    assert np.allclose(a[0], a[1])
    # cosine of a normalized vector with itself is 1.0
    sim = cosine_similarity_matrix(a[:1])
    assert abs(float(sim[0, 0]) - 1.0) < 1e-6


def test_cosine_dedup_keeps_first_occurrence_and_logs_drops():
    emb = HashEmbedder(dim=128)
    texts = [
        "ransomware containment summary for the leadership team",
        "ransomware containment summary for the leadership team",  # dup of 0
        "quarterly revenue variance versus budget by region",
        "OSINT collection plan for a named threat actor",
    ]
    e = emb.embed(texts)
    report = cosine_dedup(e, threshold=0.85)
    assert report.n_in == 4
    assert report.n_dropped == 1
    assert report.kept_indices == [0, 2, 3]
    assert report.dropped[0][0] == 0 and report.dropped[0][1] == 1


def test_cosine_dedup_passes_through_distinct_texts():
    emb = HashEmbedder(dim=128)
    texts = ["alpha bravo charlie", "delta echo foxtrot",
             "golf hotel india", "juliet kilo lima"]
    e = emb.embed(texts)
    report = cosine_dedup(e, threshold=0.85)
    assert report.n_kept == 4


def test_leakage_audit_flags_overlap_and_computes_rate():
    emb = HashEmbedder(dim=128)
    references = emb.embed([
        "the seed corpus contains a vulnerability triage example",
        "and an OSINT collection example",
    ])
    candidates = emb.embed([
        "the seed corpus contains a vulnerability triage example",  # dup
        "an unrelated financial expense analysis request",
    ])
    rep = leakage_audit(candidates, references, threshold=0.85)
    assert rep.n_candidates == 2 and rep.n_references == 2
    assert rep.flagged_indices == [0]
    assert abs(rep.overlap_rate - 0.5) < 1e-9
    assert rep.matches[0]["is_overlap"] is True
    assert rep.matches[1]["is_overlap"] is False


def test_leakage_audit_with_empty_references_returns_no_overlap():
    emb = HashEmbedder(dim=64)
    candidates = emb.embed(["some candidate text"])
    rep = leakage_audit(candidates, np.zeros((0, 64), dtype=np.float32))
    assert rep.flagged_indices == []
    assert rep.overlap_rate == 0.0
