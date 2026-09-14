import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from bkt import update_mastery, apply_decay, P_L0

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "jee.db"

_default_conn: Optional[sqlite3.Connection] = None


def init_db(db_path: Optional[os.PathLike | str] = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")

    conn.executescript("""
      CREATE TABLE IF NOT EXISTS concepts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        subject TEXT NOT NULL,
        created_at INTEGER NOT NULL
      );

      CREATE TABLE IF NOT EXISTS attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        concept_id INTEGER NOT NULL REFERENCES concepts(id),
        result TEXT NOT NULL CHECK (result IN ('correct', 'wrong', 'unattempted')),
        time_seconds INTEGER,
        created_at INTEGER NOT NULL
      );

      CREATE TABLE IF NOT EXISTS error_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT
      );

      CREATE TABLE IF NOT EXISTS attempt_errors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attempt_id INTEGER NOT NULL REFERENCES attempts(id),
        error_type_id INTEGER NOT NULL REFERENCES error_types(id),
        notes TEXT
      );

      CREATE TABLE IF NOT EXISTS student_concept_state (
        concept_id INTEGER PRIMARY KEY REFERENCES concepts(id),
        mastery_probability REAL NOT NULL,
        last_attempt_at INTEGER NOT NULL
      );

      CREATE TABLE IF NOT EXISTS interventions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        concept_id INTEGER NOT NULL REFERENCES concepts(id),
        plan_text TEXT NOT NULL,
        created_at INTEGER NOT NULL
      );

      CREATE TABLE IF NOT EXISTS intervention_outcomes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        intervention_id INTEGER NOT NULL REFERENCES interventions(id),
        accuracy_before REAL,
        accuracy_after REAL,
        measured_at INTEGER NOT NULL
      );
    """)

    error_types = [
        "concept_gap",
        "calculation",
        "misread",
        "time_pressure",
        "unattempted",
        "unknown",
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO error_types (name) VALUES (?)",
        [(name,) for name in error_types],
    )
    conn.commit()
    return conn


def get_connection(db_path: Optional[os.PathLike | str] = None) -> sqlite3.Connection:
    global _default_conn
    if db_path is not None:
        return init_db(db_path)
    if _default_conn is None:
        _default_conn = init_db(DEFAULT_DB_PATH)
    return _default_conn


def normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def find_or_create_concept(
    name: str, subject: str, conn: Optional[sqlite3.Connection] = None
) -> int:
    connection = conn if conn is not None else get_connection()
    target = normalize(name)

    cursor = connection.cursor()
    cursor.execute("SELECT id, name FROM concepts WHERE subject = ?", (subject,))
    for row in cursor.fetchall():
        concept_id, concept_name = row[0], row[1]
        if normalize(concept_name) == target:
            return concept_id

    created_at = int(time.time() * 1000)
    cursor.execute(
        "INSERT INTO concepts (name, subject, created_at) VALUES (?, ?, ?)",
        (name, subject, created_at),
    )
    connection.commit()
    return cursor.lastrowid  # type: ignore


def list_concepts(
    subject: str, conn: Optional[sqlite3.Connection] = None
) -> List[Dict[str, Any]]:
    connection = conn if conn is not None else get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id, name FROM concepts WHERE subject = ? ORDER BY name",
        (subject,),
    )
    return [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]


def get_weak_topics(
    subject: str, limit: int = 10, conn: Optional[sqlite3.Connection] = None
) -> List[Dict[str, Any]]:
    connection = conn if conn is not None else get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT c.id, c.name,
               COUNT(*) AS total_attempts,
               SUM(CASE WHEN a.result = 'correct' THEN 1 ELSE 0 END) AS correct,
               SUM(CASE WHEN a.result = 'wrong' THEN 1 ELSE 0 END) AS wrong,
               SUM(CASE WHEN a.result = 'unattempted' THEN 1 ELSE 0 END) AS unattempted
        FROM attempts a
        JOIN concepts c ON c.id = a.concept_id
        WHERE c.subject = ?
        GROUP BY c.id
        ORDER BY (CAST(wrong AS REAL) / total_attempts) DESC
        LIMIT ?
        """,
        (subject, limit),
    )
    result = []
    for concept_id, name, total, correct, wrong, unattempted in cursor.fetchall():
        result.append(
            {
                "id": concept_id,
                "name": name,
                "total_attempts": total,
                "correct": correct,
                "wrong": wrong,
                "unattempted": unattempted,
                "accuracy": round(correct / total, 4) if total else 0.0,
            }
        )
    return result


def get_recurring_mistakes(
    subject: str, min_occurrences: int = 2, conn: Optional[sqlite3.Connection] = None
) -> List[Dict[str, Any]]:
    connection = conn if conn is not None else get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT c.name AS concept, et.name AS error_type, COUNT(*) AS occurrences
        FROM attempt_errors ae
        JOIN attempts a ON a.id = ae.attempt_id
        JOIN concepts c ON c.id = a.concept_id
        JOIN error_types et ON et.id = ae.error_type_id
        WHERE c.subject = ?
        GROUP BY c.id, et.id
        HAVING COUNT(*) >= ?
        ORDER BY occurrences DESC
        """,
        (subject, min_occurrences),
    )
    return [
        {"concept": row[0], "error_type": row[1], "occurrences": row[2]}
        for row in cursor.fetchall()
    ]


def record_bkt_update(
    concept_id: int,
    result: str,
    attempt_time_ms: int,
    conn: Optional[sqlite3.Connection] = None,
) -> float:
    """Applies the BKT posterior update for one attempt and upserts the
    result into student_concept_state. Called from log_performance_input
    right after the attempt is inserted."""
    connection = conn if conn is not None else get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT mastery_probability FROM student_concept_state WHERE concept_id = ?",
        (concept_id,),
    )
    row = cursor.fetchone()
    prior = row[0] if row is not None else P_L0

    updated = update_mastery(prior, result)  # type: ignore[arg-type]

    cursor.execute(
        """
        INSERT INTO student_concept_state (concept_id, mastery_probability, last_attempt_at)
        VALUES (?, ?, ?)
        ON CONFLICT(concept_id) DO UPDATE SET
            mastery_probability = excluded.mastery_probability,
            last_attempt_at = excluded.last_attempt_at
        """,
        (concept_id, updated, attempt_time_ms),
    )
    connection.commit()
    return updated


def get_concept_state(
    subject: str,
    concept_id: Optional[int] = None,
    conn: Optional[sqlite3.Connection] = None,
    now_ms: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Reads current BKT mastery per concept, with the retention-decay
    nudge applied at read time (never written back — see bkt.apply_decay)."""
    connection = conn if conn is not None else get_connection()
    now = now_ms if now_ms is not None else int(time.time() * 1000)

    query = """
        SELECT c.id, c.name, s.mastery_probability, s.last_attempt_at
        FROM student_concept_state s
        JOIN concepts c ON c.id = s.concept_id
        WHERE c.subject = ?
    """
    params: List[Any] = [subject]
    if concept_id is not None:
        query += " AND c.id = ?"
        params.append(concept_id)
    query += " ORDER BY c.name"

    cursor = connection.cursor()
    cursor.execute(query, params)

    result = []
    for cid, name, mastery, last_attempt_at in cursor.fetchall():
        days_since = (now - last_attempt_at) / (1000 * 60 * 60 * 24)
        result.append(
            {
                "id": cid,
                "name": name,
                "mastery_probability": round(apply_decay(mastery, days_since), 4),
                "last_attempt_at": last_attempt_at,
            }
        )
    return result


def create_intervention(
    concept_id: int, plan_text: str, conn: Optional[sqlite3.Connection] = None
) -> int:
    connection = conn if conn is not None else get_connection()
    created_at = int(time.time() * 1000)
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO interventions (concept_id, plan_text, created_at) VALUES (?, ?, ?)",
        (concept_id, plan_text, created_at),
    )
    connection.commit()
    return cursor.lastrowid  # type: ignore


def get_progress(
    intervention_id: int, conn: Optional[sqlite3.Connection] = None
) -> Dict[str, Any]:
    """Compares accuracy on the intervention's concept before vs. after
    interventions.created_at — the closed-loop verification step."""
    connection = conn if conn is not None else get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT concept_id, plan_text, created_at FROM interventions WHERE id = ?",
        (intervention_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError(f"No intervention with id {intervention_id}")
    concept_id, plan_text, created_at = row

    cursor.execute(
        """
        SELECT
          SUM(CASE WHEN created_at < ? THEN 1 ELSE 0 END),
          SUM(CASE WHEN created_at < ? AND result = 'correct' THEN 1 ELSE 0 END),
          SUM(CASE WHEN created_at >= ? THEN 1 ELSE 0 END),
          SUM(CASE WHEN created_at >= ? AND result = 'correct' THEN 1 ELSE 0 END)
        FROM attempts
        WHERE concept_id = ?
        """,
        (created_at, created_at, created_at, created_at, concept_id),
    )
    total_before, correct_before, total_after, correct_after = cursor.fetchone()
    total_before = total_before or 0
    correct_before = correct_before or 0
    total_after = total_after or 0
    correct_after = correct_after or 0

    accuracy_before = round(correct_before / total_before, 4) if total_before else None
    accuracy_after = round(correct_after / total_after, 4) if total_after else None

    measured_at = int(time.time() * 1000)
    cursor.execute(
        """
        INSERT INTO intervention_outcomes (intervention_id, accuracy_before, accuracy_after, measured_at)
        VALUES (?, ?, ?, ?)
        """,
        (intervention_id, accuracy_before, accuracy_after, measured_at),
    )
    connection.commit()

    return {
        "intervention_id": intervention_id,
        "concept_id": concept_id,
        "plan_text": plan_text,
        "accuracy_before": accuracy_before,
        "accuracy_after": accuracy_after,
        "total_before": total_before,
        "total_after": total_after,
    }

