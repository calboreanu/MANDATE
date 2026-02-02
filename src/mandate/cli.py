from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from .hashing import compute_anchor_hash, compute_trace_entry_hash
from .validator import load_json, validate_artifact
from .constraints import parse_constraint, validate_constraint, ConstraintError


def cmd_validate(args: argparse.Namespace) -> int:
    artifact_type, issues = validate_artifact(args.path)
    print(f"artifact_type: {artifact_type}")
    if not issues:
        print("OK: no issues found.")
        return 0

    print(f"Found {len(issues)} issue(s):")
    for i, iss in enumerate(issues, 1):
        loc = f" [{iss.path}]" if iss.path else ""
        print(f"{i}. ({iss.kind}){loc} {iss.message}")
    return 2


def cmd_hash_anchor(args: argparse.Namespace) -> int:
    obj = load_json(args.path)
    anchor = obj.get("anchor")
    if not isinstance(anchor, dict):
        print("ERROR: no 'anchor' object found")
        return 2
    h = compute_anchor_hash(anchor)
    print(h)
    return 0


def cmd_hash_trace(args: argparse.Namespace) -> int:
    entry = load_json(args.path)
    if not isinstance(entry, dict):
        print("ERROR: trace entry must be a JSON object")
        return 2
    h = compute_trace_entry_hash(entry)
    print(h)
    return 0


def cmd_check_constraint(args: argparse.Namespace) -> int:
    """Validate a constraint string against the grammar."""
    constraint = args.constraint
    try:
        ast = parse_constraint(constraint)
        print(f"✓ Valid constraint")
        print(f"  Parsed: {ast}")
        return 0
    except ConstraintError as e:
        print(f"✗ Invalid constraint: {e}")
        return 2


def cmd_validate_constraints(args: argparse.Namespace) -> int:
    """Validate all constraints in a mandate-as-code artifact."""
    obj = load_json(args.path)
    anchor = obj.get("anchor", {})
    constraints = anchor.get("constraints", [])
    
    if not constraints:
        print("No constraints found in anchor.")
        return 0
    
    valid_count = 0
    invalid_count = 0
    
    for i, c in enumerate(constraints):
        # P1.2 fix: handle non-string constraints gracefully
        if not isinstance(c, str):
            print(f"  ✗ [{i}] <non-string value: {type(c).__name__}>")
            print(f"       Error: Constraint must be a string")
            invalid_count += 1
            continue
            
        try:
            parse_constraint(c)
            print(f"  ✓ [{i}] {c}")
            valid_count += 1
        except ConstraintError as e:
            print(f"  ✗ [{i}] {c}")
            print(f"       Error: {e}")
            invalid_count += 1
    
    print(f"\nSummary: {valid_count} valid, {invalid_count} invalid")
    return 2 if invalid_count > 0 else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mandate", description="MANDATE artifact utilities")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="Validate a mandate-as-code or gap-report JSON artifact")
    v.add_argument("path", type=str, help="Path to JSON artifact")
    v.set_defaults(func=cmd_validate)

    ha = sub.add_parser("hash-anchor", help="Compute anchor_hash for a mandate JSON (excluding existing anchor_hash)")
    ha.add_argument("path", type=str, help="Path to mandate-as-code JSON")
    ha.set_defaults(func=cmd_hash_anchor)

    ht = sub.add_parser("hash-trace", help="Compute hash for a trace-entry JSON (excluding existing hash)")
    ht.add_argument("path", type=str, help="Path to trace-entry JSON")
    ht.set_defaults(func=cmd_hash_trace)

    cc = sub.add_parser("check-constraint", help="Check if a constraint string is valid")
    cc.add_argument("constraint", type=str, help="Constraint string to validate")
    cc.set_defaults(func=cmd_check_constraint)

    vc = sub.add_parser("validate-constraints", help="Validate all constraints in a mandate artifact")
    vc.add_argument("path", type=str, help="Path to mandate-as-code JSON")
    vc.set_defaults(func=cmd_validate_constraints)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    rc = args.func(args)
    raise SystemExit(rc)
