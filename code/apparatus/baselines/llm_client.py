"""
LLM client abstraction for the baselines (Workstream B2).

Wraps the Anthropic and OpenAI SDKs behind one interface, captures exact token
usage, and estimates cost. MockLLMClient supports testing without API keys.

Token counts are exact and are the hard data for PROTOCOL_LOCK Section 6.5
cost tracking. Dollar cost is tokens x rate; the rate table below is
indicative and must be confirmed and pinned at the pre-registration deposit.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

# Indicative USD per million tokens, (input, output). CONFIRM AND PIN at
# deposit. These are not authoritative prices.
PRICES = {
    "claude": (3.0, 15.0),
    "gpt-4o": (2.5, 10.0),
    "gpt": (2.5, 10.0),
    "gemini": (1.25, 5.0),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int):
    """USD estimate, or None if the model is not in the rate table."""
    rate = None
    low = (model or "").lower()
    for key, r in PRICES.items():
        if key in low:
            rate = r
            break
    if rate is None:
        return None
    return round(input_tokens / 1e6 * rate[0]
                 + output_tokens / 1e6 * rate[1], 6)


@dataclass
class LLMResponse:
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def cost_usd(self):
        return estimate_cost(self.model, self.input_tokens, self.output_tokens)


class LLMClient:
    """Abstract client. generate() returns an LLMResponse."""
    provider = ""

    def generate(self, *, system: str, user: str, model: str,
                 temperature: float = 0.0, max_tokens: int = 4096) -> LLMResponse:
        raise NotImplementedError


_SECRET_RE = re.compile(
    r"(sk-ant-[A-Za-z0-9_-]+|Bearer\s+[A-Za-z0-9._-]+|x-api-key[:=]\s*[A-Za-z0-9._-]+)",
    re.IGNORECASE,
)


class BudgetedLLMClient(LLMClient):
    """Provider client wrapper that reserves and settles campaign API budget."""

    def __init__(
        self,
        inner: LLMClient,
        *,
        cost_ledger,
        run_id: str,
        system_id: str,
        task_id: str,
        run_number: int,
        role: str,
    ):
        self.inner = inner
        self.cost_ledger = cost_ledger
        self.run_id = run_id
        self.system_id = system_id
        self.task_id = task_id
        self.run_number = int(run_number)
        self.role = role
        self.provider = getattr(inner, "provider", "")
        self.attempts: list[dict] = []

    def _reserved_cost(self, *, system: str, user: str, model: str, max_tokens: int) -> float:
        # Bytes are a conservative token upper bound for UTF-8 text. Add fixed
        # chat framing slack so the reservation remains safely above actual usage.
        input_bound = len((system or "").encode("utf-8")) + len((user or "").encode("utf-8")) + 1000
        reserve = estimate_cost(model, input_bound, int(max_tokens or 0))
        if reserve is None:
            raise ValueError(f"no pinned price table entry for model {model!r}")
        return float(reserve)

    @staticmethod
    def _safe_error(exc: BaseException) -> str:
        return _SECRET_RE.sub("[REDACTED]", str(exc))[:500]

    @staticmethod
    def _get_attr_or_key(obj, name: str):
        if isinstance(obj, dict):
            return obj.get(name)
        return getattr(obj, name, None)

    @classmethod
    def _usage_cost_from_exception(cls, exc: BaseException, model: str):
        candidates = [exc]
        for name in ("response", "body", "error", "usage", "usage_metadata"):
            value = getattr(exc, name, None)
            if value is not None:
                candidates.append(value)
        for obj in list(candidates):
            for name in ("usage", "usage_metadata"):
                value = cls._get_attr_or_key(obj, name)
                if value is not None:
                    candidates.append(value)
        cost = None
        input_tokens = None
        output_tokens = None
        for obj in candidates:
            for key in ("cost_usd", "actual_cost_usd"):
                value = cls._get_attr_or_key(obj, key)
                if value is not None:
                    cost = float(value)
            for key in ("input_tokens", "prompt_tokens", "prompt_token_count"):
                value = cls._get_attr_or_key(obj, key)
                if value is not None:
                    input_tokens = int(value)
            for key in ("output_tokens", "completion_tokens", "candidates_token_count"):
                value = cls._get_attr_or_key(obj, key)
                if value is not None:
                    output_tokens = int(value)
        if cost is None and input_tokens is not None and output_tokens is not None:
            cost = estimate_cost(model, input_tokens, output_tokens)
        if cost is None:
            return None
        return {
            "actual_cost_usd": float(cost),
            "input_tokens": int(input_tokens or 0),
            "output_tokens": int(output_tokens or 0),
        }

    def _append_attempt(self, row: dict) -> None:
        self.attempts.append(dict(row))

    def generate(self, *, system: str, user: str, model: str,
                 temperature: float = 0.0, max_tokens: int = 4096) -> LLMResponse:
        reserved_cost_usd = self._reserved_cost(
            system=system,
            user=user,
            model=model,
            max_tokens=max_tokens,
        )
        reservation_id = self.cost_ledger.reserve_call(
            run_id=self.run_id,
            system_id=self.system_id,
            task_id=self.task_id,
            run_number=self.run_number,
            role=self.role,
            model=model,
            reserved_cost_usd=reserved_cost_usd,
            metadata={
                "provider": self.provider,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        try:
            self.cost_ledger.mark_dispatch_started(reservation_id)
            resp = self.inner.generate(
                system=system,
                user=user,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            usage = self._usage_cost_from_exception(exc, model)
            if usage is not None:
                actual = float(usage["actual_cost_usd"])
                input_tokens = int(usage["input_tokens"])
                output_tokens = int(usage["output_tokens"])
                status = "failed_authoritative_exception"
                cost_basis = "authoritative_exception"
                self.cost_ledger.mark_response_received(
                    reservation_id,
                    actual_cost_usd=actual,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    metadata={"exception": type(exc).__name__},
                )
            else:
                actual = float(reserved_cost_usd)
                input_tokens = 0
                output_tokens = 0
                status = "failed_dispatch_uncertain_reserved_bound"
                cost_basis = "reserved_bound_conservative"
            self.cost_ledger.settle_call(
                reservation_id,
                actual_cost_usd=actual,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                status=status,
                cost_basis=cost_basis,
                error=self._safe_error(exc),
            )
            self._append_attempt({
                "budget_reservation_id": reservation_id,
                "status": status,
                "cost_usd": round(actual, 6),
                "cost_basis": cost_basis,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            })
            raise

        actual = resp.cost_usd
        if actual is None:
            actual = estimate_cost(model, resp.input_tokens, resp.output_tokens)
        if actual is None:
            raise ValueError(f"no actual cost available for model {model!r}")
        self.cost_ledger.mark_response_received(
            reservation_id,
            actual_cost_usd=float(actual),
            input_tokens=int(resp.input_tokens or 0),
            output_tokens=int(resp.output_tokens or 0),
        )
        self.cost_ledger.settle_call(
            reservation_id,
            actual_cost_usd=float(actual),
            input_tokens=int(resp.input_tokens or 0),
            output_tokens=int(resp.output_tokens or 0),
            status="success",
            cost_basis="authoritative_response",
        )
        self._append_attempt({
            "budget_reservation_id": reservation_id,
            "status": "success",
            "cost_usd": round(float(actual), 6),
            "cost_basis": "authoritative_response",
            "input_tokens": int(resp.input_tokens or 0),
            "output_tokens": int(resp.output_tokens or 0),
        })
        raw = getattr(resp, "raw_response", None)
        if not isinstance(raw, dict):
            raw = {}
            setattr(resp, "raw_response", raw)
        raw["budget_reservation_id"] = reservation_id
        raw["budget_attempts"] = list(self.attempts)
        raw["budget_total_cost_usd"] = round(
            sum(float(a.get("cost_usd") or 0.0) for a in self.attempts),
            6,
        )
        raw["budget_cost_accounting"] = (
            "exact"
            if all(
                str(a.get("cost_basis", "")).startswith("authoritative")
                or str(a.get("cost_basis", "")) == "undispatched_zero"
                for a in self.attempts
            )
            else "conservative_upper_bound"
        )
        return resp


class AnthropicClient(LLMClient):
    provider = "anthropic"

    def __init__(self, api_key=None):
        import anthropic
        self._client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def generate(self, *, system, user, model, temperature=0.0,
                 max_tokens=4096):
        resp = self._client.messages.create(
            model=model, system=system, max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": user}])
        text = "".join(getattr(b, "text", "") for b in resp.content
                       if getattr(b, "type", "") == "text")
        return LLMResponse(text=text, model=model,
                           input_tokens=resp.usage.input_tokens,
                           output_tokens=resp.usage.output_tokens)


class OpenAIClient(LLMClient):
    provider = "openai"

    def __init__(self, api_key=None):
        import openai
        self._client = openai.OpenAI(
            api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    def generate(self, *, system, user, model, temperature=0.0,
                 max_tokens=4096):
        # Note: some newer OpenAI models expect `max_completion_tokens`
        # instead of `max_tokens`. Confirm during Phase 4 baseline
        # calibration against the pinned model; this is the single place
        # to adjust if the SDK rejects the parameter.
        resp = self._client.chat.completions.create(
            model=model, temperature=temperature, max_tokens=max_tokens,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}])
        text = resp.choices[0].message.content or ""
        usage = resp.usage
        return LLMResponse(
            text=text, model=model,
            input_tokens=getattr(usage, "prompt_tokens", 0),
            output_tokens=getattr(usage, "completion_tokens", 0))


class GeminiClient(LLMClient):
    """Google Gemini, via the current google-genai SDK. Used for Judge 3.

    Note: the google-genai API surface should be confirmed against the
    installed SDK during Phase 8 grading setup; the call is isolated here so
    it is the single place to adjust.
    """
    provider = "google"

    def __init__(self, api_key=None):
        from google import genai
        self._genai = genai
        self._client = genai.Client(
            api_key=api_key or os.environ.get("GOOGLE_API_KEY"))

    def generate(self, *, system, user, model, temperature=0.0,
                 max_tokens=4096):
        config = self._genai.types.GenerateContentConfig(
            system_instruction=system, temperature=temperature,
            max_output_tokens=max_tokens)
        resp = self._client.models.generate_content(
            model=model, contents=user, config=config)
        text = getattr(resp, "text", "") or ""
        usage = getattr(resp, "usage_metadata", None)
        return LLMResponse(
            text=text, model=model,
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0)


class MockLLMClient(LLMClient):
    """Deterministic client for tests. Returns scripted responses in order,
    then `default` once the script is exhausted.

    A queued response that is an Exception instance is RAISED instead of
    returned; this lets tests script transient provider errors (e.g.
    Gemini 503 UNAVAILABLE) and exercise the Judge retry/backoff layer.
    A queued response that is None falls through to `default`."""
    provider = "mock"

    def __init__(self, responses=None, default="{}"):
        self._responses = list(responses or [])
        self._default = default
        self.calls = []

    def generate(self, *, system, user, model, temperature=0.0,
                 max_tokens=4096):
        self.calls.append({"system": system, "user": user, "model": model})
        if self._responses:
            item = self._responses.pop(0)
        else:
            item = self._default
        if isinstance(item, BaseException):
            raise item
        text = item if item is not None else self._default
        return LLMResponse(text=text, model=model,
                           input_tokens=len((system + user).split()),
                           output_tokens=len(text.split()))
