from __future__ import annotations

from typing import Any

import numpy as np


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(y_true - y_pred))))


def smape(y_true: np.ndarray, y_pred: np.ndarray, eps: float = 1.0e-8) -> float:
    denom = np.abs(y_true) + np.abs(y_pred) + eps
    return float(np.mean(2.0 * np.abs(y_pred - y_true) / denom))


def point_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "mae": mae(y_true, y_pred),
        "rmse": rmse(y_true, y_pred),
        "smape": smape(y_true, y_pred),
    }


def interval_coverage(y_true: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> float:
    inside = (y_true >= lower) & (y_true <= upper)
    return float(np.mean(inside))


def average_interval_width(lower: np.ndarray, upper: np.ndarray) -> float:
    return float(np.mean(upper - lower))


def interval_level_summary(
    y_true: np.ndarray,
    interval_map: dict[str, tuple[np.ndarray, np.ndarray]],
) -> dict[str, dict[str, float]]:
    """Summarize empirical coverage and width for each interval level."""
    summary: dict[str, dict[str, float]] = {}
    for level in sorted(interval_map.keys(), key=int):
        lower, upper = interval_map[level]
        empirical = interval_coverage(y_true, lower, upper)
        nominal = float(level) / 100.0
        summary[level] = {
            "nominal_coverage": nominal,
            "empirical_coverage": empirical,
            "coverage_gap": empirical - nominal,
            "average_interval_width": average_interval_width(lower, upper),
        }
    return summary


def scale_interval_map(
    interval_map: dict[str, tuple[np.ndarray, np.ndarray]],
    center: np.ndarray,
    scale: float | dict[str, float],
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Scale interval widths around a shared center forecast."""
    scaled: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for level, (lower, upper) in interval_map.items():
        level_scale = float(scale[level]) if isinstance(scale, dict) else float(scale)
        lower_scaled = center - level_scale * (center - lower)
        upper_scaled = center + level_scale * (upper - center)
        lower_final = np.minimum(lower_scaled, upper_scaled)
        upper_final = np.maximum(lower_scaled, upper_scaled)
        scaled[level] = (lower_final, upper_final)
    return scaled


def learn_interval_scales(
    y_true: np.ndarray,
    center: np.ndarray,
    interval_map: dict[str, tuple[np.ndarray, np.ndarray]],
    scale_min: float = 0.25,
    scale_max: float = 1.25,
    grid_size: int = 41,
) -> dict[str, Any]:
    """Choose one scale per interval level by matching validation coverage to nominal."""
    candidate_scales = np.linspace(scale_min, scale_max, grid_size)
    best_scales: dict[str, float] = {}
    best_objectives: dict[str, float] = {}

    for level, bounds in interval_map.items():
        best_scale = float(candidate_scales[0])
        best_objective = float("inf")
        for scale in candidate_scales:
            scaled_bounds = scale_interval_map({level: bounds}, center, float(scale))[level]
            summary = interval_level_summary(y_true, {level: scaled_bounds})[level]
            objective = abs(summary["coverage_gap"]) + 1.0e-6 * float(scale)
            if objective < best_objective:
                best_objective = float(objective)
                best_scale = float(scale)
        best_scales[level] = best_scale
        best_objectives[level] = best_objective

    if not best_scales:
        raise RuntimeError("Interval calibration scale search failed.")

    best_summary = interval_level_summary(y_true, scale_interval_map(interval_map, center, best_scales))

    return {
        "scales": best_scales,
        "objective": float(np.mean(list(best_objectives.values()))),
        "objective_by_level": best_objectives,
        "grid_size": int(grid_size),
        "scale_min": float(scale_min),
        "scale_max": float(scale_max),
        "interval_summary": best_summary,
    }


def learn_conformal_interval_scales(
    y_true: np.ndarray,
    center: np.ndarray,
    interval_map: dict[str, tuple[np.ndarray, np.ndarray]],
    eps: float = 1.0e-8,
) -> dict[str, Any]:
    """Learn per-level multiplicative interval adjustments from validation conformity ratios."""
    best_scales: dict[str, float] = {}
    best_objectives: dict[str, float] = {}

    for level, (lower, upper) in interval_map.items():
        lower_radius = np.maximum(center - lower, eps)
        upper_radius = np.maximum(upper - center, eps)
        conformity = np.maximum((center - y_true) / lower_radius, (y_true - center) / upper_radius)
        conformity = np.where(np.isfinite(conformity), conformity, 1.0)
        conformity = np.clip(conformity, 0.0, None)
        sorted_scores = np.sort(conformity)
        nominal = float(level) / 100.0
        rank = int(np.ceil((len(sorted_scores) + 1) * nominal) - 1)
        rank = min(max(rank, 0), len(sorted_scores) - 1)
        scale = float(sorted_scores[rank])
        best_scales[level] = scale

    if not best_scales:
        raise RuntimeError("Conformal interval calibration search failed.")

    best_summary = interval_level_summary(y_true, scale_interval_map(interval_map, center, best_scales))
    for level, values in best_summary.items():
        best_objectives[level] = abs(values["coverage_gap"])

    return {
        "scales": best_scales,
        "objective": float(np.mean(list(best_objectives.values()))),
        "objective_by_level": best_objectives,
        "method": "conformal",
        "interval_summary": best_summary,
    }


def interval_level_summary_from_frame(
    frame,
    levels: tuple[str, ...] = ("50", "80", "95"),
) -> dict[str, dict[str, float]]:
    """Build interval summaries from a forecast trace DataFrame."""
    interval_map: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for level in levels:
        lower_col = f"lower_{level}"
        upper_col = f"upper_{level}"
        if lower_col in frame.columns and upper_col in frame.columns:
            interval_map[level] = (
                frame[lower_col].to_numpy(dtype=float),
                frame[upper_col].to_numpy(dtype=float),
            )

    if not interval_map:
        return {}

    y_true = frame["actual"].to_numpy(dtype=float)
    return interval_level_summary(y_true, interval_map)


def summarise_probabilistic_metrics(
    y_true: np.ndarray,
    nll: float | None,
    interval_map: dict[str, tuple[np.ndarray, np.ndarray]] | None,
) -> dict[str, Any]:
    if interval_map is None:
        return {
            "negative_log_likelihood": nll,
            "coverage_50": None,
            "coverage_80": None,
            "coverage_95": None,
            "average_interval_width_50": None,
            "average_interval_width_80": None,
            "average_interval_width_95": None,
            "interval_summary": {},
        }

    interval_summary = interval_level_summary(y_true, interval_map)
    summary = {
        "negative_log_likelihood": nll,
        "coverage_50": None,
        "coverage_80": None,
        "coverage_95": None,
        "average_interval_width_50": None,
        "average_interval_width_80": None,
        "average_interval_width_95": None,
        "interval_summary": interval_summary,
    }
    for level, values in interval_summary.items():
        summary[f"coverage_{level}"] = values["empirical_coverage"]
        summary[f"average_interval_width_{level}"] = values["average_interval_width"]
    return summary
