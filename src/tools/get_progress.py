import json
from fastmcp import FastMCP
from db import get_progress


def register_get_progress(server: FastMCP) -> None:
    @server.tool(
        name="get_progress",
        description=(
            "Compares accuracy on a concept before vs. after an intervention was "
            "issued via generate_daily_plan — the closed-loop verification step. "
            "Call this once enough new attempts exist after the intervention."
        ),
    )
    def handle_get_progress(intervention_id: int) -> str:
        return json.dumps(get_progress(intervention_id))
