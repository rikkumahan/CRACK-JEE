#!/usr/bin/env python3
from fastmcp import FastMCP

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


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
