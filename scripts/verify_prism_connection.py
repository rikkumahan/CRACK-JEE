#!/usr/bin/env python3
"""One-off sanity check for the PRISM integration.

Run this once PRISMTRACE_PROJECT_ID and PRISMTRACE_API_KEY are set as real
env vars, to confirm the credentials actually work against the live PRISM
API (this hits the network — do not run it in CI or without real creds).

    PRISMTRACE_PROJECT_ID=... PRISMTRACE_API_KEY=... uv run python scripts/verify_prism_connection.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from prism_client import PrismConfigError, verify_connection


def main() -> int:
    try:
        result = verify_connection(send_test_trace=True)
    except PrismConfigError as e:
        print(f"Config error: {e}")
        return 1
    except Exception as e:
        print(f"PRISM handshake failed: {e}")
        return 1

    print(f"PRISM handshake response: {result}")
    if result.get("live_connected") is False:
        print("Warning: handshake succeeded but live_connected is False.")
        return 1

    print("PRISM connection verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
