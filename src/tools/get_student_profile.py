import json
from fastmcp import FastMCP
from db import get_student_profile


def register_get_student_profile(server: FastMCP) -> None:
    @server.tool(
        name="get_student_profile",
        description=(
            "Returns her persisted study-pattern profile (pace, per-subject "
            "accuracy, skip rate, stuck-concept rate, average revision lag), "
            "updated at the end of each study session. Call alongside "
            "get_weak_topics/get_concept_state/etc. when composing a plan -- "
            "especially an exam plan -- to account for her working style, "
            "not just raw topic data."
        ),
    )
    def handle_get_student_profile() -> str:
        return json.dumps(get_student_profile())
