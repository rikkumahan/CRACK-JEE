import pytest

from bkt import update_mastery, apply_decay, P_L0


def test_correct_answer_increases_mastery():
    updated = update_mastery(P_L0, "correct")
    assert updated > P_L0


def test_wrong_answer_decreases_mastery():
    updated = update_mastery(P_L0, "wrong")
    assert updated < P_L0


def test_unattempted_does_not_change_mastery():
    assert update_mastery(P_L0, "unattempted") == P_L0


def test_update_mastery_exact_values():
    # prior=0.20, correct: numerator=0.2*0.9=0.18, denom=0.18+0.8*0.25=0.38
    # posterior=0.18/0.38=0.473684..., next = post + (1-post)*0.10
    updated = update_mastery(0.20, "correct")
    expected_posterior = 0.18 / 0.38
    expected = expected_posterior + (1 - expected_posterior) * 0.10
    assert updated == pytest.approx(expected, abs=1e-9)


def test_mastery_stays_in_bounds_after_many_updates():
    m = P_L0
    for _ in range(50):
        m = update_mastery(m, "correct")
    assert 0.0 <= m <= 1.0
    m = P_L0
    for _ in range(50):
        m = update_mastery(m, "wrong")
    assert 0.0 <= m <= 1.0


def test_decay_within_grace_period_is_noop():
    assert apply_decay(0.8, 0) == 0.8
    assert apply_decay(0.8, 14) == 0.8


def test_decay_after_grace_period_reduces_mastery():
    decayed = apply_decay(0.8, 21)  # 1 week past grace
    assert decayed == pytest.approx(0.3 + (0.8 - 0.3) * 0.97, abs=1e-9)
    assert decayed < 0.8


def test_decay_never_goes_below_floor():
    decayed = apply_decay(0.8, 14 + 7 * 500)  # very long idle
    assert decayed == pytest.approx(0.3, abs=1e-6)
    assert decayed >= 0.3
