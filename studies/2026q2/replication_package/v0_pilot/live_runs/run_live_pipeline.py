#!/usr/bin/env python3
"""
Live Pipeline Runner — executes MANDATE pipeline on constructed scenarios
and captures full output artifacts for Section 12.2 evidence.
"""
import json
import sys
import time
import traceback
from pathlib import Path

# Add AEGIS to path
AEGIS_ROOT = Path("/sessions/intelligent-ecstatic-cerf/mnt/Desktop/AEGIS")
sys.path.insert(0, str(AEGIS_ROOT / "src"))

from mandate.pipeline import Pipeline, PipelineConfig
from mandate.models import MissionInput

SCENARIOS_DIR = Path(__file__).parent / "scenarios"
OUTPUTS_DIR = Path(__file__).parent / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

def run_scenario(scenario_file: Path) -> dict:
    """Run a single scenario through the pipeline and return results."""
    with open(scenario_file) as f:
        scenario_data = json.load(f)

    scenario_name = scenario_file.stem
    metadata = scenario_data.get("metadata", {})
    print(f"\n{'='*70}")
    print(f"SCENARIO: {scenario_name}")
    print(f"  Intent: {scenario_data['intent'][:80]}...")
    print(f"  Paper ref: {metadata.get('paper_reference', 'N/A')}")
    print(f"  Claim: {metadata.get('claim', 'N/A')}")
    print(f"  Expected: {metadata.get('expected_outcome', 'N/A')}")
    print(f"{'='*70}")

    # Create pipeline with gap emission enabled
    config = PipelineConfig(strict=False, emit_gaps=True)
    pipeline = Pipeline(config)

    # Create MissionInput from scenario
    mission = MissionInput.from_dict(scenario_data)

    # Run pipeline and time it
    t0 = time.perf_counter()
    try:
        result = pipeline.run(mission)
        elapsed_ms = (time.perf_counter() - t0) * 1000
    except Exception as e:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        print(f"  EXCEPTION: {e}")
        traceback.print_exc()
        return {
            "scenario": scenario_name,
            "status": "EXCEPTION",
            "error": str(e),
            "elapsed_ms": round(elapsed_ms, 1),
            "metadata": metadata,
        }

    # Collect results
    summary = result.summary()
    print(f"\n  Pipeline result: ok={result.ok}")
    print(f"  Roles executed: {summary.get('roles_executed', 'N/A')}")
    print(f"  Roles passed: {summary.get('roles_passed', 'N/A')}")
    print(f"  Gaps detected: {summary.get('gaps', 'N/A')}")
    print(f"  Elapsed: {elapsed_ms:.1f}ms")

    # Extract key evidence
    evidence = {
        "scenario": scenario_name,
        "mission_id": scenario_data["mission_id"],
        "status": "SUCCESS" if result.ok and not result.has_gaps else ("GAP_REPORT" if result.has_gaps else "FAILURE"),
        "ok": result.ok,
        "has_gaps": result.has_gaps,
        "elapsed_ms": round(elapsed_ms, 1),
        "summary": summary,
        "metadata": metadata,
    }

    # If we have an artifact, extract key fields
    if result.artifact:
        art = result.artifact
        evidence["artifact"] = {
            "has_anchor": bool(art.get("anchor")),
            "anchor_hash": art.get("anchor", {}).get("anchor_hash", ""),
            "num_coas": len(art.get("courses_of_action", [])),
            "has_trace": bool(art.get("trace", {}).get("entries")),
            "trace_entries": len(art.get("trace", {}).get("entries", [])),
            "has_registry_reference": bool(art.get("registry_reference")),
            "has_risk_profile": bool(art.get("risk_profile")),
            "recommendation": art.get("recommendation", {}).get("primary_coa", ""),
        }

        # COA details
        coas = art.get("courses_of_action", [])
        evidence["coas"] = []
        for i, coa in enumerate(coas):
            coa_info = {
                "coa_id": coa.get("coa_id", f"COA-{i+1}"),
                "num_tasks": len(coa.get("task_dag", {}).get("nodes", [])),
                "num_edges": len(coa.get("task_dag", {}).get("edges", [])),
                "has_risk_assessment": bool(coa.get("risk_assessment")),
                "risk_score": coa.get("risk_assessment", {}).get("score", "N/A"),
            }
            if coa.get("risk_assessment"):
                coa_info["confidence_min"] = coa["risk_assessment"].get("confidence_min", "N/A")
            evidence["coas"].append(coa_info)
            print(f"  COA-{i+1}: {coa_info['num_tasks']} tasks, {coa_info['num_edges']} edges, risk={coa_info['risk_score']}")

        # Trace chain details
        trace = art.get("trace", {})
        if trace.get("entries"):
            evidence["trace_chain"] = {
                "chain_hash": trace.get("chain_hash", ""),
                "num_entries": len(trace["entries"]),
                "roles": [e.get("role", "unknown") for e in trace["entries"]],
                "all_hashed": all(bool(e.get("hash")) for e in trace["entries"]),
            }
            print(f"  Trace: {len(trace['entries'])} entries, roles={evidence['trace_chain']['roles']}")

    # If we have gap reports, extract them
    if result.gap_reports:
        evidence["gap_reports"] = []
        for gap in result.gap_reports:
            gap_info = {
                "gap_type": gap.get("gap_type", "UNKNOWN"),
                "detected_by": gap.get("detected_by", "UNKNOWN"),
                "severity": gap.get("severity", "UNKNOWN"),
                "blocking": gap.get("blocking", False),
                "field_or_task": gap.get("field_or_task", ""),
                "reason": gap.get("reason", "")[:200],
            }
            if gap.get("readiness_score"):
                gap_info["readiness_score"] = gap["readiness_score"]
            evidence["gap_reports"].append(gap_info)
            print(f"  GAP: {gap_info['gap_type']} [{gap_info['severity']}] "
                  f"by {gap_info['detected_by']} — {gap_info['reason'][:60]}")

    # Role-level detail
    evidence["role_results"] = []
    for rr in result.role_results:
        evidence["role_results"].append({
            "role": rr.role_name,
            "ok": rr.ok,
            "elapsed_ms": round(rr.elapsed_ms, 1) if hasattr(rr, 'elapsed_ms') else None,
        })

    # Save individual output
    output_file = OUTPUTS_DIR / f"{scenario_name}_result.json"
    with open(output_file, "w") as f:
        json.dump(evidence, f, indent=2, default=str)
    print(f"  Saved: {output_file.name}")

    # Also save full artifact if available
    if result.artifact:
        artifact_file = OUTPUTS_DIR / f"{scenario_name}_artifact.json"
        with open(artifact_file, "w") as f:
            json.dump(result.artifact, f, indent=2, default=str)
        print(f"  Artifact: {artifact_file.name}")

    return evidence


def main():
    print("=" * 70)
    print("MANDATE LIVE PIPELINE EXECUTION")
    print(f"Scenarios: {SCENARIOS_DIR}")
    print(f"Outputs: {OUTPUTS_DIR}")
    print("=" * 70)

    scenario_files = sorted(SCENARIOS_DIR.glob("scenario_*.json"))
    print(f"\nFound {len(scenario_files)} scenarios\n")

    all_results = []
    t_total = time.perf_counter()

    for sf in scenario_files:
        try:
            result = run_scenario(sf)
            all_results.append(result)
        except Exception as e:
            print(f"  FATAL ERROR in {sf.name}: {e}")
            traceback.print_exc()
            all_results.append({
                "scenario": sf.stem,
                "status": "FATAL",
                "error": str(e),
            })

    total_ms = (time.perf_counter() - t_total) * 1000

    # Summary table
    print(f"\n\n{'='*70}")
    print("EXECUTION SUMMARY")
    print(f"{'='*70}")
    print(f"{'Scenario':<45} {'Status':<15} {'COAs':>5} {'Gaps':>5} {'ms':>8}")
    print("-" * 80)

    for r in all_results:
        name = r.get("scenario", "?")[:44]
        status = r.get("status", "?")
        num_coas = r.get("artifact", {}).get("num_coas", 0) if "artifact" in r else 0
        num_gaps = len(r.get("gap_reports", []))
        ms = r.get("elapsed_ms", 0)
        print(f"  {name:<43} {status:<15} {num_coas:>5} {num_gaps:>5} {ms:>8.1f}")

    print(f"\nTotal wall-clock: {total_ms:.1f}ms")
    print(f"Scenarios run: {len(all_results)}")
    print(f"Successes: {sum(1 for r in all_results if r.get('status') == 'SUCCESS')}")
    print(f"Gap reports: {sum(1 for r in all_results if r.get('status') == 'GAP_REPORT')}")
    print(f"Failures: {sum(1 for r in all_results if r.get('status') in ('FAILURE', 'EXCEPTION', 'FATAL'))}")

    # Save combined results
    combined = {
        "run_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_scenarios": len(all_results),
        "total_elapsed_ms": round(total_ms, 1),
        "summary": {
            "success": sum(1 for r in all_results if r.get("status") == "SUCCESS"),
            "gap_report": sum(1 for r in all_results if r.get("status") == "GAP_REPORT"),
            "failure": sum(1 for r in all_results if r.get("status") in ("FAILURE", "EXCEPTION", "FATAL")),
        },
        "results": all_results,
    }

    combined_file = OUTPUTS_DIR / "live_run_combined_results.json"
    with open(combined_file, "w") as f:
        json.dump(combined, f, indent=2, default=str)
    print(f"\nCombined results: {combined_file}")


if __name__ == "__main__":
    main()
