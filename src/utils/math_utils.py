from __future__ import annotations

import math
from typing import Callable

import numpy as np


def softplus(x: float | np.ndarray) -> float | np.ndarray:
    """Stable softplus transform."""
    values = np.asarray(x)
    out = np.log1p(np.exp(-np.abs(values))) + np.maximum(values, 0.0)
    if np.isscalar(x):
        return float(out)
    return out


def sigmoid(x: float | np.ndarray) -> float | np.ndarray:
    """Stable logistic transform."""
    values = np.asarray(x)
    out = 1.0 / (1.0 + np.exp(-np.clip(values, -60.0, 60.0)))
    if np.isscalar(x):
        return float(out)
    return out


def softmax(x: np.ndarray) -> np.ndarray:
    """Stable softmax transform."""
    shifted = x - np.max(x)
    exps = np.exp(np.clip(shifted, -60.0, 60.0))
    return exps / np.sum(exps)


def seasonal_beta(t: int | np.ndarray, b0: float, b1: float, b2: float) -> np.ndarray:
    """Seasonal transmission rate with 52-week period."""
    t_array = np.asarray(t, dtype=float)
    phase = 2.0 * math.pi * t_array / 52.0
    return np.asarray(softplus(b0 + b1 * np.sin(phase) + b2 * np.cos(phase)), dtype=float)


def finite_difference_hessian(
    objective: Callable[[np.ndarray], float],
    x0: np.ndarray,
    step_scale: float = 1.0e-4,
) -> np.ndarray:
    """Approximate a Hessian with centered finite differences."""
    x0 = np.asarray(x0, dtype=float)
    n_params = x0.size
    hessian = np.zeros((n_params, n_params), dtype=float)
    steps = step_scale * np.maximum(1.0, np.abs(x0))
    fx = objective(x0)

    for i in range(n_params):
        ei = np.zeros_like(x0)
        ei[i] = steps[i]
        f_plus = objective(x0 + ei)
        f_minus = objective(x0 - ei)
        hessian[i, i] = (f_plus - 2.0 * fx + f_minus) / (steps[i] ** 2)

        for j in range(i + 1, n_params):
            ej = np.zeros_like(x0)
            ej[j] = steps[j]
            f_pp = objective(x0 + ei + ej)
            f_pm = objective(x0 + ei - ej)
            f_mp = objective(x0 - ei + ej)
            f_mm = objective(x0 - ei - ej)
            value = (f_pp - f_pm - f_mp + f_mm) / (4.0 * steps[i] * steps[j])
            hessian[i, j] = value
            hessian[j, i] = value

    return hessian
