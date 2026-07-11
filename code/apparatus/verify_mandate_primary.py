"""
Workstream A1: MANDATE-primary verification.

Confirms that MANDATE-primary, the fine-tuned six-role Ollama configuration,
genuinely runs the fine-tuned models and does not silently fall back to the
deterministic rule-based path. The execution plan flags this as the single
most important thing to establish before MANDATE-primary can be pinned: a run
that fell back is not an observation of MANDATE-primary, and if it went
unnoticed it would quietly corrupt the headline hypotheses H1-H5.

What this does:
  1. Loads AEGIS's canonical Ollama config (configs/llm_defaults.json).
  2. Runs MANDATE in Ollama mode over the six calibration tasks.
  3. Runs MANDATE in deterministic mode over the same tasks, for contrast.
  4. Checks every Ollama run: ok, six roles present, every role used the LLM
     (llm_used), and no role fell back (llm_fallback).
  5. Writes an A1 verification report (Markdown + JSON) with a PASS/FAIL
     verdict, and exits non-zero on FAIL.

It must run on the eval host, where Ollama and the six mandate-* models live.
It is not study-data generation: it runs on the calibration tasks, which are
a positive control, and it is gated by nothing.

Usage:
  python3 apparatus/verify_mandate_primary.py --aegis /path/to/AEGIS
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_HERE)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from apparatus.harness.ledger import RunLedger
from apparatus.harness.runner import load_tasks, run_matrix
from apparatus.harness.records import utc_now_iso
from apparatus.systems.mandate_primary import (MandatePrimarySystem,
                                               load_ollama_config)

EXPECTED_ROLES = ["Intake", "Interpreter", "Decomposition",
                  "Procedure", "Binding", "Validation"]


def git_ref(aegis_path: str) -> str:
    try:
        out = subprocess.check_output(
            ["git", "-C", aegis_path, "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL)
        ref = out.decode().strip()
        try:
            tag = subprocess.check_output(
                ["git", "-C", aegis_path, "describe", "--tags", "--exact-match"],
                stderr=subprocess.DEVNULL).decode().strip()
            return "%s (tag %s)" % (ref, tag)
        except Exception:
            return "%s (no tag)" % ref
    except Exception:
        return "UNKNOWN"


def check_run(rec) -> dict:
    """Evaluate one Ollama-mode RunRecord against the A1 criteria.

    A role genuinely ran the fine-tuned model iff llm_used is True AND
    llm_fallback is False. AEGIS's execute_with_fallback sets used_llm=True
    even when it falls back (it records that the LLM path was attempted), so
    the absence of fallback, not the presence of llm_used, is the real signal.
    """
    roles = {rt.role_name: rt for rt in rec.role_timings}
    missing = [r for r in EXPECTED_ROLES if r not in roles]
    fell = [r for r in EXPECTED_ROLES if r in roles and roles[r].llm_fallback]
    genuine = [r for r in EXPECTED_ROLES
               if r in roles and roles[r].llm_used
               and not roles[r].llm_fallback]
    ok = (rec.ok and not missing
          and len(genuine) == len(EXPECTED_ROLES))
    return {
        "run_id": rec.run_id, "task_id": rec.task_id,
        "pipeline_ok": rec.ok, "missing_roles": missing,
        "roles_on_finetuned": genuine, "roles_fell_back": fell,
        "n_finetuned": len(genuine), "passes": ok, "errors": rec.errors,
    }


def anchor_of(rec) -> str:
    """Stable string view of a record's anchor, for the ollama-vs-deterministic
    contrast. Returns '' if no anchor is present."""
    out = rec.output or {}
    art = (out.get("artifact") or {}) if isinstance(out, dict) else {}
    anchor = art.get("anchor")
    if anchor is None:
        return ""
    return json.dumps(anchor, sort_keys=True, default=str)


def main() -> int:
    ap = argparse.ArgumentParser(description="Workstream A1 verification.")
    ap.add_argument("--aegis", required=True, help="AEGIS repository root.")
    ap.add_argument("--tasks",
                    default=os.path.join(_PROJECT_ROOT, "02_calibration",
                                         "tasks"),
                    help="Directory of task JSON files (calibration tasks).")
    ap.add_argument("--runs", type=int, default=1, help="Runs per task.")
    ap.add_argument("--out-dir",
                    default=os.path.join(_PROJECT_ROOT, "00_preregistration",
                                         "a1_verification"))
    args = ap.parse_args()

    aegis_src = os.path.join(args.aegis, "src")
    if not os.path.isdir(os.path.join(aegis_src, "mandate")):
        print("[FAIL] AEGIS not found at %s" % args.aegis)
        return 2
    os.makedirs(args.out_dir, exist_ok=True)
    ref = git_ref(args.aegis)
    tasks = load_tasks(args.tasks)
    print("A1 verification: %d tasks, %d run(s) each, AEGIS %s"
          % (len(tasks), args.runs, ref))

    # --- load the authoritative Ollama config ---
    try:
        ollama_cfg = load_ollama_config(args.aegis)
    except Exception as e:
        print("[FAIL] could not load Ollama config: %r" % e)
        return 2
    print("Ollama config keys: %s" % ", ".join(sorted(ollama_cfg)))

    # --- run Ollama mode ---
    print("\n[1/2] MANDATE-primary, Ollama mode")
    ollama_sys = MandatePrimarySystem(aegis_src_path=aegis_src, mode="ollama",
                                      ollama_config=ollama_cfg, code_ref=ref)
    ollama_recs = run_matrix(
        ollama_sys, tasks, n_runs=args.runs,
        ledger=RunLedger(os.path.join(args.out_dir, "ollama_ledger.jsonl")),
        output_dir=os.path.join(args.out_dir, "ollama"))

    # --- run deterministic mode for contrast ---
    print("\n[2/2] MANDATE, deterministic mode (contrast)")
    det_sys = MandatePrimarySystem(aegis_src_path=aegis_src,
                                   mode="deterministic", code_ref=ref)
    det_recs = run_matrix(
        det_sys, tasks, n_runs=1,
        ledger=RunLedger(os.path.join(args.out_dir,
                                      "deterministic_ledger.jsonl")),
        output_dir=os.path.join(args.out_dir, "deterministic"),
        verbose=False)
    det_anchor = {r.task_id: anchor_of(r) for r in det_recs}

    # --- evaluate ---
    checks = [check_run(r) for r in ollama_recs]
    n_pass = sum(c["passes"] for c in checks)
    verdict = "PASS" if (checks and n_pass == len(checks)) else "FAIL"

    # diagnosis if not all passed
    diagnosis = ""
    if verdict == "FAIL":
        all_fell = all(len(c["roles_fell_back"]) == len(EXPECTED_ROLES)
                       for c in checks) if checks else False
        any_fell = any(c["roles_fell_back"] for c in checks)
        if not checks:
            diagnosis = "No runs were produced."
        elif all_fell:
            diagnosis = ("Every role fell back on every task. Ollama is most "
                         "likely unreachable, or the six mandate-* models are "
                         "not registered or not responding. Start 'ollama "
                         "serve' and run setup/ollama_models.sh.")
        elif any_fell:
            diagnosis = ("Partial fallback: some roles used the fine-tuned "
                         "models and some fell back to the deterministic "
                         "path. Investigate the affected roles below before "
                         "pinning MANDATE-primary.")
        else:
            diagnosis = ("Some runs did not satisfy the A1 criteria for a "
                         "reason other than fallback. See the per-run detail.")

    # output contrast (supporting evidence, not a gate)
    differs = 0
    contrast = []
    for r in ollama_recs:
        o = anchor_of(r)
        d = det_anchor.get(r.task_id, "")
        same = (o == d) and o != ""
        if not same and o != "":
            differs += 1
        contrast.append({"task_id": r.task_id, "run_id": r.run_id,
                         "anchor_differs_from_deterministic": (not same)})

    report = {
        "generated": utc_now_iso(),
        "aegis_ref": ref,
        "ollama_config_source": "configs/llm_defaults.json",
        "tasks": len(tasks), "runs_per_task": args.runs,
        "ollama_runs": len(ollama_recs),
        "verdict": verdict,
        "runs_passing": n_pass,
        "diagnosis": diagnosis,
        "per_run": checks,
        "output_contrast": {
            "anchor_differs_count": differs,
            "note": ("A differing anchor is supporting evidence that the "
                     "fine-tuned models do real work. It is not a pass/fail "
                     "criterion; the llm_used / llm_fallback flags are."),
            "detail": contrast,
        },
    }
    json_path = os.path.join(args.out_dir, "A1_verification_report.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    _write_markdown(report, os.path.join(args.out_dir,
                                         "A1_verification_report.md"))

    # --- console summary ---
    print("\n=== A1 verdict: %s (%d/%d runs pass) ==="
          % (verdict, n_pass, len(checks)))
    if diagnosis:
        print(diagnosis)
    print("Report: %s" % json_path)
    if verdict == "PASS":
        print("Next: run setup/capture_provenance.sh to record the model "
              "SHA-256 hashes and pin MANDATE-primary (TO_FILL rows D3-D6).")
    return 0 if verdict == "PASS" else 1


def _write_markdown(report: dict, path: str) -> None:
    L = []
    L.append("# Workstream A1: MANDATE-primary Verification Report")
    L.append("")
    L.append("**Generated:** %s  " % report["generated"])
    L.append("**AEGIS ref:** %s  " % report["aegis_ref"])
    L.append("**Ollama config:** %s  " % report["ollama_config_source"])
    L.append("**Verdict:** %s (%d of %d runs pass)"
             % (report["verdict"], report["runs_passing"],
                report["ollama_runs"]))
    L.append("")
    if report["diagnosis"]:
        L.append("**Diagnosis.** %s" % report["diagnosis"])
        L.append("")
    L.append("## Per-run detail")
    L.append("")
    L.append("| Run | Pipeline ok | Roles on fine-tuned LLM | Roles fell back | Pass |")
    L.append("|-----|-------------|-------------------------|-----------------|------|")
    for c in report["per_run"]:
        L.append("| %s | %s | %d/6 | %s | %s |" % (
            c["run_id"], c["pipeline_ok"], c["n_finetuned"],
            ", ".join(c["roles_fell_back"]) or "none",
            "yes" if c["passes"] else "NO"))
    L.append("")
    oc = report["output_contrast"]
    L.append("## Output contrast (supporting evidence)")
    L.append("")
    L.append("%d of %d Ollama runs produced an anchor that differs from the "
             "deterministic anchor. %s" % (oc["anchor_differs_count"],
                                           report["ollama_runs"], oc["note"]))
    L.append("")
    L.append("## What A1 establishes")
    L.append("")
    L.append("A PASS verdict means MANDATE-primary, as configured, ran the "
             "fine-tuned models on all six roles with no silent fallback to "
             "the deterministic path, on the calibration tasks. It does not "
             "by itself prove the registered models are the intended fused "
             "fine-tunes; pair this with the model SHA-256 hashes from "
             "`setup/capture_provenance.sh` (TO_FILL_TRACKER rows D3-D6).")
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
