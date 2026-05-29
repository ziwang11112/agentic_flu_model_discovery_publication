from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ToyTask:
    scenario_name: str
    observed: np.ndarray
    latent: np.ndarray
    true_observation_label: str
    delay_label: str
    seed: int


def generate_toy_series(scenario_name: str, seed: int, n: int = 48, noise_scale: float = 0.02) -> ToyTask:
    rng = np.random.default_rng(seed)
    t = np.arange(n, dtype=float)
    latent = 1.0 + 0.25 * np.sin(2.0 * np.pi * t / 12.0) + 0.015 * t
    if scenario_name == "sinusoidal_direct":
        observed = latent + rng.normal(0.0, noise_scale, size=n)
        return ToyTask(scenario_name, observed, latent, "direct", "0", seed)
    if scenario_name == "lagged_observation":
        delay = 2
        lagged = np.concatenate([np.repeat(latent[0], delay), latent[:-delay]])
        observed = lagged + rng.normal(0.0, noise_scale, size=n)
        return ToyTask(scenario_name, observed, latent, "lagged_2", str(delay), seed)
    raise ValueError(f"Unsupported toy scenario: {scenario_name}")


def recover_observation_label(task: ToyTask) -> dict[str, object]:
    candidates = {
        "direct": task.latent,
        "lagged_2": np.concatenate([np.repeat(task.latent[0], 2), task.latent[:-2]]),
    }
    scores = {
        label: float(np.mean(np.abs(task.observed - values)))
        for label, values in candidates.items()
    }
    selected = sorted(scores, key=lambda label: (scores[label], label))[0]
    return {
        "scenario_name": task.scenario_name,
        "seed": int(task.seed),
        "true_observation_label": task.true_observation_label,
        "selected_observation_label": selected,
        "recovered": bool(selected == task.true_observation_label),
        "direct_mae": scores["direct"],
        "lagged_2_mae": scores["lagged_2"],
    }


def run_toy_recovery(scenarios: list[str], seeds: list[int]) -> pd.DataFrame:
    records = [recover_observation_label(generate_toy_series(scenario, seed)) for scenario in scenarios for seed in seeds]
    return pd.DataFrame.from_records(records)
