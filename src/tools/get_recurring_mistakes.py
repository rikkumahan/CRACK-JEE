import json
from fastmcp import FastMCP
from db import get_recurring_mistakes


def register_get_recurring_mistakes(server: FastMCP) -> None:
    @server.tool(
        name="get_recurring_mistakes",
        description=(
            "Finds (concept, error_type) pairs that have occurred 2+ times across "
            "different attempts — the core differentiator versus per-test-only reports: "
            "it surfaces patterns that repeat across tests, not just within one."
        ),
    )
    def handle_get_recurring_mistakes(subject: str, min_occurrences: int = 2) -> str:
        return json.dumps(
            get_recurring_mistakes(subject, min_occurrences=min_occurrences)
        )
