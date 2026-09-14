import sys
from pathlib import Path
import pytest
from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport

SERVER_PATH = Path(__file__).resolve().parent.parent / "src" / "server.py"


@pytest.mark.asyncio
async def test_echo_tool_round_trips_a_message_over_stdio():
    transport = PythonStdioTransport(SERVER_PATH, python_cmd=sys.executable)
    async with Client(transport) as client:
        tools = await client.list_tools()
        assert any(t.name == "echo" for t in tools)

        result = await client.call_tool("echo", {"message": "ping"})
        assert result.content[0].text == "ping"


@pytest.mark.asyncio
async def test_echo_tool_in_process():
    from server import mcp

    async with Client(mcp) as client:
        tools = await client.list_tools()
        assert any(t.name == "echo" for t in tools)

        result = await client.call_tool("echo", {"message": "ping"})
        assert result.content[0].text == "ping"

