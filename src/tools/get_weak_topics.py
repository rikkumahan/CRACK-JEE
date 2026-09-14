import json
from fastmcp import FastMCP
from db import get_weak_topics


def register_get_weak_topics(server: FastMCP) -> None:
    @server.tool(
        name="get_weak_topics",
        description=(
            "Ranks concepts for a subject by wrong-answer rate, weakest first. "
            "Use this to identify which topics need the most attention."
        ),
    )
    def handle_get_weak_topics(subject: str, limit: int = 10) -> str:
        return json.dumps(get_weak_topics(subject, limit=limit))
