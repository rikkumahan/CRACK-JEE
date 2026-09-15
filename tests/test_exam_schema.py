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
