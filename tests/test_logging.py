import json
import os
import sys
from pathlib import Path
import pytest
from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport

SERVER_PATH = Path(__file__).resolve().parent.parent / "src" / "server.py"
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "jee.db"


@pytest.mark.asyncio
async def test_log_performance_input_records_attempt_and_dedups_concepts_stdio():
    if DB_PATH.exists():
        try:
            DB_PATH.unlink()
        except OSError:
            pass

    transport = PythonStdioTransport(SERVER_PATH, python_cmd=sys.executable)
    async with Client(transport) as client:
        await client.call_tool(
            "log_performance_input",
            {
                "subject": "Physics",
                "concept": "Rotational Motion",
                "result": "wrong",
                "error_type": "concept_gap",
            },
        )

        # Same concept, different phrasing/casing — must NOT create a duplicate row.
        await client.call_tool(
            "log_performance_input",
            {
                "subject": "Physics",
                "concept": "rotational motion",
                "result": "correct",
            },
        )

        list_result = await client.call_tool(
            "list_concepts",
            {"subject": "Physics"},
        )
        concepts = json.loads(list_result.content[0].text)
        assert len(concepts) == 1, "expected exactly one deduped concept"
        assert concepts[0]["name"] == "Rotational Motion"


@pytest.mark.asyncio
async def test_log_performance_input_records_attempt_and_dedups_concepts_in_process():
    from server import mcp

    async with Client(mcp) as client:
        await client.call_tool(
            "log_performance_input",
            {
                "subject": "Physics",
                "concept": "Rotational Motion",
                "result": "wrong",
                "error_type": "concept_gap",
            },
        )

        await client.call_tool(
            "log_performance_input",
            {
                "subject": "Physics",
                "concept": "rotational motion",
                "result": "correct",
            },
        )

        list_result = await client.call_tool(
            "list_concepts",
            {"subject": "Physics"},
        )
        concepts = json.loads(list_result.content[0].text)
        assert len(concepts) == 1, "expected exactly one deduped concept"
        assert concepts[0]["name"] == "Rotational Motion"
