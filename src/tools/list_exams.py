import json
from fastmcp import FastMCP
from db import list_exams


def register_list_exams(server: FastMCP) -> None:
    @server.tool(
        name="list_exams",
        description=(
            "Lists all exams set via set_exam, with exam_date and whether a "
            "plan has been generated yet. Use to resolve a vague reference "
            "like 'my upcoming Physics exam' to an exam_id."
        ),
    )
    def handle_list_exams() -> str:
        return json.dumps(list_exams())
