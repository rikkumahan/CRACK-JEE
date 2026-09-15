import json
from fastmcp import FastMCP
from db import get_time_patterns


def register_get_time_patterns(server: FastMCP) -> None:
    @server.tool(
        name="get_time_patterns",
        description=(
            "Compares average time spent on correct vs. wrong attempts per concept, and "
            "flags a 'stuck_pattern' when wrong attempts take much longer than correct "
            "ones — a sign she's getting stuck rather than making a quick, clean mistake."
        ),
    )
    def handle_get_time_patterns(subject: str) -> str:
        return json.dumps(get_time_patterns(subject))
