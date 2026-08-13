#!/usr/bin/env python3
"""Package retained source-tree data omitted from the earlier curated deposit.

The source evaluation tree may be cloud-optimized. Reading the files therefore
also materializes any provider-backed placeholders. Outputs are deterministic
gzip JSONL streams plus a checksum/count manifest. Existing frozen evidence is
never modified.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
from pathlib import Path
from typing import BinaryIO, Iterable


JSON_DIRECTORY_JOBS = {
    "baseline_1_perturbation_records.jsonl.gz": (
        "07_system_outputs/perturbations/baseline_1", 3500
    ),
    "baseline_2_perturbation_records.jsonl.gz": (
        "07_system_outputs/perturbations/baseline_2", 3500
    ),
    "baseline_3_perturbation_records.jsonl.gz": (
        "07_system_outputs/perturbations/baseline_3", 3500
    ),
    "baseline_4_perturbation_records_partial.jsonl.gz": (
        "07_system_outputs/perturbations/baseline_4", 3021
    ),
    "sampled_grading_inputs.jsonl.gz": (
        "08_grading/anonymized_outputs", 9000
    ),
    "sampled_grading_by_record.jsonl.gz": (
        "08_grading/by_record", 700
    ),
    "sampled_double_grade_pass1.jsonl.gz": (
        "08_grading/double_grade/pass1/by_record", 39
    ),
    "sampled_double_grade_pass2.jsonl.gz": (
        "08_grading/double_grade/pass2/by_record", 19
    ),
    "full_coverage_grading_inputs.jsonl.gz": (
        "08_grading_v2/anonymized_outputs", 12000
    ),
    "full_coverage_grading_by_record.jsonl.gz": (
        "08_grading_v2/by_record", 12000
    ),
    "perturbation_grading_inputs.jsonl.gz": (
        "08_grading_v2/perturbations/anonymized_outputs", 23571
    ),
    "perturbation_grading_by_record_partial.jsonl.gz": (
        "08_grading_v2/perturbations/by_record", 14685
    ),
    "perturbation_double_grade_pass1_partial.jsonl.gz": (
        "08_grading_v2/perturbations/double_grade/pass1/by_record", 811
    ),
    "perturbation_incomplete_grades.jsonl.gz": (
        "08_grading_v2/perturbations/incomplete_grades", 811
    ),
}


JSONL_JOBS = {
    "sampled_judge_gpt4o.jsonl.gz": ("08_grading/judge_1_gpt4o/scores.jsonl", 700),
    "sampled_judge_claude.jsonl.gz": ("08_grading/judge_2_claude_opus/scores.jsonl", 700),
    "sampled_judge_gemini.jsonl.gz": ("08_grading/judge_3_gemini_pro/scores.jsonl", 700),
    "full_coverage_judge_gpt4o.jsonl.gz": (
        "08_grading_v2/judge_1_gpt4o/scores.jsonl", 12000
    ),
    "full_coverage_judge_claude.jsonl.gz": (
        "08_grading_v2/judge_2_claude_opus/scores.jsonl", 12000
    ),
    "full_coverage_judge_gemini.jsonl.gz": (
        "08_grading_v2/judge_3_gemini_pro/scores.jsonl", 12000
    ),
    "perturbation_judge_gpt4o_partial.jsonl.gz": (
        "08_grading_v2/perturbations/judge_1_gpt4o/scores.jsonl", 14685
    ),
    "perturbation_judge_claude_partial.jsonl.gz": (
        "08_grading_v2/perturbations/judge_2_claude_opus/scores.jsonl", 14685
    ),
    "perturbation_judge_gemini_partial.jsonl.gz": (
        "08_grading_v2/perturbations/judge_3_gemini_pro/scores.jsonl", 14685
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gzip_writer(path: Path) -> BinaryIO:
    raw = path.open("wb")
    return gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0)


def json_files(root: Path) -> Iterable[Path]:
    return sorted(
        path for path in root.rglob("*.json")
        if path.is_file() and not path.name.startswith("_")
    )


def package_json_directory(source_root: Path, relative: str, destination: Path) -> int:
    source = source_root / relative
    files = list(json_files(source))
    with gzip_writer(destination) as output:
        for path in files:
            raw = path.read_bytes()
            record = json.loads(raw)
            envelope = {
                "source_path": path.relative_to(source_root).as_posix(),
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "record": record,
            }
            output.write(
                json.dumps(envelope, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False).encode("utf-8") + b"\n"
            )
    return len(files)


def package_jsonl(source_root: Path, relative: str, destination: Path) -> int:
    source = source_root / relative
    count = 0
    with source.open("rb") as input_handle, gzip_writer(destination) as output:
        for line in input_handle:
            if not line.strip():
                continue
            json.loads(line)
            output.write(line if line.endswith(b"\n") else line + b"\n")
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--group", choices=("all", "jsonl", "directories"), default="all",
        help="Package materialized JSONL streams first or directory-backed files.",
    )
    args = parser.parse_args()

    source_root = args.source_root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "study_release_version": "2026.08.13",
        "purpose": (
            "Retained raw and per-record evidence for the complete MANDATE study; "
            "historical source paths are provenance labels, not separate results."
        ),
        "source_root_label": "mandate_eval_2026Q2",
        "files": [],
    }

    existing_manifest = output / "manifest.json"
    if existing_manifest.is_file():
        manifest = json.loads(existing_manifest.read_text(encoding="utf-8"))
    completed = {item["path"] for item in manifest["files"]}

    directory_jobs = JSON_DIRECTORY_JOBS.items() if args.group in ("all", "directories") else ()
    for name, (relative, expected) in directory_jobs:
        if name in completed:
            continue
        destination = output / name
        count = package_json_directory(source_root, relative, destination)
        if count != expected:
            raise RuntimeError(f"{relative}: expected {expected}, got {count}")
        manifest["files"].append({
            "path": name,
            "source": relative,
            "records": count,
            "bytes": destination.stat().st_size,
            "sha256": sha256_file(destination),
        })
        print(f"{name}: {count} records")

        manifest_path = output / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    jsonl_jobs = JSONL_JOBS.items() if args.group in ("all", "jsonl") else ()
    for name, (relative, expected) in jsonl_jobs:
        if name in completed:
            continue
        destination = output / name
        count = package_jsonl(source_root, relative, destination)
        if count != expected:
            raise RuntimeError(f"{relative}: expected {expected}, got {count}")
        manifest["files"].append({
            "path": name,
            "source": relative,
            "records": count,
            "bytes": destination.stat().st_size,
            "sha256": sha256_file(destination),
        })
        print(f"{name}: {count} records")
        manifest_path = output / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
