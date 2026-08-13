from __future__ import annotations

import copy
import json
from argparse import Namespace
from pathlib import Path

from apparatus import run
from apparatus.preflight import (
    PreflightGateError,
    apparatus_root,
    build_manifest,
    default_mlt_root,
    git_commit,
    validate_pre_call_gate,
)


def _manifest(tmp_path: Path, *, allow: bool = True) -> Path:
    path = tmp_path / "preflight.json"
    manifest = build_manifest(
        mlt_root=default_mlt_root(),
        eval_root=apparatus_root(),
        allow_paid_after_preflight=allow,
        include_package_freeze=False,
    )
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _valid_gate_kwargs(tmp_path: Path) -> dict:
    mlt_root = default_mlt_root()
    eval_root = apparatus_root()
    return {
        "manifest_path": _manifest(tmp_path),
        "expected_mlt_commit": git_commit(mlt_root),
        "expected_apparatus_commit": git_commit(eval_root),
        "require_clean_worktree": False,
        "cost_ledger": str(tmp_path / "cost.jsonl"),
        "campaign_budget_usd": 1.0,
        "condition": "cond_a",
        "tasks_path": eval_root / "replication_package/v1_main/corpus/main_tasks.jsonl",
        "model": "claude-sonnet-4-6",
        "seed": 20260623,
        "runs_per_task": 1,
        "domain_profile_mode": "default",
        "llm_backend": "",
    }


def test_preflight_manifest_defaults_to_paid_disallowed(tmp_path):
    manifest = build_manifest(
        mlt_root=default_mlt_root(),
        eval_root=apparatus_root(),
        include_package_freeze=False,
    )
    assert manifest["paid_execution_allowed_after_preflight"] is False
    assert manifest["provider_schema_sha256_by_role"]
    assert "provider_prompt_sha256_by_task_role" not in manifest
    assert "provider_prompt_sha256_by_run_role" not in manifest


def test_pre_call_gate_accepts_valid_local_manifest(tmp_path):
    manifest = validate_pre_call_gate(**_valid_gate_kwargs(tmp_path))
    assert manifest["paid_execution_allowed_after_preflight"] is True


def test_pre_call_gate_rejects_before_provider_construction(tmp_path):
    args = Namespace(
        task_ids=["TASK-MAIN-FIN-001"],
        all=False,
        tasks=str(apparatus_root() / "replication_package/v1_main/corpus/main_tasks.jsonl"),
        out=str(tmp_path / "out"),
        extraction_model="wrong-model",
        runs_per_task=1,
        seed=20260623,
        skip_existing=False,
        checkpoint_every=1,
        cost_ledger=str(tmp_path / "cost.jsonl"),
        campaign_budget_usd=1.0,
        preflight_manifest=_manifest(tmp_path),
        expected_mlt_commit=git_commit(default_mlt_root()),
        expected_apparatus_commit=git_commit(apparatus_root()),
        require_clean_worktree=False,
        max_workers=1,
        domain_profile_mode="default",
        quiet=True,
    )
    assert run.cmd_run_cond_a(args) == 2
    assert not (tmp_path / "cost.jsonl").exists()


def test_pre_call_gate_rejects_adversarial_inputs(tmp_path):
    base = _valid_gate_kwargs(tmp_path)
    cases = [
        ("manifest_path", tmp_path / "missing.json", "preflight manifest does not exist"),
        ("expected_mlt_commit", "0" * 40, "MLT commit does not match command expectation"),
        ("model", "wrong-model", "wrong model"),
        ("tasks_path", apparatus_root() / "requirements.txt", "tasks corpus is not authorized"),
        ("campaign_budget_usd", 301.0, "exceeds remaining authorization"),
    ]
    for key, value, expected in cases:
        kwargs = copy.copy(base)
        kwargs[key] = value
        try:
            validate_pre_call_gate(**kwargs)
        except PreflightGateError as exc:
            assert any(expected in issue for issue in exc.issues)
        else:  # pragma: no cover
            raise AssertionError(f"gate accepted adversarial {key}")


def test_pre_call_gate_rejects_false_authorization_flag(tmp_path):
    kwargs = _valid_gate_kwargs(tmp_path)
    kwargs["manifest_path"] = _manifest(tmp_path, allow=False)
    try:
        validate_pre_call_gate(**kwargs)
    except PreflightGateError as exc:
        assert any("does not authorize paid execution" in issue for issue in exc.issues)
    else:  # pragma: no cover
        raise AssertionError("gate accepted false paid authorization")
