"""
Embeddings, cosine deduplication, and leakage audit (Workstream C2).

PLAYBOOK Phase 2 deduplicates candidate tasks at cosine 0.85, with the
"20 distinct / 20 paraphrase" calibration sanity check, and the same
similarity gate (0.85) drives the data-leakage audit against the MANDATE
training corpus, the Success Registry seed examples, and the PROMPTS
scaffolding examples (PROTOCOL_LOCK Section 13). PROTOCOL_LOCK halts the
study if the audit finds more than 5% overlap.

This module supplies two embedder backends:

  SentenceTransformerEmbedder
      The production embedder. Uses the model the ANALYSIS_PLAN environment
      pins (the caller can override). Imported lazily so the rest of the
      module remains importable without the package installed.

  HashEmbedder
      A deterministic, dependency-free embedder used by unit tests and as
      a smoke path on minimal environments. Identical strings produce
      identical vectors; otherwise similarity is reflective of token
      overlap, not semantic distance. It is **not** a substitute for the
      sentence-transformer at the 0.85 gate, and tests that depend on the
      cosine being a meaningful semantic similarity must use the production
      embedder; tests of the dedup / leakage logic itself work fine with
      hashed embeddings.

`cosine_dedup` returns the indices to keep (the first occurrence wins) and
the list of (kept_idx, dropped_idx, similarity) triples for the corpus log.
`leakage_audit` reports, for each candidate, its top reference match and
flags candidates whose top similarity meets or exceeds the threshold.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

DEFAULT_SIMILARITY_THRESHOLD = 0.85
DEFAULT_ST_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class Embedder:
    """Interface: embed a list of texts to a numpy array of shape (n, d)."""

    def embed(self, texts) -> np.ndarray:
        raise NotImplementedError

    def describe(self) -> dict:
        return {"name": type(self).__name__}


class SentenceTransformerEmbedder(Embedder):
    """The production embedder. Imports sentence-transformers lazily."""

    def __init__(self, model_name: str = DEFAULT_ST_MODEL,
                 normalize: bool = True):
        self.model_name = model_name
        self.normalize = normalize
        self._model = None

    def _ensure(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, texts) -> np.ndarray:
        model = self._ensure()
        emb = model.encode(list(texts),
                           normalize_embeddings=self.normalize,
                           convert_to_numpy=True)
        return np.asarray(emb, dtype=np.float32)

    def describe(self) -> dict:
        return {"name": "SentenceTransformerEmbedder",
                "model_name": self.model_name, "normalize": self.normalize}


class HashEmbedder(Embedder):
    """Deterministic token-hash embedder. Identical inputs produce identical
    vectors; cosine similarity reflects token overlap. Useful for unit
    tests and a no-dependency smoke path."""

    def __init__(self, dim: int = 256):
        if dim <= 0:
            raise ValueError("dim must be > 0")
        self.dim = dim

    def _vec(self, text: str) -> np.ndarray:
        v = np.zeros(self.dim, dtype=np.float32)
        toks = [t for t in (text or "").lower().split() if t]
        for tok in toks:
            h = int(hashlib.blake2b(tok.encode("utf-8"),
                                    digest_size=8).hexdigest(), 16)
            v[h % self.dim] += 1.0
        n = float(np.linalg.norm(v))
        return v / n if n > 0 else v

    def embed(self, texts) -> np.ndarray:
        return np.stack([self._vec(t) for t in texts]) if texts \
            else np.zeros((0, self.dim), dtype=np.float32)

    def describe(self) -> dict:
        return {"name": "HashEmbedder", "dim": self.dim}


def cosine_similarity_matrix(a: np.ndarray,
                             b: Optional[np.ndarray] = None) -> np.ndarray:
    """Pairwise cosine similarity. If b is None, return the n x n
    similarity of a against itself. Inputs may or may not already be
    L2-normalized; this function normalizes before the dot."""
    if a.size == 0:
        return np.zeros((0, 0 if b is None else b.shape[0]), dtype=np.float32)

    def _norm(x):
        n = np.linalg.norm(x, axis=1, keepdims=True)
        n[n == 0] = 1.0
        return x / n

    an = _norm(np.asarray(a, dtype=np.float32))
    if b is None:
        return (an @ an.T).astype(np.float32)
    bn = _norm(np.asarray(b, dtype=np.float32))
    return (an @ bn.T).astype(np.float32)


@dataclass
class DedupReport:
    n_in: int
    n_kept: int
    n_dropped: int
    threshold: float
    kept_indices: list = field(default_factory=list)
    dropped: list = field(default_factory=list)
    # `dropped` is a list of (kept_idx, dropped_idx, similarity)

    def to_dict(self) -> dict:
        return {"n_in": self.n_in, "n_kept": self.n_kept,
                "n_dropped": self.n_dropped, "threshold": self.threshold,
                "kept_indices": list(self.kept_indices),
                "dropped": [{"kept_idx": k, "dropped_idx": d,
                              "similarity": float(s)}
                             for k, d, s in self.dropped]}


def cosine_dedup(embeddings: np.ndarray,
                 threshold: float = DEFAULT_SIMILARITY_THRESHOLD
                 ) -> DedupReport:
    """Drop near-duplicates above `threshold`, first occurrence wins.

    The function is greedy and deterministic: it scans by input order; if
    candidate i has cosine >= threshold with any already-kept j (j < i), i
    is dropped with that j recorded as its match. This matches the package's
    "first-occurrence" dedup convention and makes the corpus log auditable.
    """
    n = int(embeddings.shape[0])
    if n == 0:
        return DedupReport(n_in=0, n_kept=0, n_dropped=0,
                           threshold=threshold)
    sim = cosine_similarity_matrix(embeddings)
    kept = []
    dropped = []
    for i in range(n):
        match = None
        for j in kept:
            if float(sim[i, j]) >= threshold:
                match = (j, float(sim[i, j]))
                break
        if match is None:
            kept.append(i)
        else:
            dropped.append((match[0], i, match[1]))
    return DedupReport(n_in=n, n_kept=len(kept), n_dropped=len(dropped),
                       threshold=threshold, kept_indices=kept,
                       dropped=dropped)


@dataclass
class LeakageReport:
    """The leakage audit against one or more reference corpora."""
    threshold: float
    n_candidates: int
    n_references: int
    flagged_indices: list = field(default_factory=list)
    matches: list = field(default_factory=list)
    # `matches` is per-candidate: {candidate_idx, best_ref_idx, similarity,
    # is_overlap}. `flagged_indices` is the subset where similarity >=
    # threshold.

    @property
    def overlap_rate(self) -> float:
        if self.n_candidates == 0:
            return 0.0
        return len(self.flagged_indices) / self.n_candidates

    def to_dict(self) -> dict:
        return {"threshold": self.threshold,
                "n_candidates": self.n_candidates,
                "n_references": self.n_references,
                "n_flagged": len(self.flagged_indices),
                "overlap_rate": self.overlap_rate,
                "flagged_indices": list(self.flagged_indices),
                "matches": list(self.matches)}


def leakage_audit(candidate_embeddings: np.ndarray,
                  reference_embeddings: np.ndarray,
                  threshold: float = DEFAULT_SIMILARITY_THRESHOLD
                  ) -> LeakageReport:
    """For each candidate, find its top reference match and flag overlaps.

    PROTOCOL_LOCK Section 13 halts on overlap above 5% of the candidate
    set; the caller decides whether to substitute or regenerate the flagged
    tasks. This function returns the evidence, not the halt decision.
    """
    n_c = int(candidate_embeddings.shape[0])
    n_r = int(reference_embeddings.shape[0]) if reference_embeddings.size else 0
    if n_c == 0:
        return LeakageReport(threshold=threshold, n_candidates=0,
                             n_references=n_r)
    if n_r == 0:
        return LeakageReport(threshold=threshold, n_candidates=n_c,
                             n_references=0,
                             matches=[{"candidate_idx": i,
                                       "best_ref_idx": None,
                                       "similarity": 0.0,
                                       "is_overlap": False}
                                      for i in range(n_c)])
    sim = cosine_similarity_matrix(candidate_embeddings,
                                    reference_embeddings)
    matches = []
    flagged = []
    for i in range(n_c):
        j = int(np.argmax(sim[i]))
        s = float(sim[i, j])
        is_overlap = s >= threshold
        if is_overlap:
            flagged.append(i)
        matches.append({"candidate_idx": i, "best_ref_idx": j,
                        "similarity": s, "is_overlap": is_overlap})
    return LeakageReport(threshold=threshold, n_candidates=n_c,
                         n_references=n_r, flagged_indices=flagged,
                         matches=matches)
