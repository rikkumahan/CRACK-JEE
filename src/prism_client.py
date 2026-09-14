"""Client for PRISM by Block Convey (LLM-call observability/tracing).

This project's MCP server deliberately never calls an LLM itself (see
`ex1.md` SS3/SS11) — reasoning happens in the chat client, not server-side.
So nothing here is wired into a live call path yet. This module exists so
that whoever builds a future LLM-calling feature (e.g. a student-agent
roleplay feature) can trace it immediately, via one of two options:

1. **This module** (`send_trace`) — call it manually after any direct LLM
   call, wherever that call ends up living. Use this when you need control
   over what's recorded (custom metadata, non-Anthropic/OpenAI providers).

2. **Zero-code proxy** (preferred when it fits) — for a direct Anthropic
   or OpenAI SDK call, just point the SDK's `base_url` at
   `https://prism.blockconvey.com/proxy/anthropic` (or `/proxy/openai`,
   `/proxy/gemini`) and add the `X-PRISMtrace-Key` header as a default
   header on the client. Every call through that client is traced
   automatically — no `send_trace` call needed, no change to the call
   site itself. Prefer this unless you specifically need option 1's
   control over what gets recorded.

Required env vars: PRISMTRACE_HOST, PRISMTRACE_PROJECT_ID, PRISMTRACE_API_KEY.
"""

import os
from typing import Any, Dict, List, Optional

import requests

DEFAULT_HOST = "https://prism.blockconvey.com"
TIMEOUT_SECONDS = 10


class PrismConfigError(RuntimeError):
    """Raised when required PRISM credentials are missing."""


def _get_config() -> tuple[str, str, str]:
    host = os.environ.get("PRISMTRACE_HOST", DEFAULT_HOST)
    project_id = os.environ.get("PRISMTRACE_PROJECT_ID")
    api_key = os.environ.get("PRISMTRACE_API_KEY")

    missing = [
        name
        for name, value in (
            ("PRISMTRACE_PROJECT_ID", project_id),
            ("PRISMTRACE_API_KEY", api_key),
        )
        if not value
    ]
    if missing:
        raise PrismConfigError(
            f"Missing required PRISM env var(s): {', '.join(missing)}. "
            "Set PRISMTRACE_PROJECT_ID and PRISMTRACE_API_KEY before tracing."
        )
    return host, project_id, api_key  # type: ignore[return-value]


def send_trace(
    model: str,
    input_messages: List[Dict[str, str]],
    output_message: str,
    latency_ms: int,
    session_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """POST one trace of an LLM exchange to PRISM. Returns the parsed JSON response."""
    host, project_id, api_key = _get_config()

    payload: Dict[str, Any] = {
        "project_id": project_id,
        "model": model,
        "input_messages": input_messages,
        "output_message": output_message,
        "latency_ms": latency_ms,
    }
    if session_id is not None:
        payload["session_id"] = session_id
    if agent_id is not None:
        payload["agent_id"] = agent_id
    if metadata is not None:
        payload["metadata"] = metadata

    response = requests.post(
        f"{host}/api/traces",
        json=payload,
        headers={"X-PRISMtrace-Key": api_key},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def verify_connection(send_test_trace: bool = True) -> Dict[str, Any]:
    """Run the PRISM setup-doctor handshake to confirm credentials work."""
    host, project_id, api_key = _get_config()

    response = requests.post(
        f"{host}/api/setup-doctor/handshake",
        json={"project_id": project_id, "send_test_trace": send_test_trace},
        headers={"X-PRISMtrace-Key": api_key},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()
