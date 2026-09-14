"""Dataset generator for synthetic JEE student interaction trajectories."""

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

# Add repo to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from simulator.questions import QuestionBank, build_fallback_items, normalize_question
from simulator.worlds import create_student, load_archetypes_config, load_worlds_config


@dataclass
class GenerationConfig:
    seed: int = 42
    worlds: List[str] = field(default_factory=lambda: ["A", "B", "C", "D", "E", "F", "G"])
    students_per_world: int = 50
    interactions_per_student: int = 500
    output_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent / "data" / "generated"
    )
    items_path: Optional[Path] = None


def generate_dataset(config: GenerationConfig) -> Dict[str, Path]:
    """Generates synthetic interactions and ground truth with bit-exact seed reproducibility."""
    rng = np.random.default_rng(config.seed)

    # 1. Load Question Bank
    if config.items_path and Path(config.items_path).exists():
        bank = QuestionBank.from_json(config.items_path)
    else:
        default_raw = (
            Path(__file__).resolve().parent.parent / "data" / "raw" / "items.json"
        )
        if default_raw.exists():
            bank = QuestionBank.from_json(default_raw)
        else:
            raw_fallback = build_fallback_items()
            bank = QuestionBank([normalize_question(r) for r in raw_fallback])

    questions = bank.items
    num_questions = len(questions)
    assert num_questions > 0, "QuestionBank is empty!"

    # 2. Load configurations
    worlds_dict = load_worlds_config()
    archetypes_dict = load_archetypes_config()
    archetype_keys = sorted(list(archetypes_dict.keys()))

    interactions: List[Dict[str, Any]] = []
    ground_truth_records: List[Dict[str, Any]] = []

    # Get sample concepts for ground truth tracking
    all_concepts = bank.concepts
    # To keep ground truth file compact and relevant, sample up to 30 core concepts per student
    tracked_concepts = all_concepts[: min(40, len(all_concepts))]

    total_students = 0

    for world_id in config.worlds:
        for s_idx in range(config.students_per_world):
            total_students += 1
            student_id = f"STU_{world_id}_{s_idx + 1:04d}"
            # Cycle through archetypes deterministically
            archetype_id = archetype_keys[s_idx % len(archetype_keys)]

            student = create_student(
                student_id=student_id,
                archetype_id=archetype_id,
                world_id=world_id,
                rng=rng,
                worlds_dict=worlds_dict,
                archetypes_dict=archetypes_dict,
            )

            # Initialize mastery on tracked concepts
            initial_mastery_map: Dict[str, float] = {}
            for cid in tracked_concepts:
                init_m = float(
                    np.clip(
                        rng.normal(student._default_init_mean, student._default_init_std),
                        0.05,
                        0.95,
                    )
                )
                student.set_concept_mastery(cid, init_m, day=0.0)
                initial_mastery_map[cid] = init_m

            # Simulate student practice sequence over time
            # Start at timestamp = 1704067200 (2024-01-01 00:00:00 UTC)
            current_time = 1704067200.0

            for i_idx in range(config.interactions_per_student):
                # Realistic study spacing:
                # 85% within-session (2-8 minutes), 15% study break (1-4 days)
                if i_idx > 0 and rng.random() < 0.15:
                    time_jump_seconds = float(rng.uniform(1.0, 4.0) * 86400.0)
                else:
                    time_jump_seconds = float(rng.uniform(120.0, 480.0))

                current_time += time_jump_seconds

                # Question selection:
                # With probability 0.7, pick question from tracked concepts to build depth; else random
                if rng.random() < 0.70 and tracked_concepts:
                    target_cid = tracked_concepts[int(rng.integers(0, len(tracked_concepts)))]
                    q_candidates = bank.filter(concept_id=target_cid)
                    if q_candidates:
                        q = q_candidates[int(rng.integers(0, len(q_candidates)))]
                    else:
                        q = questions[int(rng.integers(0, num_questions))]
                else:
                    q = questions[int(rng.integers(0, num_questions))]

                # World G (multi-concept interference): synthesize multi-concept question if needed
                if student.world.world_id == "G" and rng.random() < student.world.multi_concept_ratio:
                    second_concept = tracked_concepts[int(rng.integers(0, len(tracked_concepts)))]
                    q_mod = dict(q)
                    q_mod["question_concepts"] = [
                        {"concept_id": q["concept_id"], "weight": 0.6},
                        {"concept_id": second_concept, "weight": 0.4},
                    ]
                    q = q_mod

                # Time budget for World E
                time_budget = 90.0 if student.world.time_pressure_active else None

                record = student.answer_question(q, timestamp=current_time, time_budget=time_budget)
                record["world_id"] = world_id
                record["archetype"] = archetype_id
                interactions.append(record)

            # Record final ground truth for tracked concepts
            for cid in tracked_concepts:
                ground_truth_records.append({
                    "student_id": student_id,
                    "archetype": archetype_id,
                    "world_id": world_id,
                    "concept_id": cid,
                    "initial_mastery": round(initial_mastery_map[cid], 4),
                    "final_mastery": round(student.get_concept_mastery(cid), 4),
                    "learning_rate": round(student.config.learning_rate, 4),
                    "forgetting_rate": round(student.config.forgetting_rate, 4),
                    "slip_rate": round(student.config.slip_rate, 4),
                    "guess_rate": round(student.config.guess_rate, 4),
                    "careless_rate": round(student.config.careless_error_tendency, 4),
                    "time_pressure_sensitivity": round(student.config.time_pressure_sensitivity, 4),
                    "speed_factor": round(student.config.baseline_speed, 2),
                })

    # Save output CSVs
    out_dir = Path(config.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    interactions_path = out_dir / "synthetic_interactions.csv"
    ground_truth_path = out_dir / "student_ground_truth.csv"
    manifest_path = out_dir / "generation_manifest.json"

    # Export interactions
    df_int = pd.DataFrame(interactions)
    # Ensure correct column order per brief §9A
    col_order = [
        "student_id", "question_id", "exam", "year", "shift",
        "subject", "chapter", "concept_id", "timestamp", "correct",
        "time_seconds", "confidence", "error_type", "answer_changed",
        "source", "world_id", "archetype", "ground_truth_mastery"
    ]
    for c in col_order:
        if c not in df_int.columns:
            df_int[c] = ""
    df_int = df_int[col_order]
    df_int.to_csv(interactions_path, index=False, float_format="%.4f")

    # Export ground truth
    df_gt = pd.DataFrame(ground_truth_records)
    df_gt.to_csv(ground_truth_path, index=False, float_format="%.4f")

    # Export manifest
    manifest = {
        "seed": config.seed,
        "worlds": config.worlds,
        "students_per_world": config.students_per_world,
        "interactions_per_student": config.interactions_per_student,
        "total_students": total_students,
        "total_interactions": len(interactions),
        "tracked_concepts_count": len(tracked_concepts),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0.0",
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return {
        "interactions": interactions_path,
        "ground_truth": ground_truth_path,
        "manifest": manifest_path,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic JEE learner dataset.")
    parser.add_argument("--seed", type=int, default=42, help="Global random seed.")
    parser.add_argument("--worlds", type=str, default="A,B,C,D,E,F,G", help="Comma-separated worlds.")
    parser.add_argument("--students-per-world", type=int, default=50, help="Number of students per world.")
    parser.add_argument("--interactions-per-student", type=int, default=500, help="Interactions per student.")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory path.")
    parser.add_argument("--items-path", type=str, default=None, help="Path to items.json.")
    args = parser.parse_args()

    worlds_list = [w.strip() for w in args.worlds.split(",") if w.strip()]
    out_dir = Path(args.output_dir) if args.output_dir else Path(__file__).resolve().parent.parent / "data" / "generated"
    items_path = Path(args.items_path) if args.items_path else None

    config = GenerationConfig(
        seed=args.seed,
        worlds=worlds_list,
        students_per_world=args.students_per_world,
        interactions_per_student=args.interactions_per_student,
        output_dir=out_dir,
        items_path=items_path,
    )

    print(f"Generating synthetic dataset with seed {config.seed} across worlds: {config.worlds}...")
    paths = generate_dataset(config)
    print(f"Dataset generated successfully:")
    for k, p in paths.items():
        print(f"  - {k}: {p}")


if __name__ == "__main__":
    main()

