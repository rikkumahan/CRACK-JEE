import time
from typing import Literal, Optional
from fastmcp import FastMCP
from db import get_connection, find_or_create_concept

ResultType = Literal["correct", "wrong", "unattempted"]
ErrorType = Literal[
    "concept_gap",
    "calculation",
    "misread",
    "time_pressure",
    "unattempted",
    "unknown",
]


def register_log_performance_input(server: FastMCP) -> None:
    @server.tool(
        name="log_performance_input",
        description=(
            "Records one attempt (a question the student answered, right or wrong) against a concept. "
            "Call list_concepts first to check for an existing concept name before inventing a new one."
        ),
    )
    def handle_log_performance_input(
        subject: str,
        concept: str,
        result: ResultType,
        error_type: Optional[ErrorType] = None,
        time_seconds: Optional[int] = None,
        notes: Optional[str] = None,
        context: Optional[str] = None,
    ) -> str:
        conn = get_connection()
        concept_id = find_or_create_concept(concept, subject, conn=conn)

        created_at = int(time.time() * 1000)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO attempts (concept_id, result, time_seconds, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (concept_id, result, time_seconds, created_at),
        )
        attempt_id = cursor.lastrowid

        if error_type:
            cursor.execute("SELECT id FROM error_types WHERE name = ?", (error_type,))
            row = cursor.fetchone()
            if row is not None:
                error_type_id = row[0]
                cursor.execute(
                    """
                    INSERT INTO attempt_errors (attempt_id, error_type_id, notes)
                    VALUES (?, ?, ?)
                    """,
                    (attempt_id, error_type_id, notes),
                )

        conn.commit()
        return f'Logged attempt {attempt_id} for concept "{concept}" ({subject}): {result}.'

