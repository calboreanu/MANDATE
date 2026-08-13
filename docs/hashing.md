# Hashing and Canonicalization

MANDATE uses hash-linked trace entries and an immutable anchor hash.
All hashing is performed over **RFC 8785 (JCS)** canonical JSON.

## Canonicalization

As of **v1.3.0**, `mandate.hashing.canonical_json()` delegates to the
[`rfc8785`](https://pypi.org/project/rfc8785/) library (Trail of Bits),
which implements the full JSON Canonicalization Scheme per RFC 8785:

- ECMAScript-compatible number serialization (IEEE 754 doubles)
- UTF-16 lexicographic key sorting (recursive, locale-independent)
- Minimal encoding (no whitespace between tokens)
- Control characters escaped as `\uXXXX`; no Unicode normalization
- Negative zero (`-0.0`) serialized as `0` per ECMA-262

For MANDATE's typical data (string/integer keys, no negative-zero values)
the JCS output is **byte-identical** to the v1.0–v1.2 pragmatic encoding,
so existing artifact hashes remain valid.

## Legacy support

`legacy_canonical_json()` preserves the v1.0–v1.2 pragmatic behaviour
(`json.dumps(sort_keys=True, separators=(",",":"))`) for offline
verification of artifacts produced before the RFC 8785 migration.

## Migration guide (v1.2 → v1.3)

1. **No hash changes for normal artifacts.**  MANDATE data uses strings,
   integers, and nested dicts — all of which produce identical output
   under both the old and new implementations.

2. **Edge case: `-0.0`.**  If any artifact contained negative-zero as a
   JSON number, the JCS output differs (`0` instead of `-0.0`).  This is
   extremely unlikely in MANDATE data.

3. **Verification.**  To verify an old artifact against both schemes:

       from mandate.hashing import canonical_json, legacy_canonical_json
       assert canonical_json(obj) == legacy_canonical_json(obj)

4. **New dependency.**  `rfc8785>=0.1.4` is now a required dependency
   (pure Python, zero transitive deps).

The repository test suite includes the RFC examples and edge cases plus
vectors extracted from the deposited MANDATE evaluation records. These vectors
cover entry, chain, and anchor hashes and guard against regression to
`json.dumps(sort_keys=True)`.

## Result execution state

Hash validity and artifact-schema validity do not imply executability. The
`mandate-result-envelope.schema.json` contract records the artifact
representation separately from `execution_state`. The envelope schema checks
state/summary consistency; `mandate.execution_contract.validate_result_envelope`
also re-derives the blocking-or-insufficient summary from the raw gap payload.

## Anchor hash

`anchor_hash = sha256(jcs(anchor_without_anchor_hash))`

## Trace entry hash

`entry.hash = sha256(jcs(entry_without_hash))`

## Trace chain hash

This repo defines a simple chain hash:

`chain_hash = sha256(jcs([entry.hash for entry in entries_in_order]))`

If you prefer a different construction (e.g., Merkle tree, hash chaining
with parent pointers), document and version it.
