from __future__ import annotations

from typing import Any, Callable

import numpy as np
import pandas as pd

from src.evaluation.metrics import point_metrics
from src.models.base import BaseEpidemicModel


def rolling_origin_forecasts(
    model_factory: Callable[[], BaseEpidemicModel],
    y: np.ndarray,
    horizons: list[int],
    seed: int,
    initial_train_size: int,
) -> pd.DataFrame:
    """Expanding-window rolling-origin forecasts for selected horizons."""
    records: list[dict[str, Any]] = []
    horizon_to_warm_start: dict[int, np.ndarray | None] = {horizon: None for horizon in horizons}
    rng = np.random.default_rng(seed)

    for horizon in horizons:
        for origin_end in range(initial_train_size, len(y) - horizon + 1):
            model = model_factory()
            fit_result = model.fit(
                y[:origin_end],
                rng,
                warm_start=horizon_to_warm_start[horizon],
                n_restarts=model.fit_config.rolling_n_restarts,
            )
            horizon_to_warm_start[horizon] = fit_result.raw_params
            rollout = model.simulate(fit_result.raw_params, origin_end + horizon)
            target_index = origin_end + horizon - 1
            records.append(
                {
                    "origin_end": origin_end,
                    "target_t": target_index,
                    "horizon": horizon,
                    "actual": float(y[target_index]),
                    "prediction": float(rollout.predictions[target_index]),
                    "error": float(rollout.predictions[target_index] - y[target_index]),
                    "abs_error": float(abs(rollout.predictions[target_index] - y[target_index])),
                }
            )

    frame = pd.DataFrame.from_records(records)
    if frame.empty:
        return frame
    return frame.sort_values(["horizon", "target_t"]).reset_index(drop=True)


def rolling_metrics_by_horizon(frame: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Summarize rolling-origin metrics per horizon."""
    metrics: dict[str, dict[str, float]] = {}
    for horizon, subset in frame.groupby("horizon"):
        metrics[str(int(horizon))] = point_metrics(
            subset["actual"].to_numpy(dtype=float),
            subset["prediction"].to_numpy(dtype=float),
        )
    return metrics


def mean_rolling_metric(frame: pd.DataFrame, metric_name: str) -> float:
    """Average one rolling metric across all horizons."""
    per_horizon = rolling_metrics_by_horizon(frame)
    values = [metrics[metric_name] for metrics in per_horizon.values()]
    return float(np.mean(values))


def rolling_error_stability(frame: pd.DataFrame) -> float:
    """Mean per-horizon standard deviation of absolute rolling errors."""
    if frame.empty:
        return float("nan")

    horizon_stds = [
        float(np.std(subset["abs_error"].to_numpy(dtype=float)))
        for _, subset in frame.groupby("horizon")
    ]
    return float(np.mean(horizon_stds))


def rolling_blocked_metric_summary(
    frame: pd.DataFrame,
    metric_name: str,
    num_blocks: int = 3,
) -> dict[str, Any]:
    """Summarize rolling forecasts across contiguous target-time blocks."""
    if frame.empty:
        return {
            "details": pd.DataFrame(columns=["horizon", "block", "count", "mae", "rmse", "smape"]),
            "mean": float("nan"),
            "std": float("nan"),
            "num_blocks": 0,
        }

    records: list[dict[str, Any]] = []
    for horizon, subset in frame.groupby("horizon"):
        ordered = subset.sort_values("target_t").reset_index(drop=True)
        block_count = max(1, min(num_blocks, len(ordered)))
        for block_index, indices in enumerate(np.array_split(np.arange(len(ordered)), block_count), start=1):
            block = ordered.iloc[indices]
            metrics = point_metrics(
                block["actual"].to_numpy(dtype=float),
                block["prediction"].to_numpy(dtype=float),
            )
            records.append(
                {
                    "horizon": int(horizon),
                    "block": block_index,
                    "count": int(len(block)),
                    **metrics,
                }
            )

    details = pd.DataFrame.from_records(records).sort_values(["horizon", "block"]).reset_index(drop=True)
    values = details[metric_name].to_numpy(dtype=float)
    return {
        "details": details,
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
        "num_blocks": int(len(details)),
    }
