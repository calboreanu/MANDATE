"""Tests for the shared retry/backoff helper."""
import pytest

from apparatus.llm_retry import (
    DEFAULT_RETRY_BACKOFF_SEC,
    RetryingLLMClient,
    call_with_retry,
    is_retryable_error,
)


def test_default_retry_backoff_schedule():
    assert DEFAULT_RETRY_BACKOFF_SEC == (5.0, 15.0, 45.0)


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

    result = call_with_retry(
        fn,
        retry_backoff_sec=(0.0, 0.0, 0.0),
        sleep_fn=sleeps.append,
    )
    assert result == "OK"
    assert len(calls) == 3
    assert sleeps == [0.0, 0.0]


def test_call_with_retry_exhausts_on_persistent_failure():
    def fn():
        raise RuntimeError("529 overloaded_error")

    with pytest.raises(RuntimeError, match="529"):
        call_with_retry(
            fn,
            retry_backoff_sec=(0.0, 0.0, 0.0),
            sleep_fn=lambda _: None,
        )


def test_call_with_retry_no_retry_on_non_retryable():
    calls = []

    def fn():
        calls.append(1)
        raise RuntimeError("401 invalid API key")

    with pytest.raises(RuntimeError, match="401"):
        call_with_retry(
            fn,
            retry_backoff_sec=(0.0, 0.0, 0.0),
            sleep_fn=lambda _: None,
        )
    assert len(calls) == 1


def test_retrying_llm_client_wraps_generate():
    class FakeClient:
        def __init__(self):
            self.calls = []

        def generate(self, **kwargs):
            self.calls.append(kwargs)
            if len(self.calls) <= 1:
                raise RuntimeError("529 overloaded_error")
            return "OK"

    inner = FakeClient()
    wrapped = RetryingLLMClient(
        inner,
        retry_backoff_sec=(0.0, 0.0, 0.0),
        sleep_fn=lambda _: None,
    )
    assert wrapped.generate(prompt="x") == "OK"
    assert len(inner.calls) == 2


def test_retrying_llm_client_passes_through_other_attrs():
    class FakeClient:
        provider = "anthropic"

        def generate(self, **kwargs):
            return "OK"

    wrapped = RetryingLLMClient(FakeClient())
    assert wrapped.provider == "anthropic"
