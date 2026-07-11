import json
import os
import sys
import threading
import time
from types import SimpleNamespace

# Make the project root importable regardless of pytest's working directory.
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from apparatus.harness.records import OUTPUT_MANDATE_AS_CODE, RunRecord
from apparatus.run import build_parser, cmd_run_cond_a, cmd_run_cond_b


def _write_tasks(path, n=4):
    with open(path, "w") as f:
        for i in range(n):
            f.write(json.dumps({
                "task_id": f"TASK-{i:03d}",
                "request_text": f"task text {i}",
            }) + "\n")


class _ConcurrencyProbe:
    def __init__(self):
        self.active = 0
        self.max_seen = 0
        self.calls = 0
        self.lock = threading.Lock()

    def run_once(self, *, run_id, task_id, run_number, seed):
        with self.lock:
            self.active += 1
            self.calls += 1
            self.max_seen = max(self.max_seen, self.active)
        time.sleep(0.15)
        with self.lock:
            self.active -= 1
        return RunRecord(
            run_id=run_id,
            task_id=task_id,
            system_id=run_id.split("__", 1)[0],
            system_label="fake condition system",
            run_number=run_number,
            seed=seed,
            wall_clock_ms=150.0,
            api_cost_usd=0.0,
            output_type=OUTPUT_MANDATE_AS_CODE,
            output={"artifact": {"mandate_id": task_id}, "gap_reports": []},
            ok=True,
        )


def test_run_cond_a_honors_max_workers(monkeypatch, tmp_path):
    """A fake slow Cond-A system should execute concurrently when
    --max-workers > 1, proving the CLI flag is honored by the run loop."""
    import apparatus.systems.mandate_canonical as canonical

    tasks_path = tmp_path / "tasks.jsonl"
    out_dir = tmp_path / "out"
    _write_tasks(tasks_path, n=4)
    probe = _ConcurrencyProbe()

    class FakeCondASystem:
        system_id = "cond_a"
        system_label = "fake Cond-A"

        def __init__(self, extraction_model="fake",
                     domain_profile_mode="default"):
            self.extraction_model = extraction_model
            self.domain_profile_mode = domain_profile_mode

        def run(self, request_text, *, run_id, task_id, run_number, seed=None):
            return probe.run_once(run_id=run_id, task_id=task_id,
                                  run_number=run_number, seed=seed)

    monkeypatch.setattr(canonical, "CondASystem", FakeCondASystem)
    args = SimpleNamespace(
        task_ids=[],
        all=True,
        tasks=str(tasks_path),
        out=str(out_dir),
        extraction_model="fake",
        runs_per_task=1,
        seed=20260623,
        skip_existing=False,
        checkpoint_every=0,
        max_workers=4,
        quiet=True,
    )

    assert cmd_run_cond_a(args) == 0
    assert probe.calls == 4
    assert probe.max_seen > 1
    assert len(list(out_dir.glob("cond_a__*.json"))) == 4


def test_run_cond_b_honors_max_workers(monkeypatch, tmp_path):
    """Cond-B uses the same parallel checkpointing path as Cond-A."""
    import apparatus.systems.mandate_canonical as canonical

    tasks_path = tmp_path / "tasks.jsonl"
    out_dir = tmp_path / "out"
    _write_tasks(tasks_path, n=4)
    probe = _ConcurrencyProbe()

    class FakeCondBSystem:
        system_id = "cond_b"
        system_label = "fake Cond-B"

        def __init__(self, llm_backend="anthropic", llm_model="fake",
                     domain_profile_mode="default"):
            self.llm_backend = llm_backend
            self.llm_model = llm_model
            self.domain_profile_mode = domain_profile_mode

        def run(self, request_text, *, run_id, task_id, run_number, seed=None):
            return probe.run_once(run_id=run_id, task_id=task_id,
                                  run_number=run_number, seed=seed)

    monkeypatch.setattr(canonical, "CondBSystem", FakeCondBSystem)
    args = SimpleNamespace(
        task_ids=[],
        all=True,
        tasks=str(tasks_path),
        out=str(out_dir),
        llm_backend="anthropic",
        llm_model="fake",
        runs_per_task=1,
        seed=20260623,
        skip_existing=False,
        checkpoint_every=0,
        max_workers=4,
        quiet=True,
    )

    assert cmd_run_cond_b(args) == 0
    assert probe.calls == 4
    assert probe.max_seen > 1
    assert len(list(out_dir.glob("cond_b__*.json"))) == 4


def test_run_cond_b_accepts_ollama_models_param():
    parser = build_parser()
    for model in ("qwen2.5:32b", "llama3.2:3b", "mistral:7b", "phi3:14b"):
        args = parser.parse_args([
            "run-cond-b",
            "TASK-X",
            "--llm-backend",
            "ollama",
            "--llm-model",
            model,
        ])
        assert args.llm_backend == "ollama"
        assert args.llm_model == model
