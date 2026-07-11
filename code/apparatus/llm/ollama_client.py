"""Minimal Ollama JSON client for local Cond-B runs."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Optional


def _strip_markdown_fences(text: str) -> str:
    rendered = text.strip()
    if rendered.startswith("```json"):
        rendered = rendered[7:]
    elif rendered.startswith("```"):
        rendered = rendered[3:]
    if rendered.endswith("```"):
        rendered = rendered[:-3]
    return rendered.strip()


def call_ollama_json(
    model: str,
    prompt: str,
    *,
    format: str = "json",
    options: Optional[dict[str, Any]] = None,
    timeout: int = 600,
    endpoint: str = "http://localhost:11434/api/generate",
) -> dict[str, Any]:
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": format,
        "options": dict(options or {}),
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            pass
        raise RuntimeError(
            f"Ollama HTTP {exc.code}: {detail or exc.reason}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama connection error: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Ollama returned malformed JSON: {exc.msg}") from exc

    rendered = resp.get("response")
    if not isinstance(rendered, str):
        raise RuntimeError("Ollama response missing string field 'response'")
    try:
        parsed = json.loads(_strip_markdown_fences(rendered))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Ollama response is not valid JSON: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("Ollama JSON response must decode to an object")
    return parsed

