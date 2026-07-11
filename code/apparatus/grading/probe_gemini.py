"""
Pre-flight Gemini health probe.

Run before a HANDOFF_13f re-fire to check whether the provider's
high-demand window has cleared. Makes N minimal calls spaced T seconds
apart; exits 0 only if ALL probes succeed. The point is to spend a few
cents on a probe rather than 8 minutes on a relaunch that hits the same
503 wall.

Usage:
    python3 -m apparatus.grading.probe_gemini
    python3 -m apparatus.grading.probe_gemini --probes 5 --interval 60

Exit codes:
    0  all probes succeeded — safe to re-fire HANDOFF_13f
    1  at least one probe failed with a retryable error (5xx, 429,
       high demand, timeout) — wait longer
    2  non-retryable error (auth, missing key, bad request) — fix that
       before re-firing
    3  bad arguments / config

The probe uses the exact same `GeminiClient` and model that the Phase 8
grader uses, so success here is a credible signal that the grader will
succeed too.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path


def _load_env(env_path: Path) -> None:
    """Minimal .env loader; mirrors what the grader pipeline does."""
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def _classify_error(exc: BaseException) -> str:
    """retryable | non_retryable based on the apparatus's own heuristic."""
    from apparatus.grading.judge import _is_retryable_error
    return "retryable" if _is_retryable_error(exc) else "non_retryable"


def probe_once(model: str, max_tokens: int) -> tuple:
    """One probe call. Returns (ok: bool, classification: str, msg: str)."""
    from apparatus.baselines.llm_client import GeminiClient
    try:
        client = GeminiClient(os.environ["GOOGLE_API_KEY"])
    except KeyError:
        return False, "non_retryable", "GOOGLE_API_KEY not set in environment"

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
        return False, "retryable", (
            "empty response from Gemini "
            "(thinking-mode budget may have consumed all output tokens)")
    return True, "ok", f"reply: {text[:60]}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--probes", type=int, default=3,
                    help="Number of consecutive probes that must all "
                         "succeed (default: 3).")
    ap.add_argument("--interval", type=float, default=30.0,
                    help="Seconds between probes (default: 30).")
    ap.add_argument("--model", default="gemini-2.5-pro",
                    help="Gemini model (default: gemini-2.5-pro, the "
                         "Phase 8 judge model).")
    ap.add_argument("--max-tokens", type=int, default=8192,
                    help="Max tokens (default: 8192, same as the Phase 8 "
                         "Gemini judge to surface the thinking-budget "
                         "failure mode).")
    ap.add_argument("--env", type=Path, default=Path(".env"),
                    help="Path to .env (default: ./.env).")
    args = ap.parse_args()

    if args.probes < 1:
        print("ERROR: --probes must be >= 1", file=sys.stderr)
        return 3
    if args.interval < 0:
        print("ERROR: --interval must be >= 0", file=sys.stderr)
        return 3

    _load_env(args.env)
    if not os.environ.get("GOOGLE_API_KEY", "").strip():
        print("HALT: GOOGLE_API_KEY missing from environment "
              f"(checked {args.env})", file=sys.stderr)
        return 2

    print(f"Gemini health probe: model={args.model}, "
          f"probes={args.probes}, interval={args.interval}s, "
          f"max_tokens={args.max_tokens}")

    n_ok = 0
    saw_non_retryable = False
    for i in range(1, args.probes + 1):
        if i > 1:
            time.sleep(args.interval)
        t0 = time.time()
        ok, cls, msg = probe_once(args.model, args.max_tokens)
        dt = time.time() - t0
        status = "OK" if ok else cls.upper()
        print(f"  probe {i}/{args.probes} [{status:14s}] ({dt:.1f}s) "
              f"{msg}")
        if ok:
            n_ok += 1
        elif cls == "non_retryable":
            saw_non_retryable = True
            break

    print()
    print(f"Result: {n_ok}/{args.probes} probes succeeded")
    if n_ok == args.probes:
        print("DECISION: SAFE TO RE-FIRE HANDOFF_13f")
        return 0
    if saw_non_retryable:
        print("DECISION: HALT — non-retryable Gemini error; do not re-fire")
        return 2
    print("DECISION: WAIT — provider still degraded; re-run this probe in "
          "30-60 minutes")
    return 1


if __name__ == "__main__":
    sys.exit(main())
