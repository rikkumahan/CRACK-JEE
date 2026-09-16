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
3. **Use minimal detail level**: Keep `detail_level="minimal"` on `get_architecture_overview` to prevent token bloat (saving ~97% tokens).
4. **Auto-updating**: The graph automatically updates incrementally on file edits via hooks (`code-review-graph update --skip-flows`).
5. **Offline docs**: Consult the generated wiki in `.code-review-graph/wiki/index.md` for architectural community documentation.
