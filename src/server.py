#!/usr/bin/env python3
from fastmcp import FastMCP
from tools.list_concepts import register_list_concepts
from tools.log_performance_input import register_log_performance_input
from tools.get_weak_topics import register_get_weak_topics
from tools.get_recurring_mistakes import register_get_recurring_mistakes
from tools.get_concept_state import register_get_concept_state
from tools.generate_daily_plan import register_generate_daily_plan
from tools.get_progress import register_get_progress
from tools.get_revision_due import register_get_revision_due
from tools.get_time_patterns import register_get_time_patterns
from tools.set_exam import register_set_exam
from tools.list_exams import register_list_exams
from tools.get_exam import register_get_exam
from tools.generate_exam_plan import register_generate_exam_plan
from tools.get_exam_progress import register_get_exam_progress
from tools.end_study_session import register_end_study_session
from tools.get_student_profile import register_get_student_profile

INSTRUCTIONS = """\
This server tracks one JEE student's test performance and helps her improve. \
Talk to her like a coach, not a dashboard — explain why something is weak, \
not just that it is.

Logging a result: call list_concepts first to check whether the concept \
already exists under a different phrasing (e.g. "Rotational Motion" vs \
"Rotational Dynamics") before creating a new one, then log_performance_input.

Deciding what to study: call get_weak_topics, get_recurring_mistakes, \
get_concept_state, get_revision_due, and get_time_patterns together, not \
just one — they answer different questions (worst accuracy, repeating \
mistakes, current mastery, what's about to be forgotten, where she's \
getting stuck vs. making quick errors). get_weak_topics' skip_rate and \
attempted_accuracy matter too: JEE has negative marking, so skipping \
wisely and guessing wrong are different problems, not the same weakness. \
Reason over all of this yourself — it's real judgment, not a lookup — then \
call generate_daily_plan with a concrete, time-blocked plan you write \
yourself (e.g. "20 minutes: 5 friction problems focusing on free-body \
diagrams"), never generic advice like "revise Physics for 2 hours".

Closing the loop: after her next test on a concept you made a plan for, \
call get_progress with that plan's intervention_id to check whether it \
actually worked (accuracy before vs. after). This is the one thing a \
normal coaching report can't do — always use it, don't skip it.

Exam planning: when she mentions an upcoming exam and syllabus, call \
set_exam (or list_exams to find an existing one), then get_exam to check \
not_yet_attempted topics, then the usual analytics tools per subject plus \
get_student_profile, before writing the full plan yourself and saving it \
with generate_exam_plan. Call end_study_session when she wraps up for the \
day (it's a safe no-op if nothing was logged) and get_exam_progress after \
her next relevant test.\
"""

mcp = FastMCP(
    name="jee-performance-engine",
    version="0.1.0",
    instructions=INSTRUCTIONS,
)


@mcp.tool(
    name="echo",
    description="Echoes back the message it is given. Used only to verify the MCP connection is alive.",
)
def echo(message: str) -> str:
    return message


register_list_concepts(mcp)
register_log_performance_input(mcp)
register_get_weak_topics(mcp)
register_get_recurring_mistakes(mcp)
register_get_concept_state(mcp)
register_generate_daily_plan(mcp)
register_get_progress(mcp)
register_get_revision_due(mcp)
register_get_time_patterns(mcp)
register_set_exam(mcp)
register_list_exams(mcp)
register_get_exam(mcp)
register_generate_exam_plan(mcp)
register_get_exam_progress(mcp)
register_end_study_session(mcp)
register_get_student_profile(mcp)



def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

