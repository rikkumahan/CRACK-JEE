import pytest

from db import init_db, find_or_create_concept, get_time_patterns


@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_jee.db"
    conn = init_db(db_path)
    yield conn, db_path
    conn.close()


def record_attempt(conn, concept_id, result, time_seconds):
    conn.execute(
        "INSERT INTO attempts (concept_id, result, time_seconds, created_at) VALUES (?, ?, ?, 0)",
        (concept_id, result, time_seconds),
    )
    conn.commit()


def test_flags_stuck_pattern_when_wrong_attempts_take_much_longer(test_db):
    conn, _ = test_db
    cid = find_or_create_concept("Thermodynamics", "Physics", conn=conn)
    record_attempt(conn, cid, "correct", 60)
    record_attempt(conn, cid, "correct", 60)
    record_attempt(conn, cid, "wrong", 300)
    record_attempt(conn, cid, "wrong", 320)
    record_attempt(conn, cid, "wrong", 310)

    result = get_time_patterns("Physics", conn=conn)
    assert len(result) == 1
    row = result[0]
    assert row["name"] == "Thermodynamics"
    assert row["avg_time_correct"] == pytest.approx(60.0)
    assert row["avg_time_wrong"] == pytest.approx(310.0)
    assert row["stuck_pattern"] is True


def test_no_flag_when_timing_is_uniform(test_db):
    conn, _ = test_db
    cid = find_or_create_concept("Kinematics", "Physics", conn=conn)
    record_attempt(conn, cid, "correct", 90)
    record_attempt(conn, cid, "wrong", 95)
    record_attempt(conn, cid, "wrong", 100)
    record_attempt(conn, cid, "wrong", 92)

    result = get_time_patterns("Physics", conn=conn)
    assert result[0]["stuck_pattern"] is False


def test_no_flag_with_too_few_wrong_attempts(test_db):
    conn, _ = test_db
    cid = find_or_create_concept("Optics", "Physics", conn=conn)
    record_attempt(conn, cid, "correct", 60)
    record_attempt(conn, cid, "wrong", 600)
    record_attempt(conn, cid, "wrong", 620)

    result = get_time_patterns("Physics", conn=conn)
    assert result[0]["stuck_pattern"] is False


def test_handles_missing_time_data_without_crashing(test_db):
    conn, _ = test_db
    cid = find_or_create_concept("Electrostatics", "Physics", conn=conn)
    conn.execute(
        "INSERT INTO attempts (concept_id, result, time_seconds, created_at) VALUES (?, 'correct', NULL, 0)",
        (cid,),
    )
    conn.commit()

    result = get_time_patterns("Physics", conn=conn)
    assert result[0]["avg_time_correct"] is None
    assert result[0]["avg_time_wrong"] is None
    assert result[0]["stuck_pattern"] is False
