import json
import pytest
from fastmcp import Client
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


@pytest.mark.parametrize(
    "bad_date",
    [
        "15-11-2026",  # wrong field order
        "2026/11/15",  # wrong separator
        "Nov 15 2026",  # not ISO at all
        "2026-13-01",  # invalid month
        "",
        None,
    ],
)
def test_set_exam_rejects_malformed_exam_date(test_db, bad_date):
    conn, _ = test_db
    with pytest.raises(ValueError):
        set_exam("Bad Date Exam", bad_date, [], conn=conn)


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

