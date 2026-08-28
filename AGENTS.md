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