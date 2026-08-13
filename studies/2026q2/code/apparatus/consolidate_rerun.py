"""Consolidate V3 per-record checkpoints into condition JSONL files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .rerun_analysis import (
    _load_result_envelope_schema,
    load_corpus_rows,
    load_json,
    sha256_file,
    validate_record,
)


def load_shard(
    path: Path,
    *,
    condition: str,
    preflight_manifest: dict,
    corpus_rows: dict[str, dict],
    result_envelope_schema: dict | None,
    expected_mlt_commit: str,
    expected_apparatus_commit: str,
    require_clean_worktree: bool,
) -> list[dict]:
    rows = []
    for fp in sorted(path.glob("*.json")):
        if fp.name.startswith(".") or ".tmp." in fp.name:
            raise ValueError(f"incomplete or hidden checkpoint present: {fp}")
        rec = json.loads(fp.read_text(encoding="utf-8"))
        issues = validate_record(
            rec,
            condition=condition,
            expected_mlt_commit=expected_mlt_commit,
            expected_apparatus_commit=expected_apparatus_commit,
            require_clean_worktree=require_clean_worktree,
            preflight_manifest=preflight_manifest,
            corpus_rows=corpus_rows,
            result_envelope_schema=result_envelope_schema,
        )
        if issues:
            raise ValueError(f"{fp}: " + "; ".join(issues))
        rows.append(rec)
    return rows


def sort_key(rec: dict) -> tuple:
    task_id = str(rec.get("task_id", ""))
    split = 1 if "-HOLD" in task_id or "-HOLDOUT" in task_id else 0
    return (split, task_id, int(rec.get("run_number") or 0), int(rec.get("seed") or 0))


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for row in sorted(rows, key=sort_key):
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False, default=str) + "\n")
    tmp.replace(path)


def consolidate(
    condition: str,
    shards: list[Path],
    out_path: Path,
    *,
    preflight_manifest: dict,
    corpus_rows: dict[str, dict],
    result_envelope_schema: dict | None,
    expected_mlt_commit: str,
    expected_apparatus_commit: str,
    require_clean_worktree: bool,
) -> dict:
    rows = []
    seen_keys = set()
    seen_run_ids = set()
    shard_hashes = {}
    provenance_keys = set()
    for shard in shards:
        shard_rows = load_shard(
            shard,
            condition=condition,
            preflight_manifest=preflight_manifest,
            corpus_rows=corpus_rows,
            result_envelope_schema=result_envelope_schema,
            expected_mlt_commit=expected_mlt_commit,
            expected_apparatus_commit=expected_apparatus_commit,
            require_clean_worktree=require_clean_worktree,
        )
        shard_hashes[str(shard)] = {
            "records": len(shard_rows),
            "file_hashes": {
                fp.name: sha256_file(fp)
                for fp in sorted(shard.glob("*.json"))
            },
        }
        for rec in shard_rows:
            run_id = rec.get("run_id")
            key = (rec.get("task_id"), rec.get("run_number"), rec.get("seed"))
            if run_id in seen_run_ids:
                raise ValueError(f"{condition}: duplicate run_id {run_id}")
            if key in seen_keys:
                raise ValueError(f"{condition}: duplicate task/run/seed {key}")
            seen_run_ids.add(run_id)
            seen_keys.add(key)
            model_versions = rec.get("model_versions") if isinstance(rec.get("model_versions"), dict) else {}
            provenance_keys.add(json.dumps({
                "mlt_git_commit": model_versions.get("mlt_git_commit"),
                "apparatus_git_commit": model_versions.get("apparatus_git_commit"),
                "mlt_source_hashes": model_versions.get("mlt_source_hashes"),
                "apparatus_source_hashes": model_versions.get("apparatus_source_hashes"),
            }, sort_keys=True))
            rows.append(rec)
    if len(provenance_keys) > 1:
        raise ValueError(f"{condition}: mixed provenance across shards")
    write_jsonl(out_path, rows)
    return {
        "condition": condition,
        "records": len(rows),
        "output": str(out_path),
        "output_sha256": sha256_file(out_path),
        "shards": shard_hashes,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cond-a-shards", nargs="+", type=Path, required=True)
    parser.add_argument("--cond-b-shards", nargs="+", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--preflight-manifest", type=Path, required=True)
    parser.add_argument("--main-corpus", type=Path, required=True)
    parser.add_argument("--holdout-corpus", type=Path, required=True)
    parser.add_argument("--expected-mlt-commit", required=True)
    parser.add_argument("--expected-apparatus-commit", required=True)
    parser.add_argument("--require-clean-worktree", action="store_true")
    args = parser.parse_args(argv)

    args.out_root.mkdir(parents=True, exist_ok=True)
    preflight_manifest = load_json(args.preflight_manifest)
    corpus_rows = load_corpus_rows([args.main_corpus, args.holdout_corpus])
    result_envelope_schema = _load_result_envelope_schema(preflight_manifest)
    manifest = {
        "inputs": {
            "preflight_manifest": str(args.preflight_manifest),
            "preflight_manifest_sha256": sha256_file(args.preflight_manifest),
            "main_corpus": str(args.main_corpus),
            "main_corpus_sha256": sha256_file(args.main_corpus),
            "holdout_corpus": str(args.holdout_corpus),
            "holdout_corpus_sha256": sha256_file(args.holdout_corpus),
            "expected_mlt_commit": args.expected_mlt_commit,
            "expected_apparatus_commit": args.expected_apparatus_commit,
            "require_clean_worktree": bool(args.require_clean_worktree),
        },
        "cond_a": consolidate(
            "cond_a",
            args.cond_a_shards,
            args.out_root / "cond_a_rerun.jsonl",
            preflight_manifest=preflight_manifest,
            corpus_rows=corpus_rows,
            result_envelope_schema=result_envelope_schema,
            expected_mlt_commit=args.expected_mlt_commit,
            expected_apparatus_commit=args.expected_apparatus_commit,
            require_clean_worktree=args.require_clean_worktree,
        ),
        "cond_b": consolidate(
            "cond_b",
            args.cond_b_shards,
            args.out_root / "cond_b_rerun.jsonl",
            preflight_manifest=preflight_manifest,
            corpus_rows=corpus_rows,
            result_envelope_schema=result_envelope_schema,
            expected_mlt_commit=args.expected_mlt_commit,
            expected_apparatus_commit=args.expected_apparatus_commit,
            require_clean_worktree=args.require_clean_worktree,
        ),
    }
    manifest_path = args.out_root / "rerun_manifest.json"
    manifest["outputs"] = {
        "cond_a_rerun_sha256": sha256_file(args.out_root / "cond_a_rerun.jsonl"),
        "cond_b_rerun_sha256": sha256_file(args.out_root / "cond_b_rerun.jsonl"),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
