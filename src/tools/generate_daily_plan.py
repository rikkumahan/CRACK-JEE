import json
from fastmcp import FastMCP
from db import create_intervention


def register_generate_daily_plan(server: FastMCP) -> None:
    @server.tool(
        name="generate_daily_plan",
        description=(
            "Persists a concrete, time-blocked daily plan for one concept after "
            "you've reasoned over get_weak_topics/get_recurring_mistakes/"
            "get_concept_state results. Compose the plan text yourself first — "
            "this tool only saves it and starts tracking whether it worked."
        ),
    )
    def handle_generate_daily_plan(concept_id: int, plan_text: str) -> str:
        intervention_id = create_intervention(concept_id, plan_text)
        return json.dumps({"intervention_id": intervention_id, "concept_id": concept_id})
