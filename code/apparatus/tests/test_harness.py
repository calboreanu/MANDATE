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
import json

import pytest

# Make the project root importable regardless of pytest's working directory.
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from apparatus.harness.records import RunRecord, RoleTiming, HARNESS_VERSION
from apparatus.harness.ledger import CampaignBudgetExceeded, CampaignCostLedger, RunLedger
from apparatus.harness.runner import Task, run_matrix
from apparatus.rerun_analysis import _validate_cost_ledger
from apparatus.baselines.llm_client import BudgetedLLMClient, LLMResponse
from apparatus.systems.reference import ReferenceSystem


def _ledger_rows(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


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
    assert not list((tmp_path / "sub").glob("*.tmp.*"))
    import json
    reloaded = RunRecord.from_dict(json.loads(path.read_text()))
    assert reloaded.ok is True


def test_runledger_refuses_duplicate_run_id(tmp_path):
    ledger = RunLedger(str(tmp_path / "ledger.jsonl"))
    rec = RunRecord(run_id="r1", task_id="T1", system_id="s",
                    system_label="S", run_number=1)
    ledger.append(rec)
    with pytest.raises(ValueError, match="duplicate run_id"):
        ledger.append(rec)


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


def test_campaign_budget_cutoff_stops_before_next_record(tmp_path):
    class CostSystem(ReferenceSystem):
        def run(self, *args, **kwargs):
            rec = super().run(*args, **kwargs)
            rec.api_cost_usd = 0.05
            return rec

    ledger = RunLedger(str(tmp_path / "ledger.jsonl"))
    cost_ledger = CampaignCostLedger(str(tmp_path / "cost.jsonl"), 0.05)
    with pytest.raises(CampaignBudgetExceeded):
        run_matrix(
            CostSystem(),
            [Task("T1", "x"), Task("T2", "y")],
            n_runs=1,
            ledger=ledger,
            output_dir=str(tmp_path / "out"),
            verbose=False,
            cost_ledger=cost_ledger,
        )
    assert ledger.count() == 1
    assert cost_ledger.total() == 0.05


def test_campaign_budget_reservation_and_settlement(tmp_path):
    ledger = CampaignCostLedger(str(tmp_path / "cost.jsonl"), 0.10)
    reservation_id = ledger.reserve_call(
        run_id="r1",
        system_id="cond_a",
        task_id="T1",
        run_number=1,
        role="PreExtractor",
        model="claude-sonnet-4-6",
        reserved_cost_usd=0.05,
    )
    assert ledger.total() == 0.0
    assert ledger.reserved_total() == 0.05
    ledger.settle_call(
        reservation_id,
        actual_cost_usd=0.02,
        input_tokens=100,
        output_tokens=200,
    )
    assert ledger.total() == 0.02
    assert ledger.reserved_total() == 0.02
    with pytest.raises(ValueError, match="duplicate"):
        ledger.settle_call(reservation_id, actual_cost_usd=0.02)


def test_campaign_budget_reservation_refuses_over_cap(tmp_path):
    ledger = CampaignCostLedger(str(tmp_path / "cost.jsonl"), 0.01)
    with pytest.raises(CampaignBudgetExceeded):
        ledger.reserve_call(
            run_id="r1",
            system_id="cond_a",
            task_id="T1",
            run_number=1,
            role="PreExtractor",
            model="claude-sonnet-4-6",
            reserved_cost_usd=0.02,
        )


def test_budgeted_llm_client_records_attempt_settlement(tmp_path):
    class FakeClient:
        provider = "anthropic"

        def generate(self, **kwargs):
            return LLMResponse(
                text="OK",
                model=kwargs["model"],
                input_tokens=10,
                output_tokens=20,
            )

    ledger = CampaignCostLedger(str(tmp_path / "cost.jsonl"), 0.10)
    client = BudgetedLLMClient(
        FakeClient(),
        cost_ledger=ledger,
        run_id="cond_a__T1__r01",
        system_id="cond_a",
        task_id="T1",
        run_number=1,
        role="PreExtractor",
    )
    resp = client.generate(
        system="system",
        user="user",
        model="claude-sonnet-4-6",
        max_tokens=10,
    )
    assert resp.raw_response["budget_reservation_id"]
    assert ledger.total() == resp.cost_usd


def test_run_matrix_paid_path_appends_record_summary_and_resumes(tmp_path):
    class FakeClient:
        provider = "anthropic"

        def __init__(self):
            self.calls = 0

        def generate(self, **kwargs):
            self.calls += 1
            return LLMResponse(
                text="OK",
                model=kwargs["model"],
                input_tokens=10,
                output_tokens=20,
            )

    class PaidSystem(ReferenceSystem):
        system_id = "cond_a"
        system_label = "Paid path"

        def __init__(self, client):
            self.client = client

        def run(self, request_text, *, run_id, task_id, run_number, seed=None):
            budgeted = BudgetedLLMClient(
                self.client,
                cost_ledger=cost_ledger,
                run_id=run_id,
                system_id=self.system_id,
                task_id=task_id,
                run_number=run_number,
                role="PreExtractor",
            )
            resp = budgeted.generate(
                system="system",
                user=request_text,
                model="claude-sonnet-4-6",
                max_tokens=10,
            )
            return RunRecord(
                run_id=run_id,
                task_id=task_id,
                system_id=self.system_id,
                system_label=self.system_label,
                run_number=run_number,
                seed=seed,
                ok=True,
                api_cost_usd=resp.raw_response["budget_total_cost_usd"],
                output={
                    "text": resp.text,
                    "mission_input_metadata": {
                        "raw_provider_response": {
                            "provider": getattr(self.client, "provider", ""),
                            "model": resp.model,
                            "input_tokens": resp.input_tokens,
                            "output_tokens": resp.output_tokens,
                            "cost_usd": resp.raw_response["budget_total_cost_usd"],
                            "response_cost_usd": resp.cost_usd,
                            "budget_reservation_id": resp.raw_response["budget_reservation_id"],
                            "budget_attempts": list(resp.raw_response["budget_attempts"]),
                            "budget_total_cost_usd": resp.raw_response["budget_total_cost_usd"],
                            "budget_cost_accounting": resp.raw_response["budget_cost_accounting"],
                            "text": resp.text,
                            "retry": {
                                "attempts": 1,
                                "max_attempts": 1,
                                "errors": [],
                                "final_status": "success",
                            },
                        },
                    },
                },
            )

    cost_path = tmp_path / "cost.jsonl"
    cost_ledger = CampaignCostLedger(str(cost_path), 1.0)
    client = FakeClient()
    out_dir = tmp_path / "out"
    recs = run_matrix(
        PaidSystem(client),
        [Task("T1", "paid task")],
        n_runs=1,
        ledger=RunLedger(str(tmp_path / "ledger.jsonl")),
        output_dir=str(out_dir),
        verbose=False,
        cost_ledger=cost_ledger,
    )
    rows = _ledger_rows(cost_path)
    assert {"reservation", "attempt_state", "settlement", "record_summary"}.issubset(
        {row["row_type"] for row in rows}
    )
    assert cost_ledger.has_record_summary(recs[0].run_id)
    assert _validate_cost_ledger([recs[0].to_dict()], cost_path) == []

    resume_client = FakeClient()
    resumed = run_matrix(
        PaidSystem(resume_client),
        [Task("T1", "paid task")],
        n_runs=1,
        ledger=RunLedger(str(tmp_path / "resume.jsonl")),
        output_dir=str(out_dir),
        verbose=False,
        skip_existing=True,
        cost_ledger=cost_ledger,
    )
    assert len(resumed) == 1
    assert resume_client.calls == 0
    with pytest.raises(ValueError, match="duplicate"):
        cost_ledger.append_record_summary(recs[0])


def test_campaign_budget_reconciles_undispatched_reservation(tmp_path):
    ledger = CampaignCostLedger(str(tmp_path / "cost.jsonl"), 1.0)
    rid = ledger.reserve_call(
        run_id="r1",
        system_id="cond_a",
        task_id="T1",
        run_number=1,
        role="PreExtractor",
        model="claude-sonnet-4-6",
        reserved_cost_usd=0.05,
    )
    result = ledger.reconcile_stale_attempts()
    rows = _ledger_rows(tmp_path / "cost.jsonl")
    settlement = next(row for row in rows if row.get("row_type") == "settlement")
    assert result["count"] == 1
    assert settlement["reservation_id"] == rid
    assert settlement["status"] == "reconciled_undispatched_zero"
    assert settlement["actual_cost_usd"] == 0.0


def test_campaign_budget_reconciles_dispatched_uncertain_to_reserved_bound(tmp_path):
    ledger = CampaignCostLedger(str(tmp_path / "cost.jsonl"), 1.0)
    rid = ledger.reserve_call(
        run_id="r1",
        system_id="cond_a",
        task_id="T1",
        run_number=1,
        role="PreExtractor",
        model="claude-sonnet-4-6",
        reserved_cost_usd=0.05,
    )
    ledger.mark_dispatch_started(rid)
    ledger.reconcile_stale_attempts()
    settlement = next(row for row in _ledger_rows(tmp_path / "cost.jsonl") if row.get("row_type") == "settlement")
    assert settlement["status"] == "reconciled_dispatch_uncertain_reserved_bound"
    assert settlement["actual_cost_usd"] == 0.05
    assert settlement["cost_basis"] == "reserved_bound_conservative"


def test_campaign_budget_reconciles_response_received_to_authoritative_cost(tmp_path):
    ledger = CampaignCostLedger(str(tmp_path / "cost.jsonl"), 1.0)
    rid = ledger.reserve_call(
        run_id="r1",
        system_id="cond_a",
        task_id="T1",
        run_number=1,
        role="PreExtractor",
        model="claude-sonnet-4-6",
        reserved_cost_usd=0.05,
    )
    ledger.mark_dispatch_started(rid)
    ledger.mark_response_received(rid, actual_cost_usd=0.012345, input_tokens=10, output_tokens=20)
    ledger.reconcile_stale_attempts()
    settlement = next(row for row in _ledger_rows(tmp_path / "cost.jsonl") if row.get("row_type") == "settlement")
    assert settlement["status"] == "reconciled_response_received"
    assert settlement["actual_cost_usd"] == 0.012345
    assert settlement["input_tokens"] == 10


def test_skip_existing_recovers_missing_record_summary_after_settlement(tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    rec = RunRecord(
        run_id="reference__T1__r01",
        task_id="T1",
        system_id="reference",
        system_label="Reference",
        run_number=1,
        ok=True,
        api_cost_usd=0.01,
    )
    rec.save(str(out_dir / "reference__T1__r01.json"))
    cost_ledger = CampaignCostLedger(str(tmp_path / "cost.jsonl"), 1.0)
    rid = cost_ledger.reserve_call(
        run_id=rec.run_id,
        system_id=rec.system_id,
        task_id=rec.task_id,
        run_number=rec.run_number,
        role="PreExtractor",
        model="claude-sonnet-4-6",
        reserved_cost_usd=0.02,
    )
    cost_ledger.mark_dispatch_started(rid)
    cost_ledger.mark_response_received(rid, actual_cost_usd=0.01)
    cost_ledger.settle_call(rid, actual_cost_usd=0.01, status="success")

    run_matrix(
        ReferenceSystem(),
        [Task("T1", "x")],
        n_runs=1,
        ledger=RunLedger(str(tmp_path / "ledger.jsonl")),
        output_dir=str(out_dir),
        verbose=False,
        skip_existing=True,
        cost_ledger=cost_ledger,
    )
    assert cost_ledger.has_record_summary(rec.run_id)


def test_budgeted_llm_client_debits_uncertain_failed_dispatch_to_reserved_bound(tmp_path):
    class FakeClient:
        provider = "anthropic"

        def generate(self, **kwargs):
            raise RuntimeError("529 overloaded_error")

    ledger = CampaignCostLedger(str(tmp_path / "cost.jsonl"), 1.0)
    client = BudgetedLLMClient(
        FakeClient(),
        cost_ledger=ledger,
        run_id="cond_a__T1__r01",
        system_id="cond_a",
        task_id="T1",
        run_number=1,
        role="PreExtractor",
    )
    with pytest.raises(RuntimeError):
        client.generate(system="system", user="user", model="claude-sonnet-4-6", max_tokens=10)
    settlement = next(row for row in _ledger_rows(tmp_path / "cost.jsonl") if row.get("row_type") == "settlement")
    assert settlement["status"] == "failed_dispatch_uncertain_reserved_bound"
    assert settlement["actual_cost_usd"] == settlement["reserved_cost_usd"]


def test_budgeted_llm_client_uses_authoritative_exception_usage(tmp_path):
    class ChargedError(RuntimeError):
        input_tokens = 10
        output_tokens = 20

    class FakeClient:
        provider = "anthropic"

        def generate(self, **kwargs):
            raise ChargedError("529 overloaded_error")

    ledger = CampaignCostLedger(str(tmp_path / "cost.jsonl"), 1.0)
    client = BudgetedLLMClient(
        FakeClient(),
        cost_ledger=ledger,
        run_id="cond_a__T1__r01",
        system_id="cond_a",
        task_id="T1",
        run_number=1,
        role="PreExtractor",
    )
    with pytest.raises(ChargedError):
        client.generate(system="system", user="user", model="claude-sonnet-4-6", max_tokens=10)
    settlement = next(row for row in _ledger_rows(tmp_path / "cost.jsonl") if row.get("row_type") == "settlement")
    assert settlement["status"] == "failed_authoritative_exception"
    assert settlement["cost_basis"] == "authoritative_exception"
    assert settlement["input_tokens"] == 10


def test_skip_existing_requires_cost_ledger_evidence(tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    rec = RunRecord(
        run_id="reference__T1__r01",
        task_id="T1",
        system_id="reference",
        system_label="Reference",
        run_number=1,
        ok=True,
        api_cost_usd=0.01,
    )
    rec.save(str(out_dir / "reference__T1__r01.json"))
    with pytest.raises(ValueError, match="absent from cost ledger"):
        run_matrix(
            ReferenceSystem(),
            [Task("T1", "x")],
            n_runs=1,
            ledger=RunLedger(str(tmp_path / "ledger.jsonl")),
            output_dir=str(out_dir),
            verbose=False,
            skip_existing=True,
            cost_ledger=CampaignCostLedger(str(tmp_path / "cost.jsonl"), 1.0),
        )
