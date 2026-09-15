import json
from fastmcp import FastMCP
from db import update_student_profile


def register_end_study_session(server: FastMCP) -> None:
    @server.tool(
        name="end_study_session",
        description=(
            "Call when the student signals she's wrapping up for now (e.g. "
            "'that's it for today', 'done'). Recomputes her study-pattern "
            "profile from this session's activity. No-ops safely if nothing "
            "was logged this session (e.g. she only asked for advice)."
        ),
    )
    def handle_end_study_session() -> str:
        return json.dumps(update_student_profile())
