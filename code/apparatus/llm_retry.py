"""Shared LLM retry/backoff helper.

Extracted from apparatus.grading.judge so the same retry pattern can be reused
by grading, preprocessing, and canonical-MANDATE adapter paths. The retry
layer pattern-matches rendered exception text rather than provider-specific
exception types, so it works uniformly across SDKs.
"""
from __future__ import annotations

import re
import time
from typing import Any, Callable, Sequence


DEFAULT_RETRY_BACKOFF_SEC: tuple[float, ...] = (5.0, 15.0, 45.0)

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
    r"api_error",
    r"server_error",
    r"service.?unavailable",
)
_RETRYABLE_RE = re.compile("|".join(RETRYABLE_PATTERNS), re.IGNORECASE)


def is_retryable_error(exc: BaseException) -> bool:
    """True if an exception looks like a transient provider error."""
    rendered = "%r %s" % (exc, exc)
    return bool(_RETRYABLE_RE.search(rendered))


def call_with_retry(
    fn: Callable[..., Any],
    *args,
    retry_backoff_sec: Sequence[float] = DEFAULT_RETRY_BACKOFF_SEC,
    sleep_fn: Callable[[float], None] = time.sleep,
    **kwargs,
) -> Any:
    """Call ``fn`` with retry+backoff on transient provider errors."""
    attempts = 1 + len(retry_backoff_sec)
    last_exc: BaseException | None = None
    for i in range(attempts):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if i >= len(retry_backoff_sec):
                raise
            if not is_retryable_error(exc):
                raise
            sleep_fn(float(retry_backoff_sec[i]))
    if last_exc is not None:  # pragma: no cover
        raise last_exc


class RetryingLLMClient:
    """Decorator that retries transient failures from an inner ``generate``."""

    def __init__(
        self,
        inner: Any,
        retry_backoff_sec: Sequence[float] = DEFAULT_RETRY_BACKOFF_SEC,
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        self._inner = inner
        self._retry_backoff_sec = tuple(retry_backoff_sec)
        self._sleep = sleep_fn

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    def generate(self, *args, **kwargs) -> Any:
        return call_with_retry(
            self._inner.generate,
            *args,
            retry_backoff_sec=self._retry_backoff_sec,
            sleep_fn=self._sleep,
            **kwargs,
        )
