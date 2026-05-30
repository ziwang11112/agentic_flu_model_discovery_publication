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


def _lagged(values: np.ndarray, delay: int) -> np.ndarray:
    if delay <= 0:
        return values.copy()
    return np.concatenate([np.repeat(values[0], delay), values[:-delay]])


def candidate_observation_series(latent: np.ndarray) -> dict[str, tuple[str, np.ndarray]]:
    return {
        "direct": ("0", latent),
        "lagged_1": ("1", _lagged(latent, 1)),
        "lagged_2": ("2", _lagged(latent, 2)),
        "mixture": ("mixed", 0.6 * latent + 0.4 * _lagged(latent, 2)),
    }


def generate_toy_series(scenario_name: str, seed: int, n: int = 48, noise_scale: float = 0.02) -> ToyTask:
    rng = np.random.default_rng(seed)
    t = np.arange(n, dtype=float)
    latent = 1.0 + 0.25 * np.sin(2.0 * np.pi * t / 12.0) + 0.015 * t
    if scenario_name in {"sinusoidal_direct", "direct_signal"}:
        observed = latent + rng.normal(0.0, noise_scale, size=n)
        return ToyTask(scenario_name, observed, latent, "direct", "0", seed)
    if scenario_name == "lagged_signal_1":
        observed = _lagged(latent, 1) + rng.normal(0.0, noise_scale, size=n)
        return ToyTask(scenario_name, observed, latent, "lagged_1", "1", seed)
    if scenario_name in {"lagged_observation", "lagged_signal_2"}:
        observed = _lagged(latent, 2) + rng.normal(0.0, noise_scale, size=n)
        return ToyTask(scenario_name, observed, latent, "lagged_2", "2", seed)
    if scenario_name == "mixture_signal":
        observed = 0.6 * latent + 0.4 * _lagged(latent, 2) + rng.normal(0.0, noise_scale, size=n)
        return ToyTask(scenario_name, observed, latent, "mixture", "mixed", seed)
    if scenario_name == "noisy_lagged_signal":
        observed = _lagged(latent, 2) + rng.normal(0.0, max(noise_scale, 0.08), size=n)
        return ToyTask(scenario_name, observed, latent, "lagged_2", "2", seed)
    raise ValueError(f"Unsupported toy scenario: {scenario_name}")


def score_observation_label_candidates(task: ToyTask) -> dict[str, dict[str, object]]:
    candidates = candidate_observation_series(task.latent)
    return {
        label: {
            "observation_label": label,
            "delay_label": delay_label,
            "rolling_error": float(np.mean(np.abs(task.observed - values))),
        }
        for label, (delay_label, values) in candidates.items()
    }


def recover_observation_label(task: ToyTask) -> dict[str, object]:
    scored = score_observation_label_candidates(task)
    selected = sorted(scored, key=lambda label: (float(scored[label]["rolling_error"]), label))[0]
    return {
        "scenario_name": task.scenario_name,
        "seed": int(task.seed),
        "true_observation_label": task.true_observation_label,
        "true_delay_label": task.delay_label,
        "selected_observation_label": selected,
        "selected_delay_label": scored[selected]["delay_label"],
        "recovered": bool(selected == task.true_observation_label),
        "delay_recovered": bool(scored[selected]["delay_label"] == task.delay_label),
        "direct_mae": scored["direct"]["rolling_error"],
        "lagged_1_mae": scored["lagged_1"]["rolling_error"],
        "lagged_2_mae": scored["lagged_2"]["rolling_error"],
        "mixture_mae": scored["mixture"]["rolling_error"],
    }


def run_toy_recovery(scenarios: list[str], seeds: list[int]) -> pd.DataFrame:
    records = [recover_observation_label(generate_toy_series(scenario, seed)) for scenario in scenarios for seed in seeds]
    return pd.DataFrame.from_records(records)
