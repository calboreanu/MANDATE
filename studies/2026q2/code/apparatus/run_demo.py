"""
Demonstration run for the MANDATE evaluation harness (Workstream B1).

Runs two systems over the six calibration tasks, with no API calls and no
Ollama:

  * ReferenceSystem            harness self-test
  * MandatePrimarySystem       the real AEGIS MANDATE pipeline, in
    (deterministic mode)       deterministic mode

IMPORTANT: deterministic mode is NOT MANDATE-primary as the protocol defines
it. MANDATE-primary is the fine-tuned six-role Ollama configuration, and
verifying it runs with no silent fallback is Workstream A1 on the eval host.
This demo proves the harness wiring is correct and that RunRecords, the
ledger, output capture, and the per-role llm_used flags all populate from a
real pipeline run.

Usage:
  python3 apparatus/run_demo.py --aegis /path/to/AEGIS

Output goes to apparatus/_demo_output/ and is not part of the study record.
"""
from __future__ import annotations

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_HERE)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from apparatus.harness.ledger import RunLedger
from apparatus.harness.runner import load_tasks, run_matrix
from apparatus.systems.reference import ReferenceSystem
from apparatus.systems.mandate_primary import MandatePrimarySystem


def main() -> int:
    ap = argparse.ArgumentParser(description="Harness B1 demonstration run.")
    ap.add_argument("--aegis", default="",
                    help="Path to the AEGIS repository root (contains src/). "
                         "If omitted, only the ReferenceSystem runs.")
    ap.add_argument("--tasks",
                    default=os.path.join(_PROJECT_ROOT,
                                         "02_calibration", "tasks"),
                    help="Directory of task JSON files.")
    ap.add_argument("--runs", type=int, default=1, help="Runs per task.")
    args = ap.parse_args()

    demo_root = os.path.join(_HERE, "_demo_output")
    tasks = load_tasks(args.tasks)
    print(f"Loaded {len(tasks)} tasks from {args.tasks}")

    print("\n[1/2] ReferenceSystem")
    ref_ledger = RunLedger(os.path.join(demo_root, "reference_ledger.jsonl"))
    ref_recs = run_matrix(ReferenceSystem(), tasks, n_runs=args.runs,
                          ledger=ref_ledger,
                          output_dir=os.path.join(demo_root, "reference"))

    mand_recs = []
    if args.aegis:
        src = os.path.join(args.aegis, "src")
        print(f"\n[2/2] MandatePrimarySystem (deterministic) via {src}")
        mandate = MandatePrimarySystem(aegis_src_path=src, mode="deterministic",
                                       code_ref="UNPINNED-demo")
        mand_ledger = RunLedger(os.path.join(demo_root,
                                             "mandate_deterministic_ledger.jsonl"))
        mand_recs = run_matrix(mandate, tasks, n_runs=args.runs,
                               ledger=mand_ledger,
                               output_dir=os.path.join(demo_root,
                                                       "mandate_deterministic"))
    else:
        print("\n[2/2] MandatePrimarySystem skipped (no --aegis path given).")

    print("\n--- summary ---")
    print(f"ReferenceSystem:  {len(ref_recs)} runs, "
          f"{sum(r.ok for r in ref_recs)} ok")
    if mand_recs:
        ok = sum(r.ok for r in mand_recs)
        fb = sum(r.any_llm_fallback for r in mand_recs)
        roles = len(mand_recs[0].role_timings) if mand_recs else 0
        print(f"MANDATE (det.):   {len(mand_recs)} runs, {ok} ok, "
              f"{roles} roles captured per run, {fb} runs with llm fallback")
        print("  (deterministic mode: llm_used is False on every role by "
              "design; the fine-tuned Ollama path is verified in A1.)")
    print(f"\nDemo output: {demo_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
