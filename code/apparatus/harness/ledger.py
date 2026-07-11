"""
Append-only run ledger for the MANDATE evaluation harness (Workstream B1).

The ledger is a JSONL file: one RunRecord per line. It is the canonical
index of every system execution in the study. Per-run output JSON files are
written separately into the 07_system_outputs tree by the runner.

The ledger is append-only on purpose. Once a run is recorded it is not
rewritten; corrections are handled by re-running and by the deviation log,
never by editing history. This mirrors the freeze discipline in PROTOCOL_LOCK.
"""
from __future__ import annotations

import json
import os

from .records import RunRecord


class RunLedger:
    def __init__(self, path: str):
        self.path = path
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)
        if not os.path.exists(path):
            open(path, "a").close()

    def append(self, record: RunRecord) -> None:
        with open(self.path, "a") as f:
            f.write(json.dumps(record.to_dict(), default=str) + "\n")

    def __iter__(self):
        with open(self.path) as f:
            for line in f:
                line = line.strip()
                if line:
                    yield RunRecord.from_dict(json.loads(line))

    def count(self) -> int:
        return sum(1 for _ in self)

    @staticmethod
    def load(path: str) -> list:
        return list(RunLedger(path))
