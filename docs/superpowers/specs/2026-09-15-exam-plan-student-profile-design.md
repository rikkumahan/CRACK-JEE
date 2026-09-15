# Exam/Syllabus Study Plan + Student Profile — Design Spec

## Purpose

The sister wants to input an upcoming exam and its syllabus and get a real
study plan out of it, built from the mastery/weak-topic/time-pattern data
the server already tracks. Along the way, evaluate whether a persisted
"student profile" (pace, subject strengths, time-management tendencies)
should feed that planning — decided yes, updated at natural session
boundaries.

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
  exam_date INTEGER NOT NULL,       -- epoch ms
  syllabus TEXT NOT NULL,           -- JSON array of {"subject", "concept"}
  plan_text TEXT,                   -- NULL until generate_exam_plan runs
  plan_updated_at INTEGER,
  created_at INTEGER NOT NULL
);

CREATE TABLE student_profile (
  id INTEGER PRIMARY KEY CHECK (id = 1),   -- singleton: one real student
  summary TEXT NOT NULL,             -- JSON, see "Profile fields" below
  session_count INTEGER NOT NULL DEFAULT 0,
  updated_at INTEGER NOT NULL
);
```

No new table for exam plan history/versioning and no outcome-tracking for
exam plans (unlike `interventions`/`get_progress`) — not asked for, and the
existing per-concept `get_progress` loop already covers "did the plan
work" at concept granularity once she's executing it. Add if actually
needed later.

No per-attempt session tagging (no `session_id` column on `attempts`) —
`student_profile.session_count` increments on each `end_study_session`
call; `avg_attempts_per_session` divides total attempts by that count.
Simpler than threading a session id through the write path for a number
that's only ever read in aggregate.

## New tools

1. **`set_exam(name, exam_date, syllabus)`** — `syllabus` is a list of
   `{subject, concept}`. Upserts each concept via the existing
   `find_or_create_concept` (dedup already handled), inserts the exam row,
   returns `{exam_id, name, exam_date, syllabus}`.
2. **`list_exams()`** — returns `[{id, name, exam_date, has_plan}]` so the
   LLM can resolve "my upcoming Physics exam" to an `exam_id` without the
   user tracking numbers.
3. **`get_exam(exam_id)`** — full detail: syllabus + `plan_text` (null if
   not yet generated).
4. **`generate_exam_plan(exam_id, plan_text)`** — persists the
   LLM-composed plan text + `plan_updated_at`. Mirrors
   `generate_daily_plan`'s contract exactly (compose first, this just
   saves).
5. **`end_study_session()`** — the session-end signal. LLM calls this when
   it detects the student wrapping up ("done for today", "that's it").
   Recomputes and upserts `student_profile` from current data (see below).
6. **`get_student_profile()`** — read-only getter. Returns the stored
   profile, or an explicit "no sessions recorded yet" shape if
   `session_count == 0` (so the LLM doesn't treat empty/zero as a real
   signal).

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
  unattempted from denominator, matching `get_weak_topics`'s
  `attempted_accuracy`).
- `overall_skip_rate`: `unattempted / total` across all attempts.
- `stuck_concept_rate`: fraction of concepts where `get_time_patterns`'s
  existing `stuck_pattern` heuristic is true — reuses that logic, doesn't
  reimplement it.
- `avg_revision_lag_days`: average `days_since_last_attempt` across
  concepts currently `due_now` per `get_revision_due`'s existing logic —
  reuses that logic too.

No new heuristics invented — this table is an aggregation layer over
signals the server already computes elsewhere.

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
`generate_exam_plan`'s `plan_text`. Add a line describing when to call
`end_study_session` (natural "wrapping up" language from the student).

## Testing

TDD per repo convention. New test files: `tests/test_exams.py` (schema,
`set_exam` dedup/upsert, `list_exams`, `get_exam`),
`tests/test_student_profile.py` (`end_study_session` computation across
controlled fixture data, `get_student_profile` empty-state and populated
cases). Existing `tests/test_analytics.py`/`test_revision_due.py`/
`test_time_patterns.py` logic gets reused, not duplicated — profile
computation calls into the same `db.py` functions where possible.

## What I'm not doing

- No deterministic day-by-day scheduler (approach B) — LLM composes the
  full plan text, same as every other plan in this system.
- No syllabus-scoped analytics tools — reuse subject-scoped ones.
- No exam-plan outcome tracking (no `get_progress` equivalent for exams).
- No per-attempt session tagging — `session_count` is enough for the one
  aggregate stat (`avg_attempts_per_session`) that needs it.
- No multi-student support in `student_profile` — singleton row, matching
  this whole project's single-real-student scope.
