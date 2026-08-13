"""
MANDATE Success Registry

Provides precedent storage for successful mandate executions and
a query interface for finding similar past mandates based on anchor
similarity (intent tokens, constraint overlap, tool class coverage).

The registry is a lightweight JSON-backed store designed for local use
during pipeline evaluation. It does NOT require a database — all
records are stored in a single JSON file.

Usage:
    from mandate.success_registry import SuccessRegistry

    reg = SuccessRegistry.load("registry.json")
    reg.record(artifact, metrics)
    reg.save("registry.json")

    matches = reg.find_similar(intent="Identify vulnerabilities", top_k=3)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


# ── Tokenization ────────────────────────────────────────────────────

_STOP_WORDS = frozenset({
    "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or",
    "is", "are", "was", "were", "be", "been", "being", "with", "from",
    "by", "as", "this", "that", "it", "its", "all", "any", "each",
    "via", "into", "than",
})

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_/-]+")


def _tokenize(text: str) -> Set[str]:
    """Tokenize text into a set of lowercase tokens, excluding stop words."""
    tokens = set()
    for match in _TOKEN_RE.finditer(text.lower()):
        tok = match.group()
        if tok not in _STOP_WORDS and len(tok) > 1:
            tokens.add(tok)
    return tokens


def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Compute Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


# ── Data Models ─────────────────────────────────────────────────────


@dataclass
class SuccessRecord:
    """
    A record of a successful mandate execution.

    Stores the anchor summary, tool classes used, constraints,
    and execution metrics for similarity matching.
    """
    record_id: str
    mandate_id: str
    intent: str
    scope: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    tool_classes: List[str] = field(default_factory=list)
    tool_ids: List[str] = field(default_factory=list)
    domain: str = ""
    risk_level: str = ""
    coa_count: int = 0
    primary_coa_id: str = ""
    duration_ms: float = 0.0
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Pre-computed token sets for fast similarity queries
    _intent_tokens: Set[str] = field(default_factory=set, repr=False)
    _constraint_tokens: Set[str] = field(default_factory=set, repr=False)

    def __post_init__(self) -> None:
        if not self._intent_tokens:
            self._intent_tokens = _tokenize(self.intent)
        if not self._constraint_tokens:
            all_c = " ".join(self.constraints)
            self._constraint_tokens = _tokenize(all_c)

    @classmethod
    def from_artifact(cls, artifact: Dict[str, Any],
                      duration_ms: float = 0.0,
                      domain: str = "",
                      record_id: str = "") -> SuccessRecord:
        """Create a SuccessRecord from a mandate-as-code artifact."""
        anchor = artifact.get("anchor", {})
        rec = artifact.get("recommendation", {})
        coas = artifact.get("courses_of_action", [])

        # Extract all tool IDs and classes from COAs
        tool_ids: List[str] = []
        tool_classes: Set[str] = set()
        for coa in coas:
            for node in coa.get("task_dag", {}).get("nodes", []):
                tool_ids.extend(node.get("tool_ids", []))

        # Risk level from first COA
        risk_level = ""
        if coas:
            ra = coas[0].get("risk_assessment", {})
            risk_level = ra.get("score", "")

        mandate_id = artifact.get("mandate_id", "")
        if not record_id:
            record_id = f"SR-{mandate_id}"

        return cls(
            record_id=record_id,
            mandate_id=mandate_id,
            intent=anchor.get("intent", ""),
            scope=anchor.get("scope", []),
            constraints=anchor.get("constraints", []),
            tool_classes=sorted(tool_classes),
            tool_ids=sorted(set(tool_ids)),
            domain=domain,
            risk_level=risk_level,
            coa_count=len(coas),
            primary_coa_id=rec.get("primary_coa", ""),
            duration_ms=duration_ms,
            timestamp=datetime.now(timezone.utc).isoformat(
                timespec="milliseconds"
            ).replace("+00:00", "Z"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "mandate_id": self.mandate_id,
            "intent": self.intent,
            "scope": self.scope,
            "constraints": self.constraints,
            "tool_classes": self.tool_classes,
            "tool_ids": self.tool_ids,
            "domain": self.domain,
            "risk_level": self.risk_level,
            "coa_count": self.coa_count,
            "primary_coa_id": self.primary_coa_id,
            "duration_ms": round(self.duration_ms, 3),
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> SuccessRecord:
        return cls(
            record_id=d["record_id"],
            mandate_id=d["mandate_id"],
            intent=d.get("intent", ""),
            scope=d.get("scope", []),
            constraints=d.get("constraints", []),
            tool_classes=d.get("tool_classes", []),
            tool_ids=d.get("tool_ids", []),
            domain=d.get("domain", ""),
            risk_level=d.get("risk_level", ""),
            coa_count=d.get("coa_count", 0),
            primary_coa_id=d.get("primary_coa_id", ""),
            duration_ms=d.get("duration_ms", 0.0),
            timestamp=d.get("timestamp", ""),
            metadata=d.get("metadata", {}),
        )


@dataclass
class SimilarityMatch:
    """A similarity match result from the registry."""
    record: SuccessRecord
    overall_score: float
    intent_score: float
    constraint_score: float
    tool_class_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record.record_id,
            "mandate_id": self.record.mandate_id,
            "intent": self.record.intent[:100],
            "overall_score": round(self.overall_score, 4),
            "intent_score": round(self.intent_score, 4),
            "constraint_score": round(self.constraint_score, 4),
            "tool_class_score": round(self.tool_class_score, 4),
        }


# ── Success Registry ────────────────────────────────────────────────


class SuccessRegistry:
    """
    Precedent storage for successful mandate executions.

    Stores SuccessRecords and provides similarity-based queries
    for finding similar past mandates. Backed by a JSON file.
    """

    def __init__(self) -> None:
        self._records: Dict[str, SuccessRecord] = {}

    def __len__(self) -> int:
        return len(self._records)

    def __repr__(self) -> str:
        return f"SuccessRegistry({len(self._records)} records)"

    # ── Record Management ───────────────────────────────────────────

    def record(self, artifact: Dict[str, Any],
               duration_ms: float = 0.0,
               domain: str = "",
               record_id: str = "") -> SuccessRecord:
        """
        Record a successful mandate execution.

        Args:
            artifact: The mandate-as-code artifact dict
            duration_ms: Pipeline execution time
            domain: Domain identifier (e.g., "pentest", "incident_response")
            record_id: Custom record ID (auto-generated if empty)

        Returns:
            The created SuccessRecord
        """
        rec = SuccessRecord.from_artifact(
            artifact,
            duration_ms=duration_ms,
            domain=domain,
            record_id=record_id,
        )
        self._records[rec.record_id] = rec
        return rec

    def add_record(self, record: SuccessRecord) -> None:
        """Add a pre-built SuccessRecord."""
        self._records[record.record_id] = record

    def get_record(self, record_id: str) -> Optional[SuccessRecord]:
        """Get a record by ID."""
        return self._records.get(record_id)

    def remove_record(self, record_id: str) -> bool:
        """Remove a record by ID. Returns True if found."""
        return self._records.pop(record_id, None) is not None

    def all_records(self) -> List[SuccessRecord]:
        """Return all records sorted by record_id."""
        return sorted(self._records.values(), key=lambda r: r.record_id)

    def record_ids(self) -> List[str]:
        """Return all record IDs sorted."""
        return sorted(self._records.keys())

    # ── Similarity Queries ──────────────────────────────────────────

    def find_similar(
        self,
        intent: str = "",
        constraints: Optional[List[str]] = None,
        tool_classes: Optional[List[str]] = None,
        domain: str = "",
        top_k: int = 5,
        min_score: float = 0.0,
        weights: Optional[Dict[str, float]] = None,
    ) -> List[SimilarityMatch]:
        """
        Find records similar to the given query.

        Similarity is computed as a weighted combination of:
        - Intent token Jaccard similarity (default weight: 0.5)
        - Constraint token Jaccard similarity (default weight: 0.3)
        - Tool class set Jaccard similarity (default weight: 0.2)

        Args:
            intent: Intent text to match against
            constraints: Constraint strings to match against
            tool_classes: Tool class names to match against
            domain: If provided, only match within this domain
            top_k: Maximum number of results to return
            min_score: Minimum overall similarity score threshold
            weights: Custom weights for {intent, constraint, tool_class}

        Returns:
            List of SimilarityMatch objects, sorted by descending score
        """
        if not self._records:
            return []

        w = weights or {}
        w_intent = w.get("intent", 0.5)
        w_constraint = w.get("constraint", 0.3)
        w_tool = w.get("tool_class", 0.2)

        query_intent_tokens = _tokenize(intent)
        query_constraint_tokens = _tokenize(
            " ".join(constraints) if constraints else ""
        )
        query_tool_set = set(tool_classes) if tool_classes else set()

        matches: List[SimilarityMatch] = []

        for rec in self._records.values():
            # Filter by domain if specified
            if domain and rec.domain and rec.domain != domain:
                continue

            intent_sim = jaccard_similarity(query_intent_tokens, rec._intent_tokens)
            constraint_sim = jaccard_similarity(
                query_constraint_tokens, rec._constraint_tokens
            )
            tool_sim = jaccard_similarity(query_tool_set, set(rec.tool_classes))

            overall = (
                w_intent * intent_sim
                + w_constraint * constraint_sim
                + w_tool * tool_sim
            )

            if overall >= min_score:
                matches.append(SimilarityMatch(
                    record=rec,
                    overall_score=overall,
                    intent_score=intent_sim,
                    constraint_score=constraint_sim,
                    tool_class_score=tool_sim,
                ))

        # Sort by overall score descending
        matches.sort(key=lambda m: m.overall_score, reverse=True)
        return matches[:top_k]

    def find_by_domain(self, domain: str) -> List[SuccessRecord]:
        """Return all records for a given domain, sorted by timestamp."""
        return sorted(
            [r for r in self._records.values() if r.domain == domain],
            key=lambda r: r.timestamp,
        )

    def find_by_tool_class(self, tool_class: str) -> List[SuccessRecord]:
        """Return all records that used a specific tool class."""
        return [
            r for r in self._records.values()
            if tool_class in r.tool_classes
        ]

    # ── Persistence ─────────────────────────────────────────────────

    def save(self, path: str | Path) -> None:
        """Save registry to a JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "registry_version": "2.0.0",
            "record_count": len(self._records),
            "records": {
                rid: rec.to_dict()
                for rid, rec in sorted(self._records.items())
            },
        }
        p.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> SuccessRegistry:
        """Load registry from a JSON file."""
        p = Path(path)
        if not p.exists():
            return cls()

        raw = json.loads(p.read_text(encoding="utf-8"))
        reg = cls()
        for rid, rdata in raw.get("records", {}).items():
            rec = SuccessRecord.from_dict(rdata)
            reg._records[rec.record_id] = rec
        return reg

    def to_dict(self) -> Dict[str, Any]:
        """Serialize registry to dict."""
        return {
            "registry_version": "2.0.0",
            "record_count": len(self._records),
            "records": {
                rid: rec.to_dict()
                for rid, rec in sorted(self._records.items())
            },
        }

    def merge(self, other: SuccessRegistry) -> int:
        """
        Merge records from another registry. Returns count of new records added.
        Existing records (same record_id) are not overwritten.
        """
        added = 0
        for rid, rec in other._records.items():
            if rid not in self._records:
                self._records[rid] = rec
                added += 1
        return added

    def stats(self) -> Dict[str, Any]:
        """Return summary statistics about the registry."""
        domains: Dict[str, int] = {}
        tool_class_counts: Dict[str, int] = {}
        for rec in self._records.values():
            d = rec.domain or "unknown"
            domains[d] = domains.get(d, 0) + 1
            for tc in rec.tool_classes:
                tool_class_counts[tc] = tool_class_counts.get(tc, 0) + 1
        return {
            "total_records": len(self._records),
            "domains": domains,
            "tool_class_usage": tool_class_counts,
        }
