import json
from fastmcp import FastMCP
from db import get_exam_progress


def register_get_exam_progress(server: FastMCP) -> None:
    @server.tool(
        name="get_exam_progress",
        description=(
            "Compares accuracy across all of an exam's syllabus concepts "
            "before vs. after the latest generated plan -- the same "
            "before/after check get_progress does for a single-concept plan. "
            "Call after her next test covering exam syllabus topics."
        ),
    )
    def handle_get_exam_progress(exam_id: int) -> str:
        return json.dumps(get_exam_progress(exam_id))
