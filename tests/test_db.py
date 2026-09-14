import os
import sqlite3
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

