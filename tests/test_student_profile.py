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
