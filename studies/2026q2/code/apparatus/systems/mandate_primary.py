"""
MANDATE-primary system adapter (Workstream B1, with the B-A2 input adapter).

Wraps the AEGIS MANDATE 1+6 pipeline behind the harness System interface.

Input adapter (Decisions memo, Decision 3, recommended option): the thinnest
adapter. The raw request_text becomes MissionInput.intent; the structured
MissionInput fields are left for MANDATE's own fine-tuned Intake role to
populate. No pre-processing is done that the baselines do not also receive.

Modes:
  * "deterministic": runs MANDATE's rule-based path. Used for harness testing
    and as a substrate for some ablations. This is NOT MANDATE-primary as the
    protocol defines it.
  * "ollama": runs the fine-tuned six-role configuration through Ollama. This
    IS MANDATE-primary. Verifying it runs with no silent fallback to the
    deterministic path is Workstream A1 and happens on the eval host.

AEGIS is imported read-only from a configured source path. This module never
modifies AEGIS (SETUP Section 6).
"""
from __future__ import annotations

import dataclasses
import json
import os
import sys
import time
from typing import Optional

from ..harness.records import (RoleTiming, OUTPUT_MANDATE_AS_CODE,
                               OUTPUT_GAP_REPORT)
from ..harness.system import System


def load_ollama_config(aegis_root: str) -> dict:
    """Load AEGIS's canonical Ollama LLM configuration.

    Reads `configs/llm_defaults.json` from the AEGIS repository, keeps only
    the keys that `mandate.models.PipelineConfig` actually accepts, and
    resolves a relative `llm_prompt_dir` against the AEGIS root. This is the
    authoritative MANDATE-primary backend configuration; it is read from
    AEGIS, not invented here.

    Returns a dict suitable as `ollama_config=` for MandatePrimarySystem.
    """
    candidates = [os.path.join(aegis_root, "configs", "llm_defaults.json"),
                  os.path.join(aegis_root, "config", "llm_defaults.json")]
    cfg_path = None
    for p in candidates:
        if os.path.isfile(p):
            cfg_path = p
            break
    if cfg_path is None:
        raise FileNotFoundError(
            "llm_defaults.json not found under %s (looked in configs/ and "
            "config/)" % aegis_root)
    with open(cfg_path) as f:
        raw = json.load(f)

    src = os.path.join(aegis_root, "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from mandate.models import PipelineConfig
    valid = {fld.name for fld in dataclasses.fields(PipelineConfig)}

    cfg = {k: v for k, v in raw.items() if k in valid}
    prompt_dir = cfg.get("llm_prompt_dir", "")
    if prompt_dir and not os.path.isabs(prompt_dir):
        cfg["llm_prompt_dir"] = os.path.join(aegis_root, prompt_dir)

    # Procedure-role RAG retriever. AEGIS's cli.py reads llm_rag_index, which
    # is NOT a PipelineConfig constructor field, builds a retriever with
    # make_procedure_retriever, and passes it as llm_procedure_retriever.
    # Replicating that here is required for fidelity: without it the
    # Procedure role runs with no retrieved MITRE ATT&CK context, which is
    # not MANDATE-primary as the CLI runs it. (Filtering raw to PipelineConfig
    # fields silently drops llm_rag_index, so this step must be explicit.)
    rag_index = str(raw.get("llm_rag_index", "") or "").strip()
    if rag_index:
        if not os.path.isabs(rag_index):
            rag_index = os.path.join(aegis_root, rag_index)
        if not os.path.isfile(rag_index):
            raise FileNotFoundError(
                "llm_rag_index is set but the index file is missing: %s"
                % rag_index)
        from aegis.llm.rag_retriever import make_procedure_retriever
        cfg["llm_procedure_retriever"] = make_procedure_retriever(rag_index)
    return cfg


class MandatePrimarySystem(System):
    system_id = "mandate_primary"
    system_label = "MANDATE-primary"
    output_type = OUTPUT_MANDATE_AS_CODE

    def __init__(self, aegis_src_path: str, mode: str = "deterministic",
                 ollama_config: Optional[dict] = None, code_ref: str = ""):
        """
        aegis_src_path: path to the AEGIS `src/` directory (cloned at the
                        pinned git tag for the real study).
        mode:           "deterministic" or "ollama".
        ollama_config:  kwargs for mandate.models.PipelineConfig that select
                        the Ollama backend and the per-role fine-tuned models;
                        pinned in the pre-registration. Only used in ollama
                        mode.
        code_ref:       AEGIS git tag or commit, recorded in every RunRecord.
        """
        if mode not in ("deterministic", "ollama"):
            raise ValueError(f"unknown mode: {mode!r}")
        self.aegis_src_path = aegis_src_path
        self.mode = mode
        self.ollama_config = dict(ollama_config or {})
        self.code_ref = code_ref
        self._ensure_importable()

    def _ensure_importable(self) -> None:
        if self.aegis_src_path not in sys.path:
            sys.path.insert(0, self.aegis_src_path)
        # Fail early and clearly if AEGIS is not where we were told.
        import mandate.pipeline  # noqa: F401

    def _build_config(self):
        from mandate.models import PipelineConfig
        if self.mode == "deterministic":
            return PipelineConfig()
        return PipelineConfig(**self.ollama_config)

    def describe(self) -> dict:
        d = super().describe()
        d.update({
            "mode": self.mode,
            "aegis_src_path": self.aegis_src_path,
            "code_ref": self.code_ref,
            "input_adapter": "thinnest: request_text -> MissionInput.intent",
            "ollama_config": self.ollama_config,
        })
        return d

    def run(self, request_text: str, *, run_id: str, task_id: str,
            run_number: int, seed: Optional[int] = None):
        from mandate.pipeline import Pipeline
        from mandate.models import MissionInput

        rec = self._new_record(run_id=run_id, task_id=task_id,
                               run_number=run_number, seed=seed)
        rec.code_ref = self.code_ref
        if self.mode == "ollama":
            # record the config but not the retriever callable itself; note
            # whether the Procedure-role RAG retriever is wired
            rec.decoding_params = {
                k: v for k, v in self.ollama_config.items()
                if k != "llm_procedure_retriever"}
            rec.decoding_params["rag_retriever_wired"] = (
                "llm_procedure_retriever" in self.ollama_config)
        else:
            rec.decoding_params = {"mode": "deterministic"}

        # --- thinnest input adapter ---
        mission = MissionInput(mission_id=task_id, intent=request_text)

        t0 = time.time()
        try:
            result = Pipeline(self._build_config()).run(mission)
        except Exception as e:
            rec.wall_clock_ms = (time.time() - t0) * 1000.0
            rec.ok = False
            rec.errors = [f"pipeline error: {e!r}"]
            return rec
        rec.wall_clock_ms = (time.time() - t0) * 1000.0
        rec.local_compute_ms = rec.wall_clock_ms

        # --- per-role llm flags (the silent-fallback detector) ---
        llm_flags = {}
        for rr in getattr(result, "role_results", []) or []:
            arts = getattr(rr, "artifacts", {}) or {}
            llm_flags[rr.role_name] = (
                bool(arts.get("llm_used", False)),
                bool(arts.get("llm_fallback", False)),
                str(arts.get("llm_fallback_reason", "")),
            )

        # --- per-role timings (durations from PipelineMetrics) ---
        metric_rows = []
        metrics = getattr(result, "metrics", None)
        if metrics is not None:
            try:
                metric_rows = metrics.to_dict().get("role_timings", []) or []
            except Exception:
                metric_rows = getattr(metrics, "role_timings", []) or []

        timings = []
        if metric_rows:
            for row in metric_rows:
                name = row.get("role_name", "")
                used, fell, reason = llm_flags.get(name, (False, False, ""))
                timings.append(RoleTiming(
                    role_name=name,
                    status="success" if row.get("success", True) else "failed",
                    duration_ms=float(row.get("duration_ms", 0.0)),
                    llm_used=used, llm_fallback=fell,
                    llm_fallback_reason=reason))
        else:
            for rr in getattr(result, "role_results", []) or []:
                used, fell, reason = llm_flags.get(rr.role_name,
                                                   (False, False, ""))
                timings.append(RoleTiming(
                    role_name=rr.role_name,
                    status=getattr(rr.status, "value", str(rr.status)),
                    llm_used=used, llm_fallback=fell,
                    llm_fallback_reason=reason))
        rec.role_timings = timings

        # --- output ---
        artifact = getattr(result, "artifact", None)
        gap_reports = list(getattr(result, "gap_reports", []) or [])
        rec.output = {
            "artifact": artifact,
            "gap_reports": gap_reports,
            "has_gaps": len(gap_reports) > 0,
            # P0-G′ fix: propagate schema validity so the grading layer can
            # exclude schema-invalid-but-ok=True runs from clean observations
            # (mirrors the canonical path, mandate_canonical.py). Without this
            # the primary comparative arm saw schema_valid=None and counted
            # schema-invalid runs as clean.
            "schema_valid": getattr(result, "schema_valid", None),
        }
        rec.output_type = (OUTPUT_MANDATE_AS_CODE if artifact
                           else OUTPUT_GAP_REPORT)
        rec.ok = bool(getattr(result, "ok", False))
        rec.errors = list(getattr(result, "errors", []) or [])

        if self.mode == "deterministic":
            rec.model_versions = {"mode": "deterministic"}
            rec.api_cost_usd = 0.0
        else:
            rec.model_versions = dict(self.ollama_config.get("llm_role_models",
                                                             {}))
        return rec
