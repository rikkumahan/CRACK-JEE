# Agent Rules (shared across Claude Code, OpenCode, Antigravity)

All three tools read this file from the repo root automatically. Single
source of truth for how any agent behaves in this repo.

## Before doing anything
1. Read docs/plan.md — current spec and status.
2. Read the last ~50 lines of docs/decisions.md — recent decisions/changes.
3. Read docs/setup.md — exact build/test/lint commands. Never guess these.

## Isolation
- You run in your own git worktree. Stay in it. Do not cd into a sibling
  worktree or the main checkout.
- Work on your own branch: <tool>/<short-task-name>
  e.g. claude/auth-refactor, opencode/csv-export, antigravity/nav-redesign

## Commits
- Message format: <type>(<tool>): summary  e.g. fix(claude): handle null session
  type is one of: feat fix chore docs refactor test
- NEVER use `git commit --no-verify` or `-n`. The pre-commit gate is mandatory
  and bypass attempts are blocked at the git level.

## When you finish (or get blocked)
- The pre-commit hook runs lint/test from docs/setup.md automatically.
  Fix failures rather than working around them.
- Append a [done] or [blocked] entry to docs/decisions.md.
- Do not merge your own branch to main — that's a human review step.

## Decision log format (docs/decisions.md)
[YYYY-MM-DD HH:MM] [tool] [branch] [status] — what / why
  status: claimed | done | blocked | merged

## Task routing (default lanes)
- Claude Code -> backend logic, refactors, CI/CD, careful multi-file reasoning
- Antigravity -> frontend/UI, browser testing, parallel exploration
- OpenCode    -> cheap/high-volume/experimental work, or quota overflow

## Note on file references
Claude Code expands @file imports; OpenCode and Antigravity do not reliably.
Keep essential rules written inline here, not only linked.

<!-- code-review-graph MCP tools -->
## MCP Tools: code-review-graph

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool | Use when |
|------|----------|
| `get_minimal_context` | **Entry point (~100 tokens)** — ALWAYS call FIRST for instant risk score, affected communities, and targeted tool suggestions |
| `detect_changes` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context` | Need source snippets for review — token-efficient |
| `get_impact_radius` | Understanding blast radius of a change |
| `get_affected_flows` | Finding which execution paths are impacted |
| `query_graph` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes` | Finding functions/classes by name or keyword |
| `get_architecture_overview` | Understanding high-level codebase structure (use `detail_level="minimal"`) |
| `refactor_tool` | Planning renames, finding dead code |

### Token-Saving Protocol & Workflow

1. **Always start with `get_minimal_context(task="...")`**: Provides instant orientation in ~100 tokens without loading files into context.
2. **Explore selectively**: Use `query_graph` (with `callers_of`, `callees_of`, `imports_of`, `tests_for`) or `get_review_context` instead of raw file reading.
3. **Use minimal detail level**: Keep `detail_level="minimal"` on `get_architecture_overview` to prevent token bloat (typically cuts ~600KB down to <5KB, saving 97% tokens).
4. **Auto-updating**: The graph automatically updates incrementally on file edits via hooks (`code-review-graph update --skip-flows`).
5. **Offline docs**: Consult the generated wiki in `.code-review-graph/wiki/index.md` for architectural community documentation.