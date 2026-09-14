import json
from fastmcp import FastMCP
from db import list_concepts


def register_list_concepts(server: FastMCP) -> None:
    @server.tool(
        name="list_concepts",
        description=(
            "Lists existing concepts for a subject. Call this before log_performance_input "
            "to check whether a concept already exists under a different phrasing "
            "(e.g. 'Rotational Motion' vs 'Rotational Dynamics') — reuse the existing "
            "name rather than creating a near-duplicate."
        ),
    )
    def handle_list_concepts(subject: str) -> str:
        return json.dumps(list_concepts(subject))

