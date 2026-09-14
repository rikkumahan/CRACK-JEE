import pytest
from pathlib import Path
from simulator.questions import normalize_question, QuestionBank, ConceptRegistry

SAMPLE_RAW_RECORD = {
    "question_id": "chem_001",
    "subject": "Chemistry",
    "topic": "Physical Chemistry",
    "subtopic": "Thermodynamics",
    "difficulty": "Moderate",
    "question_type": "single_correct",
    "correct_option": "B",
    "has_image": False,
    "solution": "Sample solution"
}

def test_normalize_question_difficulty_mapping():
    # Easy -> 0.25
    q_easy = normalize_question({**SAMPLE_RAW_RECORD, "difficulty": "Easy"})
    assert q_easy["difficulty"] == 0.25

    # Moderate -> 0.50
    q_mod = normalize_question({**SAMPLE_RAW_RECORD, "difficulty": "Moderate"})
    assert q_mod["difficulty"] == 0.50

    # Tough -> 0.75
    q_tough = normalize_question({**SAMPLE_RAW_RECORD, "difficulty": "Tough"})
    assert q_tough["difficulty"] == 0.75

    # Unknown difficulty defaults to 0.50
    q_unk = normalize_question({**SAMPLE_RAW_RECORD, "difficulty": "Unknown"})
    assert q_unk["difficulty"] == 0.50

def test_normalize_question_concepts():
    q = normalize_question(SAMPLE_RAW_RECORD)
    assert "concept_id" in q
    assert q["concept_id"] == "Chemistry::Physical Chemistry::Thermodynamics"
    assert "question_concepts" in q
    assert len(q["question_concepts"]) >= 1
    # Check weights sum to 1.0
    total_weight = sum(qc["weight"] for qc in q["question_concepts"])
    assert pytest.approx(total_weight) == 1.0

def test_concept_registry_and_question_bank():
    records = [
        {
            "question_id": "phy_001",
            "subject": "Physics",
            "topic": "Mechanics",
            "subtopic": "Rotational Motion",
            "difficulty": "Tough",
            "question_type": "single_correct",
            "correct_option": "A",
        },
        {
            "question_id": "phy_002",
            "subject": "Physics",
            "topic": "Mechanics",
            "subtopic": "Rotational Motion",
            "difficulty": "Moderate",
            "question_type": "numerical",
            "correct_option": "42",
        },
        {
            "question_id": "math_001",
            "subject": "Mathematics",
            "topic": "Calculus",
            "subtopic": "Definite Integration",
            "difficulty": "Easy",
            "question_type": "single_correct",
            "correct_option": "C",
        },
    ]

    normalized = [normalize_question(r) for r in records]
    bank = QuestionBank(normalized)

    assert len(bank) == 3
    assert bank.get("phy_001")["difficulty"] == 0.75
    assert len(bank.filter(subject="Physics")) == 2
    assert len(bank.filter(concept_id="Physics::Mechanics::Rotational Motion")) == 2
    assert len(bank.concepts) == 2

    # Verify concepts registry
    registry = bank.concept_registry
    concept = registry.get("Physics::Mechanics::Rotational Motion")
    assert concept is not None
    assert concept["subject"] == "Physics"
    assert concept["topic"] == "Mechanics"
    assert concept["subtopic"] == "Rotational Motion"


def test_load_ingested_eqourse_items():
    items_path = Path(__file__).resolve().parent.parent / "data" / "raw" / "items.json"
    if items_path.exists():
        bank = QuestionBank.from_json(items_path)
        assert len(bank) == 2307
        assert len(bank.concepts) > 500
        # Verify fields on first item
        q = bank.items[0]
        assert "question_id" in q
        assert "subject" in q
        assert "difficulty" in q
        assert 0.0 <= q["difficulty"] <= 1.0
        assert "question_concepts" in q
