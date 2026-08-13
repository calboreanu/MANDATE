"""Pre-flight Anthropic health probe.

Run before Cond-A or Cond-B launches to check whether an overloaded/5xx window
has cleared. The probe spends pennies on minimal calls instead of launching
pilot records into a known-bad provider window.
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
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _classify_error(exc: BaseException) -> str:
    from apparatus.llm_retry import is_retryable_error

    return "retryable" if is_retryable_error(exc) else "non_retryable"


def probe_once(model: str, max_tokens: int) -> tuple[bool, str, str]:
    """One probe call. Returns ``(ok, classification, message)``."""
    from apparatus.baselines.llm_client import AnthropicClient

    try:
        client = AnthropicClient(os.environ["ANTHROPIC_API_KEY"])
    except KeyError:
        return False, "non_retryable", "ANTHROPIC_API_KEY not set"

    try:
        resp = client.generate(
            system="You are a health probe. Reply with exactly: OK",
            user="Reply with the two letters OK and nothing else.",
            model=model,
            temperature=0.0,
            max_tokens=max_tokens,
        )
    except Exception as exc:
        cls = _classify_error(exc)
        return False, cls, f"{type(exc).__name__}: {str(exc)[:200]}"

    text = (resp.text or "").strip()
    if not text:
        return False, "retryable", "empty response from Anthropic"
    return True, "ok", f"reply: {text[:60]}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probes", type=int, default=3)
    parser.add_argument("--interval", type=float, default=30.0)
    parser.add_argument("--model", default="claude-sonnet-4-6")
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--env", type=Path, default=Path(".env"))
    args = parser.parse_args()

    if args.probes < 1:
        print("ERROR: --probes must be >= 1", file=sys.stderr)
        return 3
    if args.interval < 0:
        print("ERROR: --interval must be >= 0", file=sys.stderr)
        return 3

    _load_env(args.env)
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        print("HALT: ANTHROPIC_API_KEY missing", file=sys.stderr)
        return 2

    print(
        f"Anthropic health probe: model={args.model}, "
        f"probes={args.probes}, interval={args.interval}s"
    )
    ok_count = 0
    saw_non_retryable = False
    for i in range(1, args.probes + 1):
        if i > 1:
            time.sleep(args.interval)
        t0 = time.time()
        ok, cls, msg = probe_once(args.model, args.max_tokens)
        elapsed = time.time() - t0
        status = "OK" if ok else cls.upper()
        print(f"  probe {i}/{args.probes} [{status:14s}] ({elapsed:.1f}s) {msg}")
        if ok:
            ok_count += 1
        elif cls == "non_retryable":
            saw_non_retryable = True
            break

    print(f"\nResult: {ok_count}/{args.probes} probes succeeded")
    if ok_count == args.probes:
        print("DECISION: SAFE TO RE-FIRE Stage 2b")
        return 0
    if saw_non_retryable:
        print("DECISION: HALT - non-retryable Anthropic error")
        return 2
    print("DECISION: WAIT - provider still degraded; re-run in 30-60 min")
    return 1


if __name__ == "__main__":
    sys.exit(main())
