"""
Tests for the MANDATE evaluation harness (Workstream B1).

These tests are dependency-free: they exercise the harness with the
ReferenceSystem and need neither AEGIS, Ollama, nor any API. The integration
exercise against the real AEGIS deterministic pipeline lives in
apparatus/run_demo.py.

Run:  python3 -m pytest apparatus/tests -q     (from the project root)
"""
import os
import sys

# Make the project root importable regardless of pytest's working directory.
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from apparatus.harness.records import RunRecord, RoleTiming, HARNESS_VERSION
from apparatus.harness.ledger import RunLedger
from apparatus.harness.runner import Task, run_matrix
from apparatus.systems.reference import ReferenceSystem


def test_runrecord_roundtrip_and_fallback_detection():
    rec = RunRecord(
        run_id="r1", task_id="T1", system_id="s", system_label="S",
        run_number=1, seed=7,
        role_timings=[
            RoleTiming("Intake", "success", 1.0, llm_used=True),
            RoleTiming("Interpreter", "success", 2.0, llm_used=True,
                       llm_fallback=True, llm_fallback_reason="timeout"),
        ],
    )
    d = rec.to_dict()
    assert d["any_llm_fallback"] is True
    assert d["fallback_roles"] == ["Interpreter"]
    assert d["llm_roles_used"] == ["Intake", "Interpreter"]
    assert d["harness_version"] == HARNESS_VERSION

    rec2 = RunRecord.from_dict(d)
    assert rec2.run_id == "r1" and rec2.seed == 7
    assert rec2.any_llm_fallback is True
    assert len(rec2.role_timings) == 2


def test_runrecord_save(tmp_path):
    rec = RunRecord(run_id="r1", task_id="T1", system_id="s",
                    system_label="S", run_number=1, ok=True)
    path = tmp_path / "sub" / "r1.json"
    rec.save(str(path))
    assert path.exists()
    import json
    reloaded = RunRecord.from_dict(json.loads(path.read_text()))
    assert reloaded.ok is True


def test_reference_run_matrix(tmp_path):
    tasks = [
        Task("T1", "Deliver the weekly report by Friday."),
        Task("T2", "Produce an analysis with ninety five percent coverage."),
    ]
    ledger = RunLedger(str(tmp_path / "ledger.jsonl"))
    recs = run_matrix(ReferenceSystem(), tasks, n_runs=3, ledger=ledger,
                      output_dir=str(tmp_path / "out"), verbose=False)
    assert len(recs) == 6                         # 2 tasks x 3 runs
    assert all(r.ok for r in recs)
    assert ledger.count() == 6
    assert len(os.listdir(tmp_path / "out")) == 6  # one output JSON per run
    # run_ids are unique and well formed
    assert len({r.run_id for r in recs}) == 6
    assert recs[0].run_id == "reference__T1__r01"


def test_reference_same_input_contract(tmp_path):
    """The harness passes only request_text. Identical text yields identical
    reference output across runs (the reference system is deterministic)."""
    ledger = RunLedger(str(tmp_path / "l.jsonl"))
    recs = run_matrix(ReferenceSystem(), [Task("T1", "five word task right here")],
                      n_runs=4, ledger=ledger, output_dir=str(tmp_path / "o"),
                      verbose=False)
    word_counts = {r.output["word_count"] for r in recs}
    assert word_counts == {5}


def test_run_matrix_skip_existing_does_not_re_execute(tmp_path):
    """HANDOFF_23 2026-06-08 diagnosis: without skip_existing, re-running
    after a partial checkpoint overwrites all previously-committed records.
    With skip_existing=True, existing <run_id>.json files are loaded into
    the ledger but NOT re-executed; the underlying system.run() is not
    called for those tuples. Verifies the resume contract HANDOFF_24 relies on."""

    class CountingSystem(ReferenceSystem):
        def __init__(self):
            super().__init__()
            self.run_calls = 0

        def run(self, *args, **kwargs):
            self.run_calls += 1
            return super().run(*args, **kwargs)

    tasks = [Task("T1", "first task text"), Task("T2", "second task text")]
    out_dir = str(tmp_path / "out")

    # First pass: execute 2 tasks x 2 runs = 4 records.
    sysA = CountingSystem()
    recsA = run_matrix(sysA, tasks, n_runs=2,
                       ledger=RunLedger(str(tmp_path / "lA.jsonl")),
                       output_dir=out_dir, verbose=False)
    assert len(recsA) == 4
    assert sysA.run_calls == 4
    assert len(os.listdir(out_dir)) == 4

    # Capture mtimes to prove files were not rewritten on the resume.
    first_pass_mtimes = {f: os.path.getmtime(os.path.join(out_dir, f))
                         for f in os.listdir(out_dir)
                         if f.endswith(".json")}

    # Second pass with skip_existing=True: load all 4 from disk, no re-exec.
    sysB = CountingSystem()
    recsB = run_matrix(sysB, tasks, n_runs=2,
                       ledger=RunLedger(str(tmp_path / "lB.jsonl")),
                       output_dir=out_dir, verbose=False, skip_existing=True)
    assert len(recsB) == 4
    assert sysB.run_calls == 0, "skip_existing=True must not re-execute"

    # Output files unchanged.
    for f, mtime in first_pass_mtimes.items():
        assert os.path.getmtime(os.path.join(out_dir, f)) == mtime, (
            f"{f} was rewritten under skip_existing=True")

    assert {r.run_id for r in recsB} == {r.run_id for r in recsA}


def test_run_matrix_skip_existing_resumes_partial_checkpoint(tmp_path):
    """Simulates the HANDOFF_11b-i situation: an output dir has 2 of the 4
    expected (task, run) JSONs from a prior interrupted run. skip_existing
    loads the 2 existing and executes only the 2 missing."""

    class CountingSystem(ReferenceSystem):
        def __init__(self):
            super().__init__()
            self.run_calls = 0

        def run(self, *args, **kwargs):
            self.run_calls += 1
            return super().run(*args, **kwargs)

    tasks = [Task("T1", "first"), Task("T2", "second")]
    out_dir = str(tmp_path / "out")
    os.makedirs(out_dir, exist_ok=True)

    # Step 1: execute T1 at runs 1, 2 only (the "interrupted checkpoint").
    pre_sys = CountingSystem()
    run_matrix(pre_sys, [tasks[0]], n_runs=2,
               ledger=RunLedger(str(tmp_path / "pre.jsonl")),
               output_dir=out_dir, verbose=False)
    assert pre_sys.run_calls == 2
    assert len(os.listdir(out_dir)) == 2

    # Step 2: resume with skip_existing=True on the full 2x2 matrix.
    resume_sys = CountingSystem()
    recs = run_matrix(resume_sys, tasks, n_runs=2,
                     ledger=RunLedger(str(tmp_path / "resume.jsonl")),
                     output_dir=out_dir, verbose=False, skip_existing=True)
    assert len(recs) == 4
    assert resume_sys.run_calls == 2     # only T2's two runs executed
    assert len(os.listdir(out_dir)) == 4


def test_failed_run_is_recorded_not_raised(tmp_path):
    """A system that raises must not abort the batch; the runner records a
    failed RunRecord as a backstop."""
    class Boom(ReferenceSystem):
        system_id = "boom"
        system_label = "Boom"

        def run(self, *a, **k):
            raise RuntimeError("intentional failure")

    ledger = RunLedger(str(tmp_path / "l.jsonl"))
    recs = run_matrix(Boom(), [Task("T1", "x"), Task("T2", "y")], n_runs=1,
                      ledger=ledger, output_dir=str(tmp_path / "o"),
                      verbose=False)
    assert len(recs) == 2
    assert all(r.ok is False for r in recs)
    assert any("intentional failure" in " ".join(r.errors) for r in recs)
    assert ledger.count() == 2
