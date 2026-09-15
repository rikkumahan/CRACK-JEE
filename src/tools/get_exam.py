import json
from fastmcp import FastMCP
from db import get_exam


def register_get_exam(server: FastMCP) -> None:
    @server.tool(
        name="get_exam",
        description=(
            "Full detail for one exam: syllabus, which syllabus concepts have "
            "zero logged attempts so far (not_yet_attempted -- check this "
            "before planning so no topic gets silently skipped), and the "
            "latest generated plan if any."
        ),
    )
    def handle_get_exam(exam_id: int) -> str:
        return json.dumps(get_exam(exam_id))
