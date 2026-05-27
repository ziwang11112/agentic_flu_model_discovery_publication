from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.baselines.forecasting import ARIMAAutoSmallBaseline, LaggedRidgeBaseline, LastObservedBaseline, RollingMeanBaseline
from src.data.split import ChronologicalSplit
from src.evaluation.baseline_pipeline import run_equal_weight_point_ensemble_family, run_forecast_baseline_family
from src.utils.io import write_json


def test_last_observed_predicts_last_training_value() -> None:
    baseline = LastObservedBaseline().fit(np.asarray([1.0, 2.0, 5.0]))

    assert baseline.predict(3).tolist() == [5.0, 5.0, 5.0]


def test_rolling_mean_4wk_predicts_mean_of_last_four_values() -> None:
    baseline = RollingMeanBaseline(window=4, model_name="rolling_mean_4wk").fit(np.asarray([1.0, 2.0, 3.0, 4.0, 9.0]))

    assert baseline.predict(2).tolist() == [4.5, 4.5]


def test_lagged_ridge_produces_finite_forecasts() -> None:
    y = np.linspace(1.0, 12.0, 12)
    baseline = LaggedRidgeBaseline().fit(y)

    predictions = baseline.predict(4)

    assert len(predictions) == 4
    assert np.all(np.isfinite(predictions))


def test_arima_auto_small_fallback_for_too_short_series() -> None:
    baseline = ARIMAAutoSmallBaseline().fit(np.asarray([1.0, 1.0, 1.0]), np.asarray([1.0]))

    assert baseline.fallback_used is True
    assert baseline.fallback_model_name == "last_observed"
    assert baseline.predict(2).tolist() == [1.0, 1.0]


def test_run_forecast_baseline_family_writes_expected_artifacts(tmp_path: Path) -> None:
    y = np.asarray([1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 11.0, 13.0, 17.0, 19.0])
    split = ChronologicalSplit(train_end=6, val_end=8, n_obs=len(y))
    artifact_dir = tmp_path / "Overall" / "rolling_mean_4wk"

    result = run_forecast_baseline_family(
        baseline_factory=lambda: RollingMeanBaseline(window=4, model_name="rolling_mean_4wk"),
        series_name="Overall",
        y=y,
        split=split,
        horizons=[1, 2],
        artifact_dir=artifact_dir,
        seed=42,
    )

    assert result["comparison_row"]["model_name"] == "rolling_mean_4wk"
    assert (artifact_dir / "metrics.json").exists()
    assert (artifact_dir / "forecast_trace.csv").exists()
    assert (artifact_dir / "rolling_origin_forecasts.csv").exists()

    forecast = pd.read_csv(artifact_dir / "forecast_trace.csv")
    rolling = pd.read_csv(artifact_dir / "rolling_origin_forecasts.csv")
    assert {"t", "actual", "full_fit_prediction", "test_forecast_prediction", "segment"}.issubset(forecast.columns)
    assert {"origin_end", "target_t", "horizon", "actual", "prediction", "error", "abs_error"}.issubset(rolling.columns)


def test_equal_weight_ensemble_excludes_failed_members_and_aligns_rolling_forecasts(tmp_path: Path) -> None:
    y = np.asarray([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0])
    split = ChronologicalSplit(train_end=3, val_end=5, n_obs=len(y))
    series_root = tmp_path / "Overall"
    _write_member_artifacts(series_root, "deterministic_seir", y, offset=1.0, target_rows=[5, 6], failure=False)
    _write_member_artifacts(series_root, "probabilistic_seir", y, offset=3.0, target_rows=[5], failure=False)
    _write_member_artifacts(series_root, "fractional_seir", y, offset=100.0, target_rows=[5], failure=True)

    result = run_equal_weight_point_ensemble_family(
        series_name="Overall",
        y=y,
        split=split,
        horizons=[1],
        artifact_dir=series_root / "equal_weight_point_ensemble",
        seed=42,
    )

    metadata = result["summary"]["baseline_metadata"]
    rolling = pd.read_csv(series_root / "equal_weight_point_ensemble" / "rolling_origin_forecasts.csv")

    assert metadata["valid_members"] == ["deterministic_seir", "probabilistic_seir"]
    assert any(item["model_name"] == "fractional_seir" and item["reason"] == "numerical_failure_flag" for item in metadata["excluded_members"])
    assert rolling["target_t"].tolist() == [5]
    assert rolling["prediction"].tolist() == [17.0]


def test_equal_weight_ensemble_respects_configured_members(tmp_path: Path) -> None:
    y = np.asarray([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0])
    split = ChronologicalSplit(train_end=3, val_end=5, n_obs=len(y))
    series_root = tmp_path / "Overall"
    _write_member_artifacts(series_root, "deterministic_seir", y, offset=1.0, target_rows=[5], failure=False)
    _write_member_artifacts(series_root, "random_structure_discovery", y, offset=100.0, target_rows=[5], failure=False)

    result = run_equal_weight_point_ensemble_family(
        series_name="Overall",
        y=y,
        split=split,
        horizons=[1],
        artifact_dir=series_root / "equal_weight_point_ensemble",
        seed=42,
        ensemble_members=["deterministic_seir"],
    )

    metadata = result["summary"]["baseline_metadata"]
    assert metadata["valid_members"] == ["deterministic_seir"]
    assert any(
        item["model_name"] == "random_structure_discovery" and item["reason"] == "not_in_ensemble_members"
        for item in metadata["excluded_members"]
    )


def _write_member_artifacts(
    series_root: Path,
    model_name: str,
    y: np.ndarray,
    offset: float,
    target_rows: list[int],
    failure: bool,
) -> None:
    model_dir = series_root / model_name
    write_json(
        {
            "series_name": "Overall",
            "model_name": model_name,
            "test_metrics": {"mae": 1.0, "rmse": 1.0, "smape": 0.1},
            "rolling_origin_summary": {"mean_mae": 1.0, "mean_rmse": 1.0},
            "complexity": {"num_free_params": 1, "num_compartments": 1},
            "numerical_diagnostics": {"numerical_failure_flag": failure},
        },
        model_dir / "metrics.json",
    )
    pd.DataFrame(
        {
            "t": np.arange(len(y)),
            "actual": y,
            "full_fit_prediction": y + offset,
            "test_forecast_prediction": y + offset,
            "segment": ["train", "train", "train", "validation", "validation", "test", "test"],
        }
    ).to_csv(model_dir / "forecast_trace.csv", index=False)
    pd.DataFrame(
        [
            {
                "origin_end": target_t,
                "target_t": target_t,
                "horizon": 1,
                "actual": float(y[target_t]),
                "prediction": float(y[target_t] + offset),
                "error": offset,
                "abs_error": abs(offset),
            }
            for target_t in target_rows
        ]
    ).to_csv(model_dir / "rolling_origin_forecasts.csv", index=False)
