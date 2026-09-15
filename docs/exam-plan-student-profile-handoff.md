# Handoff: Exam/Syllabus Study Plan + Student Profile

_Written 2026-09-15 by Claude Code, for Antigravity to implement. Unlike
the synthetic-jee-kt handoff, there's no design work left to do here — the
plan below already has exact code and tests for every step. Follow it
task-by-task, don't re-derive anything._

Read in this order:

1. [`docs/superpowers/specs/2026-09-15-exam-plan-student-profile-design.md`](superpowers/specs/2026-09-15-exam-plan-student-profile-design.md)
   — the design and why it's shaped this way. Skim for context.
2. [`docs/superpowers/plans/2026-09-15-exam-plan-student-profile.md`](superpowers/plans/2026-09-15-exam-plan-student-profile.md)
   — the actual work. 8 tasks, each with failing-test-first code, the
   implementation, and the exact `pytest` command to confirm it passes.
   This is TDD per `AGENTS.md` — write each task's test, watch it fail,
   then implement, in that order, every task.

## One correction to the plan's own commit message examples

The plan's `git commit` steps say `feat(claude): ...` throughout — that's
because Claude Code wrote it assuming Claude Code would execute it. Per
`AGENTS.md`'s own rule (`<type>(<tool>): summary`), use `(antigravity)`
instead: `feat(antigravity): add exams/exam_plans/student_profile schema`,
etc. Same for the `docs/decisions.md` entry in Task 8 — tag it
`[antigravity]`, not `[claude-code]`, and use the
`[antigravity/exam-plan-student-profile]` branch name in the log line.

## Antigravity workflow (per `AGENTS.md`)

- Branch: `antigravity/exam-plan-student-profile`, own worktree — do not
  work in the main checkout or a sibling worktree.
- This is normally Claude Code's lane (backend logic) per `AGENTS.md`'s
  default routing table — routed to Antigravity this time by explicit
  user choice, not a change to the routing convention.
- Read `docs/setup.md` for the exact test command before starting —
  currently `uv run pytest tests/ -v` (Node is decommissioned, no lint
  command configured). Never guess it.
- Append `[claimed]` when starting, `[done]` or `[blocked]` when you stop,
  to `docs/decisions.md`, in the repo's standard format.
- All 8 tasks' tests must pass — plan's Task 7 Step 6 and Task 8 Step 5
  both call for a full `uv run pytest tests/ -v` run with zero failures
  before marking done.
- Do not merge this branch — that's a human review step. Claude Code will
  verify and merge once you report `[done]`.
