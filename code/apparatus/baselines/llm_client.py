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
