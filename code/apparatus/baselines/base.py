"""
BaselineSystem base class (Workstream B2).

All six baselines are harness System adapters. This base class handles the
parts every baseline shares: assembling the RunRecord, extracting JSON from
possibly-noisy model output, validating it against the baseline specification
schema, and capturing token usage and cost. Subclasses implement `_produce`,
the actual interaction with the model or framework.

Run-status semantics:
  rec.ok            True if the system ran without an infrastructure failure
                    (an API error or a crash). It is NOT a quality judgment.
  output.schema_valid  Whether the produced output parsed and validated
                    against the baseline schema. This is the O4 signal.
A baseline that returns prose instead of JSON has ok=True (it ran) and
schema_valid=False (it failed O4). Those are different things and the
analysis treats them differently.
"""
from __future__ import annotations

import abc
import json
import time
from dataclasses import dataclass, field
from typing import Optional

from ..harness.records import RoleTiming
from ..harness.system import System
from .schema import validate_specification


@dataclass
class Step:
    """One model call inside a baseline run."""
    name: str
    duration_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: Optional[float] = None


@dataclass
class ProduceResult:
    """What a baseline's `_produce` returns: the final text (expected to be
    the JSON specification) and one Step per model call."""
    text: str
    steps: list = field(default_factory=list)   # list[Step]


def extract_json(text: str):
    """Best-effort JSON-object extraction from model output.

    Handles markdown code fences and leading or trailing prose. Returns
    (obj, error): obj is the parsed dict, or None with an error string.
    """
    if not text or not text.strip():
        return None, "empty model output"
    s = text.strip()
    # strip a leading ```json / ``` fence and a trailing ```
    if s.startswith("```"):
        nl = s.find("\n")
        if nl != -1:
            s = s[nl + 1:]
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
    s = s.strip()
    # fast path
    try:
        return json.loads(s), None
    except Exception:
        pass
    # find the first balanced {...} block
    start = s.find("{")
    if start == -1:
        return None, "no JSON object found in model output"
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(s[start:i + 1]), None
                except Exception as e:
                    return None, "JSON parse error: %s" % e
    return None, "unbalanced JSON object in model output"


class BaselineSystem(System):
    """Base for B1-B6. Subclasses set system_id / system_label and implement
    `_produce`."""
    output_type = "BASELINE_SCHEMA:specification"

    def __init__(self, llm_client, model: str, system_id: str,
                 system_label: str):
        self.client = llm_client
        self.model = model
        self.system_id = system_id
        self.system_label = system_label

    def describe(self) -> dict:
        d = super().describe()
        d.update({"model": self.model,
                  "llm_provider": getattr(self.client, "provider", "")})
        return d

    @abc.abstractmethod
    def _produce(self, request_text: str) -> ProduceResult:
        """Run the baseline on one request. Return its final text and steps."""
        raise NotImplementedError

    def run(self, request_text, *, run_id, task_id, run_number, seed=None):
        rec = self._new_record(run_id=run_id, task_id=task_id,
                               run_number=run_number, seed=seed)
        rec.model_versions = {"model": self.model,
                              "provider": getattr(self.client, "provider", "")}
        rec.decoding_params = {"temperature": 0.0}

        t0 = time.time()
        try:
            result = self._produce(request_text)
        except Exception as e:
            rec.wall_clock_ms = (time.time() - t0) * 1000.0
            rec.ok = False
            rec.errors = ["baseline error: %r" % e]
            return rec
        rec.wall_clock_ms = (time.time() - t0) * 1000.0

        # token usage, cost, and per-step timings
        costs = [s.cost_usd for s in result.steps if s.cost_usd is not None]
        rec.api_cost_usd = round(sum(costs), 6) if costs else None
        rec.role_timings = [
            RoleTiming(role_name=s.name, status="success",
                       duration_ms=s.duration_ms, llm_used=True,
                       llm_fallback=False)
            for s in result.steps]
        rec.model_versions["total_input_tokens"] = sum(
            s.input_tokens for s in result.steps)
        rec.model_versions["total_output_tokens"] = sum(
            s.output_tokens for s in result.steps)

        # extract + validate the specification
        parsed, perr = extract_json(result.text)
        if parsed is not None:
            valid, verrs = validate_specification(parsed)
        else:
            valid, verrs = False, [perr or "no JSON produced"]
        rec.output = {
            "specification": parsed,
            "raw_text": result.text,
            "schema_valid": valid,
            "schema_errors": verrs,
        }
        # ok = the system ran. schema validity is a graded outcome (O4), not
        # a run failure, so it does not set ok=False.
        rec.ok = True
        return rec
