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

### Run via uvx (what a real MCP client launches)
```
uvx --from . jee-performance-engine
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
