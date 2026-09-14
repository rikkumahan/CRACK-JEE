# Setup & Commands

Two implementations currently coexist: the original Node.js server
(`src/*.js`) and the Python/FastMCP server (`src/*.py`), which now has
feature parity (all 7 tools) and is the one to use going forward. Node's
kept alongside until an explicit decommission decision — see
`docs/fastmcp-migration-plan.md`. Both suites must pass on every commit
until that decision is made, so the pre-commit hook's single TEST_CMD
line below runs both (the hook takes only the first `# TEST_CMD:` match
in this file — do not add a second one, combine into this line instead).

## Python server (current)

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

## Node server (legacy, still passing, not yet decommissioned)

### Install
```
npm install
```

### Run locally
```
npm start
```

## Combined checks  (read by pre-commit hook)
```
# LINT_CMD: node --check src/server.js
# TEST_CMD: uv run pytest tests/ -v && npm test
```
