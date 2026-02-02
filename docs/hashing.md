# Hashing and canonicalization

MANDATE uses hash-linked trace entries and an immutable anchor hash.

## Canonicalization

The paper references RFC 8785 (JSON Canonicalization Scheme, JCS).
**Important:** This repository implements a *pragmatic deterministic JSON encoding*:

- UTF-8
- `sort_keys=True`
- no extra whitespace
- stable separators

This is not a full RFC 8785 implementation (notably around number formatting and escaping edge cases).
If strict JCS compliance is required for interoperability, replace `mandate.hashing.canonical_json()` with a compliant implementation.

## Anchor hash

`anchor_hash = sha256(canonical_json(anchor_without_anchor_hash))`

## Trace entry hash

`entry.hash = sha256(canonical_json(entry_without_hash))`

## Trace chain hash

This repo defines a simple chain hash:

`chain_hash = sha256(canonical_json([entry.hash for entry in entries_in_order]))`

If you prefer a different construction (e.g., Merkle tree, hash chaining with parent pointers), document and version it.
