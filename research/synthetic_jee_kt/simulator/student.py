"""Synthetic student model implementing IRT observation, learning dynamics, and error mechanisms."""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


@dataclass
class WorldConfig:
    world_id: str = "default"
    name: str = "Default"
    learning_dynamics: str = "diminishing"  # "diminishing" or "linear" (World A)
    learning_rate_multiplier: float = 1.0
    grace_days: int = 14
    forgetting_rate_multiplier: float = 1.0
    slip_rate_multiplier: float = 1.0
    guess_rate_multiplier: float = 1.0
    prerequisite_gating: bool = False
    prerequisite_cap: float = 0.3
    time_pressure_active: bool = False
    time_pressure_sensitivity: float = 0.0
    confidence_bias_scale: float = 0.0
    multi_concept_ratio: float = 0.0
    careless_error_elevated: bool = False


@dataclass
class StudentConfig:
    student_id: str
    archetype: str = "S10"
    learning_rate: float = 0.18
    forgetting_rate: float = 0.03
    slip_rate: float = 0.10
    guess_rate: float = 0.18
    baseline_speed: float = 90.0
    careless_error_tendency: float = 0.10
    time_pressure_sensitivity: float = 0.20
    confidence_bias: float = 0.0
    response_time_variability: float = 0.10


def sigmoid(x: float) -> float:
    if x >= 40.0:
        return 1.0
    elif x <= -40.0:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


class SyntheticStudent:
    """Controllable synthetic student learner agent."""

    def __init__(
        self,
        config: StudentConfig,
        world_config: Optional[WorldConfig] = None,
        rng: Optional[np.random.Generator] = None,
    ):
        self.config = config
        self.world = world_config or WorldConfig()
        self.rng = rng or np.random.default_rng()

        # Mastery per concept: concept_id -> float [0, 1]
        self._mastery: Dict[str, float] = {}
        # Last practice timestamp (in days) per concept
        self._last_practice_day: Dict[str, float] = {}

        # Effective student parameters modified by world
        self.effective_lr = self.config.learning_rate * self.world.learning_rate_multiplier
        self.effective_forget_rate = self.config.forgetting_rate * self.world.forgetting_rate_multiplier

        # Wire careless_error_tendency when careless errors are elevated (e.g. World D)
        careless_boost = (
            self.config.careless_error_tendency
            if (getattr(self.world, "careless_error_elevated", False) or self.world.world_id == "D")
            else 0.0
        )
        self.effective_slip = min(0.49, (self.config.slip_rate + careless_boost) * self.world.slip_rate_multiplier)
        self.effective_guess = min(0.49, self.config.guess_rate * self.world.guess_rate_multiplier)

    def set_concept_mastery(self, concept_id: str, mastery: float, day: float = 0.0) -> None:
        self._mastery[concept_id] = float(np.clip(mastery, 0.0, 1.0))
        self._last_practice_day[concept_id] = day

    def get_concept_mastery(self, concept_id: str) -> float:
        return self._mastery.get(concept_id, 0.20)

    def get_effective_mastery(
        self,
        concept_id: str,
        days_since_practice: Optional[float] = None,
        current_day: Optional[float] = None,
        prerequisite_id: Optional[str] = None,
    ) -> float:
        """Computes effective mastery applying forgetting curve and prerequisite gating."""
        raw_m = self.get_concept_mastery(concept_id)

        if days_since_practice is None:
            if current_day is not None and concept_id in self._last_practice_day:
                days_since_practice = max(0.0, current_day - self._last_practice_day[concept_id])
            else:
                days_since_practice = 0.0

        # Forgetting dynamics (§3.2)
        grace = self.world.grace_days
        floor = 0.15
        if days_since_practice <= grace:
            eff_m = raw_m
        else:
            idle = days_since_practice - grace
            eff_m = floor + (raw_m - floor) * math.exp(-self.effective_forget_rate * idle)
        eff_m = float(np.clip(eff_m, floor, 1.0))

        # World C: Prerequisite gating (§5)
        if self.world.prerequisite_gating and prerequisite_id is not None:
            prereq_eff = self.get_effective_mastery(
                prerequisite_id, current_day=current_day
            )
            cap = prereq_eff + self.world.prerequisite_cap
            eff_m = min(eff_m, cap)

        return eff_m

    def compute_p_correct(
        self,
        concept_id: str,
        difficulty: float,
        days_since_practice: Optional[float] = None,
        current_day: Optional[float] = None,
        question_concepts: Optional[List[Dict[str, Any]]] = None,
        prerequisite_id: Optional[str] = None,
    ) -> Tuple[float, float]:
        """Calculates (p_correct, p_know) using Rasch 2PL-IRT observation model."""
        # Multi-concept weighted average (§2)
        if question_concepts and len(question_concepts) > 0:
            total_weight = sum(qc.get("weight", 1.0) for qc in question_concepts)
            eff_m = sum(
                qc.get("weight", 1.0)
                * self.get_effective_mastery(
                    qc["concept_id"],
                    days_since_practice=days_since_practice,
                    current_day=current_day,
                )
                for qc in question_concepts
            ) / max(total_weight, 1e-6)
        else:
            eff_m = self.get_effective_mastery(
                concept_id,
                days_since_practice=days_since_practice,
                current_day=current_day,
                prerequisite_id=prerequisite_id,
            )

        # Ability logit with scale constant k = 4.0
        k = 4.0
        ability_logit = k * (eff_m - difficulty)
        p_know = sigmoid(ability_logit)

        # p_correct combination
        p_correct = p_know * (1.0 - self.effective_slip) + (1.0 - p_know) * self.effective_guess
        p_correct = float(np.clip(p_correct, 0.001, 0.999))
        return p_correct, p_know

    def update_learning(
        self,
        concept_id: str,
        outcome: int,
        current_day: float = 0.0,
        question_concepts: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Updates mastery on practice attempt (§3.1)."""
        target_concepts = (
            [qc["concept_id"] for qc in question_concepts]
            if question_concepts
            else [concept_id]
        )

        for cid in target_concepts:
            m = self.get_concept_mastery(cid)
            if self.world.learning_dynamics == "linear":
                # World A: near-linear gain
                gain = self.effective_lr * (0.6 + 0.4 * outcome)
            else:
                # Default: diminishing returns via (1 - mastery)
                gain = self.effective_lr * (1.0 - m) * (0.6 + 0.4 * outcome)

            new_m = float(np.clip(m + gain, 0.0, 1.0))
            self._mastery[cid] = new_m
            self._last_practice_day[cid] = current_day

    def determine_error_type(
        self, outcome: int, p_know: float, is_time_out: bool = False
    ) -> str:
        """Assigns error mechanism (§4 - 5 mechanisms for V1)."""
        if outcome == 1:
            if p_know < 0.30:
                return "GUESS"
            return "CORRECT"

        if is_time_out:
            return "TIME_PRESSURE"
        if p_know >= 0.70:
            return "SLIP"
        elif p_know < 0.35:
            return "CONCEPT_GAP"
        else:
            return "CALCULATION"

    def answer_question(
        self,
        question: Dict[str, Any],
        timestamp: float,
        time_budget: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Simulates student response to a question."""
        cid = question.get("concept_id", "General")
        diff = float(question.get("difficulty", 0.50))
        q_concepts = question.get("question_concepts")
        prereq_id = question.get("prerequisite_id")

        current_day = timestamp / 86400.0 if timestamp > 10000 else timestamp

        # Observation model
        p_correct, p_know = self.compute_p_correct(
            cid,
            difficulty=diff,
            current_day=current_day,
            question_concepts=q_concepts,
            prerequisite_id=prereq_id,
        )

        # Response time generation (§6)
        diff_factor = 1.0 + diff
        mu = math.log(max(10.0, self.config.baseline_speed * diff_factor))
        sigma = 0.3 + self.config.response_time_variability
        time_seconds = float(self.rng.lognormal(mean=mu, sigma=sigma))

        # World E: Time pressure logic
        is_time_out = False
        if self.world.time_pressure_active and time_budget is not None:
            if time_seconds > time_budget:
                is_time_out = True
                discount = max(0.1, 1.0 - self.config.time_pressure_sensitivity)
                p_correct = float(np.clip(p_correct * discount, 0.01, 0.99))

        # Sample outcome
        outcome = int(self.rng.random() < p_correct)

        # Confidence generation (§7)
        bias = self.config.confidence_bias + (
            self.rng.normal(0, self.world.confidence_bias_scale)
            if self.world.confidence_bias_scale > 0
            else 0.0
        )
        noise = float(self.rng.normal(0.0, 0.08))
        confidence = float(np.clip(p_know + bias + noise, 0.0, 1.0))

        # Error mechanism
        error_type = self.determine_error_type(outcome, p_know, is_time_out)

        # Update learning
        self.update_learning(cid, outcome, current_day, q_concepts)

        return {
            "student_id": self.config.student_id,
            "question_id": question.get("question_id", ""),
            "exam": question.get("exam", "JEE Main"),
            "year": question.get("year", 2024),
            "shift": question.get("shift", "Shift 1"),
            "subject": question.get("subject", "General"),
            "chapter": question.get("topic", "General"),
            "concept_id": cid,
            "timestamp": timestamp,
            "correct": outcome,
            "time_seconds": round(time_seconds, 1),
            "confidence": round(confidence, 3),
            "error_type": error_type,
            "answer_changed": bool(self.rng.random() < 0.08),
            "source": "synthetic_simulator",
            "p_know": round(p_know, 4),
            "ground_truth_mastery": round(self.get_concept_mastery(cid), 4),
        }

