"""
MANDATE artifact validation.

Validates:
- JSON Schema compliance
- Hash integrity (anchor_hash, trace entry hashes, chain_hash, entry_count)
- Constraint syntax (anchor constraints must parse successfully)
- Trigger syntax (off_nominal_triggers must parse as valid predicates)
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from jsonschema import Draft202012Validator

try:
    from referencing import Registry, Resource
except Exception:  # pragma: no cover
    Registry = None  # type: ignore
    Resource = None  # type: ignore

from . import hashing
from .schema import load_schema
from .constraints import parse_constraint, ConstraintError


MANDATE_SCHEMA_NAME = "mandate-as-code.schema.json"
TRACE_SCHEMA_NAME = "trace-entry.schema.json"
GAP_SCHEMA_NAME = "gap-report.schema.json"


@dataclass
class ValidationIssue:
    kind: str  # "schema" | "hash" | "constraint" | "trigger"
    message: str
    path: str = ""


def load_json(path: Union[str, Path]) -> Dict[str, Any]:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8"))


def detect_artifact_type(obj: Dict[str, Any]) -> str:
    if "gap_id" in obj and "gap_type" in obj:
        return "gap-report"
    if "mandate_id" in obj and "anchor" in obj and "courses_of_action" in obj:
        return "mandate-as-code"
    return "unknown"


def _build_registry() -> Optional[Any]:
    if Registry is None or Resource is None:
        return None

    mandate_schema = load_schema(MANDATE_SCHEMA_NAME)
    trace_schema = load_schema(TRACE_SCHEMA_NAME)
    gap_schema = load_schema(GAP_SCHEMA_NAME)

    reg = Registry()
    for s in (mandate_schema, trace_schema, gap_schema):
        sid = s.get("$id")
        if sid:
            reg = reg.with_resource(sid, Resource.from_contents(s))
    return reg


def validate_schema(obj: Dict[str, Any], artifact_type: str) -> List[ValidationIssue]:
    """Validate artifact against JSON Schema."""
    issues: List[ValidationIssue] = []
    registry = _build_registry()

    if artifact_type == "mandate-as-code":
        schema = load_schema(MANDATE_SCHEMA_NAME)
    elif artifact_type == "gap-report":
        schema = load_schema(GAP_SCHEMA_NAME)
    else:
        return [ValidationIssue(kind="schema", message="Unknown artifact type; cannot select schema.")]

    if registry is not None:
        validator = Draft202012Validator(schema, registry=registry)
    else:  # fallback (should still work if no $ref usage)
        validator = Draft202012Validator(schema)

    for err in sorted(validator.iter_errors(obj), key=str):
        path = "/".join([str(p) for p in err.absolute_path])
        issues.append(ValidationIssue(kind="schema", message=err.message, path=path))
    return issues


def validate_hashes(obj: Dict[str, Any], artifact_type: str) -> List[ValidationIssue]:
    """Validate hash integrity (anchor_hash, trace entry hashes, chain_hash, entry_count)."""
    issues: List[ValidationIssue] = []

    if artifact_type == "mandate-as-code":
        # Verify anchor_hash
        anchor = obj.get("anchor", {})
        if isinstance(anchor, dict):
            expected = hashing.compute_anchor_hash(anchor)
            got = anchor.get("anchor_hash")
            if got != expected:
                issues.append(
                    ValidationIssue(
                        kind="hash",
                        message=f"anchor_hash mismatch: got {got}, expected {expected}",
                        path="anchor/anchor_hash",
                    )
                )

        # Verify trace entries and chain_hash
        trace = obj.get("trace", {})
        if isinstance(trace, dict):
            entries = trace.get("entries", [])
            
            # P0.2 fix: Verify entry_count matches actual entry count
            declared_count = trace.get("entry_count")
            actual_count = len(entries)
            if declared_count is not None and declared_count != actual_count:
                issues.append(
                    ValidationIssue(
                        kind="hash",
                        message=f"entry_count mismatch: declared {declared_count}, actual {actual_count}",
                        path="trace/entry_count",
                    )
                )
            
            # Separate embedded objects from hash strings
            entry_hashes: List[str] = []
            
            for i, e in enumerate(entries):
                if isinstance(e, dict):
                    # Verify each embedded entry's hash
                    expected_h = hashing.compute_trace_entry_hash(e)
                    got_h = e.get("hash")
                    if got_h != expected_h:
                        issues.append(
                            ValidationIssue(
                                kind="hash",
                                message=f"trace entry hash mismatch: got {got_h}, expected {expected_h}",
                                path=f"trace/entries/{i}/hash",
                            )
                        )
                    entry_hashes.append(e.get("hash", ""))
                elif isinstance(e, str):
                    # Hash string reference
                    entry_hashes.append(e)
            
            # P0.1 fix: Always verify chain_hash, even for empty entries list
            # sha256(canonical_json([])) is the expected hash for empty traces
            expected_chain = hashing.compute_chain_hash_from_strings(entry_hashes)
            got_chain = trace.get("chain_hash")
            if got_chain != expected_chain:
                issues.append(
                    ValidationIssue(
                        kind="hash",
                        message=f"trace.chain_hash mismatch: got {got_chain}, expected {expected_chain}",
                        path="trace/chain_hash",
                    )
                )

    elif artifact_type == "gap-report":
        # gap reports reference a trace hash; we can't verify without the trace store.
        pass

    return issues


def validate_constraints(obj: Dict[str, Any], artifact_type: str) -> List[ValidationIssue]:
    """Validate that all constraint strings in anchor parse successfully."""
    issues: List[ValidationIssue] = []
    
    if artifact_type != "mandate-as-code":
        return issues
    
    anchor = obj.get("anchor", {})
    constraints = anchor.get("constraints", [])
    
    for i, constraint in enumerate(constraints):
        if not isinstance(constraint, str):
            issues.append(
                ValidationIssue(
                    kind="constraint",
                    message=f"Constraint must be a string, got {type(constraint).__name__}",
                    path=f"anchor/constraints/{i}",
                )
            )
            continue
            
        try:
            parse_constraint(constraint)
        except ConstraintError as e:
            issues.append(
                ValidationIssue(
                    kind="constraint",
                    message=f"Invalid constraint syntax: {e}",
                    path=f"anchor/constraints/{i}",
                )
            )
    
    return issues


def validate_triggers(obj: Dict[str, Any], artifact_type: str) -> List[ValidationIssue]:
    """Validate that all off_nominal_triggers in COAs parse as valid constraint predicates."""
    issues: List[ValidationIssue] = []
    
    if artifact_type != "mandate-as-code":
        return issues
    
    coas = obj.get("courses_of_action", [])
    
    for coa_idx, coa in enumerate(coas):
        coa_id = coa.get("coa_id", f"COA-{coa_idx}")
        triggers = coa.get("off_nominal_triggers", [])
        
        for i, trigger in enumerate(triggers):
            if not isinstance(trigger, str):
                issues.append(
                    ValidationIssue(
                        kind="trigger",
                        message=f"Trigger must be a string, got {type(trigger).__name__}",
                        path=f"courses_of_action/{coa_idx}/off_nominal_triggers/{i}",
                    )
                )
                continue
            
            try:
                parse_constraint(trigger)
            except ConstraintError as e:
                issues.append(
                    ValidationIssue(
                        kind="trigger",
                        message=f"Invalid trigger syntax in {coa_id}: {e}",
                        path=f"courses_of_action/{coa_idx}/off_nominal_triggers/{i}",
                    )
                )
    
    return issues


def validate_artifact(path: Union[str, Path]) -> Tuple[str, List[ValidationIssue]]:
    """
    Validate a MANDATE artifact (mandate-as-code or gap-report).
    
    Performs:
    - JSON Schema validation
    - Hash integrity checks
    - Constraint syntax validation (for mandate-as-code)
    - Off-nominal trigger syntax validation (for mandate-as-code)
    
    Args:
        path: Path to the JSON artifact file
        
    Returns:
        Tuple of (artifact_type, list of validation issues)
    """
    obj = load_json(path)
    artifact_type = detect_artifact_type(obj)

    issues: List[ValidationIssue] = []
    issues.extend(validate_schema(obj, artifact_type))
    issues.extend(validate_hashes(obj, artifact_type))
    issues.extend(validate_constraints(obj, artifact_type))
    issues.extend(validate_triggers(obj, artifact_type))
    return artifact_type, issues
