import json
import sys
from pathlib import Path
import pytest
from fastmcp import Client

SERVER_PATH = Path(__file__).resolve().parent.parent / "src" / "server.py"
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "jee.db"


@pytest.mark.asyncio
async def test_get_concept_state_moves_with_attempts_in_process():
    from server import mcp
    import db

    if db._default_conn is not None:
        db._default_conn.close()
        db._default_conn = None
    if DB_PATH.exists():
        try:
            DB_PATH.unlink()
        except OSError:
            pass

    async with Client(mcp) as client:
        state_before = await client.call_tool(
            "get_concept_state", {"subject": "Physics"}
        )
        assert json.loads(state_before.content[0].text) == []

        await client.call_tool(
            "log_performance_input",
            {"subject": "Physics", "concept": "Friction", "result": "correct"},
        )
        state_after_correct = json.loads(
            (
                await client.call_tool(
                    "get_concept_state", {"subject": "Physics"}
                )
            ).content[0].text
        )
        assert len(state_after_correct) == 1
        assert state_after_correct[0]["name"] == "Friction"
        mastery_after_correct = state_after_correct[0]["mastery_probability"]
        assert mastery_after_correct > 0.20  # P_L0

        await client.call_tool(
            "log_performance_input",
            {"subject": "Physics", "concept": "Friction", "result": "wrong"},
        )
        state_after_wrong = json.loads(
            (
                await client.call_tool(
                    "get_concept_state", {"subject": "Physics"}
                )
            ).content[0].text
        )
        mastery_after_wrong = state_after_wrong[0]["mastery_probability"]
        assert mastery_after_wrong < mastery_after_correct
