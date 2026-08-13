"""
Apparatus runner CLI (Phase 6-9 entry points).

One module, four subcommands, each a thin wrapper over the substantive
apparatus modules so a Codex eval-host run is one command per phase.

  run-system    Phase 6 / 7: run one System over a tasks file at N runs
                each, persisting RunRecords to a per-system output dir.
  anonymize     Phase 6 anonymization: strip identity from a directory of
                RunRecord JSON files, write the anonymized copies and a
                gitignored identity mapping.
  grade         Phase 8 grading: load anonymized outputs and ground truth,
                run the three-judge GradingPipeline, write ensemble scores.
  run-analysis  Phase 9: execute the analysis notebooks 01 through 10 via
                nbconvert against the in-place data; each notebook handles
                its own gated skip when its phase input is missing.

Invoke: `python -m apparatus.run <subcommand> --help`.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Optional


# --- shared helpers ---------------------------------------------------------

def _stderr(msg):
    print(msg, file=sys.stderr, flush=True)


def _load_jsonl(path):
    out = []
    with open(path) as f:
        for line in f:
            s = line.strip()
            if s:
                out.append(json.loads(s))
    return out


def _load_json(path):
    with open(path) as f:
        return json.load(f)


def _write_jsonl(path, rows):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, default=str, ensure_ascii=False) + "\n")


def _write_json(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=str, ensure_ascii=False)


def _make_cost_ledger(args):
    path = getattr(args, "cost_ledger", "") or ""
    budget = getattr(args, "campaign_budget_usd", None)
    if not path and budget is None:
        return None
    if not path or budget is None:
        raise ValueError("--cost-ledger and --campaign-budget-usd must be supplied together")
    from .harness.ledger import CampaignCostLedger

    return CampaignCostLedger(path, float(budget))


def _requires_pre_call_gate(args) -> bool:
    return bool(
        getattr(args, "cost_ledger", "")
        or getattr(args, "campaign_budget_usd", None) is not None
        or getattr(args, "preflight_manifest", None)
        or getattr(args, "expected_mlt_commit", "")
        or getattr(args, "expected_apparatus_commit", "")
        or getattr(args, "require_clean_worktree", False)
    )


def _run_pre_call_gate(args, *, condition: str, model: str, llm_backend: str = "") -> int:
    if not _requires_pre_call_gate(args):
        return 0
    from .preflight import PreflightGateError, validate_pre_call_gate

    try:
        validate_pre_call_gate(
            manifest_path=getattr(args, "preflight_manifest", None),
            expected_mlt_commit=getattr(args, "expected_mlt_commit", ""),
            expected_apparatus_commit=getattr(args, "expected_apparatus_commit", ""),
            require_clean_worktree=bool(getattr(args, "require_clean_worktree", False)),
            cost_ledger=getattr(args, "cost_ledger", ""),
            campaign_budget_usd=getattr(args, "campaign_budget_usd", None),
            condition=condition,
            tasks_path=Path(args.tasks),
            model=model,
            seed=int(args.seed),
            runs_per_task=int(args.runs_per_task),
            domain_profile_mode=getattr(args, "domain_profile_mode", "default"),
            llm_backend=llm_backend,
        )
    except PreflightGateError as exc:
        for issue in exc.issues:
            _stderr("pre-call gate failed: " + issue)
        return 2
    return 0


def _load_dotenv_from_root(path=".env"):
    """Small dotenv loader matching the corpus CLI behavior so the API
    keys are picked up automatically."""
    for cand in (path, os.path.join("..", path)):
        if os.path.isfile(cand):
            for line in open(cand):
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, _, v = s.partition("=")
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and v and k not in os.environ:
                    os.environ[k] = v
            return


# --- run-system -------------------------------------------------------------

def _make_system(name: str, args):
    """Build a System by name. Wires MANDATE-primary, baselines B1-B6,
    ablations A1-A7, and the reference self-test system."""
    if name == "mandate_primary":
        from .systems.mandate_primary import (MandatePrimarySystem,
                                                load_ollama_config)
        if not args.aegis:
            raise ValueError("--aegis is required for mandate_primary")
        cfg = None
        if args.ollama_mode:
            cfg = load_ollama_config(args.aegis)
        return MandatePrimarySystem(
            aegis_src_path=os.path.join(args.aegis, "src"),
            mode="ollama" if args.ollama_mode else "deterministic",
            ollama_config=cfg, code_ref=args.code_ref or "")
    if name == "reference":
        from .systems.reference import ReferenceSystem
        return ReferenceSystem()
    if name.startswith("baseline_"):
        from .baselines.single_prompt import baseline_b1, baseline_b2
        from .baselines.react import baseline_b3
        from .baselines.multi_agent import baseline_b4, baseline_b5, baseline_b6
        factories = {"baseline_1": baseline_b1, "baseline_2": baseline_b2,
                      "baseline_3": baseline_b3, "baseline_4": baseline_b4,
                      "baseline_5": baseline_b5, "baseline_6": baseline_b6}
        factory = factories.get(name)
        if factory is None:
            raise ValueError("unknown baseline: %s" % name)
        return factory()
    if name.startswith("ablation_"):
        from .ablations.system import AblationSystem
        aid = name.split("_", 1)[1].upper()
        if not args.aegis:
            raise ValueError("--aegis is required for ablation systems")
        # Variant src defaults to AEGIS-eval/src; for AEGIS-variant
        # ablations the caller passes --variant-src instead.
        return AblationSystem(
            ablation_id=aid,
            primary_aegis_src_path=os.path.join(args.aegis, "src"),
            variant_src_path=args.variant_src or "",
            primary_code_ref=args.code_ref or "",
            mode="ollama" if args.ollama_mode else "deterministic")
    raise ValueError("unknown system: %s" % name)


def cmd_run_system(args) -> int:
    from .harness.runner import Task, run_matrix, load_tasks
    from .harness.ledger import RunLedger

    _load_dotenv_from_root()
    scope_lock = os.path.join(os.getcwd(), "handoffs", "HANDOFF_24c_scope_lock.marker")
    if args.system in {"baseline_5", "baseline_6"} and os.path.exists(scope_lock):
        print(
            "HANDOFF_24c scope lock active; refusing to run "
            f"{args.system}. Delete {scope_lock} to override.",
            file=sys.stderr,
        )
        return 2
    system = _make_system(args.system, args)
    tasks = (load_tasks(args.tasks) if os.path.isdir(args.tasks)
              else _load_tasks_jsonl(args.tasks))
    out_dir = args.output or os.path.join("07_system_outputs", args.system)
    os.makedirs(out_dir, exist_ok=True)
    ledger_path = args.ledger or os.path.join(out_dir, "ledger.jsonl")
    ledger = RunLedger(ledger_path)
    print("running %s over %d tasks at %d runs each -> %s"
          % (args.system, len(tasks), args.runs, out_dir))
    records = run_matrix(system, tasks, n_runs=args.runs, ledger=ledger,
                          output_dir=out_dir, seed_base=args.seed_base,
                          verbose=not args.quiet,
                          skip_existing=getattr(args, "skip_existing", False))
    print("\nwrote", len(records), "RunRecords to", out_dir)
    return 0


def _load_tasks_jsonl(path: str) -> list:
    """Accept either the canonical task-dir format `load_tasks` reads, or
    a JSONL with one task per line carrying `task_id` and either `text`
    or `request_text`."""
    from .harness.runner import Task
    rows = _load_jsonl(path)
    out = []
    for r in rows:
        tid = r.get("task_id")
        text = r.get("text") or r.get("request_text") or ""
        if tid and text:
            out.append(Task(task_id=tid, request_text=text,
                            domain=r.get("domain", ""),
                            category=r.get("category", "")))
    return out


# --- run-cond-a / run-cond-b ------------------------------------------------

def _selected_condition_tasks(args) -> list:
    tasks = _load_tasks_jsonl(args.tasks)
    if args.all:
        return tasks
    wanted = set(args.task_ids or [])
    if not wanted:
        raise ValueError("provide TASK_ID(s) or --all")
    selected = [t for t in tasks if t.task_id in wanted]
    missing = sorted(wanted - {t.task_id for t in selected})
    if missing:
        raise ValueError("unknown task_id(s): %s" % ", ".join(missing))
    return selected


def _run_condition_matrix_parallel(
    system_factory: Callable[[], object],
    *,
    system_id: str,
    system_label: str,
    tasks: list,
    n_runs: int,
    ledger,
    output_dir: str,
    seed_base: int = 1000,
    max_workers: int = 1,
    verbose: bool = True,
    skip_existing: bool = False,
) -> list:
    """Run Cond-A/Cond-B with bounded per-record concurrency.

    This is intentionally scoped to the v2 condition commands instead of the
    generic harness runner. Each worker creates a fresh system instance so
    provider clients and MLT adapters are not shared across threads; completed
    records are checkpointed and appended to the ledger on the main thread.
    """
    from .harness.records import RunRecord, utc_now_iso

    os.makedirs(output_dir, exist_ok=True)
    records = []
    work_items = []
    n_skipped = 0
    ordinal = 0

    for task in tasks:
        for run_number in range(1, n_runs + 1):
            run_id = f"{system_id}__{task.task_id}__r{run_number:02d}"
            seed = seed_base + run_number
            out_path = os.path.join(output_dir, run_id + ".json")
            if skip_existing and os.path.exists(out_path):
                try:
                    with open(out_path) as fh:
                        rec = RunRecord.from_dict(json.load(fh))
                    if not ledger.has_run_id(rec.run_id):
                        ledger.append(rec)
                    records.append((ordinal, rec))
                    n_skipped += 1
                    if verbose:
                        print(f"  {run_id}: SKIP (existing)")
                    ordinal += 1
                    continue
                except Exception as e:
                    if verbose:
                        print(f"  {run_id}: existing file unreadable "
                              f"({e!r}); re-running")

            work_items.append((ordinal, task, run_number, run_id, seed,
                               out_path))
            ordinal += 1

    if verbose and work_items:
        print(f"  parallel workers: {max_workers}; scheduled "
              f"{len(work_items)} new records")

    def _execute(item):
        idx, task, run_number, run_id, seed, out_path = item
        t0 = time.time()
        try:
            system = system_factory()
            rec = system.run(task.request_text, run_id=run_id,
                             task_id=task.task_id,
                             run_number=run_number, seed=seed)
        except Exception as e:
            rec = RunRecord(
                run_id=run_id, task_id=task.task_id,
                system_id=system_id, system_label=system_label,
                run_number=run_number, seed=seed,
                started_at=utc_now_iso(),
                wall_clock_ms=(time.time() - t0) * 1000.0,
                ok=False,
                errors=[f"unhandled exception in system.run: {e!r}",
                        traceback.format_exc()],
            )
        return idx, rec, out_path

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(_execute, item) for item in work_items]
        for fut in as_completed(futures):
            idx, rec, out_path = fut.result()
            rec.save(out_path)
            ledger.append(rec)
            records.append((idx, rec))
            if verbose:
                flag = " [LLM-FALLBACK]" if rec.any_llm_fallback else ""
                print(f"  {rec.run_id}: ok={rec.ok} "
                      f"{rec.wall_clock_ms:.1f}ms{flag}")

    if verbose and skip_existing and n_skipped:
        print(f"  (skipped {n_skipped} existing records; "
              f"executed {len(work_items)} new)")
    records.sort(key=lambda item: item[0])
    return [rec for _, rec in records]


def cmd_run_cond_a(args) -> int:
    from .harness.runner import run_matrix
    from .harness.ledger import RunLedger
    from .systems.mandate_canonical import CondASystem

    _load_dotenv_from_root()
    tasks = _selected_condition_tasks(args)
    gate_rc = _run_pre_call_gate(
        args,
        condition="cond_a",
        model=args.extraction_model,
    )
    if gate_rc:
        return gate_rc
    out_dir = args.out or os.path.join("07_system_outputs", "cond_a")
    os.makedirs(out_dir, exist_ok=True)
    ledger = RunLedger(os.path.join(out_dir, "ledger.jsonl"))
    cost_ledger = _make_cost_ledger(args)
    max_workers = max(1, int(args.max_workers or 1))
    if cost_ledger is not None and max_workers != 1:
        raise ValueError("budget-capped condition runs require --max-workers 1")
    domain_profile_mode = getattr(args, "domain_profile_mode", "default")
    print("running Cond-A over %d tasks at %d runs each -> %s"
          % (len(tasks), args.runs_per_task, out_dir))
    if max_workers == 1:
        system = CondASystem(
            extraction_model=args.extraction_model,
            domain_profile_mode=domain_profile_mode,
            cost_ledger=cost_ledger,
        )
        records = run_matrix(system, tasks, n_runs=args.runs_per_task,
                             ledger=ledger, output_dir=out_dir,
                             seed_base=args.seed, verbose=not args.quiet,
                             skip_existing=args.skip_existing,
                             cost_ledger=cost_ledger)
    else:
        records = _run_condition_matrix_parallel(
            lambda: CondASystem(
                extraction_model=args.extraction_model,
                domain_profile_mode=domain_profile_mode,
            ),
            system_id="cond_a",
            system_label=CondASystem.system_label,
            tasks=tasks,
            n_runs=args.runs_per_task,
            ledger=ledger,
            output_dir=out_dir,
            seed_base=args.seed,
            max_workers=max_workers,
            verbose=not args.quiet,
            skip_existing=args.skip_existing,
        )
    print("\nwrote", len(records), "Cond-A RunRecords to", out_dir)
    return 0


def cmd_run_cond_b(args) -> int:
    from .harness.runner import run_matrix
    from .harness.ledger import RunLedger
    from .systems.mandate_canonical import CondBSystem

    _load_dotenv_from_root()
    tasks = _selected_condition_tasks(args)
    gate_rc = _run_pre_call_gate(
        args,
        condition="cond_b",
        model=args.llm_model,
        llm_backend=args.llm_backend,
    )
    if gate_rc:
        return gate_rc
    out_dir = args.out or os.path.join("07_system_outputs", "cond_b")
    os.makedirs(out_dir, exist_ok=True)
    ledger = RunLedger(os.path.join(out_dir, "ledger.jsonl"))
    cost_ledger = _make_cost_ledger(args)
    max_workers = max(1, int(args.max_workers or 1))
    if cost_ledger is not None and max_workers != 1:
        raise ValueError("budget-capped condition runs require --max-workers 1")
    domain_profile_mode = getattr(args, "domain_profile_mode", "default")
    print("running Cond-B over %d tasks at %d runs each -> %s"
          % (len(tasks), args.runs_per_task, out_dir))
    if max_workers == 1:
        system = CondBSystem(llm_backend=args.llm_backend,
                             llm_model=args.llm_model,
                             domain_profile_mode=domain_profile_mode,
                             cost_ledger=cost_ledger)
        records = run_matrix(system, tasks, n_runs=args.runs_per_task,
                             ledger=ledger, output_dir=out_dir,
                             seed_base=args.seed, verbose=not args.quiet,
                             skip_existing=args.skip_existing,
                             cost_ledger=cost_ledger)
    else:
        records = _run_condition_matrix_parallel(
            lambda: CondBSystem(llm_backend=args.llm_backend,
                                llm_model=args.llm_model,
                                domain_profile_mode=domain_profile_mode),
            system_id="cond_b",
            system_label=CondBSystem.system_label,
            tasks=tasks,
            n_runs=args.runs_per_task,
            ledger=ledger,
            output_dir=out_dir,
            seed_base=args.seed,
            max_workers=max_workers,
            verbose=not args.quiet,
            skip_existing=args.skip_existing,
        )
    print("\nwrote", len(records), "Cond-B RunRecords to", out_dir)
    return 0


# --- anonymize --------------------------------------------------------------

def cmd_anonymize(args) -> int:
    from .anonymize import Anonymizer, verify_mapping

    # Load every RunRecord JSON from the input directory tree
    records = []
    for fp in sorted(glob.glob(os.path.join(args.in_path, "**",
                                              "*.json"),
                                 recursive=True)):
        # ledger.jsonl is JSONL, not JSON; skip
        if fp.endswith(".jsonl"):
            continue
        try:
            records.append(_load_json(fp))
        except Exception as e:
            _stderr("skip %s: %r" % (fp, e))
    print("loaded", len(records), "RunRecords")
    ann = Anonymizer(seed=args.seed)
    result = ann.anonymize(records,
                            identity_tokens=args.identity_tokens or None)
    ok, msgs = verify_mapping(result)
    if not ok:
        _stderr("anonymization integrity check failed:")
        for m in msgs:
            _stderr("  " + m)
        return 4

    mapping_path = args.mapping_path or os.path.join(
        "07_system_outputs", "anonymization_mapping.json")
    if args.out_path:
        outputs_dir = args.out_path
    elif args.mapping_path:
        base = os.path.basename(args.mapping_path)
        parent = os.path.dirname(args.mapping_path) or "."
        if "cond_a" in base:
            outputs_dir = os.path.join(parent, "cond_a_anon")
        elif "cond_b" in base:
            outputs_dir = os.path.join(parent, "cond_b_anon")
        else:
            outputs_dir = os.path.join("08_grading", "anonymized_outputs")
    else:
        outputs_dir = os.path.join("08_grading", "anonymized_outputs")
    ann.save(result, outputs_dir, mapping_path)
    print("anonymized:", len(result.outputs),
          " mapping written:", mapping_path,
          " (gitignored)")
    return 0


# --- grade ------------------------------------------------------------------

def _load_anonymized_outputs(path: str) -> list:
    return _load_jsonl(path) if path.endswith(".jsonl") else [
        _load_json(p) for p in sorted(glob.glob(os.path.join(path, "*.json")))]


def _maybe_filter_and_sample_anon_outputs(anon_outputs: list, args) -> list:
    import random

    system_filter = str(getattr(args, "filter_system_id", "") or "").strip()
    if system_filter:
        wanted_systems = {s.strip() for s in system_filter.split(",") if s.strip()}
        allowed_ids = None
        manifest_path = getattr(args, "sample_manifest", "") or \
            os.path.join("08_grading", "sample_manifest.jsonl")
        if os.path.isfile(manifest_path):
            allowed_ids = {
                r.get("anon_id") for r in _load_jsonl(manifest_path)
                if r.get("system_id") in wanted_systems
            }
        else:
            mapping_path = os.path.join("07_system_outputs",
                                        "anonymization_mapping.json")
            if os.path.isfile(mapping_path):
                mapping = _load_json(mapping_path)
                allowed_ids = {
                    aid for aid, meta in mapping.items()
                    if meta.get("system_id") in wanted_systems
                }
        if allowed_ids is None:
            anon_outputs = [
                ao for ao in anon_outputs
                if ao.get("system_id") in wanted_systems
            ]
        else:
            anon_outputs = [
                ao for ao in anon_outputs
                if ao.get("anon_id") in allowed_ids
            ]

    sample_size = int(getattr(args, "sample_size", 0) or 0)
    if sample_size > 0 and len(anon_outputs) > sample_size:
        rng = random.Random(int(getattr(args, "sample_seed", 20260623)
                                or 20260623))
        idx = sorted(rng.sample(range(len(anon_outputs)), sample_size))
        anon_outputs = [anon_outputs[i] for i in idx]
    return anon_outputs


def _cmd_grade_common(args, *, use_v2: bool = False) -> int:
    """Phase 8 grading. Needs the anonymized outputs, the per-task ground
    truth, and a judges config. The judges config is a small JSON file
    naming the three judge model strings; the LLM clients pick up API
    keys from .env.

    Optionally runs a double-grade pass over a deterministically-sampled
    fraction of the anonymized outputs (PROTOCOL_LOCK §8 IRR), saving the
    second-pass scores so judge-vs-judge AND within-judge stability can
    both be computed in Phase 9.

    Resume + concurrency (patched 2026-06-17 after HANDOFF_13d ran 25
    hours with zero on-disk artifacts because the original implementation
    only wrote outputs after the full 9000-record main pass completed).
    Per-record GradedOutput JSONs are checkpointed by `pipe.grade_all`
    to `<out_dir>/by_record/<anon_id>.json` as each record completes.
    `--skip-existing` loads existing checkpoints and skips re-grading.
    `--max-workers` runs the three judges per record in a bounded
    ThreadPoolExecutor for roughly 3x throughput.
    """
    from .grading.judge import judge_gpt4o, judge_claude_opus, judge_gemini_pro
    from .grading.pipeline import GradingPipeline

    _load_dotenv_from_root()
    anon_outputs = _load_anonymized_outputs(args.anonymized)
    anon_outputs = _maybe_filter_and_sample_anon_outputs(anon_outputs, args)
    gt_path = args.ground_truth
    ground_truth_by_task = _load_json(gt_path) if gt_path.endswith(".json") \
        else {r["task_id"]: r for r in _load_jsonl(gt_path)}

    cfg = _load_json(args.judges_config) if args.judges_config else {}
    judge_kwargs = {}
    if use_v2:
        from .grading.rubric_v2 import (
            GRADER_SYSTEM_V2,
            render_grader_prompt_v2,
            render_schema_check_prompt,
        )
        judge_kwargs = {
            "grader_system": GRADER_SYSTEM_V2,
            "render_grader_prompt_fn": render_grader_prompt_v2,
            "render_schema_check_prompt_fn": render_schema_check_prompt,
        }
    judges = [
        judge_gpt4o(model=cfg.get("gpt4o", "gpt-4o"), **judge_kwargs),
        judge_claude_opus(model=cfg.get("claude", "claude-opus-4-6"),
                          **judge_kwargs),
        judge_gemini_pro(model=cfg.get("gemini", "gemini-2.5-pro"),
                         **judge_kwargs),
    ]
    pipe = GradingPipeline(judges=judges)
    out_dir = args.out or "08_grading"
    label = "v2 " if use_v2 else ""
    print(f"grading {len(anon_outputs)} anonymized outputs with "
          f"{label}3-judge rubric")
    graded = pipe.grade_all(
        anon_outputs, ground_truth_by_task,
        checkpoint_dir=out_dir,
        skip_existing=bool(getattr(args, "skip_existing", False)),
        max_workers=int(getattr(args, "max_workers", 3) or 3),
    )
    pipe.save(graded, out_dir)
    irr = pipe.irr(graded)

    # --- Double-grade sample for PROTOCOL_LOCK §8 IRR (added 2026-06-16
    #     after HANDOFF_13b HALT diagnosed that cmd_grade was not invoking
    #     pipe.double_grade despite the protocol requiring a 20% sample).
    dgp = float(getattr(args, "double_grade_pct", 0.0) or 0.0)
    if dgp > 0.0:
        seed = int(getattr(args, "double_grade_seed", 20260616) or 20260616)
        rng = random.Random(seed)
        n_sample = max(1, int(round(len(anon_outputs) * dgp)))
        sample_idx = sorted(rng.sample(range(len(anon_outputs)), n_sample))
        sample = [anon_outputs[i] for i in sample_idx]
        print(f"\ndouble-grading sample: {n_sample} of {len(anon_outputs)} "
              f"({dgp*100:.0f}%, seed={seed})")
        dg_dir = os.path.join(out_dir, "double_grade")
        os.makedirs(dg_dir, exist_ok=True)
        pass1, pass2 = pipe.double_grade(
            sample, ground_truth_by_task,
            checkpoint_dir=dg_dir,
            skip_existing=bool(getattr(args, "skip_existing", False)),
            max_workers=int(getattr(args, "max_workers", 3) or 3),
        )
        # Save both passes under a sister directory so post-hoc IRR can read both.
        # Per-record double-grade checkpoints also live under
        # double_grade/pass1/by_record and double_grade/pass2/by_record.
        with open(os.path.join(dg_dir, "sample_anon_ids.json"), "w") as f:
            json.dump([s.get("anon_id") for s in sample], f, indent=2)
        with open(os.path.join(dg_dir, "pass1_scores.jsonl"), "w") as f:
            for g in pass1:
                f.write(json.dumps(g.to_dict(), default=str) + "\n")
        with open(os.path.join(dg_dir, "pass2_scores.jsonl"), "w") as f:
            for g in pass2:
                f.write(json.dumps(g.to_dict(), default=str) + "\n")
        irr["double_grade"] = {
            "sample_size": n_sample, "seed": seed,
            "sample_pct": dgp,
            "pass1_irr": pipe.irr(pass1),
            "pass2_irr": pipe.irr(pass2),
        }

    _write_json(os.path.join(out_dir, "irr.json"), irr)
    print("\ngrading IRR:", irr.get("min_pairwise_kappa"),
          " halt:", irr.get("halt"))
    if "double_grade" in irr:
        dg = irr["double_grade"]
        print("double-grade pass1 IRR:", dg["pass1_irr"].get("min_pairwise_kappa"),
              " pass2 IRR:", dg["pass2_irr"].get("min_pairwise_kappa"))
    return 0


def cmd_grade(args) -> int:
    return _cmd_grade_common(args, use_v2=False)


def cmd_grade_v2(args) -> int:
    return _cmd_grade_common(args, use_v2=True)


# --- run-analysis -----------------------------------------------------------

def cmd_run_analysis(args) -> int:
    """Execute analysis notebooks 01 through 10 via nbconvert. Each
    notebook handles its own gated skip when its phase input is missing;
    the runner simply executes each in order and surfaces any that fail
    hard (a clean gated-skip is not a failure)."""
    nb_dir = args.notebooks or "09_analysis"
    files = sorted(glob.glob(os.path.join(nb_dir, "*.ipynb")))
    if not files:
        _stderr("no notebooks under %s" % nb_dir)
        return 3
    print("found", len(files), "notebooks")
    try:
        import nbformat
        from nbconvert.preprocessors import ExecutePreprocessor
    except ImportError as e:
        _stderr("nbconvert / nbformat not installed: %r" % e)
        _stderr("pip install nbconvert nbformat")
        return 2

    failed = []
    for fp in files:
        print("  executing", os.path.basename(fp), "...", end=" ", flush=True)
        nb = nbformat.read(fp, as_version=4)
        ep = ExecutePreprocessor(timeout=args.cell_timeout, kernel_name="python3")
        try:
            ep.preprocess(nb, {"metadata": {"path": nb_dir}})
            with open(fp, "w") as f:
                nbformat.write(nb, f)
            print("OK")
        except Exception as e:
            failed.append((os.path.basename(fp), repr(e)[:200]))
            print("FAIL")
    if failed:
        _stderr("notebooks failing:")
        for name, msg in failed:
            _stderr("  %s -- %s" % (name, msg))
        return 4
    print("all notebooks executed cleanly")
    return 0


# --- argparse ---------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="apparatus.run",
                                  description=("Phase 6-9 apparatus run "
                                                "entry points"))
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run-system",
                         help="Phase 6 / 7: run one System on a tasks file")
    r.add_argument("--system", required=True,
                    help=("mandate_primary | reference | baseline_1..6 | "
                          "ablation_a1..a7"))
    r.add_argument("--tasks", required=True,
                    help="JSONL of {task_id,text} or a task directory")
    r.add_argument("--runs", type=int, default=10)
    r.add_argument("--output", default="",
                    help="default 07_system_outputs/<system>/")
    r.add_argument("--ledger", default="",
                    help="default <output>/ledger.jsonl")
    r.add_argument("--seed-base", type=int, default=20260601)
    r.add_argument("--aegis", default="",
                    help="AEGIS-eval root (required for "
                          "mandate_primary/ablation_*)")
    r.add_argument("--ollama-mode", action="store_true",
                    help="MANDATE-primary in Ollama (fine-tuned) mode; "
                          "default deterministic")
    r.add_argument("--variant-src", default="",
                    help="AEGIS-variant src path for an aegis-variant ablation")
    r.add_argument("--code-ref", default="")
    r.add_argument("--quiet", action="store_true")
    r.add_argument("--skip-existing", action="store_true",
                    help="Resume mode: load existing <output>/<run_id>.json "
                         "records into the ledger but do not re-execute them. "
                         "Required when resuming a long-running multi-day "
                         "Phase 6 leg from a partial checkpoint without "
                         "overwriting committed records (HANDOFF_23 "
                         "2026-06-08 halt diagnosis).")
    r.set_defaults(func=cmd_run_system)

    ca = sub.add_parser("run-cond-a",
                        help="v2 Cond-A: extractor -> canonical MLT MANDATE")
    ca.add_argument("task_ids", nargs="*")
    ca.add_argument("--all", action="store_true",
                    help="Run every task in --tasks")
    ca.add_argument("--tasks", default="04_ground_truth/main_tasks.jsonl",
                    help="JSONL with task_id and text/request_text")
    ca.add_argument("--out", default="07_system_outputs/cond_a")
    ca.add_argument("--extraction-model", default="claude-sonnet-4-6")
    ca.add_argument("--runs-per-task", type=int, default=1)
    ca.add_argument("--seed", type=int, default=20260623)
    ca.add_argument("--skip-existing", action="store_true")
    ca.add_argument("--checkpoint-every", type=int, default=0,
                    help="Accepted for handoff compatibility; records are "
                         "checkpointed individually.")
    ca.add_argument("--cost-ledger", default="",
                    help="Shared JSONL campaign cost ledger for budget cutoff.")
    ca.add_argument("--campaign-budget-usd", type=float, default=None,
                    help="User-approved total campaign spend cap in USD.")
    ca.add_argument("--preflight-manifest", type=Path,
                    help="Local preflight manifest authorizing paid execution.")
    ca.add_argument("--expected-mlt-commit", default="",
                    help="Expected local MLT commit for fail-closed paid runs.")
    ca.add_argument("--expected-apparatus-commit", default="",
                    help="Expected local apparatus commit for fail-closed paid runs.")
    ca.add_argument("--require-clean-worktree", action="store_true",
                    help="Fail before paid execution if tracked source is dirty.")
    ca.add_argument("--max-workers", type=int, default=1,
                    help="Run up to N Cond-A records concurrently while "
                         "checkpointing each completed record individually.")
    ca.add_argument("--domain-profile-mode",
                    choices=["default", "auto"],
                    default="default",
                    help="DomainProfile selection. 'default' passes None to "
                         "canonical PipelineConfig, preserving pre-HANDOFF_19d "
                         "behavior. 'auto' maps task ID prefix "
                         "INT->defense_intel, SEC->incident_response, "
                         "FIN->None.")
    ca.add_argument("--quiet", action="store_true")
    ca.set_defaults(func=cmd_run_cond_a)

    cb = sub.add_parser("run-cond-b",
                        help="v2 Cond-B: canonical MLT MANDATE with LLM hooks")
    cb.add_argument("task_ids", nargs="*")
    cb.add_argument("--all", action="store_true",
                    help="Run every task in --tasks")
    cb.add_argument("--tasks", default="04_ground_truth/main_tasks.jsonl",
                    help="JSONL with task_id and text/request_text")
    cb.add_argument("--out", default="07_system_outputs/cond_b")
    cb.add_argument("--llm-backend", default="anthropic",
                    choices=["anthropic", "ollama"])
    cb.add_argument("--llm-model", default="claude-sonnet-4-6",
                    help="For anthropic: claude-sonnet-4-6 etc. For "
                         "ollama: qwen2.5:32b, llama3.2:3b, mistral:7b, "
                         "phi3:14b.")
    cb.add_argument("--runs-per-task", type=int, default=1)
    cb.add_argument("--seed", type=int, default=20260623)
    cb.add_argument("--skip-existing", action="store_true")
    cb.add_argument("--checkpoint-every", type=int, default=0,
                    help="Accepted for handoff compatibility; records are "
                         "checkpointed individually.")
    cb.add_argument("--cost-ledger", default="",
                    help="Shared JSONL campaign cost ledger for budget cutoff.")
    cb.add_argument("--campaign-budget-usd", type=float, default=None,
                    help="User-approved total campaign spend cap in USD.")
    cb.add_argument("--preflight-manifest", type=Path,
                    help="Local preflight manifest authorizing paid execution.")
    cb.add_argument("--expected-mlt-commit", default="",
                    help="Expected local MLT commit for fail-closed paid runs.")
    cb.add_argument("--expected-apparatus-commit", default="",
                    help="Expected local apparatus commit for fail-closed paid runs.")
    cb.add_argument("--require-clean-worktree", action="store_true",
                    help="Fail before paid execution if tracked source is dirty.")
    cb.add_argument("--max-workers", type=int, default=1,
                    help="Run up to N Cond-B records concurrently while "
                         "checkpointing each completed record individually.")
    cb.add_argument("--domain-profile-mode",
                    choices=["default", "auto"],
                    default="default",
                    help="DomainProfile selection. 'default' passes None to "
                         "canonical PipelineConfig, preserving pre-HANDOFF_19d "
                         "behavior. 'auto' maps task ID prefix "
                         "INT->defense_intel, SEC->incident_response, "
                         "FIN->None.")
    cb.add_argument("--quiet", action="store_true")
    cb.set_defaults(func=cmd_run_cond_b)

    a = sub.add_parser("anonymize",
                         help="Phase 6 anonymization")
    a.add_argument("--in", "--inputs", dest="in_path", required=True,
                    help="directory of RunRecord JSONs")
    a.add_argument("--out", dest="out_path", default="",
                    help="default 08_grading/anonymized_outputs/")
    a.add_argument("--mapping-path", "--mapping-output", default="",
                    help="default 07_system_outputs/"
                          "anonymization_mapping.json (gitignored)")
    a.add_argument("--seed", type=int, default=20260523)
    a.add_argument("--identity-tokens", nargs="+", default=[],
                    help="extra system-identifying strings to scrub")
    a.set_defaults(func=cmd_anonymize)

    g = sub.add_parser("grade", help="Phase 8 three-judge grading")
    g.add_argument("--anonymized", required=True,
                    help="JSONL or directory of anonymized outputs")
    g.add_argument("--ground-truth", required=True,
                    help="JSON map task_id -> ground_truth, or JSONL. Each "
                          "entry's anchor fields must be under an 'anchor' "
                          "sub-key (pipeline.py reads gt.get('anchor', {})).")
    g.add_argument("--judges-config", default="",
                    help="JSON {gpt4o, claude, gemini} model strings")
    g.add_argument("--out", default="08_grading")
    g.add_argument("--double-grade-pct", type=float, default=0.0,
                    help="Fraction of anonymized outputs to double-grade for "
                          "IRR (PROTOCOL_LOCK §8). Default 0.0 (skip). "
                          "Phase 8 production runs should pass 0.20 per the "
                          "protocol's 20% sample.")
    g.add_argument("--double-grade-seed", type=int, default=20260616,
                    help="Seed for the deterministic double-grade sample "
                          "selection. Default 20260616.")
    g.add_argument("--skip-existing", action="store_true",
                    help="Resume mode: skip records whose checkpoint "
                          "at <out>/by_record/<anon_id>.json already "
                          "exists. Required to resume a crashed grading "
                          "run without re-burning API spend on records "
                          "already graded (HANDOFF_13d 2026-06-17 "
                          "diagnosis).")
    g.add_argument("--max-workers", type=int, default=3,
                    help="Per-record judge concurrency. Default 3 (one "
                          "thread per judge). Set 1 for serial. Higher "
                          "values risk API rate limits.")
    g.set_defaults(func=cmd_grade)

    gv2 = sub.add_parser("grade-v2",
                         help="Phase 8 grading with v2 shape-neutral rubric")
    gv2.add_argument("--anonymized", required=True,
                     help="JSONL or directory of anonymized outputs")
    gv2.add_argument("--filter-system-id", default="",
                     help="Comma-separated system IDs to include. If the "
                          "D-08 sample manifest exists, filtering uses that "
                          "manifest so Cond-X/baseline re-grades stay on "
                          "the existing 700-record sample.")
    gv2.add_argument("--sample-manifest", default="",
                     help="Optional sample manifest JSONL for system filters")
    gv2.add_argument("--sample-size", type=int, default=0,
                     help="Optional deterministic sample size after filters")
    gv2.add_argument("--sample-seed", type=int, default=20260623)
    gv2.add_argument("--ground-truth", required=True,
                     help="JSON map task_id -> ground_truth, or JSONL")
    gv2.add_argument("--judges-config", default="",
                     help="JSON {gpt4o, claude, gemini} model strings")
    gv2.add_argument("--rubric", default="v2", choices=["v2"],
                     help="Accepted for handoff compatibility; grade-v2 "
                          "always uses the v2 rubric.")
    gv2.add_argument("--full-coverage", action="store_true",
                     help="Accepted for handoff compatibility. Full coverage "
                          "is the default unless --sample-size or "
                          "--filter-system-id is supplied.")
    gv2.add_argument("--out", default="08_grading_v2")
    gv2.add_argument("--double-grade-pct", type=float, default=0.0)
    gv2.add_argument("--double-grade-seed", type=int, default=20260623)
    gv2.add_argument("--skip-existing", action="store_true")
    gv2.add_argument("--max-workers", type=int, default=3)
    gv2.set_defaults(func=cmd_grade_v2)

    an = sub.add_parser("run-analysis",
                          help="Phase 9 execute notebooks 01 through 10")
    an.add_argument("--notebooks", default="09_analysis")
    an.add_argument("--cell-timeout", type=int, default=600)
    an.set_defaults(func=cmd_run_analysis)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
