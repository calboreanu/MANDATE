"""Strict analyzer for the V3 corrected-routing rerun."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from mlt.mandate.execution_contract import (
    CONTRACT_SCHEMA_VERSION,
    has_blocking_or_insufficient_signal,
    validate_result_envelope,
)
from mlt.mandate.validator import validate_obj
from apparatus.preprocess.extract_mission_input import EXTRACTION_PROMPT


ALLOWED_STATES = {
    "EXECUTABLE",
    "NON_EXECUTABLE_GAPS",
    "NON_EXECUTABLE_VALIDATION",
    "FAILED",
}
EXPECTED_SEEDS = set(range(20260624, 20260634))
RUNS_PER_TASK = 10
EXPECTED_MODEL = "claude-sonnet-4-6"
CORPUS_HASHES = {
    "main_tasks.jsonl": "a6fb48501ebd58088452a0e68a329f0bf7b1df6b623e9abb940f7a8094b65dbb",
    "holdout_tasks.jsonl": "d92b7e3b68f15e3abfe54a2cff7c81a1b7f0959b03a7a7597c8e52501504f9ae",
}
V1_ROLES = {
    "cond_a_main": "replication_package/v1_main/system_outputs/cond_a_main.jsonl",
    "cond_a_holdout": "replication_package/v1_main/system_outputs/cond_a_holdout.jsonl",
    "cond_b_main": "replication_package/v1_main/system_outputs/cond_b_main.jsonl",
    "cond_b_holdout": "replication_package/v1_main/system_outputs/cond_b_holdout.jsonl",
}
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


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


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            s = line.strip()
            if not s:
                continue
            try:
                rows.append(json.loads(s))
            except Exception as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
    return rows


def load_records(path: Path) -> list[dict[str, Any]]:
    if path.is_dir():
        rows = []
        for fp in sorted(path.glob("*.json")):
            if fp.name.endswith(".tmp") or ".tmp." in fp.name:
                raise ValueError(f"incomplete JSON checkpoint present: {fp}")
            rows.append(json.loads(fp.read_text(encoding="utf-8")))
        return rows
    return load_jsonl(path)


def load_corpus_ids(path: Path | None) -> set[str]:
    if path is None:
        return set()
    return {str(row.get("task_id")) for row in load_jsonl(path)}


def load_corpus_rows(paths: list[Path | None]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in paths:
        if path is None:
            continue
        for row in load_jsonl(path):
            task_id = str(row.get("task_id") or "")
            if task_id:
                rows[task_id] = row
    return rows


def split_for_task(task_id: str, main_ids: set[str] | None = None, holdout_ids: set[str] | None = None) -> str:
    if main_ids and task_id in main_ids:
        return "main"
    if holdout_ids and task_id in holdout_ids:
        return "holdout"
    text = str(task_id)
    if "-HOLD" in text or "-HOLDOUT" in text:
        return "holdout"
    return "main"


def _record_id(record: dict[str, Any]) -> str:
    return str(record.get("run_id") or "<missing-run-id>")


def _output(record: dict[str, Any]) -> dict[str, Any]:
    return record.get("output") if isinstance(record.get("output"), dict) else {}


def _gap_reports(record: dict[str, Any]) -> list[dict[str, Any]]:
    return [g for g in (_output(record).get("gap_reports") or []) if isinstance(g, dict)]


def _artifact(record: dict[str, Any]) -> dict[str, Any] | None:
    artifact = _output(record).get("artifact")
    return artifact if isinstance(artifact, dict) else None


def _envelope(record: dict[str, Any]) -> dict[str, Any] | None:
    env = _output(record).get("result_envelope")
    return env if isinstance(env, dict) else None


def _state(record: dict[str, Any]) -> str:
    return str(record.get("execution_state") or _output(record).get("execution_state") or "")


def _condition(record: dict[str, Any], fallback: str = "") -> str:
    sid = str(record.get("system_id") or "")
    if sid in {"cond_a", "cond_b"}:
        return sid
    rid = str(record.get("run_id") or "")
    if rid.startswith("cond_a__"):
        return "cond_a"
    if rid.startswith("cond_b__"):
        return "cond_b"
    return fallback


def record_blocks(record: dict[str, Any]) -> bool:
    return has_blocking_or_insufficient_signal(_gap_reports(record))


def _provider_responses(record: dict[str, Any]) -> list[dict[str, Any]]:
    out = _output(record)
    responses = out.get("provider_responses")
    return [r for r in responses if isinstance(r, dict)] if isinstance(responses, list) else []


def _cond_a_raw_response(record: dict[str, Any]) -> dict[str, Any]:
    meta = _output(record).get("mission_input_metadata")
    if not isinstance(meta, dict):
        return {}
    raw = meta.get("raw_provider_response")
    return raw if isinstance(raw, dict) else {}


def _budget_attempt_id(attempt: dict[str, Any]) -> str:
    return str(
        attempt.get("budget_reservation_id")
        or attempt.get("reservation_id")
        or ""
    )


def _normalize_budget_attempt(attempt: dict[str, Any], *, role: str = "") -> dict[str, Any]:
    row = dict(attempt)
    rid = _budget_attempt_id(row)
    if rid:
        row["budget_reservation_id"] = rid
        row.setdefault("reservation_id", rid)
    if role and not row.get("role"):
        row["role"] = role
    if row.get("cost_usd") is not None:
        cost = round(float(row.get("cost_usd") or 0.0), 6)
        row["cost_usd"] = cost
        row.setdefault("debit_usd", cost)
    elif row.get("debit_usd") is not None:
        cost = round(float(row.get("debit_usd") or 0.0), 6)
        row["cost_usd"] = cost
        row["debit_usd"] = cost
    return row


def _record_budget_attempts(record: dict[str, Any]) -> list[dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    condition = _condition(record)
    if condition == "cond_a":
        raw = _cond_a_raw_response(record)
        for attempt in list(raw.get("budget_attempts") or []):
            if isinstance(attempt, dict):
                attempts.append(_normalize_budget_attempt(attempt, role="PreExtractor"))
    elif condition == "cond_b":
        for response in _provider_responses(record):
            role = str(response.get("role") or "")
            raw = response.get("raw_response") if isinstance(response.get("raw_response"), dict) else {}
            for attempt in list(raw.get("budget_attempts") or []):
                if isinstance(attempt, dict):
                    attempts.append(_normalize_budget_attempt(attempt, role=role))
    out = _output(record)
    for attempt in list(out.get("recovered_budget_attempts") or []):
        if isinstance(attempt, dict):
            attempts.append(_normalize_budget_attempt(attempt))
    return attempts


def _attempt_cost_total(attempts: list[dict[str, Any]]) -> float:
    return round(sum(float(a.get("cost_usd") or 0.0) for a in attempts), 6)


def _attempt_accounting_mode(attempts: list[dict[str, Any]]) -> str:
    if all(
        str(a.get("cost_basis") or "").startswith("authoritative")
        or str(a.get("cost_basis") or "") == "undispatched_zero"
        for a in attempts
    ):
        return "exact"
    return "conservative_upper_bound"


def provider_cost_sum(record: dict[str, Any]) -> float | None:
    attempts = _record_budget_attempts(record)
    if attempts:
        return _attempt_cost_total(attempts)
    return None


def _hex64(value: Any) -> bool:
    return isinstance(value, str) and bool(HEX64_RE.match(value))


def _manifest_root(manifest: dict[str, Any], key: str, fallback_env: str) -> Path | None:
    value = manifest.get(key) or os.environ.get(fallback_env)
    if not value:
        return None
    return Path(str(value))


def _compare_hash_maps(
    *,
    rid: str,
    label: str,
    actual: Any,
    expected: Any,
) -> list[str]:
    issues: list[str] = []
    if not isinstance(expected, dict) or not expected:
        return [f"{rid}: preflight manifest missing {label} source hashes"]
    if not isinstance(actual, dict):
        return [f"{rid}: missing {label} source hashes"]
    actual_keys = set(actual)
    expected_keys = set(expected)
    missing = sorted(expected_keys - actual_keys)
    extra = sorted(actual_keys - expected_keys)
    changed = sorted(k for k in actual_keys & expected_keys if actual.get(k) != expected.get(k))
    if missing:
        issues.append(f"{rid}: {label} source hashes missing entries: {', '.join(missing)}")
    if extra:
        issues.append(f"{rid}: {label} source hashes extra entries: {', '.join(extra)}")
    if changed:
        issues.append(f"{rid}: {label} source hashes changed entries: {', '.join(changed)}")
    return issues


def _validate_manifest_files(manifest: dict[str, Any] | None) -> list[str]:
    if not manifest:
        return ["missing preflight manifest"]
    issues: list[str] = []
    mlt_root = _manifest_root(manifest, "mlt_root", "MLT_ROOT")
    eval_root = _manifest_root(manifest, "eval_root", "EVAL_ROOT")
    source_hashes = manifest.get("source_hashes") if isinstance(manifest.get("source_hashes"), dict) else {}
    for label, root in (("mlt", mlt_root), ("apparatus", eval_root)):
        expected = source_hashes.get(label)
        if not isinstance(expected, dict) or not expected:
            issues.append(f"preflight manifest missing {label} source hashes")
            continue
        if root is None:
            issues.append(f"preflight manifest missing {label} root")
            continue
        for rel, expected_hash in sorted(expected.items()):
            path = root / rel
            if not path.is_file():
                issues.append(f"preflight manifest {label} source file missing: {rel}")
                continue
            got = sha256_file(path)
            if got != expected_hash:
                issues.append(f"preflight manifest {label} source hash mismatch: {rel}")

    schema_hashes = manifest.get("schema_hashes") if isinstance(manifest.get("schema_hashes"), dict) else {}
    if mlt_root is not None and schema_hashes.get("result_envelope_schema"):
        path = mlt_root / "src/mlt/schemas/mandate-result-envelope.schema.json"
        if not path.is_file() or sha256_file(path) != schema_hashes["result_envelope_schema"]:
            issues.append("preflight result-envelope schema hash mismatch")
    else:
        issues.append("preflight manifest missing result-envelope schema hash")
    if eval_root is not None and schema_hashes.get("runrecord_schema_v1"):
        path = eval_root / "replication_package/v1_main/schemas/runrecord_schema_v1.json"
        if not path.is_file() or sha256_file(path) != schema_hashes["runrecord_schema_v1"]:
            issues.append("preflight RunRecord schema hash mismatch")
    else:
        issues.append("preflight manifest missing RunRecord schema hash")

    prompt_hashes = manifest.get("prompt_source_hashes") if isinstance(manifest.get("prompt_source_hashes"), dict) else {}
    if mlt_root is not None and prompt_hashes.get("mlt_prompt_templates_py"):
        path = mlt_root / "src/mlt/sdk/llm/prompt_templates.py"
        if not path.is_file() or sha256_file(path) != prompt_hashes["mlt_prompt_templates_py"]:
            issues.append("preflight MLT prompt-template source hash mismatch")
    else:
        issues.append("preflight manifest missing MLT prompt-template source hash")
    if eval_root is not None and prompt_hashes.get("extract_mission_input_py"):
        path = eval_root / "code/apparatus/preprocess/extract_mission_input.py"
        if not path.is_file() or sha256_file(path) != prompt_hashes["extract_mission_input_py"]:
            issues.append("preflight Cond-A extraction source hash mismatch")
    else:
        issues.append("preflight manifest missing Cond-A extraction source hash")

    template_hashes = manifest.get("prompt_template_hashes") if isinstance(manifest.get("prompt_template_hashes"), dict) else {}
    expected_template = template_hashes.get("cond_a_extraction_prompt_template")
    if expected_template and expected_template != sha256_text(EXTRACTION_PROMPT):
        issues.append("preflight Cond-A extraction prompt template hash mismatch")
    elif not expected_template:
        issues.append("preflight manifest missing Cond-A extraction prompt template hash")
    return issues


def _load_result_envelope_schema(manifest: dict[str, Any] | None) -> dict[str, Any] | None:
    root = _manifest_root(manifest or {}, "mlt_root", "MLT_ROOT")
    if root is None:
        return None
    path = root / "src/mlt/schemas/mandate-result-envelope.schema.json"
    if not path.is_file():
        return None
    return load_json(path)


def _validate_envelope_json_schema(envelope: dict[str, Any], schema: dict[str, Any] | None) -> list[str]:
    if schema is None:
        return ["result-envelope JSON Schema unavailable"]
    try:
        import jsonschema
    except Exception as exc:  # pragma: no cover - dependency is pinned in test env
        return [f"jsonschema unavailable: {exc}"]
    validator = jsonschema.Draft202012Validator(schema)
    return [
        f"result_envelope JSON Schema {'.'.join(str(p) for p in error.path) or '<root>'}: {error.message}"
        for error in sorted(validator.iter_errors(envelope), key=lambda e: list(e.path))
    ]


def _validate_record_provenance(
    record: dict[str, Any],
    *,
    preflight_manifest: dict[str, Any] | None,
) -> list[str]:
    rid = _record_id(record)
    if not preflight_manifest:
        return [f"{rid}: missing preflight manifest"]
    issues: list[str] = []
    mv = record.get("model_versions") if isinstance(record.get("model_versions"), dict) else {}
    source_hashes = preflight_manifest.get("source_hashes") if isinstance(preflight_manifest.get("source_hashes"), dict) else {}
    issues.extend(_compare_hash_maps(
        rid=rid,
        label="mlt",
        actual=mv.get("mlt_source_hashes"),
        expected=source_hashes.get("mlt"),
    ))
    issues.extend(_compare_hash_maps(
        rid=rid,
        label="apparatus",
        actual=mv.get("apparatus_source_hashes"),
        expected=source_hashes.get("apparatus"),
    ))
    schema_hashes = preflight_manifest.get("schema_hashes") if isinstance(preflight_manifest.get("schema_hashes"), dict) else {}
    if schema_hashes.get("result_envelope_schema") is None:
        issues.append(f"{rid}: preflight missing result-envelope schema hash")
    if schema_hashes.get("runrecord_schema_v1") is None:
        issues.append(f"{rid}: preflight missing RunRecord schema hash")
    return issues


def _validate_prompt_and_schema_evidence(
    record: dict[str, Any],
    *,
    preflight_manifest: dict[str, Any] | None,
    corpus_rows: dict[str, dict[str, Any]] | None,
) -> list[str]:
    rid = _record_id(record)
    issues: list[str] = []
    manifest = preflight_manifest or {}
    condition = _condition(record)
    if condition == "cond_a":
        meta = _output(record).get("mission_input_metadata") or {}
        template_hash = sha256_text(EXTRACTION_PROMPT)
        expected_template = (
            (manifest.get("prompt_template_hashes") or {}).get("cond_a_extraction_prompt_template")
            if isinstance(manifest.get("prompt_template_hashes"), dict)
            else None
        ) or template_hash
        if meta.get("extraction_prompt_template_sha256") != expected_template:
            issues.append(f"{rid}: Cond-A extraction prompt template hash mismatch")
        row = (corpus_rows or {}).get(str(record.get("task_id")))
        if row:
            task_text = str(row.get("request_text") if row.get("request_text") is not None else row.get("text") or "")
            expected_prompt = sha256_text(
                EXTRACTION_PROMPT.replace("{task_text}", task_text)
            )
            if meta.get("extraction_prompt_sha256") != expected_prompt:
                issues.append(f"{rid}: Cond-A rendered extraction prompt hash mismatch")
    elif condition == "cond_b":
        expected_schema_by_role = (
            manifest.get("provider_schema_sha256_by_role")
            if isinstance(manifest.get("provider_schema_sha256_by_role"), dict)
            else {}
        )
        if not expected_schema_by_role:
            issues.append(f"{rid}: preflight manifest missing provider schema hash expectations")
        for response in _provider_responses(record):
            role = str(response.get("role") or "")
            if not _hex64(response.get("prompt_sha256")):
                issues.append(f"{rid}: provider response {role} prompt hash invalid")
            if not _hex64(response.get("schema_sha256")):
                issues.append(f"{rid}: provider response {role} schema hash invalid")
            expected_schema = expected_schema_by_role.get(role)
            if expected_schema is None:
                issues.append(f"{rid}: preflight manifest missing provider schema hash for role {role}")
            elif response.get("schema_sha256") != expected_schema:
                issues.append(f"{rid}: provider response {role} schema hash mismatch")
            rendered_prompt = response.get("rendered_prompt")
            payload = response.get("canonical_prompt_payload")
            evidence_format = response.get("prompt_evidence_format")
            if isinstance(rendered_prompt, str):
                recomputed = sha256_text(rendered_prompt)
                if evidence_format not in (None, "rendered_prompt.v1"):
                    issues.append(f"{rid}: provider response {role} unknown prompt evidence format")
                if response.get("prompt_sha256") != recomputed:
                    issues.append(f"{rid}: provider response {role} prompt hash mismatch")
            elif isinstance(payload, dict):
                canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
                recomputed = sha256_text(canonical)
                if evidence_format not in (None, "canonical_prompt_payload.v1"):
                    issues.append(f"{rid}: provider response {role} unknown prompt evidence format")
                if response.get("prompt_sha256") != recomputed:
                    issues.append(f"{rid}: provider response {role} prompt hash mismatch")
            else:
                issues.append(f"{rid}: provider response {role} missing rendered prompt evidence")
    return issues


def _validate_budget_attempts(
    *,
    rid: str,
    label: str,
    raw: dict[str, Any],
    parent_cost_usd: Any = None,
) -> list[str]:
    issues: list[str] = []
    required = {"budget_attempts", "budget_total_cost_usd", "budget_cost_accounting"}
    missing = sorted(k for k in required if raw.get(k) in (None, ""))
    if missing:
        issues.append(f"{rid}: {label} missing budget fields: {', '.join(missing)}")
        return issues
    attempts = raw.get("budget_attempts")
    if not isinstance(attempts, list) or not attempts:
        issues.append(f"{rid}: {label} budget_attempts must be a non-empty list")
        return issues
    normalized: list[dict[str, Any]] = []
    ids: list[str] = []
    for i, attempt in enumerate(attempts):
        if not isinstance(attempt, dict):
            issues.append(f"{rid}: {label} budget attempt {i} must be an object")
            continue
        row = _normalize_budget_attempt(attempt)
        normalized.append(row)
        attempt_id = _budget_attempt_id(row)
        if not attempt_id:
            issues.append(f"{rid}: {label} budget attempt {i} missing reservation ID")
        else:
            ids.append(attempt_id)
        for key in ("status", "cost_basis", "cost_usd"):
            if row.get(key) in (None, ""):
                issues.append(f"{rid}: {label} budget attempt {i} missing {key}")
    duplicates = sorted(item for item, count in Counter(ids).items() if count > 1)
    if duplicates:
        issues.append(f"{rid}: {label} duplicate budget attempt IDs: {', '.join(duplicates)}")
    try:
        total = _attempt_cost_total(normalized)
    except Exception as exc:
        issues.append(f"{rid}: {label} invalid budget attempt cost: {exc}")
        return issues
    if abs(total - round(float(raw.get("budget_total_cost_usd") or 0.0), 6)) > 0.000001:
        issues.append(f"{rid}: {label} budget attempt total mismatch")
    if parent_cost_usd is not None and abs(total - round(float(parent_cost_usd or 0.0), 6)) > 0.000001:
        issues.append(f"{rid}: {label} role cost mismatch")
    mode = raw.get("budget_cost_accounting")
    if mode not in ("exact", "conservative_upper_bound"):
        issues.append(f"{rid}: {label} invalid budget cost accounting status")
    else:
        expected_mode = _attempt_accounting_mode(normalized)
        if mode == "exact" and expected_mode != "exact":
            issues.append(f"{rid}: {label} budget accounting understates conservative cost")
    return issues


def _validate_provider_evidence(record: dict[str, Any]) -> list[str]:
    rid = _record_id(record)
    issues: list[str] = []
    cost = record.get("api_cost_usd")
    if cost is None:
        issues.append(f"{rid}: missing or null API cost")
    condition = _condition(record)
    if condition == "cond_a":
        raw = _cond_a_raw_response(record)
        required = {
            "provider", "model", "input_tokens", "output_tokens", "cost_usd",
            "text", "retry", "budget_attempts", "budget_total_cost_usd",
            "budget_cost_accounting",
        }
        missing = sorted(k for k in required if raw.get(k) in (None, ""))
        if missing:
            issues.append(f"{rid}: missing Cond-A provider provenance fields: {', '.join(missing)}")
        retry = raw.get("retry") if isinstance(raw.get("retry"), dict) else {}
        if retry.get("final_status") != "success":
            issues.append(f"{rid}: unresolved retry/provider errors")
        issues.extend(_validate_budget_attempts(
            rid=rid,
            label="Cond-A provider response",
            raw=raw,
            parent_cost_usd=raw.get("cost_usd"),
        ))
        meta = _output(record).get("mission_input_metadata") or {}
        for key in ("extraction_prompt_sha256", "extraction_prompt_template_sha256"):
            if not isinstance(meta, dict) or not meta.get(key):
                issues.append(f"{rid}: missing {key}")
    elif condition == "cond_b":
        responses = _provider_responses(record)
        if not responses:
            issues.append(f"{rid}: missing provider_responses")
        if _output(record).get("provider_response_count") != len(responses):
            issues.append(f"{rid}: provider_response_count mismatch")
        for i, response in enumerate(responses):
            required = {
                "role", "provider", "model", "prompt_sha256", "schema_sha256",
                "input_tokens", "output_tokens", "cost_usd", "raw_response",
            }
            missing = sorted(k for k in required if response.get(k) in (None, ""))
            if missing:
                issues.append(f"{rid}: provider response {i} missing fields: {', '.join(missing)}")
            if response.get("ok") is not True:
                issues.append(f"{rid}: unresolved retry/provider errors")
            raw = response.get("raw_response") if isinstance(response.get("raw_response"), dict) else {}
            if not isinstance(raw.get("retry"), dict):
                issues.append(f"{rid}: provider response {i} missing retry metadata")
            elif raw["retry"].get("final_status") != "success":
                issues.append(f"{rid}: unresolved retry/provider errors")
            issues.extend(_validate_budget_attempts(
                rid=rid,
                label=f"provider response {i}",
                raw=raw,
                parent_cost_usd=response.get("cost_usd"),
            ))
    else:
        issues.append(f"{rid}: unknown condition for provider provenance")

    provider_cost = provider_cost_sum(record)
    if provider_cost is None:
        issues.append(f"{rid}: missing provider cost evidence")
    elif cost is None or abs(round(float(cost), 6) - provider_cost) > 0.000001:
        issues.append(f"{rid}: provider cost sum mismatch")
    return issues


def _validate_artifact_and_gaps(record: dict[str, Any]) -> list[str]:
    rid = _record_id(record)
    issues: list[str] = []
    artifact = _artifact(record)
    if artifact is not None:
        artifact_type, artifact_issues = validate_obj(artifact)
        if artifact_type != "mandate-as-code":
            issues.append(f"{rid}: artifact type is {artifact_type}, expected mandate-as-code")
        for issue in artifact_issues:
            issues.append(f"{rid}: artifact {issue.kind} {issue.path}: {issue.message}")
    for i, gap in enumerate(_gap_reports(record)):
        gap_type, gap_issues = validate_obj(gap)
        if gap_type != "gap-report":
            issues.append(f"{rid}: gap {i} type is {gap_type}, expected gap-report")
        for issue in gap_issues:
            issues.append(f"{rid}: gap {i} {issue.kind} {issue.path}: {issue.message}")
    if artifact is None and not _gap_reports(record) and _state(record) != "FAILED":
        issues.append(f"{rid}: missing artifact/gap schema evidence")
    return issues


def validate_record(
    record: dict[str, Any],
    *,
    condition: str = "",
    expected_mlt_commit: str | None = None,
    expected_apparatus_commit: str | None = None,
    require_clean_worktree: bool = False,
    preflight_manifest: dict[str, Any] | None = None,
    corpus_rows: dict[str, dict[str, Any]] | None = None,
    result_envelope_schema: dict[str, Any] | None = None,
) -> list[str]:
    issues: list[str] = []
    rid = _record_id(record)
    state = _state(record)
    if state not in ALLOWED_STATES:
        issues.append(f"{rid}: invalid/missing execution_state {state!r}")
    if condition and _condition(record, condition) != condition:
        issues.append(f"{rid}: wrong condition/system ID")
    if record.get("system_id") != (condition or _condition(record)):
        issues.append(f"{rid}: system_id and condition disagree")
    if not isinstance(record.get("run_number"), int):
        issues.append(f"{rid}: missing run number")
    elif record.get("seed") != 20260623 + int(record.get("run_number")):
        issues.append(f"{rid}: wrong seed for run number")

    out = _output(record)
    if not out:
        issues.append(f"{rid}: output must be object")
        return issues
    envelope = _envelope(record)
    if envelope is None:
        issues.append(f"{rid}: missing result_envelope")
        return issues

    if record.get("contract_schema_version") != CONTRACT_SCHEMA_VERSION:
        issues.append(f"{rid}: unknown contract version")
    if envelope.get("contract_schema_version") != CONTRACT_SCHEMA_VERSION:
        issues.append(f"{rid}: envelope unknown contract version")
    if envelope.get("execution_state") != state:
        issues.append(f"{rid}: top-level/envelope state mismatch")
    if envelope.get("ok") != record.get("ok"):
        issues.append(f"{rid}: top-level/envelope ok mismatch")
    if envelope.get("schema_valid") != out.get("schema_valid"):
        issues.append(f"{rid}: top-level/envelope schema-validity mismatch")
    if out.get("execution_state") != state:
        issues.append(f"{rid}: output execution_state mismatch")
    if out.get("contract_schema_version") != CONTRACT_SCHEMA_VERSION:
        issues.append(f"{rid}: output contract_schema_version mismatch")

    issues.extend(
        f"{rid}: {issue}"
        for issue in _validate_envelope_json_schema(envelope, result_envelope_schema)
    )
    issues.extend(validate_result_envelope(
        envelope,
        artifact=_artifact(record),
        gap_reports=_gap_reports(record),
        schema_valid=out.get("schema_valid"),
        errors=list(record.get("errors") or []),
        validation=out.get("validation") if isinstance(out.get("validation"), dict) else None,
    ))
    issues = [f"{rid}: {issue}" if not issue.startswith(rid) else issue for issue in issues]

    if state == "EXECUTABLE" and record_blocks(record):
        issues.append(f"{rid}: EXECUTABLE with blocking/insufficient signal")
    if state == "NON_EXECUTABLE_GAPS" and not record_blocks(record):
        issues.append(f"{rid}: NON_EXECUTABLE_GAPS without recomputed blocking/insufficient signal")
    if state in {"NON_EXECUTABLE_GAPS", "NON_EXECUTABLE_VALIDATION", "FAILED"} and record.get("ok") is not False:
        issues.append(f"{rid}: {state} requires ok=false")
    if state == "EXECUTABLE" and record.get("ok") is not True:
        issues.append(f"{rid}: EXECUTABLE requires ok=true")

    issues.extend(_validate_artifact_and_gaps(record))
    issues.extend(_validate_provider_evidence(record))
    issues.extend(_validate_record_provenance(
        record,
        preflight_manifest=preflight_manifest,
    ))
    issues.extend(_validate_prompt_and_schema_evidence(
        record,
        preflight_manifest=preflight_manifest,
        corpus_rows=corpus_rows,
    ))

    mv = record.get("model_versions") if isinstance(record.get("model_versions"), dict) else {}
    dp = record.get("decoding_params") if isinstance(record.get("decoding_params"), dict) else {}
    if expected_mlt_commit and mv.get("mlt_git_commit") != expected_mlt_commit:
        issues.append(f"{rid}: mixed core commits")
    if expected_apparatus_commit and mv.get("apparatus_git_commit") != expected_apparatus_commit:
        issues.append(f"{rid}: mixed apparatus commits")
    if require_clean_worktree:
        if mv.get("mlt_git_dirty") is not False or mv.get("apparatus_git_dirty") is not False:
            issues.append(f"{rid}: dirty execution worktree")
    if _condition(record) == "cond_a":
        if mv.get("extraction_model") != EXPECTED_MODEL:
            issues.append(f"{rid}: wrong model/configuration")
        if dp.get("domain_profile_mode") != "default":
            issues.append(f"{rid}: wrong model/configuration")
        if dp.get("pipeline_strict") is not False or dp.get("emit_gaps") is not True:
            issues.append(f"{rid}: wrong model/configuration")
        if dp.get("llm_fallback_enabled") not in (None, False):
            issues.append(f"{rid}: wrong model/configuration")
    elif _condition(record) == "cond_b":
        if mv.get("llm_model") != EXPECTED_MODEL:
            issues.append(f"{rid}: wrong model/configuration")
        if dp.get("llm_backend") != "anthropic" or dp.get("llm_temperature") != 0.0:
            issues.append(f"{rid}: wrong model/configuration")
        if dp.get("llm_max_tokens") != 4096 or dp.get("domain_profile_mode") != "auto":
            issues.append(f"{rid}: wrong model/configuration")
        if dp.get("pipeline_strict") is not False or dp.get("emit_gaps") is not True:
            issues.append(f"{rid}: wrong model/configuration")
        if dp.get("llm_fallback_enabled") is not True:
            issues.append(f"{rid}: wrong model/configuration")
    return issues


def _validate_cost_ledger(records: list[dict[str, Any]], ledger_path: Path | None) -> list[str]:
    if ledger_path is None:
        return ["missing campaign cost ledger"]
    issues: list[str] = []
    rows = load_jsonl(ledger_path)
    reservations = [r for r in rows if r.get("row_type") == "reservation"]
    settlements = [r for r in rows if r.get("row_type") == "settlement"]
    summaries = [r for r in rows if r.get("row_type") in {"record_summary", None}]
    reservation_ids = [r.get("reservation_id") for r in reservations]
    if len(reservation_ids) != len(set(reservation_ids)):
        issues.append("duplicate cost-ledger reservation")
    settlement_ids = [r.get("reservation_id") for r in settlements]
    if len(settlement_ids) != len(set(settlement_ids)):
        issues.append("duplicate cost-ledger entry")
    active = sorted(set(reservation_ids) - set(settlement_ids))
    if active:
        issues.append(f"active/unsettled reservations present: {len(active)}")
    summary_by_run = defaultdict(list)
    for row in summaries:
        summary_by_run[row.get("run_id")].append(row)
    for run_id, rows_for_run in summary_by_run.items():
        if len(rows_for_run) > 1:
            issues.append(f"duplicate cost-ledger record summary: {run_id}")
    records_by_run = {rec.get("run_id"): rec for rec in records}
    for run_id, rec in records_by_run.items():
        if run_id not in summary_by_run:
            issues.append(f"{run_id}: resume checkpoint absent from cost ledger")
            continue
        ledger_cost = round(float(summary_by_run[run_id][0].get("api_cost_usd") or 0.0), 6)
        record_cost = round(float(rec.get("api_cost_usd") or 0.0), 6)
        if abs(ledger_cost - record_cost) > 0.000001:
            issues.append(f"{run_id}: campaign ledger cost mismatch")
    settlement_by_run = defaultdict(float)
    for row in settlements:
        settlement_by_run[row.get("run_id")] += float(row.get("actual_cost_usd") or 0.0)
    for run_id, rec in records_by_run.items():
        if run_id in settlement_by_run:
            if abs(round(settlement_by_run[run_id], 6) - round(float(rec.get("api_cost_usd") or 0.0), 6)) > 0.000001:
                issues.append(f"{run_id}: campaign ledger cost mismatch")
    settlements_by_run = defaultdict(list)
    for row in settlements:
        settlements_by_run[row.get("run_id")].append(row)
    for run_id, rec in records_by_run.items():
        run_settlements = settlements_by_run.get(run_id, [])
        if not run_settlements:
            continue
        attempt_by_id = defaultdict(list)
        for attempt in _record_budget_attempts(rec):
            attempt_id = _budget_attempt_id(attempt)
            if attempt_id:
                attempt_by_id[attempt_id].append(attempt)
        settlement_ids_for_run = {
            str(row.get("reservation_id") or "")
            for row in run_settlements
            if row.get("reservation_id")
        }
        for row in run_settlements:
            reservation_id = str(row.get("reservation_id") or "")
            matches = attempt_by_id.get(reservation_id, [])
            if len(matches) != 1:
                issues.append(
                    f"{run_id}: ledger settlement {reservation_id} appears "
                    f"{len(matches)} times in record attempt evidence"
                )
                continue
            attempt = matches[0]
            attempt_cost = round(float(attempt.get("cost_usd") or 0.0), 6)
            settlement_cost = round(float(row.get("actual_cost_usd") or 0.0), 6)
            if abs(attempt_cost - settlement_cost) > 0.000001:
                issues.append(f"{run_id}: ledger settlement {reservation_id} cost mismatch")
            if str(attempt.get("status") or "") != str(row.get("status") or ""):
                issues.append(f"{run_id}: ledger settlement {reservation_id} status mismatch")
            if str(attempt.get("cost_basis") or "") != str(row.get("cost_basis") or ""):
                issues.append(f"{run_id}: ledger settlement {reservation_id} cost basis mismatch")
        extra_ids = sorted(
            attempt_id
            for attempt_id in attempt_by_id
            if attempt_id not in settlement_ids_for_run
        )
        if extra_ids:
            issues.append(
                f"{run_id}: record attempt evidence absent from cost ledger: "
                + ", ".join(extra_ids)
            )
    return issues


def _cost_accounting_report(records: list[dict[str, Any]], ledger_path: Path | None) -> dict[str, Any]:
    if ledger_path is None or not ledger_path.exists():
        return {
            "ledger_path": str(ledger_path) if ledger_path else None,
            "mode": "missing",
            "settled_total_usd": None,
        }
    rows = load_jsonl(ledger_path)
    settlements = [row for row in rows if row.get("row_type") == "settlement"]
    summaries = [row for row in rows if row.get("row_type") in {"record_summary", None}]
    record_run_ids = {rec.get("run_id") for rec in records}
    conservative = [
        row for row in settlements
        if "conservative" in str(row.get("cost_basis") or "")
        or "reserved_bound" in str(row.get("status") or "")
    ]
    extra_attempt_cost = round(
        sum(
            float(row.get("actual_cost_usd") or 0.0)
            for row in settlements
            if row.get("run_id") not in record_run_ids
        ),
        6,
    )
    return {
        "ledger_path": str(ledger_path),
        "mode": "conservative_upper_bound" if conservative else "exact",
        "settled_total_usd": round(sum(float(row.get("actual_cost_usd") or 0.0) for row in settlements), 6),
        "record_summary_total_usd": round(sum(float(row.get("api_cost_usd") or 0.0) for row in summaries), 6),
        "conservative_settlement_count": len(conservative),
        "extra_attempt_cost_usd": extra_attempt_cost,
        "reservation_count": sum(1 for row in rows if row.get("row_type") == "reservation"),
        "settlement_count": len(settlements),
        "record_summary_count": len(summaries),
    }


def _validate_v1_paths(
    *,
    paths_by_role: dict[str, Path],
    manifest: dict[str, Any] | None,
) -> list[str]:
    issues: list[str] = []
    if set(paths_by_role) != set(V1_ROLES):
        missing = sorted(set(V1_ROLES) - set(paths_by_role))
        extra = sorted(set(paths_by_role) - set(V1_ROLES))
        if missing:
            issues.append(f"missing semantic V1 paths: {', '.join(missing)}")
        if extra:
            issues.append(f"unknown semantic V1 paths: {', '.join(extra)}")
    expected_hashes = (
        manifest.get("v1_condition_hashes")
        if manifest and isinstance(manifest.get("v1_condition_hashes"), dict)
        else {}
    )
    if not expected_hashes:
        issues.append("preflight manifest missing V1 condition hashes")
    for role, rel in V1_ROLES.items():
        path = paths_by_role.get(role)
        if path is None:
            continue
        if not path.is_file():
            issues.append(f"{role}: V1 file missing")
            continue
        if path.as_posix().endswith(rel) is False:
            issues.append(f"{role}: V1 file role/path mismatch")
        got = sha256_file(path)
        expected = expected_hashes.get(rel)
        if expected is None:
            issues.append(f"{role}: preflight manifest missing V1 hash")
        elif got != expected:
            issues.append(f"{role}: V1 hash mismatch")
    return issues


def _manifest_hash_for_path(hash_map: dict[str, str], path: Path) -> str | None:
    path_s = path.as_posix()
    for rel, digest in hash_map.items():
        if path_s.endswith(str(rel)):
            return digest
    return None


def _retry_cost_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    final_status = Counter()
    budget_accounting = Counter()
    retry_errors = 0
    provider_calls = 0
    for record in records:
        if _condition(record) == "cond_a":
            raw = _cond_a_raw_response(record)
            retry = raw.get("retry") if isinstance(raw.get("retry"), dict) else {}
            final_status[str(retry.get("final_status") or "missing")] += 1
            retry_errors += len(retry.get("errors") or []) if isinstance(retry, dict) else 0
            budget_accounting[str(raw.get("budget_cost_accounting") or "not_recorded")] += 1
            provider_calls += 1 if raw else 0
        else:
            for response in _provider_responses(record):
                raw = response.get("raw_response") if isinstance(response.get("raw_response"), dict) else {}
                retry = raw.get("retry") if isinstance(raw.get("retry"), dict) else {}
                final_status[str(retry.get("final_status") or "missing")] += 1
                retry_errors += len(retry.get("errors") or []) if isinstance(retry, dict) else 0
                budget_accounting[str(raw.get("budget_cost_accounting") or "not_recorded")] += 1
                provider_calls += 1
    return {
        "provider_call_count": provider_calls,
        "retry_final_status": dict(final_status),
        "retry_error_count": retry_errors,
        "budget_cost_accounting": dict(budget_accounting),
    }


def _trace_integrity_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    with_artifact = 0
    trace_entry_total = 0
    chain_hash_present = 0
    for record in records:
        artifact = _artifact(record)
        if not artifact:
            continue
        with_artifact += 1
        trace = artifact.get("trace") if isinstance(artifact.get("trace"), dict) else {}
        trace_entry_total += int(trace.get("entry_count") or 0)
        if trace.get("chain_hash"):
            chain_hash_present += 1
    return {
        "records_with_artifact": with_artifact,
        "trace_entry_total": trace_entry_total,
        "records_with_chain_hash": chain_hash_present,
        "validated_by": "mlt.mandate.validator.validate_obj",
    }


def summarize(
    records_by_condition: dict[str, list[dict[str, Any]]],
    *,
    smoke: bool,
    main_ids: set[str] | None = None,
    holdout_ids: set[str] | None = None,
    corpus_rows: dict[str, dict[str, Any]] | None = None,
    expected_mlt_commit: str | None = None,
    expected_apparatus_commit: str | None = None,
    require_clean_worktree: bool = False,
    cost_ledger: Path | None = None,
    preflight_manifest: dict[str, Any] | None = None,
) -> tuple[dict, list[str]]:
    issues: list[str] = []
    issues.extend(_validate_manifest_files(preflight_manifest))
    result_envelope_schema = _load_result_envelope_schema(preflight_manifest)
    all_records = []
    for condition, records in records_by_condition.items():
        for record in records:
            record["_condition"] = condition
        all_records.extend(records)

    seen_run_ids = set()
    seen_keys = set()
    for condition, records in records_by_condition.items():
        for rec in records:
            issues.extend(validate_record(
                rec,
                condition=condition,
                expected_mlt_commit=expected_mlt_commit,
                expected_apparatus_commit=expected_apparatus_commit,
                require_clean_worktree=require_clean_worktree,
                preflight_manifest=preflight_manifest,
                corpus_rows=corpus_rows,
                result_envelope_schema=result_envelope_schema,
            ))
            run_id = rec.get("run_id")
            if run_id in seen_run_ids:
                issues.append(f"duplicate run_id: {run_id}")
            seen_run_ids.add(run_id)
            key = (condition, rec.get("task_id"), rec.get("run_number"), rec.get("seed"))
            if key in seen_keys:
                issues.append(f"duplicate composite key: {key}")
            seen_keys.add(key)

    issues.extend(_validate_cost_ledger(all_records, cost_ledger))
    for label in ("mlt_source_hashes", "apparatus_source_hashes"):
        maps = {
            json.dumps(
                (rec.get("model_versions") or {}).get(label, {}),
                sort_keys=True,
            )
            for rec in all_records
        }
        if len(maps) > 1:
            issues.append(f"mixed {label} across records")

    blocking_records = [rec for rec in all_records if record_blocks(rec)]
    executable_with_blocking = [
        rec for rec in blocking_records
        if _state(rec) == "EXECUTABLE"
    ]

    state_counts = Counter(_state(rec) for rec in all_records)
    by_condition = {}
    fallback_outcomes: dict[str, dict[str, Any]] = {}
    for condition, records in records_by_condition.items():
        by_split = defaultdict(list)
        for rec in records:
            by_split[split_for_task(str(rec.get("task_id", "")), main_ids, holdout_ids)].append(rec)
        fallback_outcomes[condition] = {}
        for fallback_value in (False, True):
            rows = [rec for rec in records if bool(rec.get("any_llm_fallback")) is fallback_value]
            fallback_outcomes[condition][str(fallback_value).lower()] = {
                "records": len(rows),
                "states": dict(Counter(_state(rec) for rec in rows)),
            }
        by_condition[condition] = {
            "records": len(records),
            "states": dict(Counter(_state(rec) for rec in records)),
            "splits": {name: len(rows) for name, rows in sorted(by_split.items())},
            "fallback_records": sum(1 for rec in records if rec.get("any_llm_fallback")),
            "api_cost_usd": round(sum(float(rec.get("api_cost_usd") or 0.0) for rec in records), 6),
        }

        if not smoke:
            if len(records) != 1500:
                issues.append(f"{condition}: expected 1500 records, found {len(records)}")
            expected_by_split = {"main": main_ids or set(), "holdout": holdout_ids or set()}
            for split, expected_ids in expected_by_split.items():
                rows = by_split.get(split, [])
                if len(rows) != len(expected_ids) * RUNS_PER_TASK:
                    issues.append(f"{condition}/{split}: expected {len(expected_ids) * RUNS_PER_TASK} records, found {len(rows)}")
                task_ids = {str(rec.get("task_id")) for rec in rows}
                if task_ids != expected_ids:
                    issues.append(f"{condition}/{split}: task ID set mismatch")
                for task_id in expected_ids:
                    task_rows = [rec for rec in rows if str(rec.get("task_id")) == task_id]
                    seeds = {rec.get("seed") for rec in task_rows}
                    runs = {rec.get("run_number") for rec in task_rows}
                    if seeds != EXPECTED_SEEDS:
                        issues.append(f"{condition}/{task_id}: seeds mismatch")
                    if runs != set(range(1, RUNS_PER_TASK + 1)):
                        issues.append(f"{condition}/{task_id}: run numbers mismatch")
            if any(_state(rec) == "FAILED" for rec in records):
                issues.append(f"{condition}: final FAILED records present")

    n = len(blocking_records)
    if all_records and n == 0:
        issues.append("N=0 in a purported blocking-routing release report")
    zero_event_upper_95 = None if n == 0 else 1.0 - math.pow(0.05, 1.0 / n)
    report = {
        "ok": not issues,
        "smoke": smoke,
        "total_records": len(all_records),
        "primary_denominator_N": n,
        "executable_with_blocking_count": len(executable_with_blocking),
        "executable_with_blocking_rate": (len(executable_with_blocking) / n) if n else None,
        "zero_event_upper_95": zero_event_upper_95,
        "state_distribution": dict(state_counts),
        "by_condition": by_condition,
        "fallback_outcomes": fallback_outcomes,
        "retry_cost_report": _retry_cost_report(all_records),
        "trace_integrity_report": _trace_integrity_report(all_records),
        "cost_accounting": _cost_accounting_report(all_records, cost_ledger),
        "issues": issues,
    }
    return report, issues


def v1_counts(paths: list[Path]) -> dict[str, Any]:
    rows = []
    for path in paths:
        rows.extend(load_jsonl(path))
    return {
        "records": len(rows),
        "output_type": dict(Counter(row.get("output_type") for row in rows)),
        "ok": dict(Counter(str(row.get("ok")) for row in rows)),
        "blocking_or_insufficient": sum(1 for row in rows if record_blocks(row)),
    }


def write_tables(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "rerun_routing_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["condition", "records", "fallback_records", "api_cost_usd", "states"])
        for condition, row in sorted(report["by_condition"].items()):
            writer.writerow([
                condition,
                row["records"],
                row["fallback_records"],
                row["api_cost_usd"],
                json.dumps(row["states"], sort_keys=True),
            ])
    tex = (
        "\\begin{tabular}{lrrr}\n"
        "Condition & Records & Fallback records & Cost (USD)\\\\\n"
        "\\hline\n"
    )
    for condition, row in sorted(report["by_condition"].items()):
        tex += f"{condition} & {row['records']} & {row['fallback_records']} & {row['api_cost_usd']:.6f}\\\\\n"
    tex += "\\end{tabular}\n"
    (out_dir / "rerun_routing_summary.tex").write_text(tex, encoding="utf-8")
    with (out_dir / "fallback_outcomes.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["condition", "fallback", "records", "states"])
        for condition, rows in sorted(report.get("fallback_outcomes", {}).items()):
            for fallback, payload in sorted(rows.items()):
                writer.writerow([
                    condition,
                    fallback,
                    payload["records"],
                    json.dumps(payload["states"], sort_keys=True),
                ])
    (out_dir / "retry_cost_report.json").write_text(
        json.dumps(report.get("retry_cost_report", {}), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out_dir / "cost_report.json").write_text(
        json.dumps(report.get("cost_accounting", {}), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out_dir / "trace_integrity_report.json").write_text(
        json.dumps(report.get("trace_integrity_report", {}), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v3-cond-a", required=True, type=Path)
    parser.add_argument("--v3-cond-b", required=True, type=Path)
    parser.add_argument("--v1", nargs="*", type=Path, default=[])
    parser.add_argument("--v1-cond-a-main", type=Path)
    parser.add_argument("--v1-cond-a-holdout", type=Path)
    parser.add_argument("--v1-cond-b-main", type=Path)
    parser.add_argument("--v1-cond-b-holdout", type=Path)
    parser.add_argument("--main-corpus", type=Path)
    parser.add_argument("--holdout-corpus", type=Path)
    parser.add_argument("--cost-ledger", type=Path)
    parser.add_argument("--preflight-manifest", type=Path, required=True)
    parser.add_argument("--expected-mlt-commit", default="")
    parser.add_argument("--expected-apparatus-commit", default="")
    parser.add_argument("--require-clean-worktree", action="store_true")
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)

    issues: list[str] = []
    preflight_manifest: dict[str, Any] | None = None
    if not args.preflight_manifest.is_file():
        issues.append("missing preflight manifest")
    else:
        preflight_manifest = load_json(args.preflight_manifest)
    if not args.smoke:
        if args.main_corpus is None or args.holdout_corpus is None:
            issues.append("non-smoke mode requires both corpus files")
        if args.cost_ledger is None:
            issues.append("non-smoke mode requires --cost-ledger")
        if not args.expected_mlt_commit or not args.expected_apparatus_commit:
            issues.append("non-smoke mode requires expected core and apparatus commits")

    main_ids = load_corpus_ids(args.main_corpus)
    holdout_ids = load_corpus_ids(args.holdout_corpus)
    corpus_rows = load_corpus_rows([args.main_corpus, args.holdout_corpus])
    manifest_corpus_hashes = (
        preflight_manifest.get("corpus_hashes", {})
        if preflight_manifest and isinstance(preflight_manifest.get("corpus_hashes"), dict)
        else {}
    )
    if args.main_corpus:
        got = sha256_file(args.main_corpus)
        expected = _manifest_hash_for_path(manifest_corpus_hashes, args.main_corpus)
        if expected is None:
            issues.append("preflight manifest missing main corpus hash")
        elif got != expected:
            issues.append(f"main corpus hash mismatch: {got}")
    if args.holdout_corpus:
        got = sha256_file(args.holdout_corpus)
        expected = _manifest_hash_for_path(manifest_corpus_hashes, args.holdout_corpus)
        if expected is None:
            issues.append("preflight manifest missing holdout corpus hash")
        elif got != expected:
            issues.append(f"holdout corpus hash mismatch: {got}")

    v1_paths_by_role = {
        "cond_a_main": args.v1_cond_a_main,
        "cond_a_holdout": args.v1_cond_a_holdout,
        "cond_b_main": args.v1_cond_b_main,
        "cond_b_holdout": args.v1_cond_b_holdout,
    }
    v1_paths_by_role = {k: v for k, v in v1_paths_by_role.items() if v is not None}
    for path in args.v1:
        matched = False
        for role, rel in V1_ROLES.items():
            if path.as_posix().endswith(rel):
                v1_paths_by_role.setdefault(role, path)
                matched = True
                break
        if not matched:
            issues.append(f"unrecognized V1 path role: {path}")
    if not args.smoke:
        issues.extend(_validate_v1_paths(
            paths_by_role=v1_paths_by_role,
            manifest=preflight_manifest,
        ))

    report, record_issues = summarize(
        {
            "cond_a": load_records(args.v3_cond_a),
            "cond_b": load_records(args.v3_cond_b),
        },
        smoke=args.smoke,
        main_ids=main_ids,
        holdout_ids=holdout_ids,
        corpus_rows=corpus_rows,
        expected_mlt_commit=args.expected_mlt_commit or None,
        expected_apparatus_commit=args.expected_apparatus_commit or None,
        require_clean_worktree=args.require_clean_worktree,
        cost_ledger=args.cost_ledger,
        preflight_manifest=preflight_manifest,
    )
    issues.extend(record_issues)
    if v1_paths_by_role:
        report["v1"] = v1_counts([v1_paths_by_role[k] for k in sorted(v1_paths_by_role)])
    report["corpus_hashes"] = {
        "main_tasks.jsonl": sha256_file(args.main_corpus) if args.main_corpus else None,
        "holdout_tasks.jsonl": sha256_file(args.holdout_corpus) if args.holdout_corpus else None,
    }
    report["preflight_manifest"] = str(args.preflight_manifest)
    report["issues"] = issues
    report["ok"] = not issues

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    write_tables(report, args.out_dir)
    if issues:
        for issue in issues:
            print(f"FAIL: {issue}", file=sys.stderr)
        return 1
    print(
        "PASS: N={N}, executable_with_blocking={bad}".format(
            N=report["primary_denominator_N"],
            bad=report["executable_with_blocking_count"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
