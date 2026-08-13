#!/usr/bin/env python3
"""
MVP ablation-evaluation harness — canonical MLT MANDATE + the seven ablations.

For each corpus task it builds a minimal MissionInput from the request text
(deterministic; no extraction LLM), runs the canonical engine plus each
runnable ablation, writes one RunRecord per (system, task), and emits an
aggregate comparison summary (summary.json + SUMMARY.md).

With --gradeable it also emits the judge-ready layout used by the v2 grading
stage: anonymized_outputs/OUT-*.json ({anon_id, task_id, output_type, output,
ok}, system identity stripped) + anonymization_mapping.json (the private
OUT->system key) + grading_manifest.jsonl.

Deterministic ablations (A2..A7) need no model. A1 (role separation) is a single
combined LLM call; --include-a1 runs it with a deterministic stub adapter.

Usage:
    PYTHONPATH="<eval_root>:<MLT>/src" python3 scripts/run_ablation_mvp.py \
        --tasks 04_ground_truth/main_tasks.jsonl 04_ground_truth/holdout_tasks.jsonl \
        --out _ablation_mvp --include-a1 --gradeable

Writes only under --out (never the frozen 07_system_outputs tree).
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

_HERE = Path(__file__).resolve()
_EVAL_ROOT = _HERE.parents[1]
if str(_EVAL_ROOT) not in sys.path:
    sys.path.insert(0, str(_EVAL_ROOT))

from apparatus.systems.mandate_canonical import (  # noqa: E402
    CODE_REF,
    _record_from_result,
    _role_timings,
    run_ablation,
)
from apparatus.harness.records import utc_now_iso  # noqa: E402
from mlt.mandate.models import MissionInput, PipelineConfig  # noqa: E402
from mlt.mandate.pipeline import Pipeline  # noqa: E402
from mlt.sdk.llm.adapter import LLMResponse  # noqa: E402

DETERMINISTIC_ABLATIONS = ["A2", "A3", "A4", "A5", "A6", "A7"]
# Output keys that would leak system identity to a blind judge.
_LEAK_KEYS = ("ablation_id", "domain_profile_mode", "domain_profile_name")


class _StubConfig:
    retry_count = 0


class _StubAdapter:
    """Deterministic single-call stub for A1 (no live model needed)."""

    def __init__(self) -> None:
        self.config = _StubConfig()

    def generate(self, prompt: str, schema: dict) -> LLMResponse:
        return LLMResponse(
            output={
                "anchor": {
                    "mission_intent": "single-pass combined intent",
                    "minimum": {"description": "minimum acceptable outcome"},
                    "target": {"description": "target outcome"},
                    "constraints": [],
                },
                "courses_of_action": [
                    {"coa_id": "COA-1", "approach": "single combined approach",
                     "task_dag": {"nodes": [], "edges": []}}
                ],
                "recommendation": {"primary_coa": "COA-1", "fallback_sequence": [],
                                   "rationale": "single combined pass"},
            },
            tokens_used=1,
            latency_ms=0.0,
        )


def _mission(task: Dict[str, Any]) -> MissionInput:
    return MissionInput(mission_id=str(task["task_id"]), intent=str(task.get("text", "")))


def _canonical_record(task: Dict[str, Any], seed: int) -> Dict[str, Any]:
    tid = str(task["task_id"])
    started = utc_now_iso()
    t0 = time.time()
    result = Pipeline(PipelineConfig(strict=False, emit_gaps=True)).run(_mission(task))
    elapsed = (time.time() - t0) * 1000.0
    rec = _record_from_result(
        run_id=f"canonical__{tid}__r{seed:02d}",
        task_id=tid,
        system_id="canonical",
        system_label="MANDATE v1.0.0rc1 canonical (minimal input)",
        run_number=1,
        seed=seed,
        started_at=started,
        elapsed_ms=elapsed,
        result=result,
        role_timings=_role_timings(result),
        model_versions={"mlt": CODE_REF},
        decoding_params={"condition": "canonical", "strict": False, "emit_gaps": True},
        api_cost_usd=None,
    )
    return rec.to_dict()


def _signature(rec: Dict[str, Any]) -> Dict[str, Any]:
    out = rec.get("output") or {}
    art = out.get("artifact") or {}
    anchor = art.get("anchor") or {}
    meta = art.get("metadata") or {}
    trace = art.get("trace") or {}
    coas = art.get("courses_of_action") or []
    bands = all(
        (c.get("risk_assessment") or {}).get("confidence_min")
        == (c.get("risk_assessment") or {}).get("confidence_target")
        for c in coas
    ) if coas else None
    return {
        "ok": bool(rec.get("ok")),
        "trace_entries": trace.get("entry_count"),
        "has_target_band": "target" in anchor,
        "has_nist_rmf": "nist_rmf" in meta,
        "has_registry_reference": "registry_reference" in art,
        "n_coas": len(coas),
        "coa_bands_collapsed": bands,
        "wall_clock_ms": rec.get("wall_clock_ms"),
    }


def _anon_id(run_id: str) -> str:
    return "OUT-" + hashlib.sha256(run_id.encode()).hexdigest()[:8].upper()


def _anonymized(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Judge-facing record: task_id + output + ok only; system identity removed."""
    out = dict(rec.get("output") or {})
    for k in _LEAK_KEYS:
        out.pop(k, None)
    return {
        "anon_id": _anon_id(str(rec.get("run_id", ""))),
        "task_id": rec.get("task_id"),
        "output_type": rec.get("output_type"),
        "output": out,
        "ok": bool(rec.get("ok")),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", nargs="+", default=["04_ground_truth/main_tasks.jsonl"])
    ap.add_argument("--out", default="_ablation_mvp")
    ap.add_argument("--limit", type=int, default=0, help="0 = all tasks")
    ap.add_argument("--seed", type=int, default=20260629)
    ap.add_argument("--include-a1", action="store_true")
    ap.add_argument("--gradeable", action="store_true",
                    help="also emit anonymized_outputs/ + anonymization_mapping.json")
    args = ap.parse_args()

    tasks: List[Dict[str, Any]] = []
    for tp in args.tasks:
        p = Path(tp)
        if not p.is_absolute():
            p = _EVAL_ROOT / p
        tasks += [json.loads(l) for l in open(p) if l.strip()]
    if args.limit:
        tasks = tasks[: args.limit]

    out_root = Path(args.out)
    if not out_root.is_absolute():
        out_root = _EVAL_ROOT / out_root
    out_root.mkdir(parents=True, exist_ok=True)

    systems = ["canonical"] + DETERMINISTIC_ABLATIONS + (["A1"] if args.include_a1 else [])
    agg: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
    records: List[Tuple[str, Dict[str, Any]]] = []  # (raw_system_dir, record)

    def handle(sys_dir: str, agg_key: str, rec: Dict[str, Any]) -> None:
        _write(out_root, sys_dir, str(rec["task_id"]), rec)
        agg[agg_key].append(_signature(rec))
        records.append((sys_dir, rec))

    for task in tasks:
        tid = str(task["task_id"])
        text = str(task.get("text", ""))
        handle("canonical", "canonical", _canonical_record(task, args.seed))
        for aid in DETERMINISTIC_ABLATIONS:
            handle(f"ablation_{aid.lower()}", aid,
                   run_ablation(tid, text, _mission(task), aid, seed=args.seed))
        if args.include_a1:
            handle("ablation_a1", "A1",
                   run_ablation(tid, text, _mission(task), "A1",
                                seed=args.seed, llm_adapter=_StubAdapter()))

    summary = _summarize(agg)
    (out_root / "summary.json").write_text(json.dumps(summary, indent=2))
    (out_root / "SUMMARY.md").write_text(_render_md(summary, len(tasks)))

    graded = 0
    if args.gradeable:
        graded = _emit_gradeable(out_root, records)

    print(f"Wrote {len(records)} records across {len(systems)} systems over "
          f"{len(tasks)} tasks -> {out_root}"
          + (f"; {graded} anonymized (gradeable)" if args.gradeable else ""))
    print(_render_md(summary, len(tasks)))
    return 0


def _emit_gradeable(out_root: Path, records: List[Tuple[str, Dict[str, Any]]]) -> int:
    anon_dir = out_root / "anonymized_outputs"
    anon_dir.mkdir(parents=True, exist_ok=True)
    mapping: Dict[str, Dict[str, Any]] = {}
    manifest: List[Dict[str, Any]] = []
    for _sys_dir, rec in records:
        a = _anonymized(rec)
        aid = a["anon_id"]
        (anon_dir / f"{aid}.json").write_text(json.dumps(a, indent=2))
        mapping[aid] = {
            "system_id": rec.get("system_id"),
            "system_label": rec.get("system_label"),
            "run_id": rec.get("run_id"),
            "run_number": rec.get("run_number"),
            "task_id": rec.get("task_id"),
        }
        manifest.append({"anon_id": aid, "task_id": rec.get("task_id")})
    (out_root / "anonymization_mapping.json").write_text(json.dumps(mapping, indent=2))
    with open(out_root / "grading_manifest.jsonl", "w") as f:
        for row in manifest:
            f.write(json.dumps(row) + "\n")
    return len(mapping)


def _write(out_root: Path, system: str, task_id: str, rec: Dict[str, Any]) -> None:
    d = out_root / system
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{system}__{task_id}.json").write_text(json.dumps(rec, indent=2))


def _summarize(agg: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for sys_id, sigs in agg.items():
        n = len(sigs)
        out[sys_id] = {
            "n": n,
            "ok": sum(1 for s in sigs if s["ok"]),
            "trace_entry_count_dist": dict(collections.Counter(s["trace_entries"] for s in sigs)),
            "has_target_band": sum(1 for s in sigs if s["has_target_band"]),
            "has_nist_rmf": sum(1 for s in sigs if s["has_nist_rmf"]),
            "has_registry_reference": sum(1 for s in sigs if s["has_registry_reference"]),
            "coa_bands_collapsed": sum(1 for s in sigs if s["coa_bands_collapsed"]),
            "mean_wall_clock_ms": round(
                sum(float(s["wall_clock_ms"] or 0) for s in sigs) / n, 3) if n else None,
        }
    return out


def _render_md(summary: Dict[str, Any], n_tasks: int) -> str:
    lines = [
        "# Ablation MVP — canonical vs ablations",
        "",
        f"Tasks: {n_tasks}. Deterministic (minimal-input) run; canonical engine "
        "= mlt-stack-1.0.0rc1.",
        "",
        "| System | n | ok | trace entries | target band | nist_rmf | registry | COA bands collapsed |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for sid in ["canonical", "A2", "A3", "A4", "A5", "A6", "A7", "A1"]:
        s = summary.get(sid)
        if not s:
            continue
        lines.append(
            f"| {sid} | {s['n']} | {s['ok']} | {s['trace_entry_count_dist']} | "
            f"{s['has_target_band']} | {s['has_nist_rmf']} | "
            f"{s['has_registry_reference']} | {s['coa_bands_collapsed']} |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
