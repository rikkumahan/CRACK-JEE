#!/usr/bin/env bash
# Create an isolated worktree for a tool+task, and open it in its own
# VS Code window (recommended: one window per active worktree).
#
# Usage: scripts/new-worktree.sh <tool> <task-name> [--no-open]
#   e.g. scripts/new-worktree.sh claude auth-refactor
set -euo pipefail
tool="${1:?usage: new-worktree.sh <tool> <task-name> [--no-open]}"
task="${2:?usage: new-worktree.sh <tool> <task-name> [--no-open]}"
no_open=false
[ "${3:-}" = "--no-open" ] && no_open=true

ROOT="$(git rev-parse --show-toplevel)"
branch="${tool}/${task}"
dir="${ROOT}/../$(basename "$ROOT")-${tool}-${task}"

git worktree add "$dir" -b "$branch"
( cd "$dir" && bash "$ROOT/scripts/install-hooks.sh" )

echo ""
echo "worktree ready: $dir  (branch $branch)"

if [ "$no_open" = false ] && command -v code >/dev/null 2>&1; then
  code -n "$dir"
  echo "opened in a new VS Code window."
else
  echo "open manually with: code -n \"$dir\""
fi