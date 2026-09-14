"""World and Archetype configuration loading and student factory."""

from pathlib import Path
from typing import Any, Dict, Optional
import numpy as np
import yaml

from simulator.student import StudentConfig, SyntheticStudent, WorldConfig


def load_worlds_config(config_path: Optional[Path] = None) -> Dict[str, WorldConfig]:
    if config_path is None:
        config_path = (
            Path(__file__).resolve().parent.parent / "configs" / "worlds.yaml"
        )
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    worlds = {}
    for wid, data in raw.get("worlds", {}).items():
        worlds[wid] = WorldConfig(
            world_id=wid,
            name=data.get("name", wid),
            learning_dynamics=data.get("learning_dynamics", "diminishing"),
            learning_rate_multiplier=float(data.get("learning_rate_multiplier", 1.0)),
            grace_days=int(data.get("grace_days", 14)),
            forgetting_rate_multiplier=float(data.get("forgetting_rate_multiplier", 1.0)),
            slip_rate_multiplier=float(data.get("slip_rate_multiplier", 1.0)),
            guess_rate_multiplier=float(data.get("guess_rate_multiplier", 1.0)),
            prerequisite_gating=bool(data.get("prerequisite_gating", False)),
            prerequisite_cap=float(data.get("prerequisite_cap", 0.3)),
            time_pressure_active=bool(data.get("time_pressure_active", False)),
            time_pressure_sensitivity=float(data.get("time_pressure_sensitivity", 0.0)),
            confidence_bias_scale=float(data.get("confidence_bias_scale", 0.0)),
            multi_concept_ratio=float(data.get("multi_concept_ratio", 0.0)),
        )
    return worlds


def load_archetypes_config(config_path: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    if config_path is None:
        config_path = (
            Path(__file__).resolve().parent.parent / "configs" / "archetypes.yaml"
        )
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return raw.get("archetypes", {})


def create_student(
    student_id: str,
    archetype_id: str = "S10",
    world_id: str = "A",
    rng: Optional[np.random.Generator] = None,
    worlds_dict: Optional[Dict[str, WorldConfig]] = None,
    archetypes_dict: Optional[Dict[str, Dict[str, Any]]] = None,
) -> SyntheticStudent:
    """Instantiates a SyntheticStudent according to archetype preset and world parameters."""
    rng = rng or np.random.default_rng()
    if worlds_dict is None:
        worlds_dict = load_worlds_config()
    if archetypes_dict is None:
        archetypes_dict = load_archetypes_config()

    arch = archetypes_dict.get(archetype_id, archetypes_dict.get("S10", {}))
    world = worlds_dict.get(world_id, WorldConfig())

    # Add small stochastic jitter to student parameters per spec
    lr = float(np.clip(arch.get("learning_rate", 0.18) + rng.normal(0, 0.02), 0.05, 0.60))
    fr = float(np.clip(arch.get("forgetting_rate", 0.03) + rng.normal(0, 0.005), 0.005, 0.25))
    sr = float(np.clip(arch.get("slip_rate", 0.10) + rng.normal(0, 0.01), 0.01, 0.40))
    gr = float(np.clip(arch.get("guess_rate", 0.18) + rng.normal(0, 0.02), 0.05, 0.45))
    speed = float(np.clip(arch.get("baseline_speed", 90.0) + rng.normal(0, 5.0), 30.0, 240.0))

    config = StudentConfig(
        student_id=student_id,
        archetype=archetype_id,
        learning_rate=lr,
        forgetting_rate=fr,
        slip_rate=sr,
        guess_rate=gr,
        baseline_speed=speed,
        careless_error_tendency=float(arch.get("careless_error_tendency", 0.10)),
        time_pressure_sensitivity=float(arch.get("time_pressure_sensitivity", 0.20)),
        confidence_bias=float(arch.get("confidence_bias", 0.0)),
        response_time_variability=0.10,
    )

    student = SyntheticStudent(config, world_config=world, rng=rng)

    # Initialize mastery distribution
    init_mean = float(arch.get("initial_mastery_mean", 0.40))
    init_std = float(arch.get("initial_mastery_std", 0.10))
    student._default_init_mean = init_mean
    student._default_init_std = init_std

    return student

