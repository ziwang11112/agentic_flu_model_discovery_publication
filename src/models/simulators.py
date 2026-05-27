from __future__ import annotations

import math
from typing import Callable

import numpy as np


def euler_discrete_simulation(
    initial_state: np.ndarray,
    n_steps: int,
    drift_fn: Callable[[np.ndarray, int], np.ndarray],
) -> np.ndarray:
    """Forward-simulate a discrete epidemic system with Euler-style updates."""
    states = np.zeros((n_steps, initial_state.size), dtype=float)
    states[0] = initial_state
    for t in range(n_steps - 1):
        next_state = states[t] + drift_fn(states[t], t)
        if not np.all(np.isfinite(next_state)):
            states[t + 1 :] = np.nan
            break
        states[t + 1] = next_state
    return states


def caputo_l1_simulation(
    initial_state: np.ndarray,
    n_steps: int,
    alpha: float,
    drift_fn: Callable[[np.ndarray, int], np.ndarray],
) -> np.ndarray:
    """Caputo-style L1 discrete-memory approximation."""
    states = np.zeros((n_steps, initial_state.size), dtype=float)
    drifts = np.zeros_like(states)
    states[0] = initial_state
    drifts[0] = drift_fn(states[0], 0)
    coefficient = 1.0 / math.gamma(alpha + 1.0)

    for next_idx in range(1, n_steps):
        weights = np.array(
            [
                (next_idx - j) ** alpha - (next_idx - 1 - j) ** alpha
                for j in range(next_idx)
            ],
            dtype=float,
        )
        next_state = initial_state + coefficient * np.sum(weights[:, None] * drifts[:next_idx], axis=0)
        if not np.all(np.isfinite(next_state)):
            states[next_idx:] = np.nan
            break
        states[next_idx] = next_state
        drifts[next_idx] = drift_fn(states[next_idx], next_idx)
    return states


def negative_state_penalty(states: np.ndarray) -> float:
    """Average squared amount of state negativity."""
    return float(np.mean(np.square(np.minimum(states, 0.0))))


def mass_conservation_penalty(states: np.ndarray) -> float:
    """Average squared total-population drift."""
    return float(np.mean(np.square(np.sum(states, axis=1) - 1.0)))
