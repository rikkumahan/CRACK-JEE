#!/usr/bin/env bash
# Installs tracked hooks into the DEFAULT .git/hooks (no custom
# core.hooksPath — avoids the Claude Code worktree/hooksPath overwrite bug).
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$(git rev-parse --git-path hooks)"
mkdir -p "$HOOKS_DIR"
for h in pre-commit commit-msg; do
  if [ -f "$ROOT/.githooks-src/$h" ]; then
    cp "$ROOT/.githooks-src/$h" "$HOOKS_DIR/$h"
    chmod +x "$HOOKS_DIR/$h"
    echo "· installed $h -> $HOOKS_DIR/$h"
  fi
done
if git config --local --get core.hooksPath >/dev/null 2>&1; then
  echo "local core.hooksPath was set — unsetting (worktree-safety)."
  git config --local --unset core.hooksPath || true
fi
echo "· hooks installed."