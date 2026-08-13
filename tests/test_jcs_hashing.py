"""
Tests for RFC 8785 (JCS) canonicalization and MANDATE hashing integrity.

Covers:
- RFC 8785 compliance: number serialization, key sorting, string escaping
- Legacy compatibility: JCS matches pragmatic encoding for MANDATE data
- Hash computation: anchor, trace entry, chain
- Edge cases: negative zero, unicode, deep nesting, empty structures
- Migration verification: legacy_canonical_json parity for typical data
"""

from __future__ import annotations

import hashlib
import json
import pytest

from mandate.hashing import (
    canonical_json,
    legacy_canonical_json,
    sha256_hex,
    sha256_bytes_hex,
    compute_anchor_hash,
    compute_trace_entry_hash,
    compute_chain_hash,
    compute_chain_hash_from_strings,
)


def test_deposited_record_hash_vectors():
    """Reproduce entry, chain, and anchor hashes from the evaluation deposit."""
    from pathlib import Path

    vectors_path = Path(__file__).parent / "fixtures" / "deposited_hash_vectors.json"
    vectors = json.loads(vectors_path.read_text(encoding="utf-8"))["vectors"]
    for vector in vectors:
        if "entry" in vector:
            assert compute_trace_entry_hash(vector["entry"]) == vector["expected_entry_hash"]
        if "expected_chain_hash" in vector:
            assert compute_chain_hash_from_strings(vector["entry_hashes"]) == vector["expected_chain_hash"]
        if "anchor" in vector:
            assert compute_anchor_hash(vector["anchor"]) == vector["expected_anchor_hash"]


# ── RFC 8785 Number Serialization ────────────────────────────────────


class TestJCSNumbers:
    """Verify RFC 8785 number serialization rules."""

    def test_integer(self):
        assert canonical_json(42) == "42"

    def test_negative_integer(self):
        assert canonical_json(-1) == "-1"

    def test_zero(self):
        assert canonical_json(0) == "0"

    def test_negative_zero_becomes_zero(self):
        """RFC 8785: -0.0 serializes as 0."""
        result = canonical_json(-0.0)
        assert result == "0", f"Expected '0', got '{result}'"

    def test_float_trailing_zeros_stripped(self):
        """4.50 → 4.5"""
        assert canonical_json(4.5) == "4.5"

    def test_float_precision(self):
        result = canonical_json(0.8)
        assert result == "0.8"

    def test_large_exponent(self):
        """1e30 should use exponent notation."""
        result = canonical_json(1e30)
        assert result == "1e+30"

    def test_small_exponent(self):
        """Very small numbers use exponent notation."""
        result = canonical_json(1e-30)
        assert result == "1e-30"

    def test_integer_float(self):
        """1.0 is an integer-valued float."""
        result = canonical_json(1.0)
        assert result == "1"

    def test_max_safe_integer(self):
        """JavaScript MAX_SAFE_INTEGER."""
        result = canonical_json(9007199254740991)
        assert result == "9007199254740991"

    def test_negative_max_safe_integer(self):
        result = canonical_json(-9007199254740991)
        assert result == "-9007199254740991"


# ── RFC 8785 Key Sorting ─────────────────────────────────────────────


class TestJCSKeySorting:
    """Verify RFC 8785 UTF-16 lexicographic key sorting."""

    def test_basic_sorting(self):
        obj = {"b": 2, "a": 1, "c": 3}
        result = canonical_json(obj)
        assert result == '{"a":1,"b":2,"c":3}'

    def test_numeric_string_keys(self):
        """Numeric string keys sort by UTF-16 code point, not numerically."""
        obj = {"10": "ten", "2": "two", "1": "one"}
        result = canonical_json(obj)
        assert result == '{"1":"one","10":"ten","2":"two"}'

    def test_recursive_sorting(self):
        obj = {"z": {"b": 2, "a": 1}, "a": 0}
        result = canonical_json(obj)
        assert result == '{"a":0,"z":{"a":1,"b":2}}'

    def test_mixed_case_keys(self):
        """Uppercase sorts before lowercase in UTF-16."""
        obj = {"b": 2, "A": 1}
        result = canonical_json(obj)
        assert result == '{"A":1,"b":2}'

    def test_empty_string_key(self):
        obj = {"": 0, "a": 1}
        result = canonical_json(obj)
        assert result == '{"":0,"a":1}'


# ── RFC 8785 String Escaping ─────────────────────────────────────────


class TestJCSStringEscaping:
    """Verify RFC 8785 string escaping rules."""

    def test_backslash_escaped(self):
        result = canonical_json("a\\b")
        assert result == '"a\\\\b"'

    def test_quote_escaped(self):
        result = canonical_json('a"b')
        assert result == '"a\\"b"'

    def test_newline_escaped(self):
        result = canonical_json("a\nb")
        assert result == '"a\\nb"'

    def test_tab_escaped(self):
        result = canonical_json("a\tb")
        assert result == '"a\\tb"'

    def test_unicode_preserved(self):
        """Non-ASCII characters preserved as-is (not escaped)."""
        result = canonical_json("café")
        assert result == '"café"'


# ── RFC 8785 Structural ──────────────────────────────────────────────


class TestJCSStructural:
    """Verify structural canonicalization."""

    def test_no_whitespace(self):
        obj = {"key": [1, 2, 3]}
        result = canonical_json(obj)
        assert " " not in result
        assert "\n" not in result

    def test_boolean_values(self):
        assert canonical_json(True) == "true"
        assert canonical_json(False) == "false"

    def test_null_value(self):
        assert canonical_json(None) == "null"

    def test_empty_object(self):
        assert canonical_json({}) == "{}"

    def test_empty_array(self):
        assert canonical_json([]) == "[]"

    def test_array_order_preserved(self):
        """RFC 8785: array element order is preserved, not sorted."""
        assert canonical_json([3, 1, 2]) == "[3,1,2]"

    def test_nested_empty_structures(self):
        obj = {"a": [], "b": {}}
        result = canonical_json(obj)
        assert result == '{"a":[],"b":{}}'


# ── Legacy Compatibility ─────────────────────────────────────────────


class TestLegacyCompatibility:
    """Verify JCS matches legacy encoding for MANDATE-typical data."""

    MANDATE_TYPICAL_DATA = [
        {"intent": "Assess security posture", "constraints": ["FORBIDS x"]},
        {"a": 1, "b": 2, "c": 3},
        ["hash1", "hash2", "hash3"],
        {"nested": {"z": 3, "a": 1}},
        {"risk_tolerance": {"max_autonomous_score": "LOW", "escalate_above": "MEDIUM"}},
        [],
        {},
        {"mission_id": "MANDATE-NM-001", "intent": "Test", "scope": ["10.0.1.0/24"]},
    ]

    @pytest.mark.parametrize("obj", MANDATE_TYPICAL_DATA)
    def test_jcs_matches_legacy(self, obj):
        """JCS output identical to legacy for typical MANDATE data."""
        assert canonical_json(obj) == legacy_canonical_json(obj)

    def test_negative_zero_differs(self):
        """The one known difference: -0.0 → '0' (JCS) vs '-0.0' (legacy)."""
        obj = {"val": -0.0}
        jcs = canonical_json(obj)
        legacy = legacy_canonical_json(obj)
        assert jcs == '{"val":0}'
        assert legacy == '{"val":-0.0}'
        assert jcs != legacy

    def test_legacy_function_still_works(self):
        """legacy_canonical_json still uses the old json.dumps approach."""
        obj = {"b": 2, "a": 1}
        result = legacy_canonical_json(obj)
        assert result == '{"a":1,"b":2}'


# ── Hash Computation ─────────────────────────────────────────────────


class TestHashComputation:
    """Test MANDATE hash computation functions."""

    def test_sha256_hex(self):
        result = sha256_hex("hello")
        assert len(result) == 64
        assert result == hashlib.sha256(b"hello").hexdigest()

    def test_sha256_bytes_hex(self):
        result = sha256_bytes_hex(b"hello")
        assert result == hashlib.sha256(b"hello").hexdigest()

    def test_sha256_hex_and_bytes_hex_agree(self):
        data = "test data"
        assert sha256_hex(data) == sha256_bytes_hex(data.encode("utf-8"))

    def test_compute_anchor_hash_deterministic(self):
        anchor = {"intent": "test", "constraints": [], "anchor_hash": "old_hash"}
        h1 = compute_anchor_hash(anchor)
        h2 = compute_anchor_hash(anchor)
        assert h1 == h2
        assert len(h1) == 64

    def test_compute_anchor_hash_excludes_anchor_hash_field(self):
        anchor_with = {"intent": "test", "anchor_hash": "some_hash"}
        anchor_without = {"intent": "test"}
        assert compute_anchor_hash(anchor_with) == compute_anchor_hash(anchor_without)

    def test_compute_anchor_hash_does_not_mutate(self):
        anchor = {"intent": "test", "anchor_hash": "keep_me"}
        compute_anchor_hash(anchor)
        assert anchor["anchor_hash"] == "keep_me"

    def test_compute_trace_entry_hash_deterministic(self):
        entry = {"role": "Intake", "action": "parse", "hash": "old"}
        h1 = compute_trace_entry_hash(entry)
        h2 = compute_trace_entry_hash(entry)
        assert h1 == h2
        assert len(h1) == 64

    def test_compute_trace_entry_hash_excludes_hash_field(self):
        with_hash = {"role": "Intake", "hash": "xyz"}
        without_hash = {"role": "Intake"}
        assert compute_trace_entry_hash(with_hash) == compute_trace_entry_hash(without_hash)

    def test_compute_trace_entry_hash_does_not_mutate(self):
        entry = {"role": "Intake", "hash": "keep_me"}
        compute_trace_entry_hash(entry)
        assert entry["hash"] == "keep_me"

    def test_compute_chain_hash_from_entries(self):
        entries = [
            {"hash": "aaa"},
            {"hash": "bbb"},
        ]
        result = compute_chain_hash(entries)
        assert len(result) == 64

    def test_compute_chain_hash_from_strings(self):
        result = compute_chain_hash_from_strings(["aaa", "bbb"])
        assert len(result) == 64

    def test_chain_hash_matches_between_methods(self):
        entries = [{"hash": "aaa"}, {"hash": "bbb"}]
        h1 = compute_chain_hash(entries)
        h2 = compute_chain_hash_from_strings(["aaa", "bbb"])
        assert h1 == h2

    def test_empty_chain_hash(self):
        """Hash of empty list is deterministic."""
        h = compute_chain_hash_from_strings([])
        assert len(h) == 64
        # Should be sha256 of JCS([]) = sha256("[]")
        expected = hashlib.sha256(b"[]").hexdigest()
        assert h == expected

    def test_chain_hash_order_matters(self):
        h1 = compute_chain_hash_from_strings(["aaa", "bbb"])
        h2 = compute_chain_hash_from_strings(["bbb", "aaa"])
        assert h1 != h2


# ── RFC 8785 Test Vectors (from RFC Appendix B) ─────────────────────


class TestRFC8785Vectors:
    """
    Test against known RFC 8785 canonicalization results.

    These vectors verify that MANDATE's canonical_json produces
    output consistent with the RFC 8785 specification.
    """

    def test_vector_sorted_keys(self):
        """Keys sorted in UTF-16 lexicographic order."""
        obj = {"peach": 1, "cherry": 2, "apple": 3}
        expected = '{"apple":3,"cherry":2,"peach":1}'
        assert canonical_json(obj) == expected

    def test_vector_nested_sorting(self):
        obj = {
            "1": {"f": {"f": "hi", "F": 5}, "": "empty"},
            "10": {},
            "": "empty",
            "a": {},
            "111": [{"e": "yes", "E": "no"}],
        }
        result = canonical_json(obj)
        parsed = json.loads(result)
        # Verify key order at top level
        keys = list(json.loads(result, object_pairs_hook=lambda pairs: pairs))
        top_keys = [k for k, v in keys]
        assert top_keys == ["", "1", "10", "111", "a"]

    def test_vector_number_formatting(self):
        """RFC 8785 number serialization test cases."""
        # Integers
        assert canonical_json(0) == "0"
        assert canonical_json(1) == "1"
        assert canonical_json(-1) == "-1"

        # Floats that look like integers
        assert canonical_json(1.0) == "1"
        assert canonical_json(0.0) == "0"

        # Standard floats
        assert canonical_json(0.5) == "0.5"
        assert canonical_json(-0.5) == "-0.5"

        # Large numbers
        assert canonical_json(1e20) == "100000000000000000000"

    def test_vector_string_escaping(self):
        """RFC 8785 string escaping: control chars, quotes, backslash."""
        # Tab
        assert canonical_json("\t") == '"\\t"'
        # Newline
        assert canonical_json("\n") == '"\\n"'
        # Backspace
        assert canonical_json("\b") == '"\\b"'
        # Form feed
        assert canonical_json("\f") == '"\\f"'
        # Carriage return
        assert canonical_json("\r") == '"\\r"'

    def test_vector_mixed_types(self):
        """Mixed type object."""
        obj = {
            "numbers": [333333333.33333329, 1e30, 4.5, 0.002, 1e-27, -0.0],
            "string": "hello",
            "bool_true": True,
            "bool_false": False,
            "null_val": None,
        }
        result = canonical_json(obj)
        parsed = json.loads(result)
        assert parsed["bool_true"] is True
        assert parsed["bool_false"] is False
        assert parsed["null_val"] is None
        assert parsed["string"] == "hello"

    def test_vector_negative_zero_in_array(self):
        """Negative zero in an array position."""
        assert canonical_json([-0.0]) == "[0]"

    def test_vector_deeply_nested(self):
        obj = {"a": {"b": {"c": {"d": 1}}}}
        expected = '{"a":{"b":{"c":{"d":1}}}}'
        assert canonical_json(obj) == expected

    def test_canonical_json_is_valid_json(self):
        """Output of canonical_json is always valid JSON."""
        test_objects = [
            {},
            [],
            42,
            "hello",
            True,
            None,
            {"key": [1, {"nested": True}]},
            {"unicode": "café naïve über"},
        ]
        for obj in test_objects:
            result = canonical_json(obj)
            parsed = json.loads(result)
            # Re-canonicalize to verify idempotence
            assert canonical_json(parsed) == result


# ── MANDATE Artifact Hash Integration ────────────────────────────────


class TestMandateArtifactHashing:
    """
    Verify hash computation for realistic MANDATE artifact structures.
    """

    def test_full_anchor_hash_cycle(self):
        """Build an anchor, compute its hash, embed it, verify it matches."""
        anchor = {
            "intent": "Identify vulnerabilities",
            "minimum_outcome": {"description": "Enumerate services"},
            "target_outcome": {"description": "Achieve initial access"},
            "constraints": [
                "target.scope IN ['10.0.1.0/24']",
                "FORBIDS data_exfiltration",
            ],
            "risk_tolerance": {
                "max_autonomous_score": "LOW",
                "escalate_above": "MEDIUM",
            },
        }
        h = compute_anchor_hash(anchor)
        anchor["anchor_hash"] = h
        # Recomputing should give the same hash (anchor_hash excluded)
        assert compute_anchor_hash(anchor) == h

    def test_trace_chain_integrity(self):
        """Build a trace chain and verify hashes link correctly."""
        entries = []
        for i, role in enumerate(["Intake", "Interpreter", "Decomposition"]):
            entry = {
                "role": role,
                "action": f"execute_stage_{i+1}",
                "mission_id": "MANDATE-TEST-001",
                "timestamp": "2026-02-11T12:00:00Z",
            }
            entry["hash"] = compute_trace_entry_hash(entry)
            entries.append(entry)

        chain = compute_chain_hash(entries)
        assert len(chain) == 64

        # Verify chain matches string-based computation
        hashes = [e["hash"] for e in entries]
        assert compute_chain_hash_from_strings(hashes) == chain

    def test_different_data_different_hashes(self):
        """Changing any field changes the hash."""
        base = {"intent": "test", "scope": ["a"]}
        h1 = compute_anchor_hash(base)

        modified = {"intent": "test", "scope": ["b"]}
        h2 = compute_anchor_hash(modified)

        assert h1 != h2
