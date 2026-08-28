@AGENTS.md

## Claude Code specific
- Default to Sonnet for routine work; escalate to Opus only for complex
  refactors or architecture decisions.
- Tag docs/decisions.md entries with [claude-code].
- Modular rules live in .claude/rules/ (auto-loaded). Keep this file short.