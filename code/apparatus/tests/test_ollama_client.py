import json

from apparatus.llm.ollama_client import call_ollama_json


class _FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_call_ollama_json_mocks_urlopen(monkeypatch):
    calls = []

    def fake_urlopen(req, timeout):
        calls.append({
            "url": req.full_url,
            "timeout": timeout,
            "body": json.loads(req.data.decode("utf-8")),
        })
        return _FakeHTTPResponse({
            "response": '{"decision_summary": "ok"}',
        })

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    out = call_ollama_json(
        "mistral:7b",
        "prompt",
        options={"temperature": 0.0, "num_predict": 2048, "seed": 20260624},
        timeout=9,
    )

    assert out == {"decision_summary": "ok"}
    assert calls[0]["url"] == "http://localhost:11434/api/generate"
    assert calls[0]["timeout"] == 9
    assert calls[0]["body"]["model"] == "mistral:7b"
    assert calls[0]["body"]["format"] == "json"
    assert calls[0]["body"]["stream"] is False
    assert calls[0]["body"]["options"]["seed"] == 20260624
