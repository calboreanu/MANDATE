from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Dict, List


def canonical_json(obj: Any) -> str:
    """
    Deterministic JSON encoding used for hashing.

    NOTE: This is a pragmatic canonicalization (sort_keys + stable separators).
    It is NOT a full RFC 8785 (JCS) implementation. See docs/hashing.md.
    """
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_anchor_hash(anchor: Dict[str, Any]) -> str:
    a = copy.deepcopy(anchor)
    a.pop("anchor_hash", None)
    return sha256_hex(canonical_json(a))


def compute_trace_entry_hash(entry: Dict[str, Any]) -> str:
    e = copy.deepcopy(entry)
    e.pop("hash", None)
    return sha256_hex(canonical_json(e))


def compute_chain_hash(entries: List[Dict[str, Any]]) -> str:
    """
    Simple chain hash: sha256(canonical_json([entry.hash for entry in entries_in_order])).
    """
    hashes = [e["hash"] for e in entries]
    return sha256_hex(canonical_json(hashes))


def compute_chain_hash_from_strings(hashes: List[str]) -> str:
    """
    Compute chain hash from a list of hash strings directly.
    
    This is used when trace entries are stored as hash references rather than
    embedded objects.
    """
    return sha256_hex(canonical_json(hashes))
