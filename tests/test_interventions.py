import json
import pytest
from fastmcp import Client

from db import init_db, find_or_create_concept, create_intervention, get_progress


@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_jee.db"
    conn = init_db(db_path)
    yield conn, db_path
    conn.close()


def record_attempt_at(conn, concept_id, result, created_at):
    conn.execute(
        "INSERT INTO attempts (concept_id, result, time_seconds, created_at) VALUES (?, ?, NULL, ?)",
        (concept_id, result, created_at),
    )
    conn.commit()


def test_create_intervention_returns_id(test_db):
    conn, _ = test_db
    cid = find_or_create_concept("Friction", "Physics", conn=conn)
    intervention_id = create_intervention(cid, "Practice 10 friction problems", conn=conn)
    assert isinstance(intervention_id, int)

    row = conn.execute(
        "SELECT concept_id, plan_text FROM interventions WHERE id = ?", (intervention_id,)
    ).fetchone()
    assert row[0] == cid
    assert row[1] == "Practice 10 friction problems"


def test_get_progress_splits_accuracy_before_and_after(test_db):
    conn, _ = test_db
    cid = find_or_create_concept("Friction", "Physics", conn=conn)

    # Before: 1 correct, 3 wrong -> 25% accuracy
    record_attempt_at(conn, cid, "wrong", 1000)
    record_attempt_at(conn, cid, "wrong", 2000)
    record_attempt_at(conn, cid, "wrong", 3000)
    record_attempt_at(conn, cid, "correct", 4000)

    conn.execute(
        "INSERT INTO interventions (concept_id, plan_text, created_at) VALUES (?, ?, ?)",
        (cid, "Practice friction", 5000),
    )
    conn.commit()
    intervention_id = conn.execute(
        "SELECT id FROM interventions WHERE concept_id = ?", (cid,)
    ).fetchone()[0]

    # After: 3 correct, 1 wrong -> 75% accuracy
    record_attempt_at(conn, cid, "correct", 6000)
    record_attempt_at(conn, cid, "correct", 7000)
    record_attempt_at(conn, cid, "correct", 8000)
    record_attempt_at(conn, cid, "wrong", 9000)

    result = get_progress(intervention_id, conn=conn)
    assert result["total_before"] == 4
    assert result["accuracy_before"] == pytest.approx(0.25)
    assert result["total_after"] == 4
    assert result["accuracy_after"] == pytest.approx(0.75)

    # Verify it was persisted
    outcome = conn.execute(
        "SELECT accuracy_before, accuracy_after FROM intervention_outcomes WHERE intervention_id = ?",
        (intervention_id,),
    ).fetchone()
    assert outcome[0] == pytest.approx(0.25)
    assert outcome[1] == pytest.approx(0.75)


def test_get_progress_handles_no_attempts_either_side(test_db):
    conn, _ = test_db
    cid = find_or_create_concept("Torque", "Physics", conn=conn)
    intervention_id = create_intervention(cid, "Review torque basics", conn=conn)

    result = get_progress(intervention_id, conn=conn)
    assert result["total_before"] == 0
    assert result["accuracy_before"] is None
    assert result["total_after"] == 0
    assert result["accuracy_after"] is None


def test_get_progress_raises_for_unknown_intervention(test_db):
    conn, _ = test_db
    with pytest.raises(ValueError):
        get_progress(9999, conn=conn)


@pytest.mark.asyncio
async def test_generate_daily_plan_and_get_progress_wired_end_to_end():
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
        await client.call_tool(
            "log_performance_input",
            {"subject": "Physics", "concept": "Friction", "result": "wrong"},
        )

        list_result = await client.call_tool("list_concepts", {"subject": "Physics"})
        concept_id = json.loads(list_result.content[0].text)[0]["id"]

        plan_result = await client.call_tool(
            "generate_daily_plan",
            {"concept_id": concept_id, "plan_text": "Do 5 friction problems, focus on free-body diagrams."},
        )
        intervention_id = json.loads(plan_result.content[0].text)["intervention_id"]
        assert isinstance(intervention_id, int)

        await client.call_tool(
            "log_performance_input",
            {"subject": "Physics", "concept": "Friction", "result": "correct"},
        )

        progress_result = await client.call_tool(
            "get_progress", {"intervention_id": intervention_id}
        )
        progress = json.loads(progress_result.content[0].text)
        assert progress["total_before"] == 1
        assert progress["total_after"] == 1
        assert progress["accuracy_before"] == pytest.approx(0.0)
        assert progress["accuracy_after"] == pytest.approx(1.0)
