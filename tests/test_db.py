import os
import sqlite3
import threading
import pytest
from pathlib import Path

from db import (
    init_db,
    get_connection,
    normalize,
    find_or_create_concept,
    list_concepts,
)


@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_jee.db"
    conn = init_db(db_path)
    yield conn, db_path
    conn.close()


def test_schema_creates_tables_and_seeds_error_types(test_db):
    conn, _ = test_db
    cursor = conn.cursor()

    # Verify all 4 tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert {"concepts", "attempts", "error_types", "attempt_errors"}.issubset(tables)

    # Verify 6 error types are seeded
    cursor.execute("SELECT name FROM error_types ORDER BY id")
    error_types = [row[0] for row in cursor.fetchall()]
    assert error_types == [
        "concept_gap",
        "calculation",
        "misread",
        "time_pressure",
        "unattempted",
        "unknown",
    ]


def test_normalize():
    assert normalize("Rotational Motion") == "rotationalmotion"
    assert normalize("rotational motion") == "rotationalmotion"
    assert normalize("Rotational-Motion!") == "rotationalmotion"
    assert normalize("   Rotational   Motion 123 ") == "rotationalmotion123"


def test_find_or_create_concept_deduplication(test_db):
    conn, db_path = test_db
    id1 = find_or_create_concept("Rotational Motion", "Physics", conn=conn)
    id2 = find_or_create_concept("rotational motion", "Physics", conn=conn)
    assert id1 == id2

    cursor = conn.cursor()
    cursor.execute("SELECT id, name, subject FROM concepts WHERE subject = 'Physics'")
    rows = cursor.fetchall()
    assert len(rows) == 1
    assert rows[0][0] == id1
    assert rows[0][1] == "Rotational Motion"


def test_find_or_create_concept_scoped_by_subject(test_db):
    conn, db_path = test_db
    id_physics = find_or_create_concept("Rotational Motion", "Physics", conn=conn)
    id_math = find_or_create_concept("Rotational Motion", "Math", conn=conn)
    assert id_physics != id_math

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM concepts")
    assert cursor.fetchone()[0] == 2


def test_list_concepts(test_db):
    conn, db_path = test_db
    find_or_create_concept("Kinematics", "Physics", conn=conn)
    find_or_create_concept("Dynamics", "Physics", conn=conn)
    find_or_create_concept("Calculus", "Math", conn=conn)

    physics_concepts = list_concepts("Physics", conn=conn)
    assert len(physics_concepts) == 2
    assert physics_concepts[0]["name"] == "Dynamics"
    assert physics_concepts[1]["name"] == "Kinematics"

    math_concepts = list_concepts("Math", conn=conn)
    assert len(math_concepts) == 1
    assert math_concepts[0]["name"] == "Calculus"


def test_find_or_create_concept_survives_concurrent_creation_race(test_db):
    """10 threads racing to create the same brand-new concept name must
    produce exactly one row, not one per thread. Without BEGIN IMMEDIATE
    around the check-then-insert, this used to be able to duplicate the
    concept and silently split its attempts/mastery across two ids."""
    _, db_path = test_db
    results = []

    def worker():
        c = init_db(db_path)
        results.append(find_or_create_concept("Rotational Motion", "Physics", conn=c))
        c.close()

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 10
    assert len(set(results)) == 1

    check_conn = init_db(db_path)
    cursor = check_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM concepts WHERE subject = 'Physics'")
    assert cursor.fetchone()[0] == 1
    check_conn.close()


def test_find_or_create_concept_self_heals_after_abandoned_transaction(test_db):
    """A prior write on the same connection that raised before its own
    commit() (e.g. a caller's later statement failing) leaves sqlite3's
    implicit transaction open. Without a rollback first, the BEGIN
    IMMEDIATE this function issues would raise "cannot start a
    transaction within a transaction" -- permanently, since the shared
    connection stays dirty across every future call. This must recover,
    not crash."""
    conn, _ = test_db
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO concepts (name, subject, created_at) VALUES (?, ?, ?)",
        ("Stray Uncommitted Write", "Physics", 1),
    )
    assert conn.in_transaction

    concept_id = find_or_create_concept("Rotational Motion", "Physics", conn=conn)
    assert concept_id is not None

    cursor.execute("SELECT name FROM concepts WHERE subject = 'Physics' ORDER BY name")
    names = [row[0] for row in cursor.fetchall()]
    assert names == ["Rotational Motion"]

