#!/usr/bin/env python3
from fastmcp import FastMCP
from tools.list_concepts import register_list_concepts
from tools.log_performance_input import register_log_performance_input
from tools.get_weak_topics import register_get_weak_topics
from tools.get_recurring_mistakes import register_get_recurring_mistakes
from tools.get_concept_state import register_get_concept_state
from tools.generate_daily_plan import register_generate_daily_plan
from tools.get_progress import register_get_progress

mcp = FastMCP(
    name="jee-performance-engine",
    version="0.1.0",
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


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

