"""
Baseline specification schema (Workstream B2).

PROTOCOL_LOCK Section 11: baselines are not required to produce MANDATE's full
mandate-as-code, but they must produce a defined structured output that
supports comparison on anchor completeness, gap detection, and schema
validity. This module defines that schema, shared by all six baselines.

The shape is anchor-equivalent: it mirrors the fields the SME ground-truth
anchor carries (see the calibration tasks' expected_anchor and PROMPTS
Section 2), so baseline output is graded on the same rubric as MANDATE.

PROTOCOL_LOCK Section 11 permits per-baseline schemas. A single shared schema
is used here, on purpose, for comparability across baselines. That choice is
pre-registered.
"""
from __future__ import annotations

SCHEMA_ID = "baseline-specification-v1"

BASELINE_SPECIFICATION_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": SCHEMA_ID,
    "type": "object",
    "required": ["mission_intent", "minimum", "target", "constraints",
                 "suspected_gaps"],
    "additionalProperties": False,
    "properties": {
        "mission_intent": {"type": "string", "minLength": 1},
        "minimum": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["dimension", "threshold", "rationale"],
                "additionalProperties": False,
                "properties": {
                    "dimension": {"type": "string"},
                    "threshold": {"type": ["string", "null"]},
                    "rationale": {"type": "string"},
                },
            },
        },
        "target": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["dimension", "objective", "rationale"],
                "additionalProperties": False,
                "properties": {
                    "dimension": {"type": "string"},
                    "objective": {"type": ["string", "null"]},
                    "rationale": {"type": "string"},
                },
            },
        },
        "constraints": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["predicate", "rationale"],
                "additionalProperties": False,
                "properties": {
                    "predicate": {"type": "string"},
                    "rationale": {"type": "string"},
                },
            },
        },
        "suspected_gaps": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["field", "reason"],
                "additionalProperties": False,
                "properties": {
                    "field": {"type": "string"},
                    "reason": {"type": "string"},
                },
            },
        },
    },
}


def validate_specification(obj) -> tuple:
    """Validate a parsed object against the baseline specification schema.

    Returns (is_valid: bool, errors: list[str]).
    """
    try:
        import jsonschema
    except ImportError:
        return False, ["jsonschema is not installed"]
    if not isinstance(obj, dict):
        return False, ["top-level value is not a JSON object"]
    validator = jsonschema.Draft202012Validator(BASELINE_SPECIFICATION_SCHEMA)
    errors = sorted(validator.iter_errors(obj), key=lambda e: list(e.path))
    if not errors:
        return True, []
    return False, ["%s: %s" % ("/".join(str(p) for p in e.path) or "<root>",
                               e.message) for e in errors]
