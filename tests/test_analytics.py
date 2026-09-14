import pytest

from db import init_db, find_or_create_concept, get_weak_topics, get_recurring_mistakes


@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_jee.db"
    conn = init_db(db_path)
    yield conn, db_path
    conn.close()


def record_attempt(conn, concept_id, result, error_type=None):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO attempts (concept_id, result, time_seconds, created_at) VALUES (?, ?, NULL, 0)",
        (concept_id, result),
    )
    attempt_id = cursor.lastrowid
    if error_type:
        cursor.execute("SELECT id FROM error_types WHERE name = ?", (error_type,))
        error_type_id = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO attempt_errors (attempt_id, error_type_id, notes) VALUES (?, ?, NULL)",
            (attempt_id, error_type_id),
        )
    conn.commit()
    return attempt_id


def test_get_weak_topics_ranks_by_wrong_rate(test_db):
    conn, _ = test_db
    weak = find_or_create_concept("Friction", "Physics", conn=conn)
    strong = find_or_create_concept("Kinematics", "Physics", conn=conn)

    record_attempt(conn, weak, "correct")
    record_attempt(conn, weak, "wrong")
    record_attempt(conn, weak, "wrong")
    record_attempt(conn, weak, "wrong")

    record_attempt(conn, strong, "correct")
    record_attempt(conn, strong, "correct")
    record_attempt(conn, strong, "correct")
    record_attempt(conn, strong, "wrong")

    result = get_weak_topics("Physics", conn=conn)
    assert result[0]["name"] == "Friction"
    assert result[0]["total_attempts"] == 4
    assert result[0]["correct"] == 1
    assert result[0]["wrong"] == 3
    assert result[0]["accuracy"] == pytest.approx(0.25)
    assert result[1]["name"] == "Kinematics"


def test_get_weak_topics_respects_limit(test_db):
    conn, _ = test_db
    for name in ["A", "B", "C"]:
        cid = find_or_create_concept(name, "Physics", conn=conn)
        record_attempt(conn, cid, "wrong")

    result = get_weak_topics("Physics", limit=2, conn=conn)
    assert len(result) == 2


def test_get_weak_topics_scoped_by_subject(test_db):
    conn, _ = test_db
    phys = find_or_create_concept("Friction", "Physics", conn=conn)
    math = find_or_create_concept("Calculus", "Math", conn=conn)
    record_attempt(conn, phys, "wrong")
    record_attempt(conn, math, "wrong")

    result = get_weak_topics("Physics", conn=conn)
    assert len(result) == 1
    assert result[0]["name"] == "Friction"


def test_get_recurring_mistakes_finds_repeated_error_pattern(test_db):
    conn, _ = test_db
    friction = find_or_create_concept("Friction", "Physics", conn=conn)
    torque = find_or_create_concept("Torque", "Physics", conn=conn)

    record_attempt(conn, friction, "wrong", error_type="concept_gap")
    record_attempt(conn, friction, "wrong", error_type="concept_gap")
    record_attempt(conn, torque, "wrong", error_type="calculation")  # only once

    result = get_recurring_mistakes("Physics", conn=conn)
    assert len(result) == 1
    assert result[0]["concept"] == "Friction"
    assert result[0]["error_type"] == "concept_gap"
    assert result[0]["occurrences"] == 2


def test_get_recurring_mistakes_respects_min_occurrences(test_db):
    conn, _ = test_db
    friction = find_or_create_concept("Friction", "Physics", conn=conn)
    record_attempt(conn, friction, "wrong", error_type="concept_gap")
    record_attempt(conn, friction, "wrong", error_type="concept_gap")
    record_attempt(conn, friction, "wrong", error_type="concept_gap")

    result = get_recurring_mistakes("Physics", min_occurrences=3, conn=conn)
    assert len(result) == 1

    result_stricter = get_recurring_mistakes("Physics", min_occurrences=4, conn=conn)
    assert len(result_stricter) == 0
