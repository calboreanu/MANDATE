#!/usr/bin/env python3
"""Verify the MANDATE 2026Q2 study as one versioned evidence release."""

from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Iterable


def jsonl_count(path: Path) -> int:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    issues: list[str] = []

    campaign_outputs = repo / "replication_package/v1_main/system_outputs"
    expected_campaign_counts = {
        "mandate_primary_main.jsonl": 1200,
        "mandate_primary_holdout.jsonl": 300,
        "cond_a_main.jsonl": 1200,
        "cond_a_holdout.jsonl": 300,
        "cond_b_main.jsonl": 1200,
        "cond_b_holdout.jsonl": 300,
    }
    observed_campaign_counts = {}
    for name, expected in expected_campaign_counts.items():
        path = campaign_outputs / name
        observed = jsonl_count(path) if path.is_file() else -1
        observed_campaign_counts[name] = observed
        if observed != expected:
            issues.append(f"{name}: expected {expected}, got {observed}")

    grades = repo / "replication_package/v1_main/grading/v2_full_coverage/ensemble_scores.jsonl"
    grade_count = jsonl_count(grades) if grades.is_file() else -1
    if grade_count != 12000:
        issues.append(f"ensemble grading: expected 12000, got {grade_count}")

    perturbations = repo / "replication_package/v2_complete/perturbations_mandate"
    perturbation_count = sum(jsonl_count(path) for path in perturbations.glob("*.jsonl"))
    if perturbation_count != 4200:
        issues.append(f"MANDATE perturbations: expected 4200, got {perturbation_count}")

    routing = subprocess.run(
        [sys.executable, str(repo / "code/scripts/verify_v3_corrected_routing.py")],
        cwd=repo, text=True, capture_output=True,
    )
    try:
        routing_report = json.loads(routing.stdout)
    except json.JSONDecodeError:
        routing_report = {"ok": False, "issues": [routing.stderr or routing.stdout]}
    if routing.returncode != 0 or not routing_report.get("ok"):
        issues.append("routing-purpose test did not verify")

    retained_manifest_path = repo / "replication_package/retained_study_data/manifest.json"
    retained_report = {"present": retained_manifest_path.is_file(), "files": 0, "records": 0}
    if retained_manifest_path.is_file():
        retained_manifest = json.loads(retained_manifest_path.read_text(encoding="utf-8"))
        for item in retained_manifest.get("files", []):
            path = retained_manifest_path.parent / item["path"]
            retained_report["files"] += 1
            retained_report["records"] += int(item["records"])
            if not path.is_file():
                issues.append(f"retained file missing: {item['path']}")
                continue
            if sha256_file(path) != item["sha256"]:
                issues.append(f"retained file hash mismatch: {item['path']}")
            observed = jsonl_count(path)
            if observed != item["records"]:
                issues.append(
                    f"retained file count mismatch: {item['path']} "
                    f"expected {item['records']}, got {observed}"
                )

    report = {
        "study_release_version": "2026.08.13",
        "ok": not issues,
        "issues": issues,
        "campaign_record_counts": observed_campaign_counts,
        "ensemble_grade_records": grade_count,
        "mandate_perturbation_records": perturbation_count,
        "routing_purpose_test": {
            "purpose": (
                "Check whether blocking or insufficient-for-automation signals "
                "route to explicit non-executable states in the successor implementation."
            ),
            "records": routing_report.get("records"),
            "signal_denominator": routing_report.get("primary_denominator_N"),
            "routing_contract_violations": routing_report.get("executable_with_blocking"),
        },
        "retained_study_data": retained_report,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
