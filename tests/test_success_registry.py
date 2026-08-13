"""Tests for mandate.success_registry — Success Registry and Similarity Matching."""
import json
import pytest
from pathlib import Path

from mandate.success_registry import (
    SuccessRecord,
    SuccessRegistry,
    SimilarityMatch,
    _tokenize,
    jaccard_similarity,
)


# ── Tokenization ────────────────────────────────────────────────────

class TestTokenization:
    def test_basic_tokenize(self):
        tokens = _tokenize("Identify vulnerabilities in web application")
        assert "identify" in tokens
        assert "vulnerabilities" in tokens
        assert "web" in tokens
        assert "application" in tokens
        assert "in" not in tokens  # stop word

    def test_stop_words_removed(self):
        tokens = _tokenize("the quick brown fox and a lazy dog")
        assert "the" not in tokens
        assert "and" not in tokens
        assert "a" not in tokens
        assert "quick" in tokens

    def test_empty_string(self):
        assert _tokenize("") == set()

    def test_single_char_excluded(self):
        tokens = _tokenize("a b c dd ee")
        assert "a" not in tokens
        assert "b" not in tokens
        assert "c" not in tokens
        assert "dd" in tokens
        assert "ee" in tokens

    def test_case_insensitive(self):
        tokens = _tokenize("RECON Scan EXPLOIT")
        assert "recon" in tokens
        assert "scan" in tokens
        assert "exploit" in tokens


class TestJaccardSimilarity:
    def test_identical_sets(self):
        assert jaccard_similarity({"a", "b"}, {"a", "b"}) == 1.0

    def test_disjoint_sets(self):
        assert jaccard_similarity({"a", "b"}, {"c", "d"}) == 0.0

    def test_partial_overlap(self):
        sim = jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"})
        assert abs(sim - 0.5) < 0.01  # 2/4 = 0.5

    def test_empty_both(self):
        assert jaccard_similarity(set(), set()) == 1.0

    def test_one_empty(self):
        assert jaccard_similarity({"a"}, set()) == 0.0
        assert jaccard_similarity(set(), {"a"}) == 0.0


# ── SuccessRecord ───────────────────────────────────────────────────

class TestSuccessRecord:
    def test_basic_creation(self):
        rec = SuccessRecord(
            record_id="SR-001",
            mandate_id="M-001",
            intent="Identify vulnerabilities",
        )
        assert rec.record_id == "SR-001"
        assert rec.mandate_id == "M-001"
        assert rec._intent_tokens == _tokenize("Identify vulnerabilities")

    def test_from_artifact(self):
        artifact = {
            "mandate_id": "M-001",
            "anchor": {
                "intent": "Scan network for vulns",
                "scope": ["10.0.0.0/24"],
                "constraints": ["execution.duration <= PT4H"],
            },
            "courses_of_action": [
                {
                    "coa_id": "COA-1",
                    "task_dag": {
                        "nodes": [
                            {"tool_ids": ["nmap"]},
                            {"tool_ids": ["nuclei"]},
                        ]
                    },
                    "risk_assessment": {"score": "LOW"},
                }
            ],
            "recommendation": {"primary_coa": "COA-1"},
        }
        rec = SuccessRecord.from_artifact(artifact, duration_ms=50.0, domain="pentest")
        assert rec.mandate_id == "M-001"
        assert rec.domain == "pentest"
        assert rec.duration_ms == 50.0
        assert rec.coa_count == 1
        assert rec.primary_coa_id == "COA-1"
        assert "nmap" in rec.tool_ids
        assert "nuclei" in rec.tool_ids
        assert rec.timestamp  # Should be auto-set

    def test_to_dict_and_from_dict(self):
        rec = SuccessRecord(
            record_id="SR-001",
            mandate_id="M-001",
            intent="Test intent",
            scope=["10.0.0.0/24"],
            constraints=["execution.duration <= PT4H"],
            tool_classes=["RECON", "SCAN"],
            tool_ids=["nmap", "nuclei"],
            domain="pentest",
            risk_level="LOW",
            coa_count=2,
            duration_ms=42.5,
        )
        d = rec.to_dict()
        rec2 = SuccessRecord.from_dict(d)
        assert rec2.record_id == rec.record_id
        assert rec2.mandate_id == rec.mandate_id
        assert rec2.intent == rec.intent
        assert rec2.tool_classes == rec.tool_classes
        assert rec2.duration_ms == 42.5

    def test_empty_artifact(self):
        rec = SuccessRecord.from_artifact({})
        assert rec.mandate_id == ""
        assert rec.coa_count == 0


# ── SuccessRegistry ─────────────────────────────────────────────────

class TestSuccessRegistryBasic:
    def test_empty_registry(self):
        reg = SuccessRegistry()
        assert len(reg) == 0
        assert reg.all_records() == []

    def test_record_from_artifact(self):
        reg = SuccessRegistry()
        artifact = {
            "mandate_id": "M-001",
            "anchor": {"intent": "Test", "constraints": []},
            "courses_of_action": [],
            "recommendation": {},
        }
        rec = reg.record(artifact, domain="pentest")
        assert len(reg) == 1
        assert reg.get_record(rec.record_id) is rec

    def test_add_and_remove(self):
        reg = SuccessRegistry()
        rec = SuccessRecord(record_id="SR-001", mandate_id="M-001", intent="test")
        reg.add_record(rec)
        assert len(reg) == 1
        assert reg.remove_record("SR-001") is True
        assert reg.remove_record("SR-001") is False
        assert len(reg) == 0

    def test_record_ids_sorted(self):
        reg = SuccessRegistry()
        reg.add_record(SuccessRecord(record_id="C", mandate_id="C", intent="c"))
        reg.add_record(SuccessRecord(record_id="A", mandate_id="A", intent="a"))
        reg.add_record(SuccessRecord(record_id="B", mandate_id="B", intent="b"))
        assert reg.record_ids() == ["A", "B", "C"]


class TestSuccessRegistrySimilarity:
    def _build_registry(self):
        reg = SuccessRegistry()
        # Pentest record
        reg.add_record(SuccessRecord(
            record_id="SR-PT-001",
            mandate_id="M-PT-001",
            intent="Identify exploitable vulnerabilities in external services",
            constraints=["execution.duration <= PT4H", "FORBIDS data_exfiltration"],
            tool_classes=["RECON", "SCAN", "EXPLOIT"],
            domain="pentest",
        ))
        # IR record
        reg.add_record(SuccessRecord(
            record_id="SR-IR-001",
            mandate_id="M-IR-001",
            intent="Contain and eradicate ransomware infection",
            constraints=["execution.duration <= PT8H", "FORBIDS unauthorized_shutdown"],
            tool_classes=["DETECT", "CONTAIN", "ERADICATE", "RECOVER"],
            domain="incident_response",
        ))
        # Another pentest
        reg.add_record(SuccessRecord(
            record_id="SR-PT-002",
            mandate_id="M-PT-002",
            intent="Scan external network for vulnerabilities and report findings",
            constraints=["execution.duration <= PT2H", "FORBIDS data_exfiltration"],
            tool_classes=["RECON", "SCAN"],
            domain="pentest",
        ))
        return reg

    def test_find_similar_intent(self):
        reg = self._build_registry()
        matches = reg.find_similar(
            intent="Identify vulnerabilities in network services",
            top_k=3,
        )
        assert len(matches) > 0
        # First match should be the most similar pentest record
        assert matches[0].record.domain == "pentest"

    def test_find_similar_with_domain_filter(self):
        reg = self._build_registry()
        matches = reg.find_similar(
            intent="Contain ransomware",
            domain="incident_response",
        )
        assert len(matches) > 0
        for m in matches:
            assert m.record.domain == "incident_response"

    def test_find_similar_with_tool_classes(self):
        reg = self._build_registry()
        matches = reg.find_similar(
            intent="",
            tool_classes=["RECON", "SCAN"],
        )
        assert len(matches) > 0
        # Pentest records should score higher on tool class
        pentest_matches = [m for m in matches if m.record.domain == "pentest"]
        assert len(pentest_matches) > 0

    def test_find_similar_with_constraints(self):
        reg = self._build_registry()
        matches = reg.find_similar(
            intent="",
            constraints=["FORBIDS data_exfiltration", "execution.duration <= PT4H"],
        )
        assert len(matches) > 0

    def test_find_similar_empty_registry(self):
        reg = SuccessRegistry()
        matches = reg.find_similar(intent="anything")
        assert matches == []

    def test_min_score_filter(self):
        reg = self._build_registry()
        matches = reg.find_similar(
            intent="Completely unrelated quantum computing task",
            min_score=0.5,
        )
        # Very dissimilar intent should yield no high-score matches
        assert len(matches) == 0 or all(m.overall_score >= 0.5 for m in matches)

    def test_custom_weights(self):
        reg = self._build_registry()
        # Weight tool_class heavily
        matches = reg.find_similar(
            intent="anything",
            tool_classes=["DETECT", "CONTAIN"],
            weights={"intent": 0.0, "constraint": 0.0, "tool_class": 1.0},
        )
        if matches:
            # IR record should score highest with these tools
            assert matches[0].record.domain == "incident_response"

    def test_top_k(self):
        reg = self._build_registry()
        matches = reg.find_similar(intent="vulnerabilities", top_k=1)
        assert len(matches) <= 1


class TestSuccessRegistryQueries:
    def test_find_by_domain(self):
        reg = SuccessRegistry()
        reg.add_record(SuccessRecord(
            record_id="A", mandate_id="A", intent="a",
            domain="pentest", timestamp="2026-01-01T00:00:00Z",
        ))
        reg.add_record(SuccessRecord(
            record_id="B", mandate_id="B", intent="b",
            domain="ir", timestamp="2026-01-02T00:00:00Z",
        ))
        results = reg.find_by_domain("pentest")
        assert len(results) == 1
        assert results[0].record_id == "A"

    def test_find_by_tool_class(self):
        reg = SuccessRegistry()
        reg.add_record(SuccessRecord(
            record_id="A", mandate_id="A", intent="a",
            tool_classes=["RECON", "SCAN"],
        ))
        reg.add_record(SuccessRecord(
            record_id="B", mandate_id="B", intent="b",
            tool_classes=["EXPLOIT"],
        ))
        results = reg.find_by_tool_class("RECON")
        assert len(results) == 1
        assert results[0].record_id == "A"


class TestSuccessRegistryPersistence:
    def test_save_and_load(self, tmp_path):
        reg = SuccessRegistry()
        reg.add_record(SuccessRecord(
            record_id="SR-001",
            mandate_id="M-001",
            intent="Test persistence",
            domain="pentest",
            tool_classes=["RECON"],
            duration_ms=25.0,
        ))
        reg.add_record(SuccessRecord(
            record_id="SR-002",
            mandate_id="M-002",
            intent="Another test",
            domain="ir",
        ))

        path = tmp_path / "registry.json"
        reg.save(path)

        # Load and verify
        reg2 = SuccessRegistry.load(path)
        assert len(reg2) == 2
        r = reg2.get_record("SR-001")
        assert r is not None
        assert r.intent == "Test persistence"
        assert r.domain == "pentest"
        assert r.duration_ms == 25.0

    def test_load_nonexistent(self, tmp_path):
        reg = SuccessRegistry.load(tmp_path / "nope.json")
        assert len(reg) == 0

    def test_merge(self):
        reg1 = SuccessRegistry()
        reg1.add_record(SuccessRecord(record_id="A", mandate_id="A", intent="a"))
        reg1.add_record(SuccessRecord(record_id="B", mandate_id="B", intent="b"))

        reg2 = SuccessRegistry()
        reg2.add_record(SuccessRecord(record_id="B", mandate_id="B", intent="b"))
        reg2.add_record(SuccessRecord(record_id="C", mandate_id="C", intent="c"))

        added = reg1.merge(reg2)
        assert added == 1  # Only C is new
        assert len(reg1) == 3

    def test_stats(self):
        reg = SuccessRegistry()
        reg.add_record(SuccessRecord(
            record_id="A", mandate_id="A", intent="a",
            domain="pentest", tool_classes=["RECON", "SCAN"],
        ))
        reg.add_record(SuccessRecord(
            record_id="B", mandate_id="B", intent="b",
            domain="pentest", tool_classes=["RECON"],
        ))
        reg.add_record(SuccessRecord(
            record_id="C", mandate_id="C", intent="c",
            domain="ir", tool_classes=["DETECT"],
        ))

        stats = reg.stats()
        assert stats["total_records"] == 3
        assert stats["domains"]["pentest"] == 2
        assert stats["domains"]["ir"] == 1
        assert stats["tool_class_usage"]["RECON"] == 2

    def test_to_dict(self):
        reg = SuccessRegistry()
        reg.add_record(SuccessRecord(record_id="A", mandate_id="A", intent="a"))
        d = reg.to_dict()
        assert d["registry_version"] == "2.0.0"
        assert d["record_count"] == 1
        assert "A" in d["records"]


class TestSimilarityMatch:
    def test_to_dict(self):
        rec = SuccessRecord(
            record_id="SR-001",
            mandate_id="M-001",
            intent="Short intent for dict test",
        )
        match = SimilarityMatch(
            record=rec,
            overall_score=0.75,
            intent_score=0.8,
            constraint_score=0.6,
            tool_class_score=0.9,
        )
        d = match.to_dict()
        assert d["record_id"] == "SR-001"
        assert d["overall_score"] == 0.75
        assert d["intent_score"] == 0.8
