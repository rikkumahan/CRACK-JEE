import json
from fastmcp import FastMCP
from db import get_revision_due


def register_get_revision_due(server: FastMCP) -> None:
    @server.tool(
        name="get_revision_due",
        description=(
            "Flags concepts she should revise soon, before she forgets them (spaced "
            "repetition based on BKT mastery decay) — 'due_now' concepts have already "
            "decayed below the threshold, 'due_soon' ones will within days_ahead days."
        ),
    )
    def handle_get_revision_due(
        subject: str, days_ahead: int = 14, threshold: float = 0.5
    ) -> str:
        return json.dumps(
            get_revision_due(subject, days_ahead=days_ahead, threshold=threshold)
        )
