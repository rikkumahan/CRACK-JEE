import pytest
import numpy as np
from pathlib import Path
from simulator.student import SyntheticStudent, StudentConfig, WorldConfig
from simulator.worlds import load_worlds_config, load_archetypes_config, create_student


def test_student_config_defaults():
    config = StudentConfig(student_id="S_TEST_01")
    assert config.learning_rate > 0
    assert config.forgetting_rate > 0
    assert 0 <= config.slip_rate <= 0.5
    assert 0 <= config.guess_rate <= 0.5


def test_irt_p_correct_bounds():
    rng = np.random.default_rng(42)
    student = SyntheticStudent(StudentConfig("S1", slip_rate=0.1, guess_rate=0.2), rng=rng)
    
    # Easy question (d = 0.1), student has mastery 0.9
    student.set_concept_mastery("C1", 0.9)
    p_easy, p_know_easy = student.compute_p_correct("C1", difficulty=0.1)
    assert 0.8 <= p_know_easy <= 1.0
    assert 0.7 <= p_easy <= 1.0

    # Hard question (d = 0.9), student has mastery 0.1
    student.set_concept_mastery("C2", 0.1)
    p_hard, p_know_hard = student.compute_p_correct("C2", difficulty=0.9)
    assert 0.0 <= p_know_hard <= 0.2
    assert p_hard < p_easy


def test_learning_dynamics():
    rng = np.random.default_rng(100)
    student = SyntheticStudent(StudentConfig("S1", learning_rate=0.2), rng=rng)
    student.set_concept_mastery("C1", 0.3)

    # Attempt with wrong answer
    m_before = student.get_concept_mastery("C1")
    student.update_learning("C1", outcome=0)
    m_after_wrong = student.get_concept_mastery("C1")
    assert m_after_wrong > m_before

    # Attempt with correct answer yields larger gain
    gain_wrong = m_after_wrong - m_before
    student.set_concept_mastery("C1", 0.3)
    student.update_learning("C1", outcome=1)
    gain_correct = student.get_concept_mastery("C1") - 0.3
    assert gain_correct > gain_wrong


def test_forgetting_dynamics():
    rng = np.random.default_rng(200)
    student = SyntheticStudent(StudentConfig("S1", forgetting_rate=0.05), rng=rng)
    student.set_concept_mastery("C1", 0.8)

    # Within grace days (14 days default), no decay
    eff_10 = student.get_effective_mastery("C1", days_since_practice=10)
    assert eff_10 == 0.8

    # After grace days, exponential decay towards floor 0.15
    eff_30 = student.get_effective_mastery("C1", days_since_practice=30)
    assert eff_30 < 0.8
    assert eff_30 >= 0.15

    # After a very long time, reaches floor
    eff_1000 = student.get_effective_mastery("C1", days_since_practice=1000)
    assert pytest.approx(eff_1000, abs=0.01) == 0.15


def test_error_mechanisms():
    rng = np.random.default_rng(300)
    student = SyntheticStudent(StudentConfig("S1", slip_rate=0.2, guess_rate=0.2), rng=rng)

    # High p_know + wrong outcome -> SLIP
    err_slip = student.determine_error_type(outcome=0, p_know=0.85, is_time_out=False)
    assert err_slip == "SLIP"

    # Low p_know + wrong outcome -> CONCEPT_GAP
    err_gap = student.determine_error_type(outcome=0, p_know=0.20, is_time_out=False)
    assert err_gap == "CONCEPT_GAP"

    # Moderate p_know + wrong outcome -> CALCULATION
    err_calc = student.determine_error_type(outcome=0, p_know=0.50, is_time_out=False)
    assert err_calc == "CALCULATION"

    # Low p_know + correct outcome -> GUESS
    err_guess = student.determine_error_type(outcome=1, p_know=0.15, is_time_out=False)
    assert err_guess == "GUESS"


def test_strict_reproducibility():
    # Same seed -> identical interactions
    rng1 = np.random.default_rng(42)
    s1 = SyntheticStudent(StudentConfig("S1"), rng=rng1)
    s1.set_concept_mastery("C1", 0.5)

    rng2 = np.random.default_rng(42)
    s2 = SyntheticStudent(StudentConfig("S1"), rng=rng2)
    s2.set_concept_mastery("C1", 0.5)

    q = {"question_id": "Q1", "concept_id": "C1", "difficulty": 0.5, "question_concepts": [{"concept_id": "C1", "weight": 1.0}]}

    out1 = [s1.answer_question(q, timestamp=t) for t in range(20)]
    out2 = [s2.answer_question(q, timestamp=t) for t in range(20)]

    assert [o["correct"] for o in out1] == [o["correct"] for o in out2]
    assert [o["error_type"] for o in out1] == [o["error_type"] for o in out2]
    assert [o["time_seconds"] for o in out1] == [o["time_seconds"] for o in out2]


def test_all_worlds_and_archetypes_instantiation():
    worlds = load_worlds_config()
    archetypes = load_archetypes_config()

    expected_worlds = ["A", "B", "C", "D", "E", "F", "G"]
    for w in expected_worlds:
        assert w in worlds

    expected_archetypes = [f"S{i:02d}" for i in range(1, 11)]
    for a in expected_archetypes:
        assert a in archetypes

    rng = np.random.default_rng(999)
    for w in expected_worlds:
        for a in expected_archetypes:
            st = create_student(f"student_{w}_{a}", archetype_id=a, world_id=w, rng=rng, worlds_dict=worlds, archetypes_dict=archetypes)
            assert st.config.student_id == f"student_{w}_{a}"
            assert st.world.world_id == w
