import json
from fastmcp import FastMCP
from db import get_weak_topics


def register_get_weak_topics(server: FastMCP) -> None:
    @server.tool(
        name="get_weak_topics",
        description=(
            "Ranks concepts for a subject by wrong-answer rate, weakest first. "
            "Use this to identify which topics need the most attention. Also returns "
            "skip_rate and attempted_accuracy per concept — useful for JEE-style negative "
            "marking strategy (is she skipping wisely, or guessing on things to avoid?), "
            "not just raw accuracy."
        ),
    )
    def handle_get_weak_topics(subject: str, limit: int = 10) -> str:
        return json.dumps(get_weak_topics(subject, limit=limit))
