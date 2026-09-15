# Exam/Syllabus Study Plan + Student Profile — Design Spec

## Purpose

The sister wants to input an upcoming exam and its syllabus and get a real
study plan out of it, built from the mastery/weak-topic/time-pattern data
the server already tracks. Along the way, evaluate whether a persisted
"student profile" (pace, subject strengths, time-management tendencies)
should feed that planning — decided yes, updated at natural session
boundaries.

Revised after a self-verification pass against the actual codebase and a
joint review round — see "Revision notes" at the bottom for what changed
from the first draft and why.

## Approach (chosen: A)

Reuse the existing "LLM composes, tool persists" split already used by
`generate_daily_plan`/`create_intervention`, at exam scope instead of
single-concept scope. No new scheduling algorithm — the LLM calls the
existing analytics tools (per subject in the syllabus) plus the new
`get_student_profile`, reasons over them, and writes the plan text itself;
the server only stores state and does arithmetic. This was chosen over a
deterministic day-by-day scheduler because time allocation trade-offs
(depth vs. breadth vs. days-until-exam) are judgment calls, and `ex1.md`
§3's standing principle is that the LLM handles judgment while code handles
calculation/persistence.

## Schema additions (`src/db.py` `init_db`)

```sql
CREATE TABLE exams (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  exam_date TEXT NOT NULL,          -- "YYYY-MM-DD", not epoch ms (see below)
  syllabus TEXT NOT NULL,           -- JSON array of {subject, concept, concept_id}
  created_at INTEGER NOT NULL
);

CREATE TABLE exam_plans (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  exam_id INTEGER NOT NULL REFERENCES exams(id),
  plan_text TEXT NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE TABLE student_profile (
  id INTEGER PRIMARY KEY CHECK (id = 1),   -- singleton: one real student
  summary TEXT NOT NULL,             -- JSON, see "Profile fields" below
  session_count INTEGER NOT NULL DEFAULT 0,
  updated_at INTEGER NOT NULL
);
```

**`exam_date` is a plain string, not epoch ms.** Every existing timestamp
column (`created_at`, `last_attempt_at`, etc.) is server-generated —
nothing in this codebase today asks the LLM to produce a timestamp itself.
Exam date is inherently LLM-supplied (it comes from what she says), so
epoch-ms would be the first case of asking the LLM to do timestamp math,
with real risk of timezone/off-by-one errors. `"YYYY-MM-DD"` is simple for
the LLM to produce correctly from natural language, and the server does
`datetime.date` arithmetic for "days until exam," not the LLM.

**`exam_plans` is a history table, not a column on `exams`.** Regenerating
a plan inserts a new row rather than overwriting — enables `get_exam_progress`
(below) to follow up on whether a specific plan actually worked, and keeps
a record of what was recommended over time as the exam approaches.

No per-attempt session tagging (no `session_id` column on `attempts`) —
`student_profile.session_count` increments on each `end_study_session`
call that actually finds new data (see "Empty sessions" below);
`avg_attempts_per_session` divides total attempts by that count. Simpler
than threading a session id through the write path for a number that's
only ever read in aggregate.

## New tools

1. **`set_exam(name, exam_date, syllabus)`** — `syllabus` is a list of
   `{subject, concept}`. Upserts each concept via the existing
   `find_or_create_concept` (dedup already handled), resolves each to a
   `concept_id`, stores the syllabus JSON with those ids included, inserts
   the exam row. Returns `{exam_id, name, exam_date, syllabus}`.
2. **`list_exams()`** — returns `[{id, name, exam_date, has_plan}]` so the
   LLM can resolve "my upcoming Physics exam" to an `exam_id` without the
   user tracking numbers. `has_plan` = at least one row in `exam_plans` for
   that exam.
3. **`get_exam(exam_id)`** — full detail: syllabus, `not_yet_attempted`
   (syllabus entries with zero rows in `attempts` — see below), and the
   latest plan's `plan_text`/`created_at` (null if none generated yet).
4. **`generate_exam_plan(exam_id, plan_text)`** — inserts a new row into
   `exam_plans`. Mirrors `generate_daily_plan`'s contract (compose first,
   this just saves) but keeps history instead of overwriting.
5. **`get_exam_progress(exam_id)`** — reuses `get_progress`'s before/after
   accuracy-split logic, aggregated across every concept in the syllabus
   instead of one, split at the latest plan's `created_at`. Answers "did
   the last plan actually work" the same way `get_progress` does for a
   single-concept intervention.
6. **`end_study_session()`** — the session-end signal. LLM calls this when
   it detects the student wrapping up ("done for today", "that's it"). If
   no attempts were logged since the last `student_profile.updated_at`
   (or ever, if no profile exists yet), it's a no-op — returns the
   existing profile unchanged, does not increment `session_count`. This
   covers "she came just for a suggestion, logged nothing" without
   diluting `avg_attempts_per_session` with a meaningless zero. Otherwise
   recomputes and upserts `student_profile`.
7. **`get_student_profile()`** — read-only getter. Returns the stored
   profile, or an explicit "no sessions recorded yet" shape if
   `session_count == 0`.

## `not_yet_attempted` (used by `get_exam`)

`get_weak_topics`/`get_concept_state` both join against
`attempts`/`student_concept_state` — a syllabus concept with zero logged
attempts simply doesn't appear in either tool's output, it isn't flagged
as "zero data," it's just absent. Relying on the LLM to notice an absence
across a list diff is unreliable, so `get_exam` computes this directly:
for each `concept_id` in the syllabus, `SELECT COUNT(*) FROM attempts
WHERE concept_id = ?` — zero means "not yet attempted." Returned as an
explicit list so the plan can't quietly skip topics she hasn't started.

## Profile fields (`student_profile.summary`, JSON)

Computed in one new `db.update_student_profile()` call, over all subjects
(loops `SELECT DISTINCT subject FROM concepts`):

```json
{
  "avg_attempts_per_session": 8.3,
  "subject_accuracy": {"Physics": 0.62, "Chemistry": 0.71},
  "overall_skip_rate": 0.15,
  "stuck_concept_rate": 0.22,
  "avg_revision_lag_days": 4.2
}
```

- `avg_attempts_per_session`: `COUNT(*) FROM attempts / session_count`.
- `subject_accuracy`: per-subject `correct / attempted` (excludes
  unattempted from the denominator, matching `get_weak_topics`'s
  `attempted_accuracy`).
- `overall_skip_rate`: `unattempted / total` across all attempts.
- `stuck_concept_rate`: fraction of concepts where `get_time_patterns`'s
  existing `stuck_pattern` heuristic is true — reuses that logic per
  subject, doesn't reimplement it.
- `avg_revision_lag_days`: average `days_since_last_attempt` across
  concepts currently `due_now` per `get_revision_due`'s existing logic —
  reused per subject, not reimplemented.

No new heuristics invented — this is an aggregation layer over signals the
server already computes elsewhere.

## Empty sessions

`end_study_session` must distinguish "she studied, then wrapped up" from
"she asked for advice and left without logging anything." The no-op check
(any `attempts.created_at > student_profile.updated_at`, or any attempt at
all if `session_count == 0`) handles this directly: an advice-only visit
triggers zero `log_performance_input` calls, so the check finds nothing
new and skips the update entirely. Nothing is lost — it's correctly
excluded from the pace stat rather than counted as a zero-attempt session.

## No new "syllabus-scoped" analytics tool

Considered adding a variant of `get_weak_topics`/`get_concept_state`/etc.
that filters to an arbitrary concept list (the syllabus) instead of a
whole subject. Skipped: the syllabus rarely spans more than 1-2 subjects,
and the LLM already gets the full syllabus list back from `get_exam`. It
can call the existing per-subject tools (already scoped correctly) and
cross-reference against the syllabus list itself when composing the plan
— no new filtering layer to build or test.

## `docs/chat-client-system-prompt.md` update

Add: after `set_exam`/on a planning request referencing an exam, call
`get_exam` (or `list_exams` + `get_exam`) plus `get_weak_topics`/
`get_concept_state`/`get_revision_due`/`get_time_patterns` per syllabus
subject, plus `get_student_profile`, before composing
`generate_exam_plan`'s `plan_text` — explicitly checking `not_yet_attempted`
so no syllabus topic goes uncovered. Add a line describing when to call
`end_study_session` (natural "wrapping up" language from the student), and
when to call `get_exam_progress` (after her next test covering exam
syllabus topics, same spirit as the existing `get_progress` step).

## Testing

TDD per repo convention. New test files: `tests/test_exams.py` (schema,
`set_exam` dedup/upsert, `list_exams`, `get_exam` incl. `not_yet_attempted`,
`generate_exam_plan` history behavior, `get_exam_progress` before/after
split), `tests/test_student_profile.py` (`end_study_session` computation
across controlled fixture data, the empty-session no-op case,
`get_student_profile` empty-state and populated cases). Existing
`tests/test_analytics.py`/`test_revision_due.py`/`test_time_patterns.py`
logic gets reused, not duplicated — profile computation calls into the
same `db.py` functions where possible.

## What I'm not doing

- No deterministic day-by-day scheduler (approach B) — LLM composes the
  full plan text, same as every other plan in this system.
- No syllabus-scoped analytics tools — reuse subject-scoped ones.
- No per-attempt session tagging — the no-op-on-empty-session check plus
  `session_count` is enough for the one aggregate stat
  (`avg_attempts_per_session`) that needs it.
- No multi-student support in `student_profile` — singleton row, matching
  this whole project's single-real-student scope.
- No editing/deleting past exam plans — `exam_plans` is append-only, same
  spirit as `docs/decisions.md`.

## Revision notes (from self-verification + joint review)

First draft specced `exam_date` as epoch ms and `plan_text` as a single
overwritable column on `exams` with no outcome tracking. Verifying against
the actual code (inner-join behavior on `get_weak_topics`/
`get_concept_state`, the fact that no tool anywhere asks the LLM to supply
a timestamp) surfaced four real gaps, resolved together: `exam_date` →
string not epoch ms; never-attempted syllabus topics → surfaced explicitly
instead of relying on LLM inference; plan history → kept via a new
`exam_plans` table plus `get_exam_progress`, instead of overwrite-in-place;
empty sessions → no-op instead of always incrementing `session_count`.
