import json
import subprocess
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_raw_jsonrpc_handshake_via_uvx():
    """Verify uvx launches the server cleanly via a raw JSON-RPC stdio handshake.
    
    This matches the raw handshake technique from docs/fastmcp-migration-plan.md step 5:
    spawns `uvx --from . jee-performance-engine`, writes an `initialize` request to stdin,
    and confirms the JSON-RPC response on stdout.
    """
    cmd = ["uvx", "--from", str(REPO_ROOT), "jee-performance-engine"]
    proc = subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # 1. Initialize request
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "raw-handshake-test", "version": "0.1.0"},
            },
        }
        proc.stdin.write(json.dumps(init_req) + "\n")
        proc.stdin.flush()

        raw_line = proc.stdout.readline()
        assert raw_line, "Expected stdout response from server on uvx initialize"
        resp = json.loads(raw_line)

        assert resp.get("jsonrpc") == "2.0"
        assert resp.get("id") == 1
        assert "result" in resp
        result = resp["result"]
        assert result.get("serverInfo", {}).get("name") == "jee-performance-engine"
        assert result.get("serverInfo", {}).get("version") == "0.1.0"
        assert "protocolVersion" in result

        # 2. Initialized notification
        proc.stdin.write(
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
            + "\n"
        )
        proc.stdin.flush()

        # 3. List tools
        proc.stdin.write(
            json.dumps(
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
            )
            + "\n"
        )
        proc.stdin.flush()

        tools_resp = json.loads(proc.stdout.readline())
        assert tools_resp.get("id") == 2
        tool_names = {t["name"] for t in tools_resp["result"]["tools"]}
        assert {"echo", "list_concepts", "log_performance_input"}.issubset(tool_names)

        # 4. Call echo tool
        proc.stdin.write(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "echo",
                        "arguments": {"message": "handshake verified"},
                    },
                }
            )
            + "\n"
        )
        proc.stdin.flush()

        call_resp = json.loads(proc.stdout.readline())
        assert call_resp.get("id") == 3
        assert call_resp["result"]["content"][0]["text"] == "handshake verified"

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

