# Exam/Syllabus Study Plan + Student Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the student set an upcoming exam + syllabus, get an LLM-composed study plan that reasons over her existing mastery/weak-topic/time-pattern data, follow up on whether that plan worked, and persist a "study pattern" profile updated at natural session boundaries to inform future planning.

**Architecture:** Pure additive extension of `src/db.py` (3 new tables, ~9 new functions) plus 7 new thin FastMCP tool wrappers in `src/tools/`, following the exact "LLM composes, tool persists" pattern already used by `generate_daily_plan`/`get_progress`. No new scheduling logic, no modification to BKT/decay math — this is a read/aggregate/persist layer on top of what already exists.

**Tech Stack:** Python, `fastmcp`, `sqlite3` (stdlib), `pytest` + `pytest-asyncio` (already in the project).

**Spec:** `docs/superpowers/specs/2026-09-15-exam-plan-student-profile-design.md`

## Global Constraints

- `exam_date` is stored and passed as a plain `"YYYY-MM-DD"` string, never epoch ms — no tool anywhere in this codebase asks the LLM to produce a timestamp itself, and this must not become the first one.
- Every new `db.py` function takes an optional `conn=None` parameter and falls back to `get_connection()`, matching every existing function in the file. Every new function that writes must call `connection.commit()` itself.
- `exam_plans` is append-only (insert only, never update/delete a row) — mirrors `docs/decisions.md`'s own append-only convention and is required for `get_exam_progress` to have a real "before this plan" boundary.
- Reuse existing logic instead of reimplementing it: `stuck_concept_rate` must call `get_time_patterns`, `avg_revision_lag_days` must call `get_revision_due` — not duplicate their SQL.
- Every new tool file follows the exact shape of `src/tools/get_concept_state.py`: one `register_<tool_name>(server: FastMCP)` function, one `@server.tool(name=..., description=...)`-decorated inner function, `json.dumps(...)` the `db.py` call's return value.
- Commit message format: `<type>(claude): summary` (see `AGENTS.md`) — this plan uses `feat(claude)`/`test(claude)`/`docs(claude)` throughout.

---

## Task 1: Schema — `exams`, `exam_plans`, `student_profile` tables

**Files:**
- Modify: `src/db.py:1-11` (imports), `src/db.py:27-76` (`init_db`'s `executescript`)
- Test: `tests/test_exam_schema.py` (new)

**Interfaces:**
- Produces: three new tables other tasks' functions read/write directly via raw SQL — no wrapper function needed for schema itself.

- [ ] **Step 1: Write the failing test**

Create `tests/test_exam_schema.py`:

```python
import pytest
from db import init_db


@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_jee.db"
    conn = init_db(db_path)
    yield conn, db_path
    conn.close()


def test_schema_creates_exam_and_profile_tables(test_db):
    conn, _ = test_db
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert {"exams", "exam_plans", "student_profile"}.issubset(tables)


def test_student_profile_is_a_singleton(test_db):
    conn, _ = test_db
    conn.execute(
        "INSERT INTO student_profile (id, summary, session_count, updated_at) VALUES (1, '{}', 0, 0)"
    )
    conn.commit()
    with pytest.raises(Exception):
        conn.execute(
            "INSERT INTO student_profile (id, summary, session_count, updated_at) VALUES (2, '{}', 0, 0)"
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_exam_schema.py -v`
Expected: FAIL — tables don't exist yet.

- [ ] **Step 3: Add `import json` and the three tables**

In `src/db.py`, add `json` to the imports at the top (line 1-6 currently reads `os`, `re`, `sqlite3`, `time`; add `json` alongside them):

```python
import json
import os
import re
import sqlite3
import time
```

Then, inside `init_db`'s `conn.executescript("""...""")` block, add these three tables right after the existing `intervention_outcomes` table definition (before the closing `""")`):

```sql
      CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        exam_date TEXT NOT NULL,
        syllabus TEXT NOT NULL,
        created_at INTEGER NOT NULL
      );

      CREATE TABLE IF NOT EXISTS exam_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER NOT NULL REFERENCES exams(id),
        plan_text TEXT NOT NULL,
        created_at INTEGER NOT NULL
      );

      CREATE TABLE IF NOT EXISTS student_profile (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        summary TEXT NOT NULL,
        session_count INTEGER NOT NULL DEFAULT 0,
        updated_at INTEGER NOT NULL
      );
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_exam_schema.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/db.py tests/test_exam_schema.py
git commit -m "feat(claude): add exams/exam_plans/student_profile schema"
```

---

## Task 2: `db.set_exam` + `db.list_exams`

**Files:**
- Modify: `src/db.py` (append new functions after `get_progress`, i.e. after line ~449)
- Test: `tests/test_exams.py` (new — this file grows across Tasks 2-4)

**Interfaces:**
- Consumes: `find_or_create_concept(name: str, subject: str, conn=None) -> int` (existing, `src/db.py:107`)
- Produces:
  - `set_exam(name: str, exam_date: str, syllabus: List[Dict[str, str]], conn=None) -> Dict[str, Any]` — returns `{exam_id, name, exam_date, syllabus}` where `syllabus` is `[{subject, concept, concept_id}, ...]`
  - `list_exams(conn=None) -> List[Dict[str, Any]]` — returns `[{id, name, exam_date, has_plan}, ...]`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_exams.py`:

```python
import pytest
from db import init_db, set_exam, list_exams, generate_exam_plan


@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_jee.db"
    conn = init_db(db_path)
    yield conn, db_path
    conn.close()


def test_set_exam_creates_exam_and_dedupes_concepts(test_db):
    conn, _ = test_db
    result = set_exam(
        "JEE Main Mock 3",
        "2026-11-15",
        [
            {"subject": "Physics", "concept": "Rotational Motion"},
            {"subject": "Physics", "concept": "rotational motion"},
        ],
        conn=conn,
    )
    assert result["name"] == "JEE Main Mock 3"
    assert result["exam_date"] == "2026-11-15"
    concept_ids = {item["concept_id"] for item in result["syllabus"]}
    assert len(concept_ids) == 1


def test_list_exams_reports_has_plan(test_db):
    conn, _ = test_db
    exam = set_exam(
        "Chem Unit Test", "2026-10-01",
        [{"subject": "Chemistry", "concept": "Aldehydes"}], conn=conn,
    )
    exams = list_exams(conn=conn)
    assert len(exams) == 1
    assert exams[0]["name"] == "Chem Unit Test"
    assert exams[0]["has_plan"] is False

    generate_exam_plan(exam["exam_id"], "Study aldehyde reactions.", conn=conn)
    exams = list_exams(conn=conn)
    assert exams[0]["has_plan"] is True
```

Note: this test file imports `generate_exam_plan`, which doesn't exist yet — that's expected, it's written in Task 3. This test file is shared across Tasks 2-4.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_exams.py -v`
Expected: FAIL — `ImportError: cannot import name 'set_exam'` (and `generate_exam_plan`).

- [ ] **Step 3: Implement `set_exam` and `list_exams`**

Append to `src/db.py`, after `get_progress`:

```python
def set_exam(
    name: str,
    exam_date: str,
    syllabus: List[Dict[str, str]],
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """syllabus: list of {"subject": ..., "concept": ...}. Resolves each
    entry through find_or_create_concept (same dedup as log_performance_input)
    and stores the resolved concept_id alongside subject/concept."""
    connection = conn if conn is not None else get_connection()
    resolved = []
    for item in syllabus:
        concept_id = find_or_create_concept(item["concept"], item["subject"], conn=connection)
        resolved.append({"subject": item["subject"], "concept": item["concept"], "concept_id": concept_id})

    created_at = int(time.time() * 1000)
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO exams (name, exam_date, syllabus, created_at) VALUES (?, ?, ?, ?)",
        (name, exam_date, json.dumps(resolved), created_at),
    )
    connection.commit()
    return {"exam_id": cursor.lastrowid, "name": name, "exam_date": exam_date, "syllabus": resolved}


def list_exams(conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    connection = conn if conn is not None else get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT e.id, e.name, e.exam_date,
               EXISTS(SELECT 1 FROM exam_plans p WHERE p.exam_id = e.id) AS has_plan
        FROM exams e
        ORDER BY e.exam_date
        """
    )
    return [
        {"id": row[0], "name": row[1], "exam_date": row[2], "has_plan": bool(row[3])}
        for row in cursor.fetchall()
    ]
```

- [ ] **Step 4: Run test to verify `set_exam`/`list_exams` behavior passes**

Run: `uv run pytest tests/test_exams.py::test_set_exam_creates_exam_and_dedupes_concepts -v`
Expected: PASS. (`test_list_exams_reports_has_plan` still fails — needs `generate_exam_plan`, Task 3.)

- [ ] **Step 5: Commit**

```bash
git add src/db.py tests/test_exams.py
git commit -m "feat(claude): add set_exam and list_exams"
```

---

## Task 3: `db.get_exam` (with `not_yet_attempted`)

**Files:**
- Modify: `src/db.py` (append after `list_exams`)
- Test: `tests/test_exams.py` (extend)

**Interfaces:**
- Consumes: `exams`/`exam_plans` tables from Task 1, `set_exam`'s stored syllabus JSON shape (`{subject, concept, concept_id}`) from Task 2.
- Produces: `get_exam(exam_id: int, conn=None) -> Dict[str, Any]` — returns
  `{exam_id, name, exam_date, syllabus, not_yet_attempted, latest_plan_text, latest_plan_created_at}`.
  Raises `ValueError` for an unknown `exam_id` (matches `get_progress`'s existing convention).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_exams.py`:

```python
def test_get_exam_flags_not_yet_attempted(test_db):
    conn, _ = test_db
    exam = set_exam(
        "Physics Final", "2026-12-01",
        [
            {"subject": "Physics", "concept": "Friction"},
            {"subject": "Physics", "concept": "Optics"},
        ],
        conn=conn,
    )
    friction_id = next(i["concept_id"] for i in exam["syllabus"] if i["concept"] == "Friction")
    conn.execute(
        "INSERT INTO attempts (concept_id, result, created_at) VALUES (?, 'correct', 1000)",
        (friction_id,),
    )
    conn.commit()

    from db import get_exam
    detail = get_exam(exam["exam_id"], conn=conn)
    not_yet = {item["concept"] for item in detail["not_yet_attempted"]}
    assert not_yet == {"Optics"}
    assert detail["latest_plan_text"] is None


def test_get_exam_raises_for_unknown_exam(test_db):
    conn, _ = test_db
    from db import get_exam
    with pytest.raises(ValueError):
        get_exam(9999, conn=conn)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_exams.py::test_get_exam_flags_not_yet_attempted -v`
Expected: FAIL — `ImportError: cannot import name 'get_exam'`.

- [ ] **Step 3: Implement `get_exam`**

Append to `src/db.py`:

```python
def get_exam(exam_id: int, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    connection = conn if conn is not None else get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT name, exam_date, syllabus FROM exams WHERE id = ?", (exam_id,))
    row = cursor.fetchone()
    if row is None:
        raise ValueError(f"No exam with id {exam_id}")
    name, exam_date, syllabus_json = row
    syllabus = json.loads(syllabus_json)

    not_yet_attempted = []
    for item in syllabus:
        cursor.execute("SELECT COUNT(*) FROM attempts WHERE concept_id = ?", (item["concept_id"],))
        if cursor.fetchone()[0] == 0:
            not_yet_attempted.append({"subject": item["subject"], "concept": item["concept"]})

    cursor.execute(
        "SELECT plan_text, created_at FROM exam_plans WHERE exam_id = ? ORDER BY created_at DESC LIMIT 1",
        (exam_id,),
    )
    plan_row = cursor.fetchone()

    return {
        "exam_id": exam_id,
        "name": name,
        "exam_date": exam_date,
        "syllabus": syllabus,
        "not_yet_attempted": not_yet_attempted,
        "latest_plan_text": plan_row[0] if plan_row else None,
        "latest_plan_created_at": plan_row[1] if plan_row else None,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_exams.py -v`
Expected: `test_get_exam_flags_not_yet_attempted` and `test_get_exam_raises_for_unknown_exam` PASS. (`test_list_exams_reports_has_plan` still pending Task 4.)

- [ ] **Step 5: Commit**

```bash
git add src/db.py tests/test_exams.py
git commit -m "feat(claude): add get_exam with not_yet_attempted tracking"
```

---

## Task 4: `db.generate_exam_plan` + `db.get_exam_progress`

**Files:**
- Modify: `src/db.py` (append after `get_exam`)
- Test: `tests/test_exams.py` (extend — this also unblocks `test_list_exams_reports_has_plan` from Task 2)

**Interfaces:**
- Consumes: `exams`/`exam_plans` tables, `get_exam`'s syllabus shape.
- Produces:
  - `generate_exam_plan(exam_id: int, plan_text: str, conn=None) -> Dict[str, Any]` — inserts a new `exam_plans` row (append-only), returns `{exam_id, plan_id, created_at}`. Raises `ValueError` for unknown `exam_id`.
  - `get_exam_progress(exam_id: int, conn=None) -> Dict[str, Any]` — returns `{exam_id, plan_created_at, accuracy_before, accuracy_after, total_before, total_after}`. Raises `ValueError` for unknown `exam_id` or if no plan has been generated yet.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_exams.py`:

```python
def test_generate_exam_plan_keeps_history(test_db):
    conn, _ = test_db
    exam = set_exam("Bio Retest", "2026-09-30", [{"subject": "Biology", "concept": "Genetics"}], conn=conn)
    generate_exam_plan(exam["exam_id"], "Plan v1", conn=conn)
    generate_exam_plan(exam["exam_id"], "Plan v2", conn=conn)

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM exam_plans WHERE exam_id = ?", (exam["exam_id"],))
    assert cursor.fetchone()[0] == 2

    from db import get_exam
    detail = get_exam(exam["exam_id"], conn=conn)
    assert detail["latest_plan_text"] == "Plan v2"


def test_generate_exam_plan_raises_for_unknown_exam(test_db):
    conn, _ = test_db
    with pytest.raises(ValueError):
        generate_exam_plan(9999, "Some plan", conn=conn)


def test_get_exam_progress_splits_before_and_after_latest_plan(test_db):
    conn, _ = test_db
    exam = set_exam("Physics Final", "2026-12-01", [{"subject": "Physics", "concept": "Friction"}], conn=conn)
    concept_id = exam["syllabus"][0]["concept_id"]

    conn.execute("INSERT INTO attempts (concept_id, result, created_at) VALUES (?, 'wrong', 1000)", (concept_id,))
    conn.execute("INSERT INTO attempts (concept_id, result, created_at) VALUES (?, 'wrong', 2000)", (concept_id,))
    conn.commit()

    from db import get_exam_progress
    generate_exam_plan(exam["exam_id"], "Focus on friction basics.", conn=conn)
    cursor = conn.cursor()
    cursor.execute("SELECT created_at FROM exam_plans WHERE exam_id = ?", (exam["exam_id"],))
    plan_created_at = cursor.fetchone()[0]

    conn.execute(
        "INSERT INTO attempts (concept_id, result, created_at) VALUES (?, 'correct', ?)",
        (concept_id, plan_created_at + 1000),
    )
    conn.commit()

    progress = get_exam_progress(exam["exam_id"], conn=conn)
    assert progress["accuracy_before"] == pytest.approx(0.0)
    assert progress["accuracy_after"] == pytest.approx(1.0)
    assert progress["total_before"] == 2
    assert progress["total_after"] == 1


def test_get_exam_progress_raises_when_no_plan_yet(test_db):
    conn, _ = test_db
    exam = set_exam("No Plan Exam", "2026-12-15", [{"subject": "Physics", "concept": "Optics"}], conn=conn)
    from db import get_exam_progress
    with pytest.raises(ValueError):
        get_exam_progress(exam["exam_id"], conn=conn)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_exams.py -v`
Expected: FAIL — `ImportError: cannot import name 'get_exam_progress'` (and `generate_exam_plan` still missing).

- [ ] **Step 3: Implement `generate_exam_plan` and `get_exam_progress`**

Append to `src/db.py`:

```python
def generate_exam_plan(
    exam_id: int, plan_text: str, conn: Optional[sqlite3.Connection] = None
) -> Dict[str, Any]:
    connection = conn if conn is not None else get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM exams WHERE id = ?", (exam_id,))
    if cursor.fetchone() is None:
        raise ValueError(f"No exam with id {exam_id}")

    created_at = int(time.time() * 1000)
    cursor.execute(
        "INSERT INTO exam_plans (exam_id, plan_text, created_at) VALUES (?, ?, ?)",
        (exam_id, plan_text, created_at),
    )
    connection.commit()
    return {"exam_id": exam_id, "plan_id": cursor.lastrowid, "created_at": created_at}


def get_exam_progress(
    exam_id: int, conn: Optional[sqlite3.Connection] = None
) -> Dict[str, Any]:
    """Reuses get_progress's before/after accuracy split, aggregated across
    every concept in the exam's syllabus instead of one."""
    connection = conn if conn is not None else get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT syllabus FROM exams WHERE id = ?", (exam_id,))
    row = cursor.fetchone()
    if row is None:
        raise ValueError(f"No exam with id {exam_id}")
    concept_ids = [item["concept_id"] for item in json.loads(row[0])]

    cursor.execute(
        "SELECT created_at FROM exam_plans WHERE exam_id = ? ORDER BY created_at DESC LIMIT 1",
        (exam_id,),
    )
    plan_row = cursor.fetchone()
    if plan_row is None:
        raise ValueError(f"No plan generated yet for exam {exam_id}")
    plan_created_at = plan_row[0]

    placeholders = ",".join("?" * len(concept_ids))
    cursor.execute(
        f"""
        SELECT
          SUM(CASE WHEN created_at < ? THEN 1 ELSE 0 END),
          SUM(CASE WHEN created_at < ? AND result = 'correct' THEN 1 ELSE 0 END),
          SUM(CASE WHEN created_at >= ? THEN 1 ELSE 0 END),
          SUM(CASE WHEN created_at >= ? AND result = 'correct' THEN 1 ELSE 0 END)
        FROM attempts
        WHERE concept_id IN ({placeholders})
        """,
        (plan_created_at, plan_created_at, plan_created_at, plan_created_at, *concept_ids),
    )
    total_before, correct_before, total_after, correct_after = cursor.fetchone()
    total_before = total_before or 0
    correct_before = correct_before or 0
    total_after = total_after or 0
    correct_after = correct_after or 0

    return {
        "exam_id": exam_id,
        "plan_created_at": plan_created_at,
        "accuracy_before": round(correct_before / total_before, 4) if total_before else None,
        "accuracy_after": round(correct_after / total_after, 4) if total_after else None,
        "total_before": total_before,
        "total_after": total_after,
    }
```

- [ ] **Step 4: Run all exam tests to verify they pass**

Run: `uv run pytest tests/test_exams.py -v`
Expected: all PASS (7 tests total across Tasks 2-4).

- [ ] **Step 5: Commit**

```bash
git add src/db.py tests/test_exams.py
git commit -m "feat(claude): add generate_exam_plan and get_exam_progress"
```

---

## Task 5: Extend `get_revision_due` with `days_since_last_attempt`

**Files:**
- Modify: `src/db.py:280-331` (`get_revision_due`)
- Test: `tests/test_revision_due.py` (extend)

**Why:** `student_profile.avg_revision_lag_days` (Task 6) needs each due concept's `days_since_last_attempt`. `get_revision_due` already computes `days_since` internally but doesn't return it — adding it as one more key on the existing return dict is additive (existing tests assert via subscript, not full-dict equality, matching the precedent set when `get_weak_topics` gained `attempted_accuracy`/`skip_rate`) and avoids Task 6 reimplementing the decay-threshold query.

**Interfaces:**
- Modifies: `get_revision_due`'s return shape — each dict gains `"days_since_last_attempt": round(days_since, 2)`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_revision_due.py`:

```python
def test_due_now_row_includes_days_since_last_attempt(test_db):
    conn, _ = test_db
    cid = find_or_create_concept("Friction", "Physics", conn=conn)
    record_bkt_update(cid, "correct", attempt_time_ms=0, conn=conn)

    now = 60 * DAY_MS
    result = get_revision_due("Physics", conn=conn, now_ms=now, threshold=0.9)
    assert result[0]["days_since_last_attempt"] == pytest.approx(60.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_revision_due.py::test_due_now_row_includes_days_since_last_attempt -v`
Expected: FAIL — `KeyError: 'days_since_last_attempt'`.

- [ ] **Step 3: Add the field**

In `src/db.py`, inside `get_revision_due`, find this block (around line 320-328):

```python
        if due_now or due_soon:
            due.append(
                {
                    "id": cid,
                    "name": name,
                    "mastery_probability": round(current, 4),
                    "projected_mastery": round(projected, 4),
                    "due_now": due_now,
                }
            )
```

Replace it with:

```python
        if due_now or due_soon:
            due.append(
                {
                    "id": cid,
                    "name": name,
                    "mastery_probability": round(current, 4),
                    "projected_mastery": round(projected, 4),
                    "due_now": due_now,
                    "days_since_last_attempt": round(days_since, 2),
                }
            )
```

- [ ] **Step 4: Run tests to verify everything still passes**

Run: `uv run pytest tests/test_revision_due.py -v`
Expected: all PASS (5 tests — 4 existing + 1 new).

- [ ] **Step 5: Commit**

```bash
git add src/db.py tests/test_revision_due.py
git commit -m "feat(claude): add days_since_last_attempt to get_revision_due"
```

---

## Task 6: `db.update_student_profile` + `db.get_student_profile`

**Files:**
- Modify: `src/db.py` (append after `get_exam_progress`)
- Test: `tests/test_student_profile.py` (new)

**Interfaces:**
- Consumes: `get_time_patterns(subject, conn=None) -> List[Dict]` (existing, has a `stuck_pattern` bool key), `get_revision_due(subject, conn=None, now_ms=None) -> List[Dict]` (existing, now has `days_since_last_attempt` from Task 5, has a `due_now` bool key).
- Produces:
  - `update_student_profile(conn=None, now_ms=None) -> Dict[str, Any]` — no-ops (`{"updated": False}`) if no attempts happened since the last update (or ever, if never run before); otherwise recomputes and upserts, returns `{"updated": True, "summary": {...}, "session_count": int}`.
  - `get_student_profile(conn=None) -> Dict[str, Any]` — returns `{"session_count": 0, "summary": None}` if never updated, else `{"session_count": int, "summary": {...}, "updated_at": int}`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_student_profile.py`:

```python
import pytest
from db import init_db, find_or_create_concept, update_student_profile, get_student_profile


@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_jee.db"
    conn = init_db(db_path)
    yield conn, db_path
    conn.close()


def test_get_student_profile_empty_state(test_db):
    conn, _ = test_db
    profile = get_student_profile(conn=conn)
    assert profile["session_count"] == 0
    assert profile["summary"] is None


def test_update_student_profile_noop_when_nothing_logged(test_db):
    conn, _ = test_db
    result = update_student_profile(conn=conn)
    assert result["updated"] is False
    assert get_student_profile(conn=conn)["session_count"] == 0


def test_update_student_profile_computes_summary_fields(test_db):
    conn, _ = test_db
    physics_id = find_or_create_concept("Friction", "Physics", conn=conn)
    chem_id = find_or_create_concept("Aldehydes", "Chemistry", conn=conn)

    conn.executemany(
        "INSERT INTO attempts (concept_id, result, created_at) VALUES (?, ?, ?)",
        [
            (physics_id, "correct", 1000),
            (physics_id, "wrong", 2000),
            (physics_id, "unattempted", 3000),
            (chem_id, "correct", 4000),
        ],
    )
    conn.commit()

    result = update_student_profile(conn=conn, now_ms=5000)
    assert result["updated"] is True
    summary = result["summary"]
    assert summary["avg_attempts_per_session"] == 4.0
    assert summary["subject_accuracy"]["Physics"] == 0.5
    assert summary["subject_accuracy"]["Chemistry"] == 1.0
    assert summary["overall_skip_rate"] == 0.25
    assert "stuck_concept_rate" in summary
    assert "avg_revision_lag_days" in summary

    profile = get_student_profile(conn=conn)
    assert profile["session_count"] == 1
    assert profile["summary"] == summary


def test_update_student_profile_noop_on_second_call_with_no_new_attempts(test_db):
    conn, _ = test_db
    concept_id = find_or_create_concept("Friction", "Physics", conn=conn)
    conn.execute(
        "INSERT INTO attempts (concept_id, result, created_at) VALUES (?, 'correct', 1000)",
        (concept_id,),
    )
    conn.commit()

    first = update_student_profile(conn=conn, now_ms=2000)
    assert first["updated"] is True

    second = update_student_profile(conn=conn, now_ms=3000)
    assert second["updated"] is False
    assert get_student_profile(conn=conn)["session_count"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_student_profile.py -v`
Expected: FAIL — `ImportError: cannot import name 'update_student_profile'`.

- [ ] **Step 3: Implement `update_student_profile` and `get_student_profile`**

Append to `src/db.py`:

```python
def update_student_profile(
    conn: Optional[sqlite3.Connection] = None, now_ms: Optional[int] = None
) -> Dict[str, Any]:
    """Recomputes and upserts the singleton student_profile row. No-ops
    (returns {"updated": False}) if no attempts happened since the last
    update, or ever, if never run before — covers an advice-only visit
    where nothing was logged, so it doesn't dilute avg_attempts_per_session
    with a meaningless zero."""
    connection = conn if conn is not None else get_connection()
    now = now_ms if now_ms is not None else int(time.time() * 1000)
    cursor = connection.cursor()

    cursor.execute("SELECT session_count, updated_at FROM student_profile WHERE id = 1")
    existing = cursor.fetchone()
    since = existing[1] if existing else 0
    session_count = existing[0] if existing else 0

    cursor.execute("SELECT COUNT(*) FROM attempts WHERE created_at > ?", (since,))
    if cursor.fetchone()[0] == 0:
        return {"updated": False}

    session_count += 1

    cursor.execute("SELECT COUNT(*) FROM attempts")
    total_attempts = cursor.fetchone()[0]
    avg_attempts_per_session = round(total_attempts / session_count, 2)

    cursor.execute("SELECT DISTINCT subject FROM concepts")
    subjects = [row[0] for row in cursor.fetchall()]

    subject_accuracy: Dict[str, float] = {}
    for subject in subjects:
        cursor.execute(
            """
            SELECT SUM(CASE WHEN a.result = 'correct' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN a.result IN ('correct', 'wrong') THEN 1 ELSE 0 END)
            FROM attempts a JOIN concepts c ON c.id = a.concept_id
            WHERE c.subject = ?
            """,
            (subject,),
        )
        correct, attempted = cursor.fetchone()
        if attempted:
            subject_accuracy[subject] = round(correct / attempted, 4)

    cursor.execute(
        "SELECT SUM(CASE WHEN result = 'unattempted' THEN 1 ELSE 0 END), COUNT(*) FROM attempts"
    )
    unattempted, total = cursor.fetchone()
    overall_skip_rate = round(unattempted / total, 4) if total else 0.0

    stuck_count = 0
    concept_count = 0
    revision_lags: List[float] = []
    for subject in subjects:
        patterns = get_time_patterns(subject, conn=connection)
        concept_count += len(patterns)
        stuck_count += sum(1 for p in patterns if p["stuck_pattern"])

        for row in get_revision_due(subject, conn=connection, now_ms=now):
            if row["due_now"]:
                revision_lags.append(row["days_since_last_attempt"])

    stuck_concept_rate = round(stuck_count / concept_count, 4) if concept_count else 0.0
    avg_revision_lag_days = (
        round(sum(revision_lags) / len(revision_lags), 2) if revision_lags else None
    )

    summary = {
        "avg_attempts_per_session": avg_attempts_per_session,
        "subject_accuracy": subject_accuracy,
        "overall_skip_rate": overall_skip_rate,
        "stuck_concept_rate": stuck_concept_rate,
        "avg_revision_lag_days": avg_revision_lag_days,
    }

    cursor.execute(
        """
        INSERT INTO student_profile (id, summary, session_count, updated_at)
        VALUES (1, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            summary = excluded.summary,
            session_count = excluded.session_count,
            updated_at = excluded.updated_at
        """,
        (json.dumps(summary), session_count, now),
    )
    connection.commit()
    return {"updated": True, "summary": summary, "session_count": session_count}


def get_student_profile(conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    connection = conn if conn is not None else get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT summary, session_count, updated_at FROM student_profile WHERE id = 1")
    row = cursor.fetchone()
    if row is None:
        return {"session_count": 0, "summary": None}
    summary_json, session_count, updated_at = row
    return {"session_count": session_count, "summary": json.loads(summary_json), "updated_at": updated_at}
```

`get_time_patterns` and `get_revision_due` are already imported implicitly — they're defined earlier in the same `db.py` module, so no new import line is needed (module-level functions calling each other within the same file).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_student_profile.py -v`
Expected: all 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/db.py tests/test_student_profile.py
git commit -m "feat(claude): add update_student_profile and get_student_profile"
```

---

## Task 7: Tool wrappers + `server.py` registration

**Files:**
- Create: `src/tools/set_exam.py`, `src/tools/list_exams.py`, `src/tools/get_exam.py`, `src/tools/generate_exam_plan.py`, `src/tools/get_exam_progress.py`, `src/tools/end_study_session.py`, `src/tools/get_student_profile.py`
- Modify: `src/server.py`
- Test: `tests/test_exams.py` (extend, end-to-end), `tests/test_student_profile.py` (extend, end-to-end)

**Interfaces:**
- Consumes: every `db.py` function from Tasks 2, 4, 6.
- Produces: 7 new MCP tool names registered on `mcp`: `set_exam`, `list_exams`, `get_exam`, `generate_exam_plan`, `get_exam_progress`, `end_study_session`, `get_student_profile`.

- [ ] **Step 1: Write the failing end-to-end tests**

Add to `tests/test_exams.py` (needs `import json`, `pytest`, and `from fastmcp import Client` — add these imports at the top of the file alongside the existing ones):

```python
import json
from fastmcp import Client


@pytest.mark.asyncio
async def test_exam_plan_wired_end_to_end():
    from server import mcp
    import db

    if db._default_conn is not None:
        db._default_conn.close()
        db._default_conn = None
    from pathlib import Path
    db_path = Path(__file__).resolve().parent.parent / "data" / "jee.db"
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass

    async with Client(mcp) as client:
        set_result = await client.call_tool(
            "set_exam",
            {
                "name": "Physics Unit Test",
                "exam_date": "2026-11-01",
                "syllabus": [{"subject": "Physics", "concept": "Friction"}],
            },
        )
        exam_id = json.loads(set_result.content[0].text)["exam_id"]

        list_result = await client.call_tool("list_exams", {})
        exams = json.loads(list_result.content[0].text)
        assert any(e["id"] == exam_id for e in exams)

        get_result = await client.call_tool("get_exam", {"exam_id": exam_id})
        detail = json.loads(get_result.content[0].text)
        assert detail["not_yet_attempted"][0]["concept"] == "Friction"

        await client.call_tool(
            "log_performance_input",
            {"subject": "Physics", "concept": "Friction", "result": "wrong"},
        )

        plan_result = await client.call_tool(
            "generate_exam_plan",
            {"exam_id": exam_id, "plan_text": "Do 10 friction problems."},
        )
        assert json.loads(plan_result.content[0].text)["exam_id"] == exam_id

        await client.call_tool(
            "log_performance_input",
            {"subject": "Physics", "concept": "Friction", "result": "correct"},
        )

        progress_result = await client.call_tool("get_exam_progress", {"exam_id": exam_id})
        progress = json.loads(progress_result.content[0].text)
        assert progress["total_before"] == 1
        assert progress["total_after"] == 1
```

Add to `tests/test_student_profile.py` (needs `import json`, `from fastmcp import Client` at the top):

```python
import json
from fastmcp import Client


@pytest.mark.asyncio
async def test_student_profile_wired_end_to_end():
    from server import mcp
    import db

    if db._default_conn is not None:
        db._default_conn.close()
        db._default_conn = None
    from pathlib import Path
    db_path = Path(__file__).resolve().parent.parent / "data" / "jee.db"
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass

    async with Client(mcp) as client:
        empty = await client.call_tool("get_student_profile", {})
        assert json.loads(empty.content[0].text)["session_count"] == 0

        await client.call_tool(
            "log_performance_input",
            {"subject": "Physics", "concept": "Friction", "result": "correct"},
        )
        end_result = await client.call_tool("end_study_session", {})
        assert json.loads(end_result.content[0].text)["updated"] is True

        profile_result = await client.call_tool("get_student_profile", {})
        profile = json.loads(profile_result.content[0].text)
        assert profile["session_count"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_exams.py::test_exam_plan_wired_end_to_end tests/test_student_profile.py::test_student_profile_wired_end_to_end -v`
Expected: FAIL — unknown tool names (`set_exam` etc. not registered).

- [ ] **Step 3: Create the 7 tool wrapper files**

Create `src/tools/set_exam.py`:

```python
import json
from typing import Dict, List
from fastmcp import FastMCP
from db import set_exam


def register_set_exam(server: FastMCP) -> None:
    @server.tool(
        name="set_exam",
        description=(
            "Persists an upcoming exam and its syllabus so planning tools can "
            "reason against it. syllabus is a list of {subject, concept} "
            "objects -- reuses the same concept dedup as log_performance_input, "
            "so phrasing doesn't need to match exactly. exam_date is a plain "
            "'YYYY-MM-DD' string."
        ),
    )
    def handle_set_exam(name: str, exam_date: str, syllabus: List[Dict[str, str]]) -> str:
        return json.dumps(set_exam(name, exam_date, syllabus))
```

Create `src/tools/list_exams.py`:

```python
import json
from fastmcp import FastMCP
from db import list_exams


def register_list_exams(server: FastMCP) -> None:
    @server.tool(
        name="list_exams",
        description=(
            "Lists all exams set via set_exam, with exam_date and whether a "
            "plan has been generated yet. Use to resolve a vague reference "
            "like 'my upcoming Physics exam' to an exam_id."
        ),
    )
    def handle_list_exams() -> str:
        return json.dumps(list_exams())
```

Create `src/tools/get_exam.py`:

```python
import json
from fastmcp import FastMCP
from db import get_exam


def register_get_exam(server: FastMCP) -> None:
    @server.tool(
        name="get_exam",
        description=(
            "Full detail for one exam: syllabus, which syllabus concepts have "
            "zero logged attempts so far (not_yet_attempted -- check this "
            "before planning so no topic gets silently skipped), and the "
            "latest generated plan if any."
        ),
    )
    def handle_get_exam(exam_id: int) -> str:
        return json.dumps(get_exam(exam_id))
```

Create `src/tools/generate_exam_plan.py`:

```python
import json
from fastmcp import FastMCP
from db import generate_exam_plan


def register_generate_exam_plan(server: FastMCP) -> None:
    @server.tool(
        name="generate_exam_plan",
        description=(
            "Persists a study plan covering an exam's full syllabus, after "
            "you've reasoned over get_exam, get_weak_topics/get_concept_state/"
            "get_revision_due/get_time_patterns per syllabus subject, and "
            "get_student_profile. Compose the plan text yourself first -- "
            "this tool only saves it, keeping every past version so "
            "get_exam_progress can measure whether it worked."
        ),
    )
    def handle_generate_exam_plan(exam_id: int, plan_text: str) -> str:
        return json.dumps(generate_exam_plan(exam_id, plan_text))
```

Create `src/tools/get_exam_progress.py`:

```python
import json
from fastmcp import FastMCP
from db import get_exam_progress


def register_get_exam_progress(server: FastMCP) -> None:
    @server.tool(
        name="get_exam_progress",
        description=(
            "Compares accuracy across all of an exam's syllabus concepts "
            "before vs. after the latest generated plan -- the same "
            "before/after check get_progress does for a single-concept plan. "
            "Call after her next test covering exam syllabus topics."
        ),
    )
    def handle_get_exam_progress(exam_id: int) -> str:
        return json.dumps(get_exam_progress(exam_id))
```

Create `src/tools/end_study_session.py`:

```python
import json
from fastmcp import FastMCP
from db import update_student_profile


def register_end_study_session(server: FastMCP) -> None:
    @server.tool(
        name="end_study_session",
        description=(
            "Call when the student signals she's wrapping up for now (e.g. "
            "'that's it for today', 'done'). Recomputes her study-pattern "
            "profile from this session's activity. No-ops safely if nothing "
            "was logged this session (e.g. she only asked for advice)."
        ),
    )
    def handle_end_study_session() -> str:
        return json.dumps(update_student_profile())
```

Create `src/tools/get_student_profile.py`:

```python
import json
from fastmcp import FastMCP
from db import get_student_profile


def register_get_student_profile(server: FastMCP) -> None:
    @server.tool(
        name="get_student_profile",
        description=(
            "Returns her persisted study-pattern profile (pace, per-subject "
            "accuracy, skip rate, stuck-concept rate, average revision lag), "
            "updated at the end of each study session. Call alongside "
            "get_weak_topics/get_concept_state/etc. when composing a plan -- "
            "especially an exam plan -- to account for her working style, "
            "not just raw topic data."
        ),
    )
    def handle_get_student_profile() -> str:
        return json.dumps(get_student_profile())
```

- [ ] **Step 4: Register the 7 tools in `src/server.py`**

Add these 7 import lines to `src/server.py`, after the existing `from tools.get_time_patterns import register_get_time_patterns` line:

```python
from tools.set_exam import register_set_exam
from tools.list_exams import register_list_exams
from tools.get_exam import register_get_exam
from tools.generate_exam_plan import register_generate_exam_plan
from tools.get_exam_progress import register_get_exam_progress
from tools.end_study_session import register_end_study_session
from tools.get_student_profile import register_get_student_profile
```

Add these 7 registration calls after the existing `register_get_time_patterns(mcp)` line:

```python
register_set_exam(mcp)
register_list_exams(mcp)
register_get_exam(mcp)
register_generate_exam_plan(mcp)
register_get_exam_progress(mcp)
register_end_study_session(mcp)
register_get_student_profile(mcp)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_exams.py tests/test_student_profile.py -v`
Expected: all PASS (9 tests in `test_exams.py`, 5 in `test_student_profile.py`).

- [ ] **Step 6: Run the full test suite**

Run: `uv run pytest tests/ -v`
Expected: all PASS (was 44 before this plan; should now be 44 + 2 (Task 1) + 5 (Task 2/3/4 net new, minus overlap already counted) — just confirm 0 failures, exact count isn't the point).

- [ ] **Step 7: Commit**

```bash
git add src/tools/set_exam.py src/tools/list_exams.py src/tools/get_exam.py src/tools/generate_exam_plan.py src/tools/get_exam_progress.py src/tools/end_study_session.py src/tools/get_student_profile.py src/server.py tests/test_exams.py tests/test_student_profile.py
git commit -m "feat(claude): register exam-plan and student-profile MCP tools"
```

---

## Task 8: System prompt update + decisions log

**Files:**
- Modify: `docs/chat-client-system-prompt.md`
- Modify: `src/server.py:13-38` (`INSTRUCTIONS` string, keep in sync with the system prompt doc per existing convention)
- Modify: `docs/decisions.md` (append-only log entry)

**Interfaces:** none — documentation only, no new code interfaces.

- [ ] **Step 1: Add an "Exam planning" section to `docs/chat-client-system-prompt.md`**

Insert this new section after the existing "**When she asks what to work on...**" section (before "**After she takes her next test...**"):

```markdown
**When she mentions an upcoming exam and its syllabus:**
1. Call `set_exam` with the exam name, `exam_date` (as a plain "YYYY-MM-DD"
   string), and `syllabus` (a list of `{subject, concept}` entries covering
   what she told you). If she references an exam she already set up, use
   `list_exams` to find its `exam_id` instead of creating a duplicate.
2. Call `get_exam` for that `exam_id` — check `not_yet_attempted` so you
   know which syllabus topics have zero data so far and don't skip them.
3. For each subject in the syllabus, call `get_weak_topics`,
   `get_concept_state`, `get_revision_due`, and `get_time_patterns` — same
   as regular planning, just once per subject the exam covers. Also call
   `get_student_profile` to factor in her overall pace, time-management
   tendencies, and subject strengths, not just this exam's topics.
4. Reason over all of it and write the full study plan yourself, covering
   the whole syllabus (including `not_yet_attempted` topics) with
   days-until-exam in mind. Call `generate_exam_plan` to save it.

**When she says she's done for now ("that's it for today", "done"):**
- Call `end_study_session`. It safely does nothing if she didn't log any
  results this session (e.g. she only asked for advice).

**After her next test covering topics from an exam's syllabus:**
- Call `get_exam_progress` with that exam's `exam_id` to check whether the
  plan actually worked (accuracy before vs. after), same spirit as
  `get_progress` for a single-concept plan.
```

- [ ] **Step 2: Update `INSTRUCTIONS` in `src/server.py` to match**

In `src/server.py`, replace the `INSTRUCTIONS` string's closing paragraph — find:

```python
Closing the loop: after her next test on a concept you made a plan for, \
call get_progress with that plan's intervention_id to check whether it \
actually worked (accuracy before vs. after). This is the one thing a \
normal coaching report can't do — always use it, don't skip it.\
"""
```

Replace with:

```python
Closing the loop: after her next test on a concept you made a plan for, \
call get_progress with that plan's intervention_id to check whether it \
actually worked (accuracy before vs. after). This is the one thing a \
normal coaching report can't do — always use it, don't skip it.

Exam planning: when she mentions an upcoming exam and syllabus, call \
set_exam (or list_exams to find an existing one), then get_exam to check \
not_yet_attempted topics, then the usual analytics tools per subject plus \
get_student_profile, before writing the full plan yourself and saving it \
with generate_exam_plan. Call end_study_session when she wraps up for the \
day (it's a safe no-op if nothing was logged) and get_exam_progress after \
her next relevant test.\
"""
```

- [ ] **Step 3: Verify the smoke test still passes (INSTRUCTIONS is just a string, but confirm the server still boots)**

Run: `uv run pytest tests/test_smoke.py -v`
Expected: PASS (2 tests).

- [ ] **Step 4: Append a decisions.md entry**

Add to the end of `docs/decisions.md` (check the current last line first with `tail` or a Read, then append after it — do not edit any existing line):

```
[2026-09-15 HH:MM] [claude-code] [master] [done] — built exam/syllabus study plan + student profile feature per docs/superpowers/specs/2026-09-15-exam-plan-student-profile-design.md: 3 new tables (exams, exam_plans append-only history, singleton student_profile), 7 new tools (set_exam, list_exams, get_exam with not_yet_attempted tracking, generate_exam_plan, get_exam_progress reusing get_progress's before/after logic across the syllabus, end_study_session with no-op-on-empty-session guard, get_student_profile). get_revision_due extended with days_since_last_attempt (additive) so avg_revision_lag_days reuses existing logic instead of reimplementing it. docs/chat-client-system-prompt.md and server.py's INSTRUCTIONS updated to match. All new + existing tests passing.
```

(Fill in the actual `HH:MM` at commit time.)

- [ ] **Step 5: Run the full test suite one final time**

Run: `uv run pytest tests/ -v`
Expected: 0 failures.

- [ ] **Step 6: Commit**

```bash
git add docs/chat-client-system-prompt.md src/server.py docs/decisions.md
git commit -m "docs(claude): update system prompt and decisions log for exam-plan feature"
```

---

## Self-Review Notes

- **Spec coverage:** every spec section has a task — schema (Task 1), `set_exam`/`list_exams` (Task 2), `get_exam`/`not_yet_attempted` (Task 3), `generate_exam_plan`/`get_exam_progress` (Task 4), the `get_revision_due` extension the spec's profile section depends on (Task 5), `update_student_profile`/`get_student_profile`/empty-session no-op (Task 6), tool registration (Task 7), system prompt + decisions log (Task 8).
- **Placeholder scan:** no TBD/TODO; every step has real code and real run commands.
- **Type consistency:** `set_exam`'s `syllabus` param type (`List[Dict[str, str]]`) matches across Task 2's function, Task 3/4's consumers reading the same JSON shape, and Task 7's tool wrapper signature. `get_revision_due`'s new `days_since_last_attempt` key (Task 5) is consumed by name in Task 6 exactly as added. `update_student_profile`'s `{"updated": bool, ...}` return shape is consumed identically by Task 7's `end_study_session` tool and its end-to-end test.
