# Codex Handoff 19c: Retry-layer extraction + extractor / Cond-B retry wiring + Anthropic probe utility

**For:** Codex (eval host)
**From:** Lead Analyst
**Date:** 2026-06-23 (late afternoon)
**Supersedes for Stage 2 only:** HANDOFF_19b's Stage 2b execution step. Stages 1, 3, 4, 5 from HANDOFF_19 remain unchanged. HANDOFF_19b's apparatus patches (Cond-A extractor prompt + Cond-B constraint-gap wrapper, commit `a810a699`) are PRESERVED — this handoff adds retry/backoff resilience around them, it does not redo them.
**Authoritative input docs:**
- `handoffs/HANDOFF_19b_stage2_report_2026-06-23.md` (the live-pilot HALT on Anthropic 4×529 + 1×500)
- `apparatus/grading/judge.py` (canonical retry/backoff implementation we're extracting from)
- `apparatus/grading/probe_gemini.py` (the parallel probe pattern from HANDOFF_13f)

**Estimated wall clock:** Stage 2c work-and-retry is ~30-60 minutes after the patches land, provider permitting.
**Estimated API cost:** ~$1.50 for the revised pilots.

---

## Why this exists — and why we're hardening before re-firing

HANDOFF_19b's apparatus patches landed correctly and verified clean (18 focused tests, 283 full suite, 1 skipped). The Stage 2b live pilot did not produce evidence because Anthropic returned 4×`529 overloaded_error` and 1×`500 api_error` across the five Cond-A pilot tasks. No Cond-A artifacts written; Cond-B not attempted to avoid further spend during the provider window.

The HALT was correct (we should not run pilots into a known-bad provider window). But the underlying problem is that the v2 apparatus has a known robustness gap: the retry/backoff machinery we built in HANDOFF_13f for the grading judges does not exist in the v2 extractor or Cond-B wrapper paths. The judge ensemble retries `_RETRYABLE_PATTERNS` (which includes `r"overloaded"` — so Anthropic 529 would be caught), but the Stage 2 extractor calls `AnthropicClient.generate()` directly and the Cond-B wrapper passes through canonical MANDATE's adapter — neither has the retry layer.

This handoff closes that gap. It does NOT take the shortcut of "wait it out and retry; if it fails again, retry again." Per PI directive: no shortcuts; keep patching. Specifically:

1. **Extract** the retry helper from `apparatus/grading/judge.py` to a shared module `apparatus/llm_retry.py` so it has a single canonical home.
2. **Refactor** `judge.py` to import from the new module. Existing 27 grading tests still pass (no behavior change).
3. **Wire** the retry helper into `apparatus/preprocess/extract_mission_input.py` so the Cond-A extractor survives transient 5xx/529.
4. **Wire** the retry helper into `apparatus/systems/mandate_canonical.py` via a `RetryingLLMClient` decorator that wraps the LLM adapter the Cond-B wrapper passes to canonical Pipeline. Each adapter call gets retry/backoff; the pipeline itself is unaware.
5. **Build** `apparatus/probe_anthropic.py` as a pre-flight gate (parallel to `apparatus/grading/probe_gemini.py`). Codex pings it before each live pilot launch.
6. **Add** at least 6 regression tests covering the new module and the two new wirings.
7. **Re-fire Stage 2b** behind the probe, with retry hardening in place.

When this lands, Stages 3-5 (full 1500-record runs + grading) inherit the resilience automatically.

---

## Patch 1 — Extract retry helper to `apparatus/llm_retry.py`

**New file:** `apparatus/llm_retry.py`

```python
"""Shared LLM retry/backoff helper.

Extracted from apparatus/grading/judge.py (HANDOFF_13f patch) so the same
retry pattern can be reused by:
  - apparatus/grading/judge.py        (existing — refactored to import)
  - apparatus/preprocess/extract_mission_input.py  (new wiring)
  - apparatus/systems/mandate_canonical.py         (new wiring via decorator)

The retry layer pattern-matches against rendered exception text rather than
provider-specific exception types, so it works uniformly across Anthropic,
OpenAI, Google, Ollama, and any future adapter.

Per HANDOFF_19b 2026-06-23 halt: Anthropic 529 `overloaded_error` matches
the `r"overloaded"` pattern below. The bug was that the extractor/Cond-B
paths bypassed the retry layer entirely; this module is the consolidation.
"""
from __future__ import annotations

import re
import time
from typing import Any, Callable, Sequence

# Default retry/backoff schedule for transient provider errors.
# Format: seconds to sleep BEFORE each retry attempt. Length = max retries.
# Worst-case backoff latency: 5 + 15 + 45 = 65 seconds.
DEFAULT_RETRY_BACKOFF_SEC: tuple = (5.0, 15.0, 45.0)

# Patterns in exception text that mark a call as retryable.
RETRYABLE_PATTERNS = (
    r"\b500\b",
    r"\b502\b",
    r"\b503\b",
    r"\b504\b",
    r"\b429\b",
    r"\b529\b",
    r"UNAVAILABLE",
    r"high demand",
    r"overloaded",
    r"rate.?limit",
    r"too many requests",
    r"timeout",
    r"timed out",
    r"connection reset",
    r"connection refused",
    r"temporarily",
    r"api_error",        # Anthropic 500 wrapper
    r"server_error",
    r"service.?unavailable",
)
_RETRYABLE_RE = re.compile("|".join(RETRYABLE_PATTERNS), re.IGNORECASE)


def is_retryable_error(exc: BaseException) -> bool:
    """True if the exception's rendered text matches a retryable pattern.

    Provider-agnostic. Each SDK raises its own hierarchy
    (anthropic.APIStatusError, google.genai.errors.ServerError,
    openai.RateLimitError); we render the exception and pattern-match.
    """
    s = "%r %s" % (exc, exc)
    return bool(_RETRYABLE_RE.search(s))


def call_with_retry(
    fn: Callable[..., Any],
    *args,
    retry_backoff_sec: Sequence[float] = DEFAULT_RETRY_BACKOFF_SEC,
    sleep_fn: Callable[[float], None] = time.sleep,
    **kwargs,
) -> Any:
    """Call `fn(*args, **kwargs)` with retry+backoff on transient errors.

    Returns fn's result on success. Re-raises the LAST exception on retry
    exhaustion, or the first non-retryable exception immediately.

    Tests can pass `retry_backoff_sec=(0.0, 0.0, 0.0)` and a no-op `sleep_fn`
    to skip real sleeping.
    """
    attempts = 1 + len(retry_backoff_sec)
    last_exc: BaseException | None = None
    for i in range(attempts):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_exc = e
            if i >= len(retry_backoff_sec):
                raise
            if not is_retryable_error(e):
                raise
            sleep_fn(retry_backoff_sec[i])
    if last_exc is not None:  # pragma: no cover (unreachable)
        raise last_exc


class RetryingLLMClient:
    """Decorator wrapping any LLM client / adapter so every .generate() call
    gets retry+backoff on transient errors.

    Works with mlt.sdk.llm.LLMAdapter, apparatus.baselines.llm_client clients,
    or any object exposing a `.generate(**kwargs)` method that may raise
    provider exceptions.

    Used by:
      - apparatus/systems/mandate_canonical.py to wrap the llm_adapter
        passed to canonical MLT Pipeline. The pipeline calls
        adapter.generate(...) inside each role; the decorator makes those
        calls resilient without modifying canonical MLT.
    """
    def __init__(self, inner,
                 retry_backoff_sec: Sequence[float] = DEFAULT_RETRY_BACKOFF_SEC,
                 sleep_fn: Callable[[float], None] = time.sleep):
        self._inner = inner
        self._retry_backoff_sec = tuple(retry_backoff_sec)
        self._sleep = sleep_fn

    def __getattr__(self, name):
        # Pass-through for any attribute we don't override.
        return getattr(self._inner, name)

    def generate(self, *args, **kwargs):
        return call_with_retry(
            self._inner.generate, *args,
            retry_backoff_sec=self._retry_backoff_sec,
            sleep_fn=self._sleep,
            **kwargs,
        )
```

---

## Patch 2 — Refactor `apparatus/grading/judge.py` to import from the new module

In `apparatus/grading/judge.py`:

**Remove:**
- The `_DEFAULT_RETRY_BACKOFF_SEC` constant (now `DEFAULT_RETRY_BACKOFF_SEC` in `llm_retry`)
- The `_RETRYABLE_PATTERNS` tuple
- The `_RETRYABLE_RE` regex
- The `_is_retryable_error()` function

**Add at top:**
```python
from ..llm_retry import (
    DEFAULT_RETRY_BACKOFF_SEC as _DEFAULT_RETRY_BACKOFF_SEC,
    is_retryable_error as _is_retryable_error,
    call_with_retry as _call_with_retry_shared,
)
```

**Modify `Judge._call_with_retry` method** to delegate to the shared helper:
```python
def _call_with_retry(self, *, system: str, user: str, max_tokens: int):
    return _call_with_retry_shared(
        self.client.generate,
        system=system, user=user, model=self.model,
        temperature=0.0, max_tokens=max_tokens,
        retry_backoff_sec=self.retry_backoff_sec,
        sleep_fn=self._sleep,
    )
```

**Existing tests must still pass.** Run after refactor:
```zsh
.venv/bin/python -m pytest apparatus/grading/tests/test_grading.py -q
# Expected: 27 passed (unchanged from HANDOFF_13f)
```

Also re-export the underscore-prefixed names from `judge.py` so the existing test
`test_judge_retries_on_transient_5xx_then_succeeds` (which references
`apparatus.grading.judge._is_retryable_error`) keeps working:

```python
# At top of judge.py, after the import, add:
__all__ = [..., "_is_retryable_error", "_DEFAULT_RETRY_BACKOFF_SEC"]
```

---

## Patch 3 — Wire retry into `apparatus/preprocess/extract_mission_input.py`

This is the Cond-A extractor. Currently calls `AnthropicClient.generate()` once with no retry.

**Replace the body of `extract()` that calls the client** with the retried version:

```python
from ..llm_retry import call_with_retry, DEFAULT_RETRY_BACKOFF_SEC

def extract(task_id: str, task_text: str,
            model: str = "claude-sonnet-4-6",
            retry_backoff_sec=DEFAULT_RETRY_BACKOFF_SEC) -> MissionInput:
    """Run the extraction LLM and return a structured MissionInput.

    The LLM call is wrapped with retry+backoff for transient provider
    errors (5xx, 529 overloaded, 429 rate limits). Per HANDOFF_19b 2026-06-23
    halt: Anthropic 529 windows broke 5/5 pilot records when the call was
    unwrapped.
    """
    client = AnthropicClient()
    prompt = EXTRACTION_PROMPT.replace("{task_text}", task_text)

    resp = call_with_retry(
        client.generate,
        system="You are a senior systems analyst extracting structured "
               "specifications from operational tasks.",
        user=prompt,
        model=model,
        temperature=0.0,
        max_tokens=4096,
        retry_backoff_sec=retry_backoff_sec,
    )

    # ... rest of extract() unchanged (parsing, constraint validation, etc.)
```

The `retry_backoff_sec` kwarg is exposed so tests can pass `(0.0, 0.0, 0.0)`
for fast-running unit tests.

---

## Patch 4 — Wire retry into `apparatus/systems/mandate_canonical.py` via `RetryingLLMClient`

This is the Cond-B path. The canonical MLT Pipeline calls the LLM adapter inside each role via `adapter.generate(...)`. We don't modify canonical MLT; we wrap the adapter before passing it in:

```python
from ..llm_retry import RetryingLLMClient, DEFAULT_RETRY_BACKOFF_SEC

def run_cond_b(task_id: str, task_text: str, llm_adapter,
               seed: int = 20260623,
               retry_backoff_sec=DEFAULT_RETRY_BACKOFF_SEC) -> dict:
    """Cond-B: canonical MLT MANDATE with LLM-augmented Interpreter end-to-end.

    The llm_adapter is wrapped with RetryingLLMClient so every internal
    .generate() call in canonical MLT roles inherits retry+backoff on
    transient provider errors. The wrapper is transparent to canonical MLT;
    it passes through every attribute access via __getattr__ and only
    overrides .generate().
    """
    # Wrap the adapter so every LLM call gets retry+backoff.
    resilient_adapter = RetryingLLMClient(
        llm_adapter,
        retry_backoff_sec=retry_backoff_sec,
    )

    # ... existing wrapper logic from HANDOFF_19b that builds MissionInput,
    # validates constraints, routes invalid ones to gap_reports, and runs
    # the canonical Pipeline — but pass `resilient_adapter` instead of the
    # raw adapter into both the Intake LLM call and PipelineConfig:

    config = PipelineConfig(
        strict=False,
        llm_adapter=resilient_adapter,
        enable_llm_interpreter=True,
    )
    # ... rest unchanged ...
```

Important: the constraint-validation wrapper logic from HANDOFF_19b stays.
The retry layer is added BENEATH that — it catches transient provider errors
on individual LLM calls; the wrapper still routes invalid-grammar constraint
emissions to `output.gap_reports`. The two patches are orthogonal.

---

## Patch 5 — Build `apparatus/probe_anthropic.py`

Parallel to `apparatus/grading/probe_gemini.py`. New file:

```python
"""Pre-flight Anthropic health probe.

Run before a Cond-A or Cond-B re-fire to check whether Anthropic's
overloaded/5xx window has cleared. Makes N minimal calls spaced T seconds
apart; exits 0 only if ALL probes succeed. The point is to spend pennies on
a probe rather than minutes/dollars on a relaunch that hits the same wall.

Usage:
    .venv/bin/python -m apparatus.probe_anthropic
    .venv/bin/python -m apparatus.probe_anthropic --probes 5 --interval 60

Exit codes:
    0  all probes succeeded — safe to re-fire Stage 2b
    1  at least one probe failed with a retryable error (529, 5xx, 429,
       overloaded, timeout) — wait longer
    2  non-retryable error (auth, missing key, bad request) — fix that
       before re-firing
    3  bad arguments / config

The probe uses the exact same AnthropicClient and model (default
claude-sonnet-4-6) that the Cond-A extractor and Cond-B wrapper use, so
success here is a credible signal the live pilots will succeed too.
"""
from __future__ import annotations
import argparse
import os
import sys
import time
from pathlib import Path


def _load_env(env_path: Path) -> None:
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def _classify_error(exc: BaseException) -> str:
    from apparatus.llm_retry import is_retryable_error
    return "retryable" if is_retryable_error(exc) else "non_retryable"


def probe_once(model: str, max_tokens: int) -> tuple:
    """One probe call. Returns (ok: bool, classification: str, msg: str)."""
    from apparatus.baselines.llm_client import AnthropicClient
    try:
        client = AnthropicClient(os.environ["ANTHROPIC_API_KEY"])
    except KeyError:
        return False, "non_retryable", "ANTHROPIC_API_KEY not set"
    try:
        resp = client.generate(
            system="You are a health probe. Reply with exactly: OK",
            user="Reply with the two letters OK and nothing else.",
            model=model, temperature=0.0, max_tokens=max_tokens)
    except Exception as e:
        cls = _classify_error(e)
        return False, cls, f"{type(e).__name__}: {str(e)[:200]}"
    text = (resp.text or "").strip()
    if not text:
        return False, "retryable", "empty response from Anthropic"
    return True, "ok", f"reply: {text[:60]}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--probes", type=int, default=3)
    ap.add_argument("--interval", type=float, default=30.0)
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--max-tokens", type=int, default=128)
    ap.add_argument("--env", type=Path, default=Path(".env"))
    args = ap.parse_args()

    if args.probes < 1:
        print("ERROR: --probes must be >= 1", file=sys.stderr); return 3
    if args.interval < 0:
        print("ERROR: --interval must be >= 0", file=sys.stderr); return 3

    _load_env(args.env)
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        print("HALT: ANTHROPIC_API_KEY missing", file=sys.stderr); return 2

    print(f"Anthropic health probe: model={args.model}, "
          f"probes={args.probes}, interval={args.interval}s")
    n_ok = 0
    saw_non_retryable = False
    for i in range(1, args.probes + 1):
        if i > 1:
            time.sleep(args.interval)
        t0 = time.time()
        ok, cls, msg = probe_once(args.model, args.max_tokens)
        dt = time.time() - t0
        status = "OK" if ok else cls.upper()
        print(f"  probe {i}/{args.probes} [{status:14s}] ({dt:.1f}s) {msg}")
        if ok:
            n_ok += 1
        elif cls == "non_retryable":
            saw_non_retryable = True
            break

    print(f"\nResult: {n_ok}/{args.probes} probes succeeded")
    if n_ok == args.probes:
        print("DECISION: SAFE TO RE-FIRE Stage 2b"); return 0
    if saw_non_retryable:
        print("DECISION: HALT — non-retryable Anthropic error"); return 2
    print("DECISION: WAIT — provider still degraded; re-run in 30-60 min")
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

---

## Patch 6 — Regression tests

**New file:** `apparatus/tests/test_llm_retry.py`

```python
"""Tests for the shared retry/backoff helper."""
import pytest
from apparatus.llm_retry import (
    DEFAULT_RETRY_BACKOFF_SEC, is_retryable_error,
    call_with_retry, RetryingLLMClient,
)


def test_anthropic_529_overloaded_is_retryable():
    assert is_retryable_error(RuntimeError("529 overloaded_error"))
    assert is_retryable_error(RuntimeError("anthropic.APIStatusError: 529"))

def test_anthropic_500_api_error_is_retryable():
    assert is_retryable_error(RuntimeError("500 api_error"))

def test_google_503_unavailable_is_retryable():
    assert is_retryable_error(RuntimeError("503 UNAVAILABLE: high demand"))

def test_openai_429_rate_limit_is_retryable():
    assert is_retryable_error(RuntimeError("429 Too Many Requests"))

def test_401_auth_is_not_retryable():
    assert not is_retryable_error(RuntimeError("401 invalid API key"))

def test_400_bad_request_is_not_retryable():
    assert not is_retryable_error(RuntimeError("400 bad_request"))

def test_call_with_retry_succeeds_after_two_retries():
    calls = []
    sleeps = []
    def fn():
        calls.append(1)
        if len(calls) <= 2:
            raise RuntimeError("529 overloaded_error")
        return "OK"
    result = call_with_retry(fn,
                              retry_backoff_sec=(0.0, 0.0, 0.0),
                              sleep_fn=sleeps.append)
    assert result == "OK"
    assert len(calls) == 3
    assert len(sleeps) == 2

def test_call_with_retry_exhausts_on_persistent_failure():
    def fn():
        raise RuntimeError("529 overloaded_error")
    with pytest.raises(RuntimeError, match="529"):
        call_with_retry(fn,
                        retry_backoff_sec=(0.0, 0.0, 0.0),
                        sleep_fn=lambda _: None)

def test_call_with_retry_no_retry_on_non_retryable():
    calls = []
    def fn():
        calls.append(1)
        raise RuntimeError("401 invalid API key")
    with pytest.raises(RuntimeError, match="401"):
        call_with_retry(fn,
                        retry_backoff_sec=(0.0, 0.0, 0.0),
                        sleep_fn=lambda _: None)
    assert len(calls) == 1  # no retry on auth error

def test_retrying_llm_client_wraps_generate():
    class FakeClient:
        def __init__(self):
            self.calls = []
        def generate(self, **kw):
            self.calls.append(kw)
            if len(self.calls) <= 1:
                raise RuntimeError("529 overloaded_error")
            return "OK"
    inner = FakeClient()
    wrapped = RetryingLLMClient(inner,
                                 retry_backoff_sec=(0.0, 0.0, 0.0),
                                 sleep_fn=lambda _: None)
    result = wrapped.generate(prompt="x")
    assert result == "OK"
    assert len(inner.calls) == 2

def test_retrying_llm_client_passes_through_other_attrs():
    class FakeClient:
        provider = "anthropic"
        def generate(self, **kw):
            return "OK"
    wrapped = RetryingLLMClient(FakeClient())
    assert wrapped.provider == "anthropic"  # pass-through
```

**Add tests to:** `apparatus/preprocess/tests/test_extract_mission_input.py` (or
wherever the Cond-A extractor tests live):

```python
def test_extractor_retries_on_anthropic_overload(monkeypatch):
    """Anthropic 529 in the middle of extraction should be retried; the
    extractor should ultimately return a valid MissionInput."""
    # Mock AnthropicClient.generate to fail twice then succeed
    # Assert valid MissionInput returned
    ...
```

**Add tests to:** `apparatus/systems/tests/test_mandate_canonical.py`:

```python
def test_cond_b_wrapper_uses_retrying_llm_client(monkeypatch):
    """The Cond-B wrapper should wrap the passed adapter with
    RetryingLLMClient before passing to canonical Pipeline."""
    ...
```

After all patches: run the full test suite.

```zsh
.venv/bin/python -m pytest apparatus/ -q
# Expected: 283 + ~10 new = ~293 passed
```

---

## Stage 2c execution: probe-gated retry

```zsh
cd "$HOME/Desktop/Desktop - lattice-ws01/MANDATE Evaluation/mandate_eval_2026Q2"

# Quarantine Stage 2b attempt artifacts
mkdir -p 07_system_outputs/cond_a/_stage2b_failed_provider
mv 07_system_outputs/cond_a/cond_a__*.json \
   07_system_outputs/cond_a/_stage2b_failed_provider/ 2>/dev/null
mv 07_system_outputs/cond_a/ledger.jsonl \
   07_system_outputs/cond_a/_stage2b_failed_provider/ 2>/dev/null

# Gate 1: Anthropic probe
.venv/bin/python -m apparatus.probe_anthropic || {
  echo "Anthropic probe failed; wait and retry the probe before launching pilots"
  exit 1
}

# Gate 2: Cond-A revised pilot (already retry-hardened)
.venv/bin/python -m apparatus.run run-cond-a \
  TASK-MAIN-INT-034 TASK-MAIN-FIN-001 TASK-MAIN-FIN-018 \
  TASK-MAIN-INT-003 TASK-MAIN-SEC-014 \
  --out 07_system_outputs/cond_a \
  --extraction-model claude-sonnet-4-6 \
  2> >(tee logs/HANDOFF_19c_cond_a_stage2c.stderr >&2)

# Gate 3: Cond-B revised pilot (already retry-hardened via RetryingLLMClient)
.venv/bin/python -m apparatus.run run-cond-b \
  TASK-MAIN-INT-034 TASK-MAIN-FIN-001 TASK-MAIN-FIN-018 \
  TASK-MAIN-INT-003 TASK-MAIN-SEC-014 \
  --out 07_system_outputs/cond_b \
  --llm-backend anthropic \
  --llm-model claude-sonnet-4-6 \
  2> >(tee logs/HANDOFF_19c_cond_b_stage2c.stderr >&2)
```

**Stage 2c success criteria** are the HANDOFF_19b revised criteria, unchanged:
- Cond-A: 5/5 ok, ≥3 canonical-grammar constraints in 4/5, COA differentiation in ≥3 records, schema-valid.
- Cond-B: 5/5 ok via wrapper, extraction_failed_constraints < 25 across 5 records, schema-valid, gap_reports populated.

If both pass → write Stage 2c report → proceed to Stage 3.
If either halts → preserve artifacts in `_stage2c_attempt_<N>/`, write 2c report with diagnosis, draft HANDOFF_19d targeted at whatever surfaced. Keep iterating.

---

## Stage 2c report template

`handoffs/HANDOFF_19c_stage2_report_2026-06-23.md`:

- Patch landing confirmation (commit hash)
- Test results (focused + full)
- Anthropic probe result: probes succeeded count, decision
- Cond-A pilot table (5 rows, columns: task_id, ok, valid_constraints, failed_grammar, n_coas, first_coa_approach, schema_valid)
- Cond-B pilot table (5 rows, columns: task_id, ok, valid_constraints, extraction_gaps, n_coas, schema_valid)
- Verdict: PROCEED to Stage 3, or HALT to Stage 2d
- Any retry-layer observations: how many retries fired during the pilots (useful diagnostic — log via stderr from the retry helper if needed)

Commit message:
```
HANDOFF_19c: retry-layer extraction to apparatus/llm_retry.py with RetryingLLMClient decorator; wired into Cond-A extractor and Cond-B wrapper to harden against Anthropic 529/500 transients (HANDOFF_19b Stage 2b halt). Built apparatus/probe_anthropic.py parallel to probe_gemini.py for pre-flight gating. judge.py refactored to import from shared module; existing 27 grading tests still pass; ~10 new tests added. Stage 2c pilot ready.
```

---

## What this unblocks

After Stage 2c PROCEED:
- Stage 3 full Cond-A + Cond-B runs (HANDOFF_19 §3, unchanged) inherit the retry/backoff resilience automatically. The 8-10 hour wall clocks won't get derailed by a 30-second provider blip.
- The retry layer also covers the v1 grading judges (already in place from HANDOFF_13f) — Stages 3 and 4 are now uniformly hardened.

## Multi-iteration discipline reminder

Per PI directive 2026-06-23: keep patching, don't quit on MANDATE. If Stage 2c surfaces another design-mismatch or transient issue, we write HANDOFF_19d with whatever the targeted fix is and iterate. The point is to ship a canonical-MANDATE evaluation that does what it claims to do, however many iterations it takes to converge.

The empirical work IS the work.
