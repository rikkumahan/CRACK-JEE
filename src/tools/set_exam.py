import json
from typing import Dict, List
from fastmcp import FastMCP
from db import set_exam


def register_set_exam(server: FastMCP) -> None:
    @server.tool(
        name="set_exam",
        description=(
            "Persists an upcoming exam and its syllabus so planning tools can "
            "reason against it. syllabus is a list of {subject, concept} "
            "objects -- reuses the same concept dedup as log_performance_input, "
            "so phrasing doesn't need to match exactly. exam_date is a plain "
            "'YYYY-MM-DD' string."
        ),
    )
    def handle_set_exam(name: str, exam_date: str, syllabus: List[Dict[str, str]]) -> str:
        return json.dumps(set_exam(name, exam_date, syllabus))
