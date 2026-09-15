import pytest

from db import init_db, find_or_create_concept, record_bkt_update, get_revision_due

DAY_MS = 1000 * 60 * 60 * 24


@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_jee.db"
    conn = init_db(db_path)
    yield conn, db_path
    conn.close()


def test_due_now_when_already_decayed_below_threshold(test_db):
    conn, _ = test_db
    cid = find_or_create_concept("Friction", "Physics", conn=conn)
    # One correct attempt long ago -> mastery starts modest, then decays hard.
    record_bkt_update(cid, "correct", attempt_time_ms=0, conn=conn)

    now = 60 * DAY_MS  # 60 days idle, well past grace + decay floor territory
    result = get_revision_due("Physics", conn=conn, now_ms=now, threshold=0.9)
    assert len(result) == 1
    assert result[0]["name"] == "Friction"
    assert result[0]["due_now"] is True


def test_due_soon_when_projection_crosses_threshold(test_db):
    conn, _ = test_db
    cid = find_or_create_concept("Kinematics", "Physics", conn=conn)
    record_bkt_update(cid, "correct", attempt_time_ms=0, conn=conn)
    # Mastery after one correct attempt from P_L0=0.20 is ~0.5263 (fixed BKT
    # math, see src/bkt.py).

    # 14 days idle: exactly at the grace boundary, current == mastery (no
    # decay applied yet, so still above threshold=0.52). Projecting 14 more
    # days (28 total idle) decays it to ~0.513, which crosses below 0.52.
    now = 14 * DAY_MS
    result = get_revision_due(
        "Physics", conn=conn, now_ms=now, threshold=0.52, days_ahead=14
    )
    assert len(result) == 1
    assert result[0]["name"] == "Kinematics"
    assert result[0]["due_now"] is False
    assert result[0]["projected_mastery"] < 0.52


def test_excludes_concepts_safely_above_threshold(test_db):
    conn, _ = test_db
    cid = find_or_create_concept("Optics", "Physics", conn=conn)
    record_bkt_update(cid, "correct", attempt_time_ms=0, conn=conn)

    now = 1 * DAY_MS  # barely idle, high mastery
    result = get_revision_due("Physics", conn=conn, now_ms=now, threshold=0.05)
    assert result == []


def test_scoped_to_subject(test_db):
    conn, _ = test_db
    cid = find_or_create_concept("Friction", "Physics", conn=conn)
    record_bkt_update(cid, "correct", attempt_time_ms=0, conn=conn)

    now = 60 * DAY_MS
    result = get_revision_due("Chemistry", conn=conn, now_ms=now, threshold=0.9)
    assert result == []


def test_due_now_row_includes_days_since_last_attempt(test_db):
    conn, _ = test_db
    cid = find_or_create_concept("Friction", "Physics", conn=conn)
    record_bkt_update(cid, "correct", attempt_time_ms=0, conn=conn)

    now = 60 * DAY_MS
    result = get_revision_due("Physics", conn=conn, now_ms=now, threshold=0.9)
    assert result[0]["days_since_last_attempt"] == pytest.approx(60.0)

