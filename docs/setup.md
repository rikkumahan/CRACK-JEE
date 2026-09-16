# Setup & Commands

The server is Python/FastMCP (`src/*.py`). The original Node.js
implementation (`src/*.js`) was decommissioned once Python reached feature
parity (all 7 tools) — see `docs/fastmcp-migration-plan.md` for the
migration history and `docs/production-readiness-notes.md` for the
decommission decision.

## Python server

### Install
```
uv sync
```

### Run locally (stdio)
```
uv run python src/server.py
```

### Run via uvx from PyPI (what a real MCP client launches)
```
uvx crack-jee
```
Published as `crack-jee` on PyPI (2026-09-17). Verified live: a fresh
`uvx crack-jee` installs from the index and completes a real JSON-RPC
`initialize` handshake.

### Run via uvx from local source (pre-publish testing)
```
uvx --from . crack-jee
```

### Research track (separate, own venv)
```
cd research/synthetic_jee_kt
uv sync
uv run pytest tests/ -v
```

## Combined checks  (read by pre-commit hook)
```
# LINT_CMD:
# TEST_CMD: uv run pytest tests/ -v
```
