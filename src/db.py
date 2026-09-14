import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

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

