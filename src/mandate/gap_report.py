"""
Gap report generation for the MANDATE pipeline.

Converts GapSpec objects (detected by pipeline roles) into
gap-report artifacts conforming to gap-report.schema.json.

Each gap is a separate artifact with:
- gap_id, gap_type, detected_by, pipeline_stage
- location (input_reference + field_or_task)
- reason, remediation, readiness_score
- trace_to_gap (SHA-256 hash linking to the trace)
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .hashing import compute_trace_entry_hash, sha256_hex
from .models import GapSpec
from .validator import validate_artifact


def gap_spec_to_artifact(
    gap: GapSpec,
    mission_id: str,
    sequence: int = 1,
) -> Dict[str, Any]:
    """
    Convert a GapSpec into a gap-report dict conforming to schema.

    Args:
        gap: The detected gap
        mission_id: Mission ID for trace linking
        sequence: Gap sequence number (for gap_id generation)

    Returns:
        Dict conforming to gap-report.schema.json
    """
    gap_id = f"GAP-{mission_id}-{sequence:03d}"

    # Build trace_to_gap hash: a hash of the gap detection context
    trace_content = {
        "role": gap.detected_by,
        "action": "gap_detection",
        "mission_id": mission_id,
        "gap_type": gap.gap_type.value,
        "field_or_task": gap.field_or_task,
    }
    trace_hash = compute_trace_entry_hash(trace_content)

    return {
        "gap_id": gap_id,
        "gap_type": gap.gap_type.value,
        "detected_by": gap.detected_by,
        "pipeline_stage": gap.pipeline_stage,
        "location": {
            "input_reference": gap.input_reference,
            "field_or_task": gap.field_or_task,
        },
        "reason": gap.reason,
        "remediation": {
            "action_required": gap.action_required,
            "responsible_party": gap.responsible_party,
            "complexity": gap.complexity,
        },
        "severity": "BLOCKING" if gap.blocking else "DEGRADING",
        "readiness_score": {
            "completion_percentage": gap.completion_percentage,
            "blocking": gap.blocking,
            "partial_spec_available": gap.partial_spec_available,
        },
        "readiness_assessment": {
            "blocking_gap_count": 1 if gap.blocking else 0,
            "recommendation": (
                "INSUFFICIENT_FOR_AUTOMATION"
                if gap.blocking else "PROCEED_WITH_CAVEATS"
            ),
        },
        "trace_to_gap": trace_hash,
    }


def build_gap_reports(
    gaps: List[GapSpec],
    mission_id: str,
) -> List[Dict[str, Any]]:
    """
    Convert a list of GapSpecs into gap-report artifacts.

    Args:
        gaps: All gaps detected during pipeline execution
        mission_id: The mission ID for ID generation and tracing

    Returns:
        List of gap-report dicts, each conforming to schema
    """
    return [
        gap_spec_to_artifact(gap, mission_id, i + 1)
        for i, gap in enumerate(gaps)
    ]


def save_gap_reports(
    gap_reports: List[Dict[str, Any]],
    output_dir: Path,
) -> List[Path]:
    """
    Save gap reports to individual JSON files.

    Args:
        gap_reports: List of gap-report artifact dicts
        output_dir: Directory to write files into

    Returns:
        List of Paths where files were written
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []

    for report in gap_reports:
        gap_id = report["gap_id"]
        path = output_dir / f"{gap_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        paths.append(path)

    return paths


def validate_gap_reports(
    gap_reports: List[Dict[str, Any]],
) -> List[Tuple[str, bool, List[str]]]:
    """
    Validate each gap report against the schema.

    Returns:
        List of (gap_id, is_valid, error_messages) tuples
    """
    import tempfile

    results = []
    for report in gap_reports:
        gap_id = report.get("gap_id", "unknown")

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            tmp_path = Path(f.name)

        try:
            artifact_type, issues = validate_artifact(str(tmp_path))
            if not issues:
                results.append((gap_id, True, []))
            else:
                errors = [
                    f"[{iss.kind}] {iss.message}"
                    for iss in issues
                ]
                results.append((gap_id, False, errors))
        except Exception as e:
            results.append((gap_id, False, [str(e)]))
        finally:
            try:
                tmp_path.unlink()
            except OSError:
                pass

    return results
