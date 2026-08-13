"""Local preflight manifest and paid-call gate for the V3 rerun."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPERIMENT_LABEL = "Corrective validation on the mlt-stack 1.0.3-derived prompt stack"
AUTHORIZATION_CAP_USD = 300.0
EXPECTED_MODEL = "claude-sonnet-4-6"
EXPECTED_SEED_BASE = 20260623
ALLOWED_RUNS_PER_TASK = {1, 10}
APPARATUS_SOURCE_RELS = [
    "code/apparatus/consolidate_rerun.py",
    "code/apparatus/harness/ledger.py",
    "code/apparatus/harness/records.py",
    "code/apparatus/harness/runner.py",
    "code/apparatus/llm_retry.py",
    "code/apparatus/preflight.py",
    "code/apparatus/preprocess/extract_mission_input.py",
    "code/apparatus/rerun_analysis.py",
    "code/apparatus/run.py",
    "code/apparatus/systems/mandate_canonical.py",
]
MLT_SOURCE_RELS = [
    "src/mlt/mandate/execution_contract.py",
    "src/mlt/mandate/pipeline.py",
    "src/mlt/schemas/mandate-result-envelope.schema.json",
    "src/mlt/sdk/llm/prompt_templates.py",
]
CORPUS_RELS = [
    "replication_package/v1_main/corpus/main_tasks.jsonl",
    "replication_package/v1_main/corpus/holdout_tasks.jsonl",
]
V1_CONDITION_RELS = [
    "replication_package/v1_main/system_outputs/cond_a_main.jsonl",
    "replication_package/v1_main/system_outputs/cond_a_holdout.jsonl",
    "replication_package/v1_main/system_outputs/cond_b_main.jsonl",
    "replication_package/v1_main/system_outputs/cond_b_holdout.jsonl",
]
RUNRECORD_SCHEMA_REL = "replication_package/v1_main/schemas/runrecord_schema_v1.json"
RESULT_ENVELOPE_SCHEMA_REL = "src/mlt/schemas/mandate-result-envelope.schema.json"
MLT_PROMPT_SOURCE_REL = "src/mlt/sdk/llm/prompt_templates.py"
EXTRACT_PROMPT_SOURCE_REL = "code/apparatus/preprocess/extract_mission_input.py"


class PreflightGateError(RuntimeError):
    """Raised when a paid condition run must stop before provider setup."""

    def __init__(self, issues: list[str]):
        self.issues = issues
        super().__init__("pre-call gate failed: " + "; ".join(issues))


def apparatus_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_mlt_root() -> Path:
    return Path(os.environ["MLT_ROOT"]) if os.environ.get("MLT_ROOT") else Path.home() / "Desktop" / "MLT-Governance-Stack"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if text:
                rows.append(json.loads(text))
    return rows


def _git(args: list[str], root: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def git_commit(root: Path) -> str:
    try:
        return _git(["rev-parse", "HEAD"], root)
    except Exception:
        return "UNKNOWN"


def git_dirty_tracked(root: Path) -> bool:
    try:
        return bool(_git(["status", "--porcelain", "--untracked-files=no"], root))
    except Exception:
        return True


def _hash_files(root: Path, rels: list[str]) -> dict[str, str]:
    return {rel: sha256_file(root / rel) for rel in rels}


def _match_manifest_hash(hash_map: dict[str, str], path: Path) -> str | None:
    posix = path.resolve().as_posix()
    for rel, digest in hash_map.items():
        if posix.endswith(rel):
            return digest
    return None


def _provider_schema_hashes(mlt_root: Path, eval_root: Path) -> dict[str, str]:
    previous = os.environ.get("MLT_ROOT")
    os.environ["MLT_ROOT"] = str(mlt_root)
    if str(eval_root / "code") not in sys.path:
        sys.path.insert(0, str(eval_root / "code"))
    if str(mlt_root / "src") not in sys.path:
        sys.path.insert(0, str(mlt_root / "src"))
    try:
        from mlt.sdk.llm import LLMAdapter, LLMConfig, LLMResponse
        from apparatus.systems.mandate_canonical import run_cond_b

        class SchemaCaptureAdapter(LLMAdapter):
            provider = "anthropic"

            def __init__(self):
                self.config = LLMConfig(model_path=EXPECTED_MODEL, max_tokens=4096, retry_count=0)
                self._role = ""
                self.schema_hashes: dict[str, str] = {}

            def set_current_role(self, role_name):
                self._role = str(role_name or "")

            def generate(self, prompt, schema):
                role = self._role or "UNKNOWN_ROLE"
                self.schema_hashes[role] = sha256_text(json.dumps(schema, sort_keys=True, default=str))
                props = schema.get("properties", {}) if isinstance(schema, dict) else {}
                output: dict[str, Any] = {"decision_summary": "Use deterministic core."}
                if "mission_id" in props:
                    output.update({
                        "mission_id": "TASK-MAIN-FIN-001",
                        "intent": "Assess reporting controls.",
                        "minimum_outcome": "Minimum outcome.",
                        "target_outcome": "Target outcome.",
                        "constraints": ["FORBIDS data_exfiltration"],
                        "scope": ["financial reporting"],
                        "risk_tolerance": "LOW",
                    })
                if "minimum_outcome" in props:
                    output["minimum_outcome"] = "Minimum outcome."
                if "target_outcome" in props:
                    output["target_outcome"] = "Target outcome."
                if "risk_tolerance" in props:
                    output["risk_tolerance"] = "LOW"
                if "candidate_coa_count" in props:
                    output["candidate_coa_count"] = 1
                if "selected_reference_ids" in props:
                    output["selected_reference_ids"] = []
                return LLMResponse(
                    output=output,
                    tokens_used=1,
                    latency_ms=0.0,
                    raw_response={"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "text": "{}"},
                )

            def generate_with_trace(self, prompt, schema):
                response = self.generate(prompt, schema)
                return response, {"provider": self.provider, "model": EXPECTED_MODEL}

        adapter = SchemaCaptureAdapter()
        run_cond_b(
            "TASK-MAIN-FIN-001",
            "Assess reporting controls.",
            adapter,
            seed=20260624,
            run_id="cond_b__TASK-MAIN-FIN-001__r01",
            run_number=1,
            retry_backoff_sec=(),
            domain_profile_mode="auto",
        )
        return dict(sorted(adapter.schema_hashes.items()))
    finally:
        if previous is None:
            os.environ.pop("MLT_ROOT", None)
        else:
            os.environ["MLT_ROOT"] = previous


def build_manifest(
    *,
    mlt_root: Path,
    eval_root: Path,
    allow_paid_after_preflight: bool = False,
    prior_authorized_spend_usd: float = 0.0,
    include_package_freeze: bool = True,
) -> dict[str, Any]:
    from apparatus.preprocess.extract_mission_input import EXTRACTION_PROMPT

    corpus_hashes = _hash_files(eval_root, CORPUS_RELS)
    v1_hashes = _hash_files(eval_root, V1_CONDITION_RELS)
    schema_by_role = _provider_schema_hashes(mlt_root, eval_root)
    prompt_template_source_hash = sha256_file(mlt_root / MLT_PROMPT_SOURCE_REL)
    package_freeze: list[str] = []
    if include_package_freeze:
        try:
            freeze = subprocess.check_output(
                [sys.executable, "-m", "pip", "freeze"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            package_freeze = [line for line in freeze.splitlines() if line.strip()]
        except Exception:
            package_freeze = []
    remaining = round(AUTHORIZATION_CAP_USD - float(prior_authorized_spend_usd or 0.0), 6)
    return {
        "apparatus_commit": git_commit(eval_root),
        "apparatus_dirty_tracked": git_dirty_tracked(eval_root),
        "authorization_cap_usd": AUTHORIZATION_CAP_USD,
        "contract_schema_version": "mandate-result-envelope.v1",
        "corpus_hashes": corpus_hashes,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "eval_root": str(eval_root),
        "experiment_label": EXPERIMENT_LABEL,
        "mlt_commit": git_commit(mlt_root),
        "mlt_dirty_tracked": git_dirty_tracked(mlt_root),
        "mlt_root": str(mlt_root),
        "package_freeze": package_freeze,
        "paid_execution_allowed_after_preflight": bool(allow_paid_after_preflight),
        "paid_execution_started": False,
        "platform": {
            "machine": platform.machine(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "system": platform.system(),
        },
        "prior_authorized_spend_usd": round(float(prior_authorized_spend_usd or 0.0), 6),
        "remaining_authorization_usd": remaining,
        "prompt_source_hashes": {
            "extract_mission_input_py": sha256_file(eval_root / EXTRACT_PROMPT_SOURCE_REL),
            "mlt_prompt_templates_py": prompt_template_source_hash,
        },
        "prompt_template_hashes": {
            "cond_a_extraction_prompt_template": sha256_text(EXTRACTION_PROMPT),
        },
        "provider_prompt_template_source_sha256_by_role": {
            role: prompt_template_source_hash for role in sorted(schema_by_role)
        },
        "provider_schema_sha256_by_role": schema_by_role,
        "schema_hashes": {
            "result_envelope_schema": sha256_file(mlt_root / RESULT_ENVELOPE_SCHEMA_REL),
            "runrecord_schema_v1": sha256_file(eval_root / RUNRECORD_SCHEMA_REL),
        },
        "source_hashes": {
            "apparatus": _hash_files(eval_root, APPARATUS_SOURCE_RELS),
            "mlt": _hash_files(mlt_root, MLT_SOURCE_RELS),
        },
        "stop_conditions": {
            "requires_clean_worktree": True,
            "requires_cost_ledger": True,
            "requires_preflight_manifest": True,
            "requires_smoke_pass_before_full_campaign": True,
            "stop_on_executable_blocking_or_insufficient": True,
            "stop_on_secret_scan_hit": True,
        },
        "v1_condition_hashes": v1_hashes,
    }


def validate_pre_call_gate(
    *,
    manifest_path: Path | None,
    expected_mlt_commit: str | None,
    expected_apparatus_commit: str | None,
    require_clean_worktree: bool,
    cost_ledger: str | None,
    campaign_budget_usd: float | None,
    condition: str,
    tasks_path: Path,
    model: str,
    seed: int,
    runs_per_task: int,
    domain_profile_mode: str,
    llm_backend: str = "",
    mlt_root: Path | None = None,
    eval_root: Path | None = None,
) -> dict[str, Any]:
    issues: list[str] = []
    if manifest_path is None:
        issues.append("missing --preflight-manifest")
        manifest: dict[str, Any] = {}
    elif not manifest_path.is_file():
        issues.append("preflight manifest does not exist")
        manifest = {}
    else:
        manifest = load_json(manifest_path)

    mlt_root = (mlt_root or default_mlt_root()).resolve()
    eval_root = (eval_root or apparatus_root()).resolve()
    if manifest:
        if manifest.get("paid_execution_allowed_after_preflight") is not True:
            issues.append("preflight manifest does not authorize paid execution")
        if Path(str(manifest.get("mlt_root", ""))).resolve() != mlt_root:
            issues.append("current MLT_ROOT does not match preflight manifest")
        if Path(str(manifest.get("eval_root", ""))).resolve() != eval_root:
            issues.append("current apparatus root does not match preflight manifest")

    actual_mlt = git_commit(mlt_root)
    actual_app = git_commit(eval_root)
    if not expected_mlt_commit:
        issues.append("missing --expected-mlt-commit")
    if not expected_apparatus_commit:
        issues.append("missing --expected-apparatus-commit")
    for label, actual, expected, manifest_key in (
        ("MLT", actual_mlt, expected_mlt_commit, "mlt_commit"),
        ("apparatus", actual_app, expected_apparatus_commit, "apparatus_commit"),
    ):
        if expected and actual != expected:
            issues.append(f"{label} commit does not match command expectation")
        if manifest and actual != manifest.get(manifest_key):
            issues.append(f"{label} commit does not match preflight manifest")

    if require_clean_worktree:
        if git_dirty_tracked(mlt_root):
            issues.append("MLT tracked worktree is dirty")
        if git_dirty_tracked(eval_root):
            issues.append("apparatus tracked worktree is dirty")

    if (cost_ledger and campaign_budget_usd is None) or (campaign_budget_usd is not None and not cost_ledger):
        issues.append("--cost-ledger and --campaign-budget-usd must be supplied together")
    if not cost_ledger:
        issues.append("missing shared campaign cost ledger")
    if campaign_budget_usd is None:
        issues.append("missing campaign budget cap")
    elif manifest:
        remaining = manifest.get("remaining_authorization_usd")
        if remaining is None:
            remaining = float(manifest.get("authorization_cap_usd", AUTHORIZATION_CAP_USD) or AUTHORIZATION_CAP_USD) - float(manifest.get("prior_authorized_spend_usd", 0.0) or 0.0)
        if float(campaign_budget_usd) > float(remaining):
            issues.append("campaign budget cap exceeds remaining authorization")

    if model != EXPECTED_MODEL:
        issues.append("wrong model for authorized experiment")
    if seed != EXPECTED_SEED_BASE:
        issues.append("wrong seed base for authorized experiment")
    if int(runs_per_task) not in ALLOWED_RUNS_PER_TASK:
        issues.append("runs-per-task outside authorized experiment")
    if condition == "cond_a" and domain_profile_mode != "default":
        issues.append("Cond-A must use default domain-profile mode")
    if condition == "cond_b":
        if domain_profile_mode != "auto":
            issues.append("Cond-B must use auto domain-profile mode")
        if llm_backend != "anthropic":
            issues.append("Cond-B must use the Anthropic backend")

    if manifest:
        source_hashes = manifest.get("source_hashes") if isinstance(manifest.get("source_hashes"), dict) else {}
        for label, root, rels in (("mlt", mlt_root, MLT_SOURCE_RELS), ("apparatus", eval_root, APPARATUS_SOURCE_RELS)):
            expected = source_hashes.get(label) if isinstance(source_hashes.get(label), dict) else {}
            for rel in rels:
                path = root / rel
                if rel not in expected:
                    issues.append(f"preflight manifest missing {label} source hash: {rel}")
                elif not path.is_file() or sha256_file(path) != expected[rel]:
                    issues.append(f"{label} source hash mismatch before paid call: {rel}")
        schema_hashes = manifest.get("schema_hashes") if isinstance(manifest.get("schema_hashes"), dict) else {}
        schema_checks = {
            "result_envelope_schema": mlt_root / RESULT_ENVELOPE_SCHEMA_REL,
            "runrecord_schema_v1": eval_root / RUNRECORD_SCHEMA_REL,
        }
        for key, path in schema_checks.items():
            if not schema_hashes.get(key):
                issues.append(f"preflight manifest missing schema hash: {key}")
            elif not path.is_file() or sha256_file(path) != schema_hashes[key]:
                issues.append(f"schema hash mismatch before paid call: {key}")
        prompt_hashes = manifest.get("prompt_source_hashes") if isinstance(manifest.get("prompt_source_hashes"), dict) else {}
        prompt_checks = {
            "mlt_prompt_templates_py": mlt_root / MLT_PROMPT_SOURCE_REL,
            "extract_mission_input_py": eval_root / EXTRACT_PROMPT_SOURCE_REL,
        }
        for key, path in prompt_checks.items():
            if not prompt_hashes.get(key):
                issues.append(f"preflight manifest missing prompt source hash: {key}")
            elif not path.is_file() or sha256_file(path) != prompt_hashes[key]:
                issues.append(f"prompt source hash mismatch before paid call: {key}")
        corpus_hashes = manifest.get("corpus_hashes") if isinstance(manifest.get("corpus_hashes"), dict) else {}
        expected_task_hash = _match_manifest_hash(corpus_hashes, tasks_path)
        if expected_task_hash is None:
            issues.append("tasks corpus is not authorized by preflight manifest")
        elif not tasks_path.is_file() or sha256_file(tasks_path) != expected_task_hash:
            issues.append("tasks corpus hash mismatch before paid call")
        for rel in V1_CONDITION_RELS:
            expected = (manifest.get("v1_condition_hashes") or {}).get(rel)
            if not expected:
                issues.append(f"preflight manifest missing V1 hash: {rel}")
            elif sha256_file(eval_root / rel) != expected:
                issues.append(f"V1 condition hash mismatch before paid call: {rel}")

    if issues:
        raise PreflightGateError(issues)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    build = sub.add_parser("build-manifest")
    build.add_argument("--mlt-root", type=Path, default=default_mlt_root())
    build.add_argument("--eval-root", type=Path, default=apparatus_root())
    build.add_argument("--out", type=Path, required=True)
    build.add_argument("--allow-paid-after-preflight", action="store_true")
    build.add_argument("--prior-authorized-spend-usd", type=float, default=0.0)
    build.add_argument("--no-package-freeze", action="store_true")
    args = parser.parse_args(argv)
    if args.cmd == "build-manifest":
        manifest = build_manifest(
            mlt_root=args.mlt_root.resolve(),
            eval_root=args.eval_root.resolve(),
            allow_paid_after_preflight=args.allow_paid_after_preflight,
            prior_authorized_spend_usd=args.prior_authorized_spend_usd,
            include_package_freeze=not args.no_package_freeze,
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        print(args.out)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
