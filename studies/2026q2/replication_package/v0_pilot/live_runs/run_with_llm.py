#!/usr/bin/env python3
"""
LLM-Backed Pipeline Runner — runs MANDATE pipeline with actual LLM agents.

REQUIREMENTS:
  1. Ollama running locally: `ollama serve`
  2. A model pulled: `ollama pull llama3.2` (or qwen2.5, mistral, etc.)
  3. AEGIS virtualenv activated: `source /path/to/AEGIS/.venv/bin/activate`

USAGE:
  # Default (Ollama with llama3.2, all roles):
  python run_with_llm.py

  # Specific model:
  python run_with_llm.py --model qwen2.5:14b

  # Specific scenarios:
  python run_with_llm.py --scenarios scenario_01_ciso_report scenario_07_multi_coa_ir

  # Compare LLM vs deterministic:
  python run_with_llm.py --compare

  # Custom Ollama endpoint:
  python run_with_llm.py --base-url http://gpu-server:11434

This script runs the SAME 8 scenarios from the deterministic evidence run but
with actual LLM agents filling each role. Each role result records:
  - llm_used: True/False (was the LLM invoked?)
  - llm_fallback: True/False (did it fall back to deterministic?)
  - llm_latency_ms: how long the LLM call took
  - llm_tokens_used: input/output token counts

The structural properties (anchor hash, trace chain, gap detection) should be
IDENTICAL between deterministic and LLM runs, because these are computed by
the framework, not the LLM. What changes with LLM:
  - Anchor extraction quality (natural language → minimum/target/constraints)
  - COA content richness (task descriptions, procedure details)
  - Binding rationale quality (why one COA is recommended over another)
"""
import argparse
import json
import sys
import time
import traceback
from pathlib import Path

AEGIS_ROOT = Path("/sessions/intelligent-ecstatic-cerf/mnt/Desktop/AEGIS")
sys.path.insert(0, str(AEGIS_ROOT / "src"))

from mandate.pipeline import Pipeline, PipelineConfig
from mandate.models import MissionInput

try:
    from aegis.llm import LLMConfig, OllamaBackend
    HAS_LLM = True
except ImportError:
    HAS_LLM = False
    print("WARNING: aegis.llm not available. Install AEGIS with LLM support.")

SCENARIOS_DIR = Path(__file__).parent / "scenarios"
OUTPUTS_DIR = Path(__file__).parent / "outputs_llm"


def create_llm_config(args) -> PipelineConfig:
    """Create pipeline config with LLM adapter."""
    adapter = OllamaBackend(
        config=LLMConfig(
            model_path=args.model,
            max_tokens=2048,
            temperature=0.0,  # Deterministic LLM output for reproducibility
            retry_count=2,
            json_mode=True,
        ),
        base_url=args.base_url,
        timeout_s=args.timeout,
    )

    config = PipelineConfig(
        strict=False,
        emit_gaps=True,
        llm_adapter=adapter,
        llm_fallback_enabled=True,
        # All 6 roles use LLM
        llm_roles=["Intake", "Interpreter", "Decomposition", "Procedure", "Binding", "Validation"],
    )
    return config


def run_scenario(scenario_file: Path, config: PipelineConfig) -> dict:
    """Run a single scenario through the LLM-backed pipeline."""
    with open(scenario_file) as f:
        scenario_data = json.load(f)

    scenario_name = scenario_file.stem
    metadata = scenario_data.get("metadata", {})
    print(f"\n{'='*70}")
    print(f"SCENARIO: {scenario_name} (LLM-backed)")
    print(f"  Intent: {scenario_data['intent'][:80]}...")
    print(f"{'='*70}")

    pipeline = Pipeline(config)
    mission = MissionInput.from_dict(scenario_data)

    t0 = time.perf_counter()
    try:
        result = pipeline.run(mission)
        elapsed_ms = (time.perf_counter() - t0) * 1000
    except Exception as e:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        print(f"  EXCEPTION: {e}")
        traceback.print_exc()
        return {"scenario": scenario_name, "status": "EXCEPTION", "error": str(e),
                "elapsed_ms": round(elapsed_ms, 1)}

    summary = result.summary()

    # Collect LLM usage details per role
    llm_details = []
    for rr in result.role_results:
        detail = {
            "role": rr.role_name,
            "ok": rr.ok,
            "llm_used": rr.artifacts.get("llm_used", False),
            "llm_fallback": rr.artifacts.get("llm_fallback", False),
            "llm_fallback_reason": rr.artifacts.get("llm_fallback_reason", ""),
            "llm_latency_ms": rr.artifacts.get("llm_latency_ms"),
            "llm_tokens_used": rr.artifacts.get("llm_tokens_used"),
        }
        llm_details.append(detail)
        status = "LLM" if detail["llm_used"] and not detail["llm_fallback"] else \
                 "FALLBACK" if detail["llm_fallback"] else "DETERMINISTIC"
        latency = f" ({detail['llm_latency_ms']:.0f}ms)" if detail.get("llm_latency_ms") else ""
        print(f"  {rr.role_name:15s} [{status:13s}]{latency}")

    evidence = {
        "scenario": scenario_name,
        "mission_id": scenario_data["mission_id"],
        "status": "SUCCESS" if result.ok and not result.has_gaps else
                  ("GAP_REPORT" if result.has_gaps else "FAILURE"),
        "ok": result.ok,
        "has_gaps": result.has_gaps,
        "elapsed_ms": round(elapsed_ms, 1),
        "summary": summary,
        "llm_details": llm_details,
        "metadata": metadata,
    }

    # Artifact details
    if result.artifact:
        art = result.artifact
        evidence["artifact"] = {
            "anchor_hash": art.get("anchor", {}).get("anchor_hash", ""),
            "num_coas": len(art.get("courses_of_action", [])),
            "trace_entries": len(art.get("trace", {}).get("entries", [])),
        }

    if result.gap_reports:
        evidence["gap_reports"] = [
            {"gap_type": g.get("gap_type"), "severity": g.get("severity"),
             "detected_by": g.get("detected_by")}
            for g in result.gap_reports
        ]

    return evidence


def compare_with_deterministic(llm_results: list) -> dict:
    """Compare LLM results with deterministic baseline."""
    det_file = Path(__file__).parent / "outputs" / "live_run_combined_results.json"
    if not det_file.exists():
        return {"error": "No deterministic baseline found. Run run_live_pipeline.py first."}

    with open(det_file) as f:
        det_data = json.load(f)

    det_results = {r["scenario"]: r for r in det_data["results"]}
    llm_map = {r["scenario"]: r for r in llm_results}

    comparisons = []
    for scenario in sorted(set(det_results) & set(llm_map)):
        det = det_results[scenario]
        llm = llm_map[scenario]
        comp = {
            "scenario": scenario,
            "status_match": det.get("status") == llm.get("status"),
            "det_status": det.get("status"),
            "llm_status": llm.get("status"),
            "anchor_hash_match": (
                det.get("artifact", {}).get("anchor_hash") ==
                llm.get("artifact", {}).get("anchor_hash")
            ) if "artifact" in det and "artifact" in llm else None,
            "gap_types_match": (
                sorted(g["gap_type"] for g in det.get("gap_reports", [])) ==
                sorted(g["gap_type"] for g in llm.get("gap_reports", []))
            ),
            "det_elapsed_ms": det.get("elapsed_ms"),
            "llm_elapsed_ms": llm.get("elapsed_ms"),
            "llm_roles_used": sum(
                1 for d in llm.get("llm_details", [])
                if d.get("llm_used") and not d.get("llm_fallback")
            ),
        }
        comparisons.append(comp)
        print(f"  {scenario}: status={'MATCH' if comp['status_match'] else 'DIFF'}, "
              f"hash={'MATCH' if comp['anchor_hash_match'] else 'DIFF'}, "
              f"gaps={'MATCH' if comp['gap_types_match'] else 'DIFF'}, "
              f"LLM roles={comp['llm_roles_used']}/6")

    return {"comparisons": comparisons}


def main():
    parser = argparse.ArgumentParser(description="Run MANDATE pipeline with LLM agents")
    parser.add_argument("--model", default="llama3.2",
                        help="Ollama model name (default: llama3.2)")
    parser.add_argument("--base-url", default="http://localhost:11434",
                        help="Ollama API endpoint")
    parser.add_argument("--timeout", type=float, default=300.0,
                        help="LLM request timeout in seconds")
    parser.add_argument("--scenarios", nargs="*",
                        help="Specific scenario names to run (default: all)")
    parser.add_argument("--compare", action="store_true",
                        help="Compare LLM results with deterministic baseline")
    args = parser.parse_args()

    if not HAS_LLM:
        print("ERROR: aegis.llm module not available.")
        sys.exit(1)

    OUTPUTS_DIR.mkdir(exist_ok=True)

    print("=" * 70)
    print("MANDATE LLM-BACKED PIPELINE EXECUTION")
    print(f"Model: {args.model}")
    print(f"Endpoint: {args.base_url}")
    print(f"Timeout: {args.timeout}s")
    print("=" * 70)

    config = create_llm_config(args)

    # Select scenarios
    if args.scenarios:
        scenario_files = [SCENARIOS_DIR / f"{s}.json" for s in args.scenarios]
    else:
        scenario_files = sorted(SCENARIOS_DIR.glob("scenario_*.json"))

    all_results = []
    t_total = time.perf_counter()

    for sf in scenario_files:
        if not sf.exists():
            print(f"  WARNING: {sf.name} not found, skipping")
            continue
        result = run_scenario(sf, config)
        all_results.append(result)

    total_ms = (time.perf_counter() - t_total) * 1000

    # Summary
    print(f"\n{'='*70}")
    print("EXECUTION SUMMARY (LLM-backed)")
    print(f"{'='*70}")
    for r in all_results:
        llm_count = sum(1 for d in r.get("llm_details", [])
                        if d.get("llm_used") and not d.get("llm_fallback"))
        fb_count = sum(1 for d in r.get("llm_details", []) if d.get("llm_fallback"))
        print(f"  {r['scenario']:<45} {r.get('status', '?'):<12} "
              f"LLM={llm_count}/6 FB={fb_count}")

    print(f"\nTotal: {total_ms:.0f}ms")

    # Save
    combined = {
        "run_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": args.model,
        "base_url": args.base_url,
        "results": all_results,
    }
    out_file = OUTPUTS_DIR / "llm_run_combined_results.json"
    with open(out_file, "w") as f:
        json.dump(combined, f, indent=2, default=str)
    print(f"Saved: {out_file}")

    # Comparison
    if args.compare:
        print(f"\n{'='*70}")
        print("DETERMINISTIC vs LLM COMPARISON")
        print(f"{'='*70}")
        comp = compare_with_deterministic(all_results)
        comp_file = OUTPUTS_DIR / "deterministic_vs_llm_comparison.json"
        with open(comp_file, "w") as f:
            json.dump(comp, f, indent=2, default=str)
        print(f"Saved: {comp_file}")


if __name__ == "__main__":
    main()
