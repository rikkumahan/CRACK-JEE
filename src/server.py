#!/usr/bin/env python3
from fastmcp import FastMCP
from tools.list_concepts import register_list_concepts
from tools.log_performance_input import register_log_performance_input
from tools.get_weak_topics import register_get_weak_topics
from tools.get_recurring_mistakes import register_get_recurring_mistakes

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


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

