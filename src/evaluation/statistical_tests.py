from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def paired_rolling_error_comparison(
    artifact_root: Path,
    reference_model: str = "constrained_structure_discovery",
    metric_col: str = "abs_error",
    n_bootstrap: int = 2000,
    seed: int = 42,
) -> pd.DataFrame:
    """Compare rolling-origin errors by aligning models on series, horizon, and target time."""
    model_frames, skipped = _load_rolling_model_frames(artifact_root, metric_col)
    records: list[dict[str, Any]] = []
    rng = np.random.default_rng(seed)

    if not model_frames:
        result = pd.DataFrame(columns=_comparison_columns())
        result.attrs["skipped_models"] = skipped
        return result

    all_errors = pd.concat(model_frames, ignore_index=True)
    for series_name, series_frame in all_errors.groupby("series_name", sort=True):
        reference = series_frame.loc[series_frame["model_name"] == reference_model].copy()
        if reference.empty:
            skipped.append({"series_name": series_name, "model_name": reference_model, "reason": "missing_reference"})
            continue
        reference = reference.loc[:, ["series_name", "horizon", "target_t", metric_col]].rename(
            columns={metric_col: "reference_error"}
        )
        for challenger_model, challenger_frame in series_frame.groupby("model_name", sort=True):
            if challenger_model == reference_model:
                continue
            challenger = challenger_frame.loc[:, ["series_name", "horizon", "target_t", metric_col]].rename(
                columns={metric_col: "challenger_error"}
            )
            aligned = reference.merge(challenger, on=["series_name", "horizon", "target_t"], how="inner")
            if aligned.empty:
                skipped.append(
                    {
                        "series_name": series_name,
                        "model_name": challenger_model,
                        "reason": "no_aligned_rolling_rows",
                    }
                )
                continue

            reference_errors = aligned["reference_error"].to_numpy(dtype=float)
            challenger_errors = aligned["challenger_error"].to_numpy(dtype=float)
            diff = challenger_errors - reference_errors
            ci_low, ci_high = _bootstrap_mean_ci(diff, rng, n_bootstrap)
            records.append(
                {
                    "series_name": series_name,
                    "reference_model": reference_model,
                    "challenger_model": challenger_model,
                    "n_aligned": int(len(aligned)),
                    "mean_abs_error_reference": float(np.mean(reference_errors)),
                    "mean_abs_error_challenger": float(np.mean(challenger_errors)),
                    "mean_diff_challenger_minus_reference": float(np.mean(diff)),
                    "ci95_low": ci_low,
                    "ci95_high": ci_high,
                    "reference_win_rate": float(np.mean(reference_errors < challenger_errors)),
                }
            )

    result = pd.DataFrame.from_records(records, columns=_comparison_columns())
    result.attrs["skipped_models"] = skipped
    return result


def _load_rolling_model_frames(
    artifact_root: Path,
    metric_col: str,
) -> tuple[list[pd.DataFrame], list[dict[str, Any]]]:
    frames: list[pd.DataFrame] = []
    skipped: list[dict[str, Any]] = []
    for metrics_path in sorted(Path(artifact_root).glob("**/metrics.json")):
        try:
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            skipped.append({"path": str(metrics_path), "reason": "invalid_metrics_json"})
            continue

        series_name = str(metrics.get("series_name", metrics_path.parent.parent.name))
        model_name = str(metrics.get("model_name", metrics_path.parent.name))
        rolling_path = metrics_path.parent / "rolling_origin_forecasts.csv"
        if not rolling_path.exists():
            skipped.append({"series_name": series_name, "model_name": model_name, "reason": "missing_rolling_origin_forecasts"})
            continue

        rolling = pd.read_csv(rolling_path)
        required = {"horizon", "target_t", metric_col}
        if not required.issubset(rolling.columns):
            skipped.append(
                {
                    "series_name": series_name,
                    "model_name": model_name,
                    "reason": f"missing_required_columns:{sorted(required - set(rolling.columns))}",
                }
            )
            continue

        frame = rolling.loc[:, ["horizon", "target_t", metric_col]].copy()
        frame.insert(0, "model_name", model_name)
        frame.insert(0, "series_name", series_name)
        frames.append(frame)

    return frames, skipped


def _bootstrap_mean_ci(diff: np.ndarray, rng: np.random.Generator, n_bootstrap: int) -> tuple[float, float]:
    if len(diff) == 0:
        return float("nan"), float("nan")
    if n_bootstrap <= 0:
        mean_diff = float(np.mean(diff))
        return mean_diff, mean_diff
    draws = np.empty(int(n_bootstrap), dtype=float)
    for idx in range(int(n_bootstrap)):
        sample = rng.choice(diff, size=len(diff), replace=True)
        draws[idx] = float(np.mean(sample))
    return float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def _comparison_columns() -> list[str]:
    return [
        "series_name",
        "reference_model",
        "challenger_model",
        "n_aligned",
        "mean_abs_error_reference",
        "mean_abs_error_challenger",
        "mean_diff_challenger_minus_reference",
        "ci95_low",
        "ci95_high",
        "reference_win_rate",
    ]
