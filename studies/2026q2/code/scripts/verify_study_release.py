#!/usr/bin/env python3
"""Verify the MANDATE 2026Q2 study as one versioned evidence release."""

from __future__ import annotations

import gzip
import hashlib
import json
import statistics
import subprocess
import sys
import tempfile
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


def load_jsonl(path: Path) -> list[dict]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def majority(values):
    values = [value for value in values if value is not None]
    if not values:
        return None, True
    counts = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    modal = max(counts, key=counts.get)
    return modal, len(counts) == 1


def verify_full_coverage_ensemble(repo: Path, issues: list[str]) -> dict:
    retained = repo / "replication_package/retained_study_data"
    names = (
        "full_coverage_judge_gpt4o.jsonl.gz",
        "full_coverage_judge_claude.jsonl.gz",
        "full_coverage_judge_gemini.jsonl.gz",
    )
    if not all((retained / name).is_file() for name in names):
        return {"present": False, "records_recomputed": 0, "mismatches": None}
    per_judge = [load_jsonl(retained / name) for name in names]
    indexes = [{row["anon_id"]: row for row in rows} for rows in per_judge]
    expected = load_jsonl(
        repo / "replication_package/v1_main/grading/v2_full_coverage/ensemble_scores.jsonl"
    )
    numeric = (
        "minimum_coverage", "target_coverage", "constraint_coverage",
        "fabrication_count", "trace_completeness",
    )
    discrete = ("mission_intent_match", "gap_classification", "adversarial_compliance")
    mismatches = 0
    for ensemble in expected:
        anon_id = ensemble["anon_id"]
        rows = [index.get(anon_id) for index in indexes]
        if any(row is None for row in rows):
            mismatches += 1
            continue
        recomputed = {}
        unanimous = []
        for field in numeric:
            values = [row.get(field) for row in rows if row.get(field) is not None]
            recomputed[field] = statistics.median(values) if values else None
        for field in discrete:
            recomputed[field], is_unanimous = majority([row.get(field) for row in rows])
            unanimous.append(is_unanimous)
        recomputed["has_disagreement"] = not all(unanimous)
        recomputed["n_judges"] = 3
        for field, value in recomputed.items():
            if ensemble.get(field) != value:
                mismatches += 1
                break
        else:
            # Judge identity is set-valued. Historical aggregation serialized
            # the same three IDs in more than one order.
            if set(ensemble.get("judge_ids") or []) != {row["judge_id"] for row in rows}:
                mismatches += 1
    if mismatches:
        issues.append(f"full-coverage ensemble reconciliation: {mismatches} mismatches")
    return {
        "present": True,
        "judge_records": sum(len(rows) for rows in per_judge),
        "records_recomputed": len(expected),
        "mismatches": mismatches,
    }


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

    ensemble_reconciliation = verify_full_coverage_ensemble(repo, issues)

    trace_report = {"present": False}
    trace_script = repo / "code/figure_scripts/verify_trace_hashes_full.py"
    if trace_script.is_file():
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name
        trace = subprocess.run(
            [sys.executable, str(trace_script), "--root", str(repo), "--report", tmp_path],
            cwd=repo, text=True, capture_output=True,
        )
        try:
            trace_totals = json.loads(Path(tmp_path).read_text(encoding="utf-8")).get("totals", {})
        except (OSError, json.JSONDecodeError):
            trace_totals = {}
        trace_report = {"present": True, "exit_code": trace.returncode, "totals": trace_totals}
        expected_trace = {
            "artifacts": 17050,
            "entries": 100500, "entry_hash_fail": 0,
            "parent_links": 83600, "parent_fail": 0,
            "chains": 16900, "chain_fail": 0,
            "anchors": 17050, "anchor_fail": 0,
            "empty_traces": 150,
        }
        for key, expected in expected_trace.items():
            if trace_totals.get(key) != expected:
                issues.append(
                    f"trace-hash verification: {key} expected {expected}, got {trace_totals.get(key)}"
                )
        if trace.returncode != 0:
            issues.append("trace-hash verification: nonzero exit")
    else:
        issues.append("trace-hash verifier missing: code/figure_scripts/verify_trace_hashes_full.py")

    reliability_report = {"present": False}
    reliability_script = repo / "code/figure_scripts/compute_reliability.py"
    if reliability_script.is_file():
        rel = subprocess.run(
            [sys.executable, str(reliability_script)], cwd=repo, text=True, capture_output=True,
        )
        try:
            rel_values = json.loads(rel.stdout).get("alpha", {})
        except json.JSONDecodeError:
            rel_values = {}
        reliability_report = {"present": True, "exit_code": rel.returncode, "alpha": rel_values}
        expected_alpha = {
            "minimum_coverage__interval": 0.855,
            "target_coverage__interval": 0.586,
            "constraint_coverage__interval": 0.589,
            "mission_intent_match__nominal": 0.536,
            "gap_classification__nominal": 0.449,
            "fabrication_count__interval": 0.218,
            "trace_completeness__interval": 0.218,
            "trace_completeness__nominal": 0.027,
        }
        for key, expected in expected_alpha.items():
            if rel_values.get(key) != expected:
                issues.append(
                    f"full-coverage reliability: {key} expected {expected}, got {rel_values.get(key)}"
                )
        if rel.returncode != 0:
            issues.append("full-coverage reliability: nonzero exit")
    else:
        issues.append("reliability script missing: code/figure_scripts/compute_reliability.py")


    report = {
        "publication_release_version": "2.0.1",
        "study_snapshot": "2026.08.13.1",
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
        "ensemble_reconciliation": ensemble_reconciliation,
        "trace_hash_verification": trace_report,
        "full_coverage_reliability": reliability_report,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
