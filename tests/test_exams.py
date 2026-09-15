import pytest
from db import init_db, set_exam, list_exams


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

    conn.execute(
        "INSERT INTO exam_plans (exam_id, plan_text, created_at) VALUES (?, 'Study aldehyde reactions.', 1000)",
        (exam["exam_id"],),
    )
    conn.commit()
    exams = list_exams(conn=conn)
    assert exams[0]["has_plan"] is True
