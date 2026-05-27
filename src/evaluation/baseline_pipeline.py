from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from src.baselines.forecasting import ForecastBaseline, LastObservedBaseline
from src.data.split import ChronologicalSplit
from src.evaluation.metrics import point_metrics, summarise_probabilistic_metrics
from src.evaluation.pipeline import _forecast_frame, _prediction_diagnostics
from src.evaluation.rolling import mean_rolling_metric, rolling_metrics_by_horizon
from src.plotting.plots import plot_full_series_fit, plot_residuals, plot_rolling_forecasts
from src.utils.io import ensure_dir, write_json

logger = logging.getLogger(__name__)


def run_forecast_baseline_family(
    baseline_factory: Callable[[], ForecastBaseline],
    series_name: str,
    y: np.ndarray,
    split: ChronologicalSplit,
    horizons: list[int],
    artifact_dir: Path,
    seed: int,
) -> dict[str, Any]:
    """Fit, evaluate, and persist one non-epidemic forecast baseline."""
    ensure_dir(artifact_dir)
    model_start = time.perf_counter()
    values = np.asarray(y, dtype=float)
    baseline_name = baseline_factory().model_name
    logger.info("Forecast baseline start model=%s series=%s", baseline_name, series_name)

    train_y = values[split.train_slice]
    val_y = values[split.val_slice]
    test_y = values[split.test_slice]

    if baseline_factory().uses_validation_selection:
        train_model = baseline_factory().fit(train_y)
        trainval_model = baseline_factory().fit(train_y, val_y)
        validation_predictions = getattr(trainval_model, "validation_predictions_", None)
        if validation_predictions is None:
            validation_predictions = train_model.predict(len(val_y))
    else:
        train_model = baseline_factory().fit(train_y)
        trainval_model = baseline_factory().fit(train_y, val_y)
        validation_predictions = train_model.predict(len(val_y))

    train_predictions = train_model.fitted_values(train_y)
    test_predictions = trainval_model.predict(len(test_y))

    full_model = baseline_factory().fit(values)
    full_predictions = full_model.fitted_values(values)
    residuals = values - full_predictions

    test_trace_predictions = np.full(len(values), np.nan, dtype=float)
    test_trace_predictions[split.train_slice] = train_predictions
    test_trace_predictions[split.val_slice] = validation_predictions
    test_trace_predictions[split.test_slice] = test_predictions
    forecast_frame = _forecast_frame(values, full_predictions, split, test_trace_predictions)
    forecast_frame.to_csv(artifact_dir / "forecast_trace.csv", index=False)

    rolling_frame = rolling_origin_forecasts_for_baseline(
        baseline_factory=baseline_factory,
        y=values,
        horizons=horizons,
        initial_train_size=split.train_end,
    )
    rolling_frame.to_csv(artifact_dir / "rolling_origin_forecasts.csv", index=False)

    _write_optional_plots(
        y=values,
        split=split,
        full_predictions=full_predictions,
        residuals=residuals,
        rolling_frame=rolling_frame,
        model_name=baseline_name,
        series_name=series_name,
        artifact_dir=artifact_dir,
    )

    summary = {
        "model_name": baseline_name,
        "model_family": "forecast_baseline",
        "series_name": series_name,
        "complexity": {
            "num_free_params": int(getattr(trainval_model, "num_free_params", 0)),
            "num_compartments": 0,
        },
        "train_metrics": point_metrics(train_y, train_predictions),
        "validation_metrics": point_metrics(val_y, np.asarray(validation_predictions, dtype=float)),
        "test_metrics": point_metrics(test_y, test_predictions),
        "probabilistic_metrics": summarise_probabilistic_metrics(test_y, None, None),
        "rolling_origin_metrics": rolling_metrics_by_horizon(rolling_frame),
        "rolling_origin_summary": {
            "mean_mae": mean_rolling_metric(rolling_frame, "mae"),
            "mean_rmse": mean_rolling_metric(rolling_frame, "rmse"),
        },
        "fit_objectives": {},
        "fit_status": _baseline_fit_status(trainval_model),
        "numerical_diagnostics": _prediction_diagnostics(
            y=values,
            test_predictions=test_predictions,
            full_predictions=full_predictions,
            train_success=True,
            train_plus_validation_success=True,
        ),
        "baseline_metadata": _baseline_metadata(trainval_model),
    }
    write_json(summary, artifact_dir / "metrics.json")
    logger.info(
        "Forecast baseline done model=%s series=%s test_mae=%.6f elapsed=%.1fs",
        baseline_name,
        series_name,
        summary["test_metrics"]["mae"],
        time.perf_counter() - model_start,
    )
    return {
        "summary": summary,
        "comparison_row": {
            "model_name": baseline_name,
            "test_mae": summary["test_metrics"]["mae"],
            "test_rmse": summary["test_metrics"]["rmse"],
            "test_smape": summary["test_metrics"]["smape"],
            "num_free_params": summary["complexity"]["num_free_params"],
            "num_compartments": 0,
        },
    }


def rolling_origin_forecasts_for_baseline(
    baseline_factory: Callable[[], ForecastBaseline],
    y: np.ndarray,
    horizons: list[int],
    initial_train_size: int,
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    values = np.asarray(y, dtype=float)
    for horizon in horizons:
        for origin_end in range(initial_train_size, len(values) - horizon + 1):
            model = baseline_factory().fit(values[:origin_end])
            prediction = float(model.predict(horizon)[-1])
            target_index = origin_end + horizon - 1
            actual = float(values[target_index])
            records.append(
                {
                    "origin_end": origin_end,
                    "target_t": target_index,
                    "horizon": horizon,
                    "actual": actual,
                    "prediction": prediction,
                    "error": prediction - actual,
                    "abs_error": abs(prediction - actual),
                }
            )

    columns = ["origin_end", "target_t", "horizon", "actual", "prediction", "error", "abs_error"]
    if not records:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame.from_records(records).sort_values(["horizon", "target_t"]).reset_index(drop=True)


def run_equal_weight_point_ensemble_family(
    series_name: str,
    y: np.ndarray,
    split: ChronologicalSplit,
    horizons: list[int],
    artifact_dir: Path,
    seed: int,
    ensemble_members: list[str] | None = None,
) -> dict[str, Any]:
    """Average point forecasts from existing, numerically healthy member artifacts."""
    del seed
    ensure_dir(artifact_dir)
    values = np.asarray(y, dtype=float)
    member_root = artifact_dir.parent
    valid_members, excluded_members = _collect_valid_ensemble_members(member_root, artifact_dir.name, ensemble_members)

    if not valid_members:
        result = run_forecast_baseline_family(
            baseline_factory=lambda: LastObservedBaseline(model_name="equal_weight_point_ensemble"),
            series_name=series_name,
            y=values,
            split=split,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=0,
        )
        summary = result["summary"]
        summary["model_family"] = "point_ensemble"
        summary["baseline_metadata"].update(
            {
                "fallback_used": True,
                "fallback_model": "last_observed",
                "valid_members": [],
                "excluded_members": excluded_members,
                "ensemble_members_configured": ensemble_members,
            }
        )
        write_json(summary, artifact_dir / "metrics.json")
        return result

    forecast_frame = _ensemble_forecast_frame(valid_members, values, split)
    rolling_frame = _ensemble_rolling_frame(valid_members)
    forecast_frame.to_csv(artifact_dir / "forecast_trace.csv", index=False)
    rolling_frame.to_csv(artifact_dir / "rolling_origin_forecasts.csv", index=False)

    full_predictions = forecast_frame["full_fit_prediction"].to_numpy(dtype=float)
    test_predictions = forecast_frame.loc[forecast_frame["segment"] == "test", "test_forecast_prediction"].to_numpy(dtype=float)
    residuals = values - full_predictions
    _write_optional_plots(
        y=values,
        split=split,
        full_predictions=full_predictions,
        residuals=residuals,
        rolling_frame=rolling_frame,
        model_name="equal_weight_point_ensemble",
        series_name=series_name,
        artifact_dir=artifact_dir,
    )

    fallback_used = len(valid_members) < 2
    summary = {
        "model_name": "equal_weight_point_ensemble",
        "model_family": "point_ensemble",
        "series_name": series_name,
        "complexity": {"num_free_params": 0, "num_compartments": 0},
        "train_metrics": point_metrics(
            values[split.train_slice],
            forecast_frame.loc[forecast_frame["segment"] == "train", "full_fit_prediction"].to_numpy(dtype=float),
        ),
        "validation_metrics": point_metrics(
            values[split.val_slice],
            forecast_frame.loc[forecast_frame["segment"] == "validation", "full_fit_prediction"].to_numpy(dtype=float),
        ),
        "test_metrics": point_metrics(values[split.test_slice], test_predictions),
        "probabilistic_metrics": summarise_probabilistic_metrics(values[split.test_slice], None, None),
        "rolling_origin_metrics": rolling_metrics_by_horizon(rolling_frame),
        "rolling_origin_summary": {
            "mean_mae": mean_rolling_metric(rolling_frame, "mae"),
            "mean_rmse": mean_rolling_metric(rolling_frame, "rmse"),
        },
        "fit_objectives": {},
        "fit_status": {
            "train_success": True,
            "train_message": "ensemble member artifacts loaded",
            "train_plus_validation_success": True,
            "train_plus_validation_message": "ensemble member artifacts loaded",
            "full_success": True,
            "full_message": "ensemble member artifacts loaded",
        },
        "numerical_diagnostics": _prediction_diagnostics(
            y=values,
            test_predictions=test_predictions,
            full_predictions=full_predictions,
            train_success=True,
            train_plus_validation_success=True,
        ),
        "baseline_metadata": {
            "valid_members": [member["model_name"] for member in valid_members],
            "excluded_members": excluded_members,
            "fallback_used": fallback_used,
            "fallback_model": valid_members[0]["model_name"] if fallback_used else None,
            "ensemble_members_configured": ensemble_members,
        },
    }
    write_json(summary, artifact_dir / "metrics.json")
    return {
        "summary": summary,
        "comparison_row": {
            "model_name": "equal_weight_point_ensemble",
            "test_mae": summary["test_metrics"]["mae"],
            "test_rmse": summary["test_metrics"]["rmse"],
            "test_smape": summary["test_metrics"]["smape"],
            "num_free_params": 0,
            "num_compartments": 0,
        },
    }


def _baseline_fit_status(model: ForecastBaseline) -> dict[str, Any]:
    fallback_reason = model.metadata.get("fallback_reason") if hasattr(model, "metadata") else None
    message = "ok" if fallback_reason is None else f"fallback: {fallback_reason}"
    return {
        "train_success": True,
        "train_message": message,
        "train_plus_validation_success": True,
        "train_plus_validation_message": message,
        "full_success": True,
        "full_message": message,
    }


def _baseline_metadata(model: ForecastBaseline) -> dict[str, Any]:
    metadata = dict(getattr(model, "metadata", {}))
    metadata.setdefault("fallback_used", bool(getattr(model, "fallback_used", False)))
    metadata.setdefault("fallback_model", getattr(model, "fallback_model_name", None))
    return metadata


def _write_optional_plots(
    *,
    y: np.ndarray,
    split: ChronologicalSplit,
    full_predictions: np.ndarray,
    residuals: np.ndarray,
    rolling_frame: pd.DataFrame,
    model_name: str,
    series_name: str,
    artifact_dir: Path,
) -> None:
    try:
        plot_full_series_fit(
            np.arange(len(y)),
            y,
            full_predictions,
            split,
            title=f"{series_name}: {model_name} full-series fit",
            path=artifact_dir / "full_series_fit.png",
        )
        plot_residuals(
            np.arange(len(y)),
            residuals,
            title=f"{series_name}: {model_name} residuals",
            path=artifact_dir / "residuals.png",
        )
        if not rolling_frame.empty:
            plot_rolling_forecasts(
                rolling_frame,
                title=f"{series_name}: {model_name}",
                path=artifact_dir / "rolling_origin.png",
            )
    except Exception as exc:
        logger.warning("Plotting skipped for model=%s artifact_dir=%s error=%s", model_name, artifact_dir, exc)


def _collect_valid_ensemble_members(
    member_root: Path,
    ensemble_dir_name: str,
    ensemble_members: list[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    allowed_members = None if ensemble_members is None else set(ensemble_members)
    valid_members: list[dict[str, Any]] = []
    excluded_members: list[dict[str, Any]] = []
    for metrics_path in sorted(member_root.glob("*/metrics.json")):
        model_name = metrics_path.parent.name
        if model_name == ensemble_dir_name:
            excluded_members.append({"model_name": model_name, "reason": "self"})
            continue
        if allowed_members is not None and model_name not in allowed_members:
            excluded_members.append({"model_name": model_name, "reason": "not_in_ensemble_members"})
            continue
        forecast_path = metrics_path.parent / "forecast_trace.csv"
        rolling_path = metrics_path.parent / "rolling_origin_forecasts.csv"
        if not forecast_path.exists() or not rolling_path.exists():
            excluded_members.append({"model_name": model_name, "reason": "missing_member_artifacts"})
            continue
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        if bool(metrics.get("numerical_diagnostics", {}).get("numerical_failure_flag", False)):
            excluded_members.append({"model_name": model_name, "reason": "numerical_failure_flag"})
            continue
        valid_members.append(
            {
                "model_name": model_name,
                "forecast_path": forecast_path,
                "rolling_path": rolling_path,
            }
        )
    return valid_members, excluded_members


def _ensemble_forecast_frame(
    members: list[dict[str, Any]],
    y: np.ndarray,
    split: ChronologicalSplit,
) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "t": np.arange(len(y)),
            "actual": y,
            "segment": np.where(
                np.arange(len(y)) < split.train_end,
                "train",
                np.where(np.arange(len(y)) < split.val_end, "validation", "test"),
            ),
        }
    )
    full_columns: list[str] = []
    test_columns: list[str] = []
    for index, member in enumerate(members):
        member_frame = pd.read_csv(member["forecast_path"]).set_index("t").reindex(frame["t"])
        full_col = f"full_fit_prediction_{index}"
        test_col = f"test_forecast_prediction_{index}"
        frame[full_col] = member_frame["full_fit_prediction"].to_numpy(dtype=float)
        frame[test_col] = member_frame["test_forecast_prediction"].to_numpy(dtype=float)
        full_columns.append(full_col)
        test_columns.append(test_col)

    frame["full_fit_prediction"] = frame[full_columns].mean(axis=1, skipna=True)
    frame["test_forecast_prediction"] = frame[test_columns].mean(axis=1, skipna=True)
    return frame.loc[:, ["t", "actual", "full_fit_prediction", "test_forecast_prediction", "segment"]]


def _ensemble_rolling_frame(members: list[dict[str, Any]]) -> pd.DataFrame:
    joined: pd.DataFrame | None = None
    prediction_columns: list[str] = []
    for index, member in enumerate(members):
        member_frame = pd.read_csv(member["rolling_path"]).loc[:, ["horizon", "target_t", "actual", "prediction"]].copy()
        prediction_col = f"prediction_{index}"
        prediction_columns.append(prediction_col)
        if joined is None:
            joined = member_frame.rename(columns={"prediction": prediction_col})
        else:
            joined = joined.merge(
                member_frame.loc[:, ["horizon", "target_t", "prediction"]].rename(columns={"prediction": prediction_col}),
                on=["horizon", "target_t"],
                how="inner",
            )

    columns = ["origin_end", "target_t", "horizon", "actual", "prediction", "error", "abs_error"]
    if joined is None or joined.empty:
        return pd.DataFrame(columns=columns)

    joined["prediction"] = joined[prediction_columns].mean(axis=1)
    joined["error"] = joined["prediction"] - joined["actual"]
    joined["abs_error"] = joined["error"].abs()
    joined["origin_end"] = joined["target_t"] - joined["horizon"] + 1
    return joined.loc[:, columns].sort_values(["horizon", "target_t"]).reset_index(drop=True)
