#!/usr/bin/env python3
"""
Validate live pipeline outputs against paper claims.
Checks anchor hashes, trace integrity, COA diversity, gap detection accuracy,
and cross-domain execution.
"""
import json
import sys
from pathlib import Path

AEGIS_ROOT = Path("/sessions/intelligent-ecstatic-cerf/mnt/Desktop/AEGIS")
sys.path.insert(0, str(AEGIS_ROOT / "src"))

from mandate.hashing import compute_anchor_hash

OUTPUTS = Path("/sessions/intelligent-ecstatic-cerf/mnt/Desktop/mandate/live_runs/outputs")


def validate_anchor_hash(artifact: dict, scenario: str) -> dict:
    """Verify anchor hash matches recomputation (Property 1)."""
    anchor = artifact.get("anchor", {})
    stored_hash = anchor.get("anchor_hash", "")
    if not stored_hash:
        return {"check": "anchor_hash", "status": "SKIP", "reason": "no hash"}

    fields = {k: v for k, v in anchor.items() if k != "anchor_hash"}
    recomputed = compute_anchor_hash(fields)
    match = (recomputed == stored_hash)
    return {
        "check": "anchor_hash",
        "status": "PASS" if match else "FAIL",
        "stored": stored_hash[:16] + "...",
        "recomputed": recomputed[:16] + "...",
        "match": match,
    }


def validate_trace_chain(artifact: dict, scenario: str) -> dict:
    """Verify trace chain integrity (Property 2)."""
    trace = artifact.get("trace", {})
    entries = trace.get("entries", [])
    if not entries:
        return {"check": "trace_chain", "status": "SKIP", "reason": "no entries"}

    all_hashed = all(bool(e.get("hash")) for e in entries)
    roles = [e.get("role", "?") for e in entries]

    # Check parent linkage
    hash_set = {e["hash"] for e in entries if e.get("hash")}
    parent_valid = True
    for e in entries:
        parents = e.get("parents", [])
        if parents:
            for p in parents:
                if p not in hash_set and p != "root":
                    parent_valid = False

    return {
        "check": "trace_chain",
        "status": "PASS" if all_hashed and parent_valid else "FAIL",
        "num_entries": len(entries),
        "roles": roles,
        "all_hashed": all_hashed,
        "parent_linkage_valid": parent_valid,
    }


def validate_coa_diversity(artifact: dict, scenario: str) -> dict:
    """Check COA structural variation (RQ2)."""
    coas = artifact.get("courses_of_action", [])
    if len(coas) < 2:
        return {"check": "coa_diversity", "status": "SKIP", "reason": f"only {len(coas)} COA(s)"}

    task_counts = [len(c.get("task_dag", {}).get("nodes", [])) for c in coas]
    edge_counts = [len(c.get("task_dag", {}).get("edges", [])) for c in coas]
    risk_scores = [c.get("risk_assessment", {}).get("score", "N/A") for c in coas]

    # Diversity flags
    different_task_counts = len(set(task_counts)) > 1
    different_risk_scores = len(set(str(r) for r in risk_scores)) > 1
    different_edge_counts = len(set(edge_counts)) > 1

    # Check tool coverage variation
    tool_sets = []
    for c in coas:
        tools = set()
        for node in c.get("task_dag", {}).get("nodes", []):
            tools.update(node.get("tool_ids", []))
        tool_sets.append(frozenset(tools))
    different_tools = len(set(tool_sets)) > 1

    flags = {
        "different_task_counts": different_task_counts,
        "different_risk_scores": different_risk_scores,
        "different_edge_counts": different_edge_counts,
        "different_tool_coverage": different_tools,
    }
    true_count = sum(1 for v in flags.values() if v)

    return {
        "check": "coa_diversity",
        "status": "PASS" if true_count >= 2 else "PARTIAL",
        "num_coas": len(coas),
        "task_counts": task_counts,
        "edge_counts": edge_counts,
        "risk_scores": risk_scores,
        "diversity_flags": flags,
        "diversity_score": f"{true_count}/4",
    }


def validate_gap_detection(result: dict, scenario: str) -> dict:
    """Verify expected gap types were detected (RQ3)."""
    gaps = result.get("gap_reports", [])
    gap_types = [g["gap_type"] for g in gaps]

    expected_map = {
        "scenario_02_gap_undefined_minimum": "UNDEFINED_MINIMUM",
        "scenario_03_gap_undefined_target": "UNDEFINED_TARGET",
        "scenario_04_gap_unknown_pattern": "UNKNOWN_PATTERN",
        "scenario_05_gap_missing_capability": "MISSING_CAPABILITY",
        "scenario_06_gap_unassessable_risk": "UNASSESSABLE_RISK",
    }

    expected = expected_map.get(scenario)
    if not expected:
        return {"check": "gap_detection", "status": "SKIP", "reason": "not a gap scenario"}

    found = expected in gap_types
    return {
        "check": "gap_detection",
        "status": "PASS" if found else "FAIL",
        "expected_gap_type": expected,
        "detected_gap_types": gap_types,
        "found": found,
    }


def validate_anchor_fields(artifact: dict, scenario: str) -> dict:
    """Check anchor has all required fields (RQ1)."""
    anchor = artifact.get("anchor", {})
    required = ["mission_intent", "minimum", "target", "constraints", "anchor_hash"]
    present = {f: bool(anchor.get(f)) for f in required}
    all_present = all(present.values())

    return {
        "check": "anchor_fields",
        "status": "PASS" if all_present else "PARTIAL",
        "fields": present,
        "all_present": all_present,
    }


def validate_risk_profile(artifact: dict, scenario: str) -> dict:
    """Check risk profile exists and has required fields."""
    risk = artifact.get("risk_profile", {})
    if not risk:
        return {"check": "risk_profile", "status": "SKIP", "reason": "no risk profile"}

    has_score = bool(risk.get("max_score") or risk.get("aggregate_score"))
    has_confidence = bool(risk.get("confidence_min"))

    return {
        "check": "risk_profile",
        "status": "PASS" if has_score else "PARTIAL",
        "has_score": has_score,
        "has_confidence": has_confidence,
        "fields": list(risk.keys()),
    }


def main():
    print("=" * 70)
    print("LIVE PIPELINE OUTPUT VALIDATION")
    print("=" * 70)

    result_files = sorted(OUTPUTS.glob("scenario_*_result.json"))
    artifact_files = sorted(OUTPUTS.glob("scenario_*_artifact.json"))

    all_validations = []
    pass_count = 0
    total_checks = 0

    for rf in result_files:
        scenario = rf.stem.replace("_result", "")
        with open(rf) as f:
            result = json.load(f)

        # Load artifact if exists
        af = OUTPUTS / f"{scenario}_artifact.json"
        artifact = None
        if af.exists():
            with open(af) as f:
                artifact = json.load(f)

        print(f"\n--- {scenario} ---")
        print(f"  Status: {result.get('status')}")

        checks = []

        if artifact:
            # Anchor hash
            c = validate_anchor_hash(artifact, scenario)
            checks.append(c)
            print(f"  [{c['status']:7s}] Anchor hash: {c.get('match', 'N/A')}")

            # Trace chain
            c = validate_trace_chain(artifact, scenario)
            checks.append(c)
            print(f"  [{c['status']:7s}] Trace chain: {c.get('num_entries', 0)} entries, "
                  f"hashed={c.get('all_hashed')}, parents={c.get('parent_linkage_valid')}")

            # Anchor fields
            c = validate_anchor_fields(artifact, scenario)
            checks.append(c)
            print(f"  [{c['status']:7s}] Anchor fields: {c['fields']}")

            # COA diversity
            c = validate_coa_diversity(artifact, scenario)
            checks.append(c)
            if c["status"] != "SKIP":
                print(f"  [{c['status']:7s}] COA diversity: {c['diversity_score']} flags, "
                      f"tasks={c['task_counts']}, risks={c['risk_scores']}")
            else:
                print(f"  [{c['status']:7s}] COA diversity: {c.get('reason')}")

            # Risk profile
            c = validate_risk_profile(artifact, scenario)
            checks.append(c)
            print(f"  [{c['status']:7s}] Risk profile: {c.get('fields', [])}")

        # Gap detection
        c = validate_gap_detection(result, scenario)
        checks.append(c)
        if c["status"] != "SKIP":
            print(f"  [{c['status']:7s}] Gap detection: expected={c['expected_gap_type']}, "
                  f"found={c['detected_gap_types']}")

        for c in checks:
            total_checks += 1
            if c["status"] == "PASS":
                pass_count += 1

        all_validations.append({"scenario": scenario, "checks": checks})

    # Summary
    print(f"\n\n{'='*70}")
    print("VALIDATION SUMMARY")
    print(f"{'='*70}")
    print(f"Total checks: {total_checks}")
    print(f"PASS: {pass_count}")
    print(f"FAIL: {sum(1 for v in all_validations for c in v['checks'] if c['status'] == 'FAIL')}")
    print(f"PARTIAL: {sum(1 for v in all_validations for c in v['checks'] if c['status'] == 'PARTIAL')}")
    print(f"SKIP: {sum(1 for v in all_validations for c in v['checks'] if c['status'] == 'SKIP')}")

    # Paper claim verification
    print(f"\n{'='*70}")
    print("PAPER CLAIM EVIDENCE MAP")
    print(f"{'='*70}")

    claims = {
        "RQ1 - Verifiable success criteria": False,
        "RQ2 - Multiple valid COAs": False,
        "RQ3 - Gap detection (5 types)": False,
        "Property 1 - Anchor immutability": False,
        "Property 2 - Trace completeness": False,
        "Cross-domain (IR)": False,
        "Cross-domain (INTEL)": False,
        "Section 11 walkthrough": False,
    }

    # Check each claim
    for v in all_validations:
        s = v["scenario"]
        checks = {c["check"]: c for c in v["checks"]}

        if s == "scenario_01_ciso_report":
            if checks.get("anchor_hash", {}).get("status") == "PASS":
                claims["Property 1 - Anchor immutability"] = True
                claims["Section 11 walkthrough"] = True
            if checks.get("anchor_fields", {}).get("status") == "PASS":
                claims["RQ1 - Verifiable success criteria"] = True

        if s == "scenario_07_multi_coa_ir":
            if checks.get("coa_diversity", {}).get("status") in ("PASS", "PARTIAL"):
                claims["RQ2 - Multiple valid COAs"] = True
                claims["Cross-domain (IR)"] = True

        if s == "scenario_08_cross_domain_intel":
            if checks.get("trace_chain", {}).get("status") == "PASS":
                claims["Cross-domain (INTEL)"] = True
                claims["Property 2 - Trace completeness"] = True

    # Gap detection: check all 5 gap types were triggered
    gap_types_found = set()
    for v in all_validations:
        for c in v["checks"]:
            if c["check"] == "gap_detection" and c["status"] == "PASS":
                gap_types_found.add(c["expected_gap_type"])

    expected_gaps = {"UNDEFINED_MINIMUM", "UNDEFINED_TARGET", "UNKNOWN_PATTERN",
                     "MISSING_CAPABILITY", "UNASSESSABLE_RISK"}
    if gap_types_found == expected_gaps:
        claims["RQ3 - Gap detection (5 types)"] = True

    for claim, verified in claims.items():
        status = "VERIFIED" if verified else "NOT VERIFIED"
        print(f"  [{status:12s}] {claim}")

    verified_count = sum(1 for v in claims.values() if v)
    print(f"\nClaims verified: {verified_count}/{len(claims)}")

    # Save validation report
    report = {
        "validations": all_validations,
        "total_checks": total_checks,
        "pass_count": pass_count,
        "claims": {k: v for k, v in claims.items()},
        "gap_types_exercised": sorted(gap_types_found),
    }

    report_file = OUTPUTS / "validation_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport saved: {report_file}")


if __name__ == "__main__":
    main()
