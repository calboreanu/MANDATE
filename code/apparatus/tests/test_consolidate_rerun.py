from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from apparatus.consolidate_rerun import main as consolidate_main
from apparatus.preprocess.extract_mission_input import EXTRACTION_PROMPT
from apparatus.tests.test_rerun_analysis import _preflight_manifest, _records


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def _fixture(tmp_path: Path):
    cond_a, cond_b = _records()
    rendered = EXTRACTION_PROMPT.replace("{task_text}", "Assess reporting controls.")
    cond_a["output"]["mission_input_metadata"]["extraction_prompt_sha256"] = hashlib.sha256(
        rendered.encode("utf-8")
    ).hexdigest()
    manifest = _preflight_manifest([cond_a, cond_b])
    manifest_path = tmp_path / "preflight.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    main_corpus = tmp_path / "main_tasks.jsonl"
    holdout_corpus = tmp_path / "holdout_tasks.jsonl"
    main_corpus.write_text(
        json.dumps({
            "task_id": "TASK-MAIN-FIN-001",
            "request_text": "Assess reporting controls.",
        }) + "\n",
        encoding="utf-8",
    )
    holdout_corpus.write_text("", encoding="utf-8")
    cond_a_dir = tmp_path / "cond_a_main"
    cond_b_dir = tmp_path / "cond_b_main"
    _write_json(cond_a_dir / f"{cond_a['run_id']}.json", cond_a)
    _write_json(cond_b_dir / f"{cond_b['run_id']}.json", cond_b)
    return cond_a, cond_b, manifest_path, main_corpus, holdout_corpus, cond_a_dir, cond_b_dir


def _argv(tmp_path: Path, fixture):
    cond_a, _cond_b, manifest_path, main_corpus, holdout_corpus, cond_a_dir, cond_b_dir = fixture
    return [
        "--cond-a-shards", str(cond_a_dir),
        "--cond-b-shards", str(cond_b_dir),
        "--out-root", str(tmp_path / "out"),
        "--preflight-manifest", str(manifest_path),
        "--main-corpus", str(main_corpus),
        "--holdout-corpus", str(holdout_corpus),
        "--expected-mlt-commit", cond_a["model_versions"]["mlt_git_commit"],
        "--expected-apparatus-commit", cond_a["model_versions"]["apparatus_git_commit"],
    ]


def test_consolidator_writes_deterministic_jsonl_and_manifest(tmp_path):
    fixture = _fixture(tmp_path)
    assert consolidate_main(_argv(tmp_path, fixture)) == 0
    out_root = tmp_path / "out"
    assert (out_root / "cond_a_rerun.jsonl").is_file()
    assert (out_root / "cond_b_rerun.jsonl").is_file()
    manifest = json.loads((out_root / "rerun_manifest.json").read_text(encoding="utf-8"))
    assert manifest["cond_a"]["records"] == 1
    assert manifest["cond_b"]["records"] == 1
    assert manifest["outputs"]["cond_a_rerun_sha256"]
    assert manifest["outputs"]["cond_b_rerun_sha256"]


def test_consolidator_rejects_duplicate_task_run_seed(tmp_path):
    fixture = _fixture(tmp_path)
    cond_a, _cond_b, _manifest_path, _main_corpus, _holdout_corpus, cond_a_dir, _cond_b_dir = fixture
    duplicate_dir = tmp_path / "cond_a_holdout"
    _write_json(duplicate_dir / "duplicate.json", cond_a)
    argv = _argv(tmp_path, fixture)
    idx = argv.index("--cond-a-shards")
    argv.insert(idx + 2, str(duplicate_dir))
    with pytest.raises(ValueError, match="duplicate"):
        consolidate_main(argv)
