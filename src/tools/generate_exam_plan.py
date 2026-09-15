import json
from fastmcp import FastMCP
from db import generate_exam_plan


def register_generate_exam_plan(server: FastMCP) -> None:
    @server.tool(
        name="generate_exam_plan",
        description=(
            "Persists a study plan covering an exam's full syllabus, after "
            "you've reasoned over get_exam, get_weak_topics/get_concept_state/"
            "get_revision_due/get_time_patterns per syllabus subject, and "
            "get_student_profile. Compose the plan text yourself first -- "
            "this tool only saves it, keeping every past version so "
            "get_exam_progress can measure whether it worked."
        ),
    )
    def handle_generate_exam_plan(exam_id: int, plan_text: str) -> str:
        return json.dumps(generate_exam_plan(exam_id, plan_text))
