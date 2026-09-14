import pytest

import prism_client


@pytest.fixture(autouse=True)
def prism_env(monkeypatch):
    monkeypatch.setenv("PRISMTRACE_PROJECT_ID", "test-project-id")
    monkeypatch.setenv("PRISMTRACE_API_KEY", "test-api-key")
    monkeypatch.delenv("PRISMTRACE_HOST", raising=False)


class FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._json_data


def test_send_trace_posts_correct_payload_and_auth_header(monkeypatch):
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return FakeResponse({"trace_id": "abc123"})

    monkeypatch.setattr(prism_client.requests, "post", fake_post)

    result = prism_client.send_trace(
        model="claude-sonnet-5",
        input_messages=[{"role": "user", "content": "hi"}],
        output_message="hello",
        latency_ms=250,
        session_id="sess-1",
        agent_id="agent-1",
        metadata={"foo": "bar"},
    )

    assert captured["url"] == "https://prism.blockconvey.com/api/traces"
    assert captured["headers"] == {"X-PRISMtrace-Key": "test-api-key"}
    assert captured["json"] == {
        "project_id": "test-project-id",
        "model": "claude-sonnet-5",
        "input_messages": [{"role": "user", "content": "hi"}],
        "output_message": "hello",
        "latency_ms": 250,
        "session_id": "sess-1",
        "agent_id": "agent-1",
        "metadata": {"foo": "bar"},
    }
    assert result == {"trace_id": "abc123"}


def test_send_trace_omits_optional_fields_when_not_given(monkeypatch):
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["json"] = json
        return FakeResponse({"trace_id": "abc123"})

    monkeypatch.setattr(prism_client.requests, "post", fake_post)

    prism_client.send_trace(
        model="claude-sonnet-5",
        input_messages=[{"role": "user", "content": "hi"}],
        output_message="hello",
        latency_ms=100,
    )

    assert "session_id" not in captured["json"]
    assert "agent_id" not in captured["json"]
    assert "metadata" not in captured["json"]


def test_send_trace_raises_clear_error_when_credentials_missing(monkeypatch):
    monkeypatch.delenv("PRISMTRACE_PROJECT_ID", raising=False)
    monkeypatch.delenv("PRISMTRACE_API_KEY", raising=False)

    with pytest.raises(prism_client.PrismConfigError, match="PRISMTRACE_PROJECT_ID"):
        prism_client.send_trace(
            model="m", input_messages=[], output_message="o", latency_ms=1
        )


def test_send_trace_raises_when_only_api_key_missing(monkeypatch):
    monkeypatch.delenv("PRISMTRACE_API_KEY", raising=False)

    with pytest.raises(prism_client.PrismConfigError, match="PRISMTRACE_API_KEY"):
        prism_client.send_trace(
            model="m", input_messages=[], output_message="o", latency_ms=1
        )


def test_verify_connection_posts_handshake_with_auth_header(monkeypatch):
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return FakeResponse({"live_connected": True})

    monkeypatch.setattr(prism_client.requests, "post", fake_post)

    result = prism_client.verify_connection()

    assert captured["url"] == "https://prism.blockconvey.com/api/setup-doctor/handshake"
    assert captured["json"] == {"project_id": "test-project-id", "send_test_trace": True}
    assert captured["headers"] == {"X-PRISMtrace-Key": "test-api-key"}
    assert result == {"live_connected": True}


def test_host_env_var_overrides_default(monkeypatch):
    monkeypatch.setenv("PRISMTRACE_HOST", "https://custom.example.com")
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        return FakeResponse({})

    monkeypatch.setattr(prism_client.requests, "post", fake_post)

    prism_client.send_trace(
        model="m", input_messages=[], output_message="o", latency_ms=1
    )

    assert captured["url"] == "https://custom.example.com/api/traces"
