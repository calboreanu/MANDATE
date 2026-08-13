from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from .hashing import compute_anchor_hash, compute_trace_entry_hash
from .validator import load_json, validate_artifact
from .constraints import parse_constraint, validate_constraint, ConstraintError
from .models import MissionInput, PipelineConfig
from .pipeline import Pipeline
from .translators.rego import translate_to_rego, TranslationError
from .translators.cedar import translate_to_cedar


def cmd_validate(args: argparse.Namespace) -> int:
    artifact_type, issues = validate_artifact(args.path)
    print(f"artifact_type: {artifact_type}")
    if not issues:
        print("OK: no issues found.")
        return 0

    print(f"Found {len(issues)} issue(s):")
    for i, iss in enumerate(issues, 1):
        loc = f" [{iss.path}]" if iss.path else ""
        print(f"{i}. ({iss.kind}){loc} {iss.message}")
    return 2


def cmd_hash_anchor(args: argparse.Namespace) -> int:
    obj = load_json(args.path)
    anchor = obj.get("anchor")
    if not isinstance(anchor, dict):
        print("ERROR: no 'anchor' object found")
        return 2
    h = compute_anchor_hash(anchor)
    print(h)
    return 0


def cmd_hash_trace(args: argparse.Namespace) -> int:
    entry = load_json(args.path)
    if not isinstance(entry, dict):
        print("ERROR: trace entry must be a JSON object")
        return 2
    h = compute_trace_entry_hash(entry)
    print(h)
    return 0


def cmd_check_constraint(args: argparse.Namespace) -> int:
    """Validate a constraint string against the grammar."""
    constraint = args.constraint
    try:
        ast = parse_constraint(constraint)
        print(f"✓ Valid constraint")
        print(f"  Parsed: {ast}")
        return 0
    except ConstraintError as e:
        print(f"✗ Invalid constraint: {e}")
        return 2


def cmd_validate_constraints(args: argparse.Namespace) -> int:
    """Validate all constraints in a mandate-as-code artifact."""
    obj = load_json(args.path)
    anchor = obj.get("anchor", {})
    constraints = anchor.get("constraints", [])

    if not constraints:
        print("No constraints found in anchor.")
        return 0

    valid_count = 0
    invalid_count = 0

    for i, c in enumerate(constraints):
        # P1.2 fix: handle non-string constraints gracefully
        if not isinstance(c, str):
            print(f"  ✗ [{i}] <non-string value: {type(c).__name__}>")
            print(f"       Error: Constraint must be a string")
            invalid_count += 1
            continue

        try:
            parse_constraint(c)
            print(f"  ✓ [{i}] {c}")
            valid_count += 1
        except ConstraintError as e:
            print(f"  ✗ [{i}] {c}")
            print(f"       Error: {e}")
            invalid_count += 1

    print(f"\nSummary: {valid_count} valid, {invalid_count} invalid")
    return 2 if invalid_count > 0 else 0


def cmd_pipeline(args: argparse.Namespace) -> int:
    """Run the 1+6 pipeline on a mission input JSON."""
    input_path = Path(args.path)
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        return 2

    # Load mission input
    try:
        raw = json.loads(input_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"ERROR: Cannot parse JSON: {e}")
        return 2
    try:
        mi = MissionInput.from_dict(raw)
    except (KeyError, TypeError) as e:
        print(f"ERROR: Invalid mission input format: {e}")
        return 2

    # Configure pipeline
    config = PipelineConfig(
        strict=not args.lenient,
        verbose=args.verbose,
        version=args.version or "1.0",
        emit_gaps=args.emit_gaps,
    )

    # Run pipeline
    pipe = Pipeline(config)

    if args.output:
        output_path = Path(args.output)
        result = pipe.run_and_save(mi, output_path)
    else:
        result = pipe.run(mi)

    # Print results
    if result.ok:
        print(f"Pipeline SUCCESS: mandate_id={result.artifact.get('mandate_id', 'N/A')}")
        print(f"  Roles executed: {len(result.role_results)}")
        print(f"  COAs generated: {len(result.artifact.get('courses_of_action', []))}")
        print(f"  Constraints: {len(result.artifact.get('anchor', {}).get('constraints', []))}")
        if result.metrics:
            print(f"  Duration: {result.metrics.total_duration_ms:.1f}ms")
        if result.has_gaps:
            print(f"  Gaps detected: {len(result.gap_reports)}")
            for gap in result.gap_reports:
                print(f"    - [{gap['gap_type']}] {gap['reason'][:80]}")
        if args.output:
            print(f"  Output: {args.output}")
            if result.gap_reports:
                gap_dir = Path(args.output).parent / "gaps"
                print(f"  Gap reports: {gap_dir}/")
        if not args.output:
            # Print artifact to stdout
            print(json.dumps(result.artifact, indent=2, ensure_ascii=False))
            if result.gap_reports:
                print("\n--- GAP REPORTS ---")
                for gap in result.gap_reports:
                    print(json.dumps(gap, indent=2, ensure_ascii=False))
        return 0
    else:
        if result.artifact and result.execution_state == "NON_EXECUTABLE_GAPS":
            print(f"Pipeline NON-EXECUTABLE: mandate_id={result.artifact.get('mandate_id', 'N/A')}")
            print(f"  Execution state: {result.execution_state}")
            print(f"  Gaps detected: {len(result.gap_reports)}")
            for gap in result.gap_reports:
                print(f"    - [{gap['gap_type']}] {gap['reason'][:80]}")
            if args.output:
                print(f"  Partial artifact: {args.output}")
                print(f"  Gap reports: {Path(args.output).parent / 'gaps'}/")
            return 3
        print("Pipeline FAILED:")
        for err in result.errors:
            print(f"  - {err}")
        return 2


def cmd_translate(args: argparse.Namespace) -> int:
    """Translate constraints from a mission input or mandate artifact to Rego or Cedar."""
    input_path = Path(args.path)
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        return 2

    try:
        raw = json.loads(input_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"ERROR: Cannot parse JSON: {e}")
        return 2

    # Extract constraints from either a mission input or a mandate artifact
    constraints: list[str] = []
    mission_id = ""

    if "anchor" in raw:
        # Mandate-as-code artifact
        constraints = raw.get("anchor", {}).get("constraints", [])
        mission_id = raw.get("mandate_id", "")
    elif "constraints" in raw:
        # Mission input
        constraints = raw.get("constraints", [])
        mission_id = raw.get("mission_id", "")
    else:
        print("ERROR: No constraints found in input file")
        return 2

    if not constraints:
        print("No constraints to translate.")
        return 0

    fmt = args.format.lower()
    try:
        if fmt == "rego":
            policy = translate_to_rego(
                constraints,
                package_name=args.package or "mandate.policy",
                rule_name=args.rule or "allow",
                mission_id=mission_id,
            )
        elif fmt == "cedar":
            policy = translate_to_cedar(
                constraints,
                namespace=args.namespace or "Mandate",
                mission_id=mission_id,
            )
        else:
            print(f"ERROR: Unsupported format: {fmt} (use 'rego' or 'cedar')")
            return 2
    except ConstraintError as e:
        print(f"ERROR: Invalid constraint syntax: {e}")
        return 2
    except TranslationError as e:
        print(f"ERROR: Translation failed: {e}")
        return 2

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(policy, encoding="utf-8")
        print(f"Policy written to {out}")
    else:
        print(policy)

    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    """Run the evaluation harness on a corpus manifest."""
    from .evaluation import EvaluationHarness

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"ERROR: Manifest file not found: {manifest_path}")
        return 2

    try:
        harness = EvaluationHarness.from_manifest(manifest_path)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"ERROR: Cannot load manifest: {e}")
        return 2

    # Filter by tags if specified
    tags = args.tags.split(",") if args.tags else None
    reps = args.repetitions or 1

    print(f"Running evaluation corpus: {manifest_path}")
    print(f"  Cases: {len(harness.cases)}")
    if tags:
        print(f"  Tag filter: {tags}")
    if reps > 1:
        print(f"  Repetitions: {reps}")
    print()

    report = harness.run_all(tags=tags, repetitions=reps)

    # Print results
    for cr in report.case_results:
        status = "PASS" if cr.passed else "FAIL"
        timing = f" ({cr.duration_ms:.1f}ms)" if cr.duration_ms else ""
        print(f"  [{status}] {cr.case_id}: {cr.name}{timing}")
        if not cr.passed:
            for check in cr.checks:
                if not check.passed:
                    print(f"         FAIL: {check.check_name} — {check.detail}")
            if cr.error:
                print(f"         ERROR: {cr.error}")

    print()
    print(f"Results: {report.cases_passed}/{report.total_cases} passed "
          f"({report.pass_rate:.0%}) in {report.total_duration_ms:.1f}ms")

    if report.benchmark_stats:
        stats = report.benchmark_stats
        print(f"\nBenchmark stats:")
        print(f"  Avg pipeline duration: {stats.avg_duration_ms:.1f}ms")
        if stats.min_duration_ms != float("inf"):
            print(f"  Min: {stats.min_duration_ms:.1f}ms  "
                  f"Max: {stats.max_duration_ms:.1f}ms")
        per_role = stats.per_role_avg_ms()
        if per_role:
            print(f"  Per-role averages:")
            for name, avg in per_role.items():
                print(f"    {name}: {avg:.1f}ms")

    # Save report if output specified
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"\nReport saved to {out}")

    return 0 if report.cases_failed == 0 else 1


def cmd_registry(args: argparse.Namespace) -> int:
    """Manage the success registry."""
    from .success_registry import SuccessRegistry

    subcmd = args.registry_cmd

    if subcmd == "stats":
        reg = SuccessRegistry.load(args.registry_path)
        if len(reg) == 0:
            print("Registry is empty.")
            return 0
        stats = reg.stats()
        print(f"Success Registry: {args.registry_path}")
        print(f"  Total records: {stats['total_records']}")
        if stats["domains"]:
            print(f"  Domains:")
            for d, count in sorted(stats["domains"].items()):
                print(f"    {d}: {count}")
        if stats["tool_class_usage"]:
            print(f"  Tool class usage:")
            for tc, count in sorted(stats["tool_class_usage"].items()):
                print(f"    {tc}: {count}")
        return 0

    elif subcmd == "query":
        reg = SuccessRegistry.load(args.registry_path)
        if len(reg) == 0:
            print("Registry is empty — no matches.")
            return 0

        matches = reg.find_similar(
            intent=args.intent or "",
            domain=args.domain or "",
            top_k=args.top_k,
        )
        if not matches:
            print("No similar records found.")
            return 0

        print(f"Top {len(matches)} similar records:")
        for i, m in enumerate(matches, 1):
            print(f"  {i}. [{m.overall_score:.3f}] {m.record.mandate_id}")
            print(f"     Intent: {m.record.intent[:80]}")
            print(f"     Scores: intent={m.intent_score:.3f} "
                  f"constraint={m.constraint_score:.3f} "
                  f"tool_class={m.tool_class_score:.3f}")
        return 0

    elif subcmd == "ingest":
        reg = SuccessRegistry.load(args.registry_path)
        artifact_path = Path(args.artifact)
        if not artifact_path.exists():
            print(f"ERROR: Artifact file not found: {artifact_path}")
            return 2
        try:
            artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"ERROR: Cannot parse artifact JSON: {e}")
            return 2

        rec = reg.record(artifact, domain=args.domain or "")
        reg.save(args.registry_path)
        print(f"Recorded: {rec.record_id} (mandate={rec.mandate_id})")
        print(f"Registry now has {len(reg)} record(s).")
        return 0

    else:
        print(f"Unknown registry subcommand: {subcmd}")
        return 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mandate", description="MANDATE artifact utilities")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="Validate a mandate-as-code or gap-report JSON artifact")
    v.add_argument("path", type=str, help="Path to JSON artifact")
    v.set_defaults(func=cmd_validate)

    ha = sub.add_parser("hash-anchor", help="Compute anchor_hash for a mandate JSON (excluding existing anchor_hash)")
    ha.add_argument("path", type=str, help="Path to mandate-as-code JSON")
    ha.set_defaults(func=cmd_hash_anchor)

    ht = sub.add_parser("hash-trace", help="Compute hash for a trace-entry JSON (excluding existing hash)")
    ht.add_argument("path", type=str, help="Path to trace-entry JSON")
    ht.set_defaults(func=cmd_hash_trace)

    cc = sub.add_parser("check-constraint", help="Check if a constraint string is valid")
    cc.add_argument("constraint", type=str, help="Constraint string to validate")
    cc.set_defaults(func=cmd_check_constraint)

    vc = sub.add_parser("validate-constraints", help="Validate all constraints in a mandate artifact")
    vc.add_argument("path", type=str, help="Path to mandate-as-code JSON")
    vc.set_defaults(func=cmd_validate_constraints)

    # Pipeline command
    pl = sub.add_parser("pipeline", help="Run the 1+6 pipeline on a mission input JSON")
    pl.add_argument("path", type=str, help="Path to mission input JSON")
    pl.add_argument("-o", "--output", type=str, help="Output path for the mandate artifact")
    pl.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    pl.add_argument("--lenient", action="store_true", help="Continue on role failures")
    pl.add_argument("--version", type=str, default="1.0", help="Artifact version string")
    pl.add_argument("--emit-gaps", action="store_true", help="Show gap-report details (gap evidence is always retained)")
    pl.set_defaults(func=cmd_pipeline)

    # Translate command
    tr = sub.add_parser("translate", help="Translate MANDATE constraints to OPA/Rego or Cedar policy")
    tr.add_argument("path", type=str, help="Path to mission input or mandate-as-code JSON")
    tr.add_argument("-f", "--format", type=str, required=True, choices=["rego", "cedar"],
                    help="Target policy language")
    tr.add_argument("-o", "--output", type=str, help="Output path for the policy file")
    tr.add_argument("--package", type=str, default="mandate.policy",
                    help="Rego package name (default: mandate.policy)")
    tr.add_argument("--rule", type=str, default="allow",
                    help="Rego rule name (default: allow)")
    tr.add_argument("--namespace", type=str, default="Mandate",
                    help="Cedar namespace (default: Mandate)")
    tr.set_defaults(func=cmd_translate)

    # Benchmark command
    bm = sub.add_parser("benchmark", help="Run evaluation harness on a corpus manifest")
    bm.add_argument("manifest", type=str, help="Path to corpus manifest.json")
    bm.add_argument("-o", "--output", type=str, help="Save evaluation report to JSON file")
    bm.add_argument("--tags", type=str, help="Comma-separated tag filter (e.g., 'pentest,standard')")
    bm.add_argument("--repetitions", type=int, default=1,
                    help="Number of repetitions per case (default: 1)")
    bm.set_defaults(func=cmd_benchmark)

    # Registry command
    rg = sub.add_parser("registry", help="Manage the success registry")
    rg_sub = rg.add_subparsers(dest="registry_cmd", required=True)

    rg_stats = rg_sub.add_parser("stats", help="Show registry statistics")
    rg_stats.add_argument("--registry-path", type=str, default="success_registry.json",
                          help="Path to registry JSON (default: success_registry.json)")

    rg_query = rg_sub.add_parser("query", help="Find similar past mandates")
    rg_query.add_argument("--registry-path", type=str, default="success_registry.json",
                          help="Path to registry JSON")
    rg_query.add_argument("--intent", type=str, help="Intent text to match")
    rg_query.add_argument("--domain", type=str, help="Filter by domain")
    rg_query.add_argument("--top-k", type=int, default=5, help="Max results (default: 5)")

    rg_ingest = rg_sub.add_parser("ingest", help="Ingest a mandate artifact into the registry")
    rg_ingest.add_argument("artifact", type=str, help="Path to mandate-as-code artifact JSON")
    rg_ingest.add_argument("--registry-path", type=str, default="success_registry.json",
                           help="Path to registry JSON")
    rg_ingest.add_argument("--domain", type=str, help="Domain identifier")

    rg.set_defaults(func=cmd_registry)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    rc = args.func(args)
    raise SystemExit(rc)
