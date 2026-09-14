import json
from typing import Optional
from fastmcp import FastMCP
from db import get_concept_state


def register_get_concept_state(server: FastMCP) -> None:
    @server.tool(
        name="get_concept_state",
        description=(
            "Returns current BKT mastery probability per concept for a subject "
            "(0-1), with a retention-decay nudge applied if the concept hasn't "
            "been attempted recently. Pass concept_id to check a single concept."
        ),
    )
    def handle_get_concept_state(subject: str, concept_id: Optional[int] = None) -> str:
        return json.dumps(get_concept_state(subject, concept_id=concept_id))
