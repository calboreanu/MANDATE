"""
Three-judge grading pipeline (Workstream B5).

Orchestrates the PLAYBOOK Phase 8 grading: each of the three judges scores
every anonymized output against ground truth; the three are aggregated; a
20%-sample double-grading supports a stability check; and inter-judge
reliability is computed with a halt flag if it falls below threshold.

The pipeline grades; it does not decide WHICH outputs to grade. In the real
study that is every anonymized output from Phases 6 and 7. Running it for
real is gated on the pre-registration deposit.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from .ensemble import EnsembleScore, aggregate, grader_irr
from .judge import JudgeScore


def _reconstruct_graded_output(d: dict) -> "GradedOutput":
    """Reconstruct a GradedOutput from its to_dict() form. Used by
    grade_all's skip_existing path to load checkpoints from disk.
    JudgeScore and EnsembleScore are dataclasses; both reconstruct from
    their dict via direct keyword unpacking against their fields."""
    from dataclasses import fields as _fields
    js_fields = {f.name for f in _fields(JudgeScore)}
    js_list = []
    for s in d.get("judge_scores", []) or []:
        if not isinstance(s, dict):
            continue
        js_list.append(JudgeScore(**{k: v for k, v in s.items()
                                     if k in js_fields}))
    ens = d.get("ensemble", {}) or {}
    ens_fields = {f.name for f in _fields(EnsembleScore)}
    ens_obj = EnsembleScore(**{k: v for k, v in ens.items()
                                if k in ens_fields}) if ens else None
    return GradedOutput(anon_id=d.get("anon_id", ""),
                        task_id=d.get("task_id", ""),
                        judge_scores=js_list, ensemble=ens_obj)


@dataclass
class GradedOutput:
    anon_id: str
    task_id: str
    judge_scores: list        # list[JudgeScore]
    ensemble: EnsembleScore

    def to_dict(self) -> dict:
        return {
            "anon_id": self.anon_id, "task_id": self.task_id,
            "judge_scores": [s.to_dict() for s in self.judge_scores],
            "ensemble": self.ensemble.to_dict(),
        }


class GradingPipeline:
    """Drives the three judges over anonymized outputs.

    ground_truth_by_task maps task_id -> a dict with:
      anchor               the SME ground-truth anchor (JSON-serializable)
      category             full_specification | gap_triggering | stretch_case
      expected_output_type MANDATE_AS_CODE | GAP_REPORT
      is_injection_trial   True for prompt-injection perturbation trials
    """

    def __init__(self, judges: list):
        if len(judges) < 2:
            raise ValueError("the ensemble needs at least 2 judges "
                             "(the protocol specifies 3)")
        self.judges = judges

    def describe(self) -> dict:
        return {"judges": [j.describe() for j in self.judges]}

    def grade_output(self, anon_output: dict, gt: dict,
                     max_workers: int = 1) -> GradedOutput:
        """Grade one anonymized output against ground truth.

        `max_workers` > 1 runs the three judges concurrently in a
        ThreadPoolExecutor. The Judge.grade() calls are I/O-bound
        (each is an LLM API call) so threads outperform processes here.
        """
        gt_json = json.dumps(gt.get("anchor", {}), indent=2, default=str)
        out_json = json.dumps(anon_output.get("output"), indent=2,
                              default=str)
        expected_type = gt.get("expected_output_type") \
            or anon_output.get("output_type", "")
        kwargs = dict(
            anon_id=anon_output["anon_id"], output_text=out_json,
            ground_truth_json=gt_json,
            expected_output_type=expected_type,
            task_category=gt.get("category", ""),
            is_injection_trial=bool(gt.get("is_injection_trial", False)))
        if max_workers > 1:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(
                    max_workers=max_workers) as ex:
                futures = [ex.submit(j.grade, **kwargs) for j in self.judges]
                scores = [f.result() for f in
                          concurrent.futures.as_completed(futures)]
        else:
            scores = [j.grade(**kwargs) for j in self.judges]
        return GradedOutput(anon_id=anon_output["anon_id"],
                            task_id=anon_output.get("task_id", ""),
                            judge_scores=scores, ensemble=aggregate(scores))

    def grade_all(self, anon_outputs: list,
                  ground_truth_by_task: dict,
                  checkpoint_dir: str = "",
                  skip_existing: bool = False,
                  max_workers: int = 1) -> list:
        """Grade every anonymized output.

        If `checkpoint_dir` is set, each completed GradedOutput is written
        to `<checkpoint_dir>/by_record/<anon_id>.json` IMMEDIATELY after
        grading. This eliminates the HANDOFF_13d 2026-06-17 failure mode
        where 25 hours of grading produced zero on-disk artifacts because
        the original implementation only flushed at the end of the full
        9000-record main pass.

        If `skip_existing=True` and a checkpoint file exists for an
        anon_id, the existing GradedOutput is loaded from disk and the
        judges are NOT called for that record. This is the resume path.

        `max_workers` > 1 runs the three judges concurrently per record
        (each judge is an I/O-bound API call; threads outperform processes).
        Default 1 preserves single-threaded behavior for backwards
        compatibility.
        """
        graded = []
        by_record_dir = ""
        incomplete_dir = ""
        if checkpoint_dir:
            by_record_dir = os.path.join(checkpoint_dir, "by_record")
            incomplete_dir = os.path.join(checkpoint_dir, "incomplete_grades")
            os.makedirs(by_record_dir, exist_ok=True)

        n_skipped = 0
        n_executed = 0
        n_incomplete = 0
        for ao in anon_outputs:
            anon_id = ao["anon_id"]
            task_id = ao.get("task_id", "")
            chk_path = os.path.join(by_record_dir, f"{anon_id}.json") \
                if by_record_dir else ""

            if skip_existing and chk_path and os.path.exists(chk_path):
                try:
                    with open(chk_path) as fh:
                        d = json.load(fh)
                    go = GradedOutput.from_dict(d) \
                        if hasattr(GradedOutput, 'from_dict') \
                        else _reconstruct_graded_output(d)
                    graded.append(go)
                    n_skipped += 1
                    continue
                except Exception as e:
                    # Corrupt checkpoint; re-grade rather than fail.
                    pass

            gt = ground_truth_by_task.get(task_id)
            if gt is None:
                raise KeyError("no ground truth for task_id %r (output %s)"
                               % (task_id, anon_id))

            go = self.grade_output(ao, gt, max_workers=max_workers)
            n_executed += 1

            # HANDOFF_13e_revised_attempt_05 2026-06-18 patch: refuse to
            # persist a checkpoint where any judge errored after the
            # retry layer exhausted. The record falls back into the
            # ungraded queue for re-grading on the next --skip-existing
            # run. Partial results are written to incomplete_grades/
            # for operator inspection but NOT to by_record/, so
            # --skip-existing will redo them without the operator having
            # to manually quarantine.
            all_judges_succeeded = bool(go.judge_scores) and all(
                getattr(s, "parse_ok", False) and not getattr(s, "error", "")
                for s in go.judge_scores)

            if all_judges_succeeded:
                graded.append(go)
                if chk_path:
                    with open(chk_path, "w") as fh:
                        json.dump(go.to_dict(), fh, default=str)
            else:
                n_incomplete += 1
                if incomplete_dir:
                    os.makedirs(incomplete_dir, exist_ok=True)
                    ipath = os.path.join(incomplete_dir, f"{anon_id}.json")
                    with open(ipath, "w") as fh:
                        json.dump(go.to_dict(), fh, default=str)
                # Surface to stderr so the operator sees throttled-judge
                # accumulation in real time. (Stderr, not stdout, so the
                # final summary print on stdout is unaffected.)
                import sys as _sys
                err_summary = []
                for s in go.judge_scores:
                    if getattr(s, "error", ""):
                        err_summary.append(
                            f"{getattr(s, 'judge_id', '?')}={s.error[:80]}")
                _sys.stderr.write(
                    f"  grade_all: INCOMPLETE {anon_id} "
                    f"(will redo on resume): {'; '.join(err_summary)}\n")
                _sys.stderr.flush()

        if checkpoint_dir and (n_skipped or n_executed):
            print(f"  grade_all: skipped {n_skipped}, executed {n_executed}, "
                  f"incomplete {n_incomplete}, persisted {len(graded)}")
        return graded

    def double_grade(self, anon_outputs_sample: list,
                     ground_truth_by_task: dict,
                     checkpoint_dir: str = "",
                     skip_existing: bool = False,
                     max_workers: int = 1) -> tuple:
        """Grade a sample twice in two independent passes (PLAYBOOK Section 8,
        20% double-grading). Returns (pass1, pass2) for stability analysis.

        If `checkpoint_dir` is supplied, each pass gets an independent
        checkpoint namespace (`pass1/` and `pass2/`) so resume mode never
        mistakes pass1 scores for pass2 scores.
        """
        pass1_dir = os.path.join(checkpoint_dir, "pass1") if checkpoint_dir else ""
        pass2_dir = os.path.join(checkpoint_dir, "pass2") if checkpoint_dir else ""
        return (self.grade_all(anon_outputs_sample, ground_truth_by_task,
                               checkpoint_dir=pass1_dir,
                               skip_existing=skip_existing,
                               max_workers=max_workers),
                self.grade_all(anon_outputs_sample, ground_truth_by_task,
                               checkpoint_dir=pass2_dir,
                               skip_existing=skip_existing,
                               max_workers=max_workers))

    def irr(self, graded: list) -> dict:
        """Inter-judge reliability report, with the halt flag."""
        return grader_irr(graded)

    def save(self, graded: list, grading_dir: str) -> None:
        """Write ensemble scores and per-judge scores into the 08_grading
        tree. One JSONL line per output."""
        ens_dir = os.path.join(grading_dir, "ensemble_aggregated")
        os.makedirs(ens_dir, exist_ok=True)
        with open(os.path.join(ens_dir, "ensemble_scores.jsonl"), "w") as f:
            for g in graded:
                f.write(json.dumps(g.ensemble.to_dict(), default=str) + "\n")
        by_judge: dict = {}
        for g in graded:
            for s in g.judge_scores:
                by_judge.setdefault(s.judge_id, []).append(s.to_dict())
        for judge_id, rows in by_judge.items():
            jdir = os.path.join(grading_dir, judge_id)
            os.makedirs(jdir, exist_ok=True)
            with open(os.path.join(jdir, "scores.jsonl"), "w") as f:
                for row in rows:
                    f.write(json.dumps(row, default=str) + "\n")
