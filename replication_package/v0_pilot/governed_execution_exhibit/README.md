# Governed Execution Exhibit: Offensive-Security COA (pilot)

**What this is.** A single end-to-end run of the AEGIS reference
implementation executing a penetration-testing course of action through
the full MANDATE -> LATTICE -> TRACE governed-execution path. It is the
artifact behind the "governed offensive-security COA execution" pilot
result in the paper (Section 6.1).

**Scope and honest boundary.** Tool backends are **simulated by ethical
design** (`aegis-emulator-runner/trace_phase.py` builds stub nmap,
nuclei, and metasploit implementations that return fixed results). This
exhibit validates the *specification-to-governed-execution path*, i.e.
that an offensive-security COA can be specified as mandate-as-code,
authorized, gated, sequenced, and evidence-logged. It does **not** test
exploitation efficacy against live targets, which is out of scope for a
specification framework and is left to operators under their own rules
of engagement. All targets are non-routable (RFC 1918 `10.0.1.0/24`)
and the only hostname is the reserved `acme.example.com` (RFC 2606).

**Mission.** `AEGIS-NORMAL-001`. Anchor mission intent: "Identify
exploitable vulnerabilities in external-facing services." Anchor
constraints include `FORBIDS data_exfiltration`, `FORBIDS
destructive_action`, `execution.duration <= PT4H`, and a target-scope
whitelist. Three COAs form a tolerance corridor (COA-1 passive recon
only; COA-2 active scanning + validation + exploit attempts; COA-3 full
aggressive). The recommendation selects COA-2 with fallback sequence
[COA-1, COA-3].

## Contents

| Path | What it is |
|---|---|
| `bundles/mandate_output.json` | The mandate-as-code artifact (anchor, 3 COAs, recommendation, trace) |
| `bundles/approved_bundle.json` | The signed approved bundle (COA-2 selected) |
| `bundles/policy.json` | The authorization policy evaluated by LATTICE |
| `output/evidence_chain.jsonl` | 8-record hash-linked, ECDSA-signed evidence chain (OPERATION_START -> 5x TOOL_INVOCATION -> CHAIN_SEALED) |
| `output/audit_log.jsonl` | LATTICE audit log (12 ALLOW verdicts; bundle approvals) |
| `keys/public_key.pem` | Public key for evidence-chain signature verification (private key intentionally excluded) |
| `scenario/mission_definition.py` | The scenario definition: COA task DAGs and the tool-to-MITRE-ATT&CK-TTP bindings (T1595, T1046, T1190) |

## Artifact caveats (honest disclosure)

- **Tool backends are simulated** (see Scope above). The evidence chain
  contains a stub `exploit_success: true` field emitted by the
  simulated metasploit backend; it is simulated output and is not
  evidence of exploitation against a real target. No paper claim rests
  on it.
- **The COA-2 `task_dag` in `mandate_output.json` contains a known
  duplicate node id (`12`) and a duplicate edge (`11 -> 12`)** in this
  demo scenario definition. It does not affect the executed five-tool
  sequence or evidence-chain verification, and is left as-is rather than
  silently corrected.
- **The authorization audit log and the execution evidence chain are
  separate records of the demo run.** `output/audit_log.jsonl` records
  multiple bundle approvals (rotating bundle hashes) from the
  authorization layer; `output/evidence_chain.jsonl` is a single sealed
  execution operation (`operation_id e218f74c...`, bundle hash
  `7d43...`). They are each internally consistent and independently
  verifiable, but are not cross-linked by a shared bundle hash, so the
  deposit does not assert one unbroken authorize-to-execute hash lineage.

## Verify

The evidence chain is validated by the reference implementation's own
verifier. From an AEGIS checkout with `trace_runtime` on the path:

```python
import json
from pathlib import Path
from trace_runtime.evidence import verify_chain
chain = [json.loads(l) for l in open("output/evidence_chain.jsonl")]
bundle_hash = chain[0]["context"]["bundle_hash"]
ok, errors = verify_chain(chain, bundle_hash, Path("keys/public_key.pem"))
assert ok and not errors, errors
```

Verified 2026-07-11: `verify_chain` returns `(True, [])`. The chain is
genesis-anchored (`previous_hash_hex` all-zero on record 1), each
record's `previous_hash_hex` equals the prior record's
`record_hash_hex`, every record carries a valid signature under
`keys/public_key.pem`, and CHAIN_SEALED's `final_chain_hash_hex`
matches the last record's `chain_hash_hex`.

## Provenance and tier

Run dated 2026-02-11 (AEGIS pilot era; predates the 2026Q2 comparative
campaign). Single scenario, single lab, author-run. It belongs to the
Tier-1 pilot evidence, not the frozen 2026Q2 corpus.
