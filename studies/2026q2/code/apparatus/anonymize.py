"""
Anonymization pipeline (Workstream B4).

PLAYBOOK Phase 6: at the end of system execution, before any grading, strip
system-identifying information from outputs, assign a random identifier per
output, and keep the identifier-to-system mapping in a separate file the
graders cannot read. PROTOCOL_LOCK Section 14.2 also calls for randomized
output order.

What this module produces:
  * anonymized outputs  - one dict per run: {anon_id, task_id, output_type,
    output, ok}. All record-level identity (system id and label, run id,
    model versions, code ref, decoding params, per-role timings) is dropped.
    Per-role timings are dropped on purpose: role names like Intake and
    Interpreter would identify MANDATE.
  * the mapping         - {anon_id: {system_id, system_label, run_id,
    run_number, task_id}}. THIS FILE MUST NOT BE READABLE BY GRADERS.

Honest limit: structural differences between MANDATE's mandate-as-code and a
baseline's specification schema are visible in the output itself and cannot be
fully hidden by string stripping. PROTOCOL_LOCK Section 13 acknowledges this;
the three-judge rubric instructs judges not to infer system identity.
Optional identity-token scrubbing of string values is available for cases
where a literal system name appears in content.
"""
from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field

# Record-level fields that name or fingerprint the system. Dropped from the
# grader-facing output.
_IDENTITY_FIELDS = ("system_id", "system_label", "run_id", "run_number",
                    "seed", "model_versions", "decoding_params", "code_ref",
                    "harness_version", "wall_clock_ms", "role_timings",
                    "started_at", "api_cost_usd", "local_compute_ms")


def _as_dict(record):
    return record.to_dict() if hasattr(record, "to_dict") else dict(record)


def _scrub(obj, tokens):
    """Recursively redact whole-word, case-insensitive token matches from
    string VALUES only. Keys are never touched, so JSON structure is intact."""
    import re
    if not tokens:
        return obj
    patt = re.compile(r"\b(" + "|".join(re.escape(t) for t in tokens) + r")\b",
                      re.IGNORECASE)
    def walk(v):
        if isinstance(v, str):
            return patt.sub("[redacted]", v)
        if isinstance(v, list):
            return [walk(x) for x in v]
        if isinstance(v, dict):
            return {k: walk(x) for k, x in v.items()}
        return v
    return walk(obj)


@dataclass
class AnonymizationResult:
    outputs: list = field(default_factory=list)   # grader-facing dicts
    mapping: dict = field(default_factory=dict)    # anon_id -> identity


class Anonymizer:
    def __init__(self, seed: int = 20260523):
        self._rng = random.Random(seed)
        self.seed = seed

    def _new_id(self, used: set) -> str:
        while True:
            anon = "OUT-%08X" % self._rng.getrandbits(32)
            if anon not in used:
                used.add(anon)
                return anon

    def anonymize(self, records, identity_tokens=None) -> AnonymizationResult:
        """Anonymize a list of RunRecords (or their dicts). Output order is
        shuffled with the seeded RNG so position does not leak system order."""
        used: set = set()
        outputs = []
        mapping = {}
        for record in records:
            d = _as_dict(record)
            anon = self._new_id(used)
            mapping[anon] = {
                "system_id": d.get("system_id", ""),
                "system_label": d.get("system_label", ""),
                "run_id": d.get("run_id", ""),
                "run_number": d.get("run_number"),
                "task_id": d.get("task_id", ""),
                # Run-health flags the primary-analysis notebook reads to compute
                # the `clean` outcome gate. Previously absent from the mapping, so
                # the notebook saw ok=True/fallback=False/schema_valid=None and the
                # gate never excluded a run. Carried here (de-anonymized side only).
                "ok": d.get("ok", False),
                "any_llm_fallback": d.get("any_llm_fallback", False),
                "schema_valid": (d.get("output") or {}).get("schema_valid"),
            }
            outputs.append({
                "anon_id": anon,
                "task_id": d.get("task_id", ""),
                "output_type": d.get("output_type", ""),
                "output": _scrub(d.get("output"), identity_tokens),
                "ok": d.get("ok", False),
            })
        self._rng.shuffle(outputs)
        return AnonymizationResult(outputs=outputs, mapping=mapping)

    def save(self, result: AnonymizationResult, outputs_path: str,
             mapping_path: str) -> None:
        for path in (outputs_path, mapping_path):
            parent = os.path.dirname(os.path.abspath(path))
            os.makedirs(parent, exist_ok=True)
        with open(outputs_path, "w") as f:
            json.dump(result.outputs, f, indent=2, default=str)
        with open(mapping_path, "w") as f:
            json.dump(result.mapping, f, indent=2, default=str)
        print("anonymized outputs -> %s" % outputs_path)
        print("mapping -> %s" % mapping_path)
        print("WARNING: the mapping file de-anonymizes every output. Store it "
              "where graders cannot read it; it is gitignored by SETUP.")


def verify_mapping(result: AnonymizationResult) -> tuple:
    """Integrity check, run before grading (PLAYBOOK Phase 6). Returns
    (ok, problems)."""
    problems = []
    out_ids = [o["anon_id"] for o in result.outputs]
    if len(out_ids) != len(set(out_ids)):
        problems.append("duplicate anon_id in outputs")
    if set(out_ids) != set(result.mapping):
        problems.append("outputs and mapping anon_id sets differ")
    for anon, ident in result.mapping.items():
        if not ident.get("system_id"):
            problems.append("mapping entry %s has no system_id" % anon)
    for o in result.outputs:
        for bad in ("system_id", "system_label", "run_id", "model_versions"):
            if bad in o:
                problems.append("output %s still carries %s"
                                % (o["anon_id"], bad))
    return (not problems), problems
