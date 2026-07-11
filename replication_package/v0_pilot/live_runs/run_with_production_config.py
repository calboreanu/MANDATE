#!/usr/bin/env python3
"""
Production Config Pipeline Run — uses the real llm_defaults.json config.

When Ollama is running with mandate-* models loaded, each role uses its
dedicated fine-tuned model. When Ollama is unavailable, each role falls
back to deterministic execution — proving the fallback mechanism works.

Either way, the structural properties (anchor hash, trace chain, gap
detection) are identical. This script captures per-role LLM metadata
to show exactly what happened.

USAGE:
  # From AEGIS root with venv activated:
  python /path/to/run_with_production_config.py

  # On Mac mini with Ollama running:
  python /path/to/run_with_production_config.py
  # → Each role uses its fine-tuned model (mandate-intake, etc.)
"""
import json
import os
import sys
import time
from pathlib import Path

# Resolve AEGIS root: check env, then look relative to script location
_script_dir = Path(__file__).resolve().parent
AEGIS_ROOT = Path(os.environ.get("AEGIS_ROOT", ""))
if not AEGIS_ROOT.is_dir():
    # Try relative to script: mandate/live_runs/ -> ../../AEGIS
    AEGIS_ROOT = (_script_dir / ".." / ".." / "AEGIS").resolve()
if not AEGIS_ROOT.is_dir():
    # Fallback: sandbox path
    AEGIS_ROOT = Path("/sessions/intelligent-ecstatic-cerf/mnt/Desktop/AEGIS")
sys.path.insert(0, str(AEGIS_ROOT / "src"))

from mandate.models import MissionInput, PipelineConfig
from mandate.pipeline import Pipeline

SCENARIOS_DIR = Path(__file__).parent / "scenarios"
OUTPUTS_DIR = Path(__file__).parent / "outputs_production_config"
OUTPUTS_DIR.mkdir(exist_ok=True)

# Load production LLM config
with open(AEGIS_ROOT / "config" / "llm_defaults.json") as f:
    LLM_CFG = json.load(f)


def build_production_config() -> PipelineConfig:
    """Build pipeline config from production llm_defaults.json."""
    return PipelineConfig(
        strict=False,
        emit_gaps=True,
        llm_backend=LLM_CFG["llm_backend"],
        llm_base_url=LLM_CFG["llm_base_url"],
        llm_fallback_enabled=LLM_CFG.get("llm_fallback_enabled", True),
        llm_default_model=LLM_CFG.get("llm_default_model", ""),
        llm_role_models=LLM_CFG.get("llm_role_models"),
        llm_role_temperatures=LLM_CFG.get("llm_role_temperatures"),
        llm_role_max_tokens=LLM_CFG.get("llm_role_max_tokens"),
        llm_role_retries=LLM_CFG.get("llm_role_retries"),
    )


def run_scenario(scenario_file: Path, config: PipelineConfig) -> dict:
    """Run scenario with production config, capture LLM metadata."""
    with open(scenario_file) as f:
        data = json.load(f)

    name = scenario_file.stem
    mission = MissionInput.from_dict(data)
    pipe = Pipeline(config)

    t0 = time.perf_counter()
    result = pipe.run(mission)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    # Per-role LLM detail
    role_details = []
    for rr in result.role_results:
        detail = {
            "role": rr.role_name,
            "ok": rr.ok,
            "llm_used": rr.artifacts.get("llm_used", False),
            "llm_fallback": rr.artifacts.get("llm_fallback", False),
            "llm_fallback_reason": rr.artifacts.get("llm_fallback_reason", ""),
            "llm_model": LLM_CFG.get("llm_role_models", {}).get(rr.role_name, "default"),
            "llm_temperature": LLM_CFG.get("llm_role_temperatures", {}).get(rr.role_name, 0.0),
            "llm_max_tokens": LLM_CFG.get("llm_role_max_tokens", {}).get(rr.role_name, 2048),
            "llm_retries": LLM_CFG.get("llm_role_retries", {}).get(rr.role_name, 2),
        }
        # If LLM succeeded (no fallback), capture token usage
        if detail["llm_used"] and not detail["llm_fallback"]:
            detail["llm_tokens_used"] = rr.artifacts.get("llm_tokens_used")
            detail["llm_latency_ms"] = rr.artifacts.get("llm_latency_ms")
            detail["llm_prompt_source"] = rr.artifacts.get("llm_prompt_source", "")
        role_details.append(detail)

    # Count LLM vs fallback
    llm_count = sum(1 for d in role_details if d["llm_used"] and not d["llm_fallback"])
    fb_count = sum(1 for d in role_details if d["llm_fallback"])
    det_count = sum(1 for d in role_details if not d["llm_used"])

    evidence = {
        "scenario": name,
        "mission_id": data["mission_id"],
        "status": "SUCCESS" if result.ok and not result.has_gaps else
                  ("GAP_REPORT" if result.has_gaps else "FAILURE"),
        "ok": result.ok,
        "has_gaps": result.has_gaps,
        "elapsed_ms": round(elapsed_ms, 1),
        "llm_summary": {
            "llm_succeeded": llm_count,
            "llm_fell_back": fb_count,
            "deterministic_only": det_count,
            "backend": LLM_CFG["llm_backend"],
            "base_url": LLM_CFG["llm_base_url"],
        },
        "role_details": role_details,
        "summary": result.summary(),
    }

    # Artifact details
    if result.artifact:
        art = result.artifact
        evidence["artifact"] = {
            "anchor_hash": art.get("anchor", {}).get("anchor_hash", ""),
            "num_coas": len(art.get("courses_of_action", [])),
            "trace_entries": len(art.get("trace", {}).get("entries", [])),
            "has_recommendation": bool(art.get("recommendation")),
        }

    if result.gap_reports:
        evidence["gap_reports"] = [
            {"gap_type": g.get("gap_type"), "severity": g.get("severity")}
            for g in result.gap_reports
        ]

    return evidence


def compare_with_deterministic(prod_results: list) -> dict:
    """Compare production config results with pure deterministic baseline."""
    det_file = Path(__file__).parent / "outputs" / "live_run_combined_results.json"
    if not det_file.exists():
        return {"error": "No deterministic baseline found"}

    with open(det_file) as f:
        det_data = json.load(f)

    det_map = {r["scenario"]: r for r in det_data["results"]}
    comparisons = []

    for prod in prod_results:
        name = prod["scenario"]
        det = det_map.get(name, {})
        if not det:
            continue

        # Compare structural properties
        det_hash = ""
        prod_hash = ""
        if "artifact" in det and det["artifact"]:
            det_hash = det["artifact"].get("anchor_hash", "")
        if "artifact" in prod and prod["artifact"]:
            prod_hash = prod["artifact"].get("anchor_hash", "")

        det_gaps = sorted(g["gap_type"] for g in det.get("gap_reports", []))
        prod_gaps = sorted(g["gap_type"] for g in prod.get("gap_reports", []))

        comp = {
            "scenario": name,
            "status_match": det.get("status") == prod.get("status"),
            "anchor_hash_match": (det_hash == prod_hash) if det_hash and prod_hash else None,
            "gap_types_match": det_gaps == prod_gaps,
            "coa_count_match": (
                det.get("artifact", {}).get("num_coas") ==
                prod.get("artifact", {}).get("num_coas")
            ) if "artifact" in det and "artifact" in prod else None,
            "trace_count_match": (
                det.get("artifact", {}).get("trace_entries") ==
                prod.get("artifact", {}).get("trace_entries")
            ) if "artifact" in det and "artifact" in prod else None,
            "llm_roles_succeeded": prod["llm_summary"]["llm_succeeded"],
            "llm_roles_fell_back": prod["llm_summary"]["llm_fell_back"],
        }
        comparisons.append(comp)

    all_match = all(
        c["status_match"] and
        (c["anchor_hash_match"] is None or c["anchor_hash_match"]) and
        c["gap_types_match"]
        for c in comparisons
    )

    return {
        "all_structural_properties_match": all_match,
        "comparisons": comparisons,
    }


def main():
    print("=" * 70)
    print("MANDATE PIPELINE — PRODUCTION LLM CONFIG")
    print(f"Backend: {LLM_CFG['llm_backend']}")
    print(f"Base URL: {LLM_CFG['llm_base_url']}")
    print(f"Fallback: {LLM_CFG.get('llm_fallback_enabled', True)}")
    print(f"Role models: {json.dumps(LLM_CFG.get('llm_role_models', {}), indent=2)}")
    print("=" * 70)

    scenario_files = sorted(SCENARIOS_DIR.glob("scenario_*.json"))
    all_results = []
    t_total = time.perf_counter()

    for sf in scenario_files:
        result = run_scenario(sf, build_production_config())
        all_results.append(result)

        llm_s = result["llm_summary"]
        print(f"\n  {result['scenario']}: {result['status']}")
        print(f"    LLM: {llm_s['llm_succeeded']}/6 succeeded, "
              f"{llm_s['llm_fell_back']}/6 fell back, "
              f"{llm_s['deterministic_only']}/6 deterministic-only")
        for rd in result["role_details"]:
            mode = ("LLM" if rd["llm_used"] and not rd["llm_fallback"] else
                    "FALLBACK" if rd["llm_fallback"] else "DETERMINISTIC")
            model = rd["llm_model"]
            reason = f" — {rd['llm_fallback_reason'][:50]}" if rd.get("llm_fallback_reason") else ""
            print(f"      {rd['role']:15s} [{mode:13s}] model={model}{reason}")

    total_ms = (time.perf_counter() - t_total) * 1000

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    total_llm = sum(r["llm_summary"]["llm_succeeded"] for r in all_results)
    total_fb = sum(r["llm_summary"]["llm_fell_back"] for r in all_results)
    total_det = sum(r["llm_summary"]["deterministic_only"] for r in all_results)
    total_roles = len(all_results) * 6

    print(f"Scenarios: {len(all_results)}")
    print(f"Total roles: {total_roles}")
    print(f"  LLM succeeded: {total_llm}/{total_roles}")
    print(f"  LLM fell back: {total_fb}/{total_roles}")
    print(f"  Deterministic: {total_det}/{total_roles}")
    print(f"Total time: {total_ms:.1f}ms")

    # Comparison
    print(f"\n{'='*70}")
    print("STRUCTURAL COMPARISON vs DETERMINISTIC BASELINE")
    print(f"{'='*70}")
    comparison = compare_with_deterministic(all_results)

    if "error" in comparison:
        print(f"  {comparison['error']}")
    else:
        for c in comparison["comparisons"]:
            markers = []
            if c["status_match"]: markers.append("status")
            if c.get("anchor_hash_match"): markers.append("hash")
            if c["gap_types_match"]: markers.append("gaps")
            if c.get("coa_count_match"): markers.append("coas")
            if c.get("trace_count_match"): markers.append("trace")
            print(f"  {c['scenario']}: MATCH on [{', '.join(markers)}] "
                  f"(LLM={c['llm_roles_succeeded']}/6)")

        print(f"\n  All structural properties identical: "
              f"{'YES' if comparison['all_structural_properties_match'] else 'NO'}")

    # Save
    combined = {
        "run_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config": LLM_CFG,
        "environment": {
            "ollama_reachable": total_llm > 0,
            "total_llm_succeeded": total_llm,
            "total_fallbacks": total_fb,
        },
        "results": all_results,
        "comparison": comparison,
    }
    out_file = OUTPUTS_DIR / "production_config_results.json"
    with open(out_file, "w") as f:
        json.dump(combined, f, indent=2, default=str)
    print(f"\nSaved: {out_file}")


if __name__ == "__main__":
    main()
