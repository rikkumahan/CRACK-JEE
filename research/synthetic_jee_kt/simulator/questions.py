"""eQOURSE question ingestion, normalization, and question bank management."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

DIFFICULTY_MAP = {
    "easy": 0.25,
    "moderate": 0.50,
    "medium": 0.50,
    "tough": 0.75,
    "hard": 0.75,
}

DEFAULT_DIFFICULTY = 0.50


def format_concept_id(subject: str, topic: str, subtopic: Optional[str] = None) -> str:
    """Creates a canonical concept ID from subject, topic, and subtopic."""
    sub = (subtopic or topic or "General").strip()
    top = (topic or "General").strip()
    subj = (subject or "General").strip()
    return f"{subj}::{top}::{sub}"


def normalize_question(record: Dict[str, Any]) -> Dict[str, Any]:
    """Normalizes an eQOURSE question record into standard simulator schema."""
    qid = str(record.get("question_id") or record.get("id") or "")
    subject = str(record.get("subject") or "General").strip()
    topic = str(record.get("topic") or "General").strip()
    subtopic = str(record.get("subtopic") or topic or "General").strip()

    raw_diff = str(record.get("difficulty") or "").strip().lower()
    difficulty = DIFFICULTY_MAP.get(raw_diff, DEFAULT_DIFFICULTY)

    q_type = str(record.get("question_type") or "single_correct").strip()
    correct_opt = str(record.get("correct_option") or record.get("answer") or "").strip()

    concept_id = format_concept_id(subject, topic, subtopic)

    # Multi-concept support: if custom question_concepts exists, keep it; else single concept
    if "question_concepts" in record and isinstance(record["question_concepts"], list):
        q_concepts = record["question_concepts"]
    else:
        q_concepts = [{"concept_id": concept_id, "weight": 1.0}]

    return {
        "question_id": qid,
        "subject": subject,
        "topic": topic,
        "subtopic": subtopic,
        "difficulty": difficulty,
        "question_type": q_type,
        "correct_option": correct_opt,
        "concept_id": concept_id,
        "question_concepts": q_concepts,
        "solution": record.get("solution", ""),
        "has_image": bool(record.get("has_image", False)),
    }


class ConceptRegistry:
    """Registry of unique concepts across subjects and topics."""

    def __init__(self):
        self._concepts: Dict[str, Dict[str, str]] = {}

    def register(self, concept_id: str, subject: str, topic: str, subtopic: str) -> None:
        if concept_id not in self._concepts:
            self._concepts[concept_id] = {
                "concept_id": concept_id,
                "subject": subject,
                "topic": topic,
                "subtopic": subtopic,
            }

    def get(self, concept_id: str) -> Optional[Dict[str, str]]:
        return self._concepts.get(concept_id)

    def all_concepts(self) -> List[Dict[str, str]]:
        return list(self._concepts.values())

    def __len__(self) -> int:
        return len(self._concepts)

    def __contains__(self, concept_id: str) -> bool:
        return concept_id in self._concepts


class QuestionBank:
    """In-memory question pool indexing items by ID, concept, and subject."""

    def __init__(self, questions: Optional[List[Dict[str, Any]]] = None):
        self.items: List[Dict[str, Any]] = []
        self._by_id: Dict[str, Dict[str, Any]] = {}
        self._by_concept: Dict[str, List[Dict[str, Any]]] = {}
        self._by_subject: Dict[str, List[Dict[str, Any]]] = {}
        self.concept_registry = ConceptRegistry()

        if questions:
            for q in questions:
                self.add(q)

    def add(self, question: Dict[str, Any]) -> None:
        norm_q = question if "concept_id" in question else normalize_question(question)
        qid = norm_q["question_id"]
        self.items.append(norm_q)
        self._by_id[qid] = norm_q

        cid = norm_q["concept_id"]
        self._by_concept.setdefault(cid, []).append(norm_q)
        self._by_subject.setdefault(norm_q["subject"], []).append(norm_q)

        self.concept_registry.register(
            cid, norm_q["subject"], norm_q["topic"], norm_q["subtopic"]
        )

        # Register any other concepts in question_concepts
        for qc in norm_q.get("question_concepts", []):
            if qc["concept_id"] not in self.concept_registry:
                parts = qc["concept_id"].split("::")
                subj = parts[0] if len(parts) > 0 else norm_q["subject"]
                top = parts[1] if len(parts) > 1 else norm_q["topic"]
                subt = parts[2] if len(parts) > 2 else norm_q["subtopic"]
                self.concept_registry.register(qc["concept_id"], subj, top, subt)

    def get(self, question_id: str) -> Optional[Dict[str, Any]]:
        return self._by_id.get(question_id)

    def filter(
        self,
        subject: Optional[str] = None,
        concept_id: Optional[str] = None,
        max_difficulty: Optional[float] = None,
        min_difficulty: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        results = self.items
        if subject is not None:
            results = self._by_subject.get(subject, [])
        if concept_id is not None:
            results = [q for q in results if q["concept_id"] == concept_id]
        if min_difficulty is not None:
            results = [q for q in results if q["difficulty"] >= min_difficulty]
        if max_difficulty is not None:
            results = [q for q in results if q["difficulty"] <= max_difficulty]
        return results

    @property
    def concepts(self) -> List[str]:
        return list(self._by_concept.keys())

    def __len__(self) -> int:
        return len(self.items)

    def to_json(self, path: Union[str, Path]) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.items, f, indent=2)

    @classmethod
    def from_json(cls, path: Union[str, Path]) -> "QuestionBank":
        path = Path(path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(data)
