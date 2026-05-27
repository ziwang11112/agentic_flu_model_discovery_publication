from __future__ import annotations

import logging
from pathlib import Path
import time
from typing import Any, Callable

import numpy as np
import pandas as pd
from scipy.stats import t as student_t

from src.data.split import ChronologicalSplit
from src.discovery.model import DiscoveryCompartmentModel
from src.discovery.search import (
    SearchConfig,
    discovery_regularization_config,
    run_exhaustive_structure_search,
    run_no_observation_search,
    run_no_stability_structure_search,
    run_random_structure_search,
    run_structure_search,
    run_validation_only_structure_selection,
)
from src.evaluation.metrics import interval_level_summary, point_metrics, summarise_probabilistic_metrics
from src.evaluation.metrics import learn_conformal_interval_scales, learn_interval_scales, scale_interval_map
from src.evaluation.rolling import mean_rolling_metric, rolling_metrics_by_horizon, rolling_origin_forecasts
from src.models.base import BaseEpidemicModel, FitConfig
from src.models.seir_delayed_observation import DelayedObservationSEIRModel
from src.plotting.plots import (
    plot_full_series_fit,
    plot_leaderboard,
    plot_probabilistic_calibration,
    plot_residuals,
    plot_rolling_forecasts,
    plot_structure_diagram,
)
from src.utils.io import ensure_dir, write_json

logger = logging.getLogger(__name__)


def _forecast_frame(
    y: np.ndarray,
    full_predictions: np.ndarray,
    split: ChronologicalSplit,
    test_predictions: np.ndarray,
    interval_map: dict[str, tuple[np.ndarray, np.ndarray]] | None = None,
    raw_interval_map: dict[str, tuple[np.ndarray, np.ndarray]] | None = None,
) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "t": np.arange(len(y)),
            "actual": y,
            "full_fit_prediction": full_predictions,
            "test_forecast_prediction": test_predictions,
            "segment": np.where(
                np.arange(len(y)) < split.train_end,
                "train",
                np.where(np.arange(len(y)) < split.val_end, "validation", "test"),
            ),
        }
    )

    if interval_map is not None:
        for level, (lower, upper) in interval_map.items():
            frame[f"lower_{level}"] = lower
            frame[f"upper_{level}"] = upper
    if raw_interval_map is not None:
        for level, (lower, upper) in raw_interval_map.items():
            frame[f"raw_lower_{level}"] = lower
            frame[f"raw_upper_{level}"] = upper
    return frame


def _max_abs_finite(values: np.ndarray) -> float:
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        return 0.0
    if np.any(np.isinf(array)):
        return float("inf")
    finite_abs = np.abs(array[np.isfinite(array)])
    if finite_abs.size == 0:
        return float("nan")
    return float(np.max(finite_abs))


def _observed_scale(y: np.ndarray) -> float:
    array = np.asarray(y, dtype=float)
    finite_abs = np.abs(array[np.isfinite(array)])
    if finite_abs.size == 0:
        return 1.0
    return max(float(np.max(finite_abs)), 1.0)


def _prediction_diagnostics(
    y: np.ndarray,
    test_predictions: np.ndarray,
    full_predictions: np.ndarray,
    train_success: bool,
    train_plus_validation_success: bool,
) -> dict[str, Any]:
    test_array = np.asarray(test_predictions, dtype=float)
    full_array = np.asarray(full_predictions, dtype=float)
    max_abs_test_prediction = _max_abs_finite(test_array)
    max_abs_full_prediction = _max_abs_finite(full_array)
    has_nonfinite_prediction = not bool(np.all(np.isfinite(test_array)) and np.all(np.isfinite(full_array)))
    has_negative_prediction = bool(np.any(test_array < 0.0) or np.any(full_array < 0.0))
    test_prediction_exceeds_100x_observed_max = bool(max_abs_test_prediction > 100.0 * _observed_scale(y))
    numerical_failure_flag = bool(
        has_nonfinite_prediction
        or test_prediction_exceeds_100x_observed_max
        or not train_success
        or not train_plus_validation_success
    )
    return {
        "max_abs_test_prediction": max_abs_test_prediction,
        "max_abs_full_prediction": max_abs_full_prediction,
        "has_nonfinite_prediction": has_nonfinite_prediction,
        "has_negative_prediction": has_negative_prediction,
        "test_prediction_exceeds_100x_observed_max": test_prediction_exceeds_100x_observed_max,
        "numerical_failure_flag": numerical_failure_flag,
    }


def run_model_family(
    model_factory: Callable[[], BaseEpidemicModel],
    series_name: str,
    y: np.ndarray,
    split: ChronologicalSplit,
    horizons: list[int],
    artifact_dir: Path,
    seed: int,
) -> dict[str, Any]:
    """Fit, evaluate, and persist one model family."""
    ensure_dir(artifact_dir)
    rng = np.random.default_rng(seed)
    model_start = time.perf_counter()
    model_name = model_factory().model_name
    logger.info("Model family start model=%s series=%s", model_name, series_name)

    train_model = model_factory()
    train_fit = train_model.fit(y[split.train_slice], rng)
    validation_rollout = train_model.simulate(train_fit.raw_params, split.val_end)
    train_predictions = validation_rollout.predictions[split.train_slice]
    validation_predictions = validation_rollout.predictions[split.val_slice]

    trainval_model = model_factory()
    trainval_fit = trainval_model.fit(y[: split.val_end], rng, warm_start=train_fit.raw_params)
    test_rollout = trainval_model.simulate(trainval_fit.raw_params, len(y))
    test_predictions = test_rollout.predictions[split.test_slice]

    full_model = model_factory()
    full_fit = full_model.fit(
        y,
        rng,
        warm_start=trainval_fit.raw_params,
        n_restarts=full_model.fit_config.rolling_n_restarts,
    )
    full_predictions = full_fit.simulation.predictions
    residuals = y - full_predictions

    interval_map_full: dict[str, tuple[np.ndarray, np.ndarray]] | None = None
    raw_interval_map_full: dict[str, tuple[np.ndarray, np.ndarray]] | None = None
    probabilistic_metrics = summarise_probabilistic_metrics(y[split.test_slice], None, None)
    calibration_report: dict[str, Any] | None = None
    validation_forecast_frame: pd.DataFrame | None = None

    if hasattr(trainval_model, "predictive_summary"):
        predictive = trainval_model.predictive_summary(y[: split.val_end], trainval_fit, len(y), rng)  # type: ignore[attr-defined]
        raw_interval_map_full = predictive["intervals"]
        interval_map_full = raw_interval_map_full
        interval_map_test = {
            level: (bounds[0][split.test_slice], bounds[1][split.test_slice])
            for level, bounds in raw_interval_map_full.items()
        }
        test_scale = trainval_fit.params["obs_scale"]
        nll = float(
            -np.sum(
                student_t.logpdf(
                    y[split.test_slice],
                    df=getattr(trainval_model, "df"),
                    loc=test_rollout.predictions[split.test_slice],
                    scale=test_scale,
                )
            )
        )
        raw_probabilistic_metrics = summarise_probabilistic_metrics(y[split.test_slice], nll, interval_map_test)
        calibration_scales = {level: 1.0 for level in interval_map_test}
        calibration_method = "none"
        validation_raw_interval_summary: dict[str, dict[str, float]] = {}
        validation_calibrated_interval_summary: dict[str, dict[str, float]] = {}
        validation_predictive_raw = train_model.predictive_summary(  # type: ignore[attr-defined]
            y[split.train_slice],
            train_fit,
            split.val_end,
            rng,
            n_draws=train_model.fit_config.calibration_draws,
        )
        validation_raw_interval_map = {
            level: (bounds[0][split.val_slice], bounds[1][split.val_slice])
            for level, bounds in validation_predictive_raw["intervals"].items()
        }
        validation_center = validation_predictive_raw["point_forecast"][split.val_slice]
        validation_forecast_frame = pd.DataFrame(
            {
                "t": np.arange(split.train_end, split.val_end),
                "actual": y[split.val_slice],
                "point_prediction": validation_center,
                "segment": "validation",
                "horizon": "static",
            }
        )
        for level, (lower, upper) in validation_raw_interval_map.items():
            validation_forecast_frame[f"raw_lower_{level}"] = lower
            validation_forecast_frame[f"raw_upper_{level}"] = upper

        if trainval_model.fit_config.calibrate_intervals:  # type: ignore[attr-defined]
            calibration_method = str(trainval_model.fit_config.interval_calibration_method).lower()  # type: ignore[attr-defined]
            if calibration_method == "scale":
                calibration_fit = learn_interval_scales(
                    y_true=y[split.val_slice],
                    center=validation_center,
                    interval_map=validation_raw_interval_map,
                    scale_min=train_model.fit_config.calibration_scale_min,
                    scale_max=train_model.fit_config.calibration_scale_max,
                    grid_size=train_model.fit_config.calibration_scale_grid_size,
                )
            elif calibration_method == "conformal":
                calibration_fit = learn_conformal_interval_scales(
                    y_true=y[split.val_slice],
                    center=validation_center,
                    interval_map=validation_raw_interval_map,
                )
            else:
                raise ValueError(f"Unsupported interval calibration method: {calibration_method}")
            calibration_scales = {level: float(scale) for level, scale in calibration_fit["scales"].items()}
            validation_raw_interval_summary = interval_level_summary(y[split.val_slice], validation_raw_interval_map)
            validation_calibrated_interval_summary = calibration_fit["interval_summary"]
            interval_map_full = scale_interval_map(
                raw_interval_map_full,
                predictive["point_forecast"],
                calibration_scales,
            )
            interval_map_test = {
                level: (bounds[0][split.test_slice], bounds[1][split.test_slice])
                for level, bounds in interval_map_full.items()
            }

        probabilistic_metrics = summarise_probabilistic_metrics(y[split.test_slice], nll, interval_map_test)
        probabilistic_metrics["uncertainty_method"] = predictive["method"]
        probabilistic_metrics["uncertainty_draws"] = predictive["draw_count"]
        probabilistic_metrics["interval_calibration_method"] = calibration_method
        probabilistic_metrics["interval_calibration_scales"] = calibration_scales
        probabilistic_metrics["raw_interval_summary"] = raw_probabilistic_metrics["interval_summary"]
        if trainval_model.fit_config.calibrate_intervals:  # type: ignore[attr-defined]
            calibration_report = {
                "series_name": series_name,
                "model_name": train_model.model_name,
                "uncertainty_method": predictive["method"],
                "uncertainty_draws": predictive["draw_count"],
                "interval_calibration_method": calibration_method,
                "interval_calibration_scales": calibration_scales,
                "validation_raw_interval_summary": validation_raw_interval_summary,
                "validation_calibrated_interval_summary": validation_calibrated_interval_summary,
                "test_raw_interval_summary": raw_probabilistic_metrics["interval_summary"],
                "test_calibrated_interval_summary": probabilistic_metrics["interval_summary"],
            }
            write_json(calibration_report, artifact_dir / "calibration_report.json")
            plot_probabilistic_calibration(
                calibration_summary=calibration_report["test_calibrated_interval_summary"],
                raw_summary=calibration_report["test_raw_interval_summary"],
                title=f"{series_name}: {train_model.model_name} calibration",
                path=artifact_dir / "calibration.png",
            )

    logger.info("Model family rolling-origin start model=%s series=%s", train_model.model_name, series_name)
    rolling_frame = rolling_origin_forecasts(
        model_factory=model_factory,
        y=y,
        horizons=horizons,
        seed=seed + 101,
        initial_train_size=split.train_end,
    )
    rolling_frame.to_csv(artifact_dir / "rolling_origin_forecasts.csv", index=False)

    forecast_frame = _forecast_frame(
        y,
        full_predictions,
        split,
        test_rollout.predictions,
        interval_map_full,
        raw_interval_map_full,
    )
    forecast_frame.to_csv(artifact_dir / "forecast_trace.csv", index=False)
    if validation_forecast_frame is not None:
        validation_forecast_frame.to_csv(artifact_dir / "validation_forecast_trace.csv", index=False)

    plot_full_series_fit(
        np.arange(len(y)),
        y,
        full_predictions,
        split,
        title=f"{series_name}: {train_model.model_name} full-series fit",
        path=artifact_dir / "full_series_fit.png",
    )
    plot_residuals(
        np.arange(len(y)),
        residuals,
        title=f"{series_name}: {train_model.model_name} residuals",
        path=artifact_dir / "residuals.png",
    )
    plot_rolling_forecasts(
        rolling_frame,
        title=f"{series_name}: {train_model.model_name}",
        path=artifact_dir / "rolling_origin.png",
    )

    summary = {
        "model_name": train_model.model_name,
        "model_family": "epidemic_model",
        "series_name": series_name,
        "complexity": {
            "num_free_params": train_fit.param_count,
            "num_compartments": len(train_model.compartment_names),
        },
        "train_metrics": point_metrics(y[split.train_slice], train_predictions),
        "validation_metrics": point_metrics(y[split.val_slice], validation_predictions),
        "test_metrics": point_metrics(y[split.test_slice], test_predictions),
        "probabilistic_metrics": probabilistic_metrics,
        "rolling_origin_metrics": rolling_metrics_by_horizon(rolling_frame),
        "rolling_origin_summary": {
            "mean_mae": mean_rolling_metric(rolling_frame, "mae"),
            "mean_rmse": mean_rolling_metric(rolling_frame, "rmse"),
        },
        "fit_objectives": {
            "train": train_fit.objective,
            "train_plus_validation": trainval_fit.objective,
            "full_series": full_fit.objective,
        },
        "fit_status": {
            "train_success": bool(train_fit.success),
            "train_message": train_fit.message,
            "train_plus_validation_success": bool(trainval_fit.success),
            "train_plus_validation_message": trainval_fit.message,
            "full_success": bool(full_fit.success),
            "full_message": full_fit.message,
        },
        "numerical_diagnostics": _prediction_diagnostics(
            y=y,
            test_predictions=test_predictions,
            full_predictions=full_predictions,
            train_success=bool(train_fit.success),
            train_plus_validation_success=bool(trainval_fit.success),
        ),
        "best_full_params": full_fit.params,
    }
    if calibration_report is not None:
        summary["calibration_report"] = calibration_report
    write_json(summary, artifact_dir / "metrics.json")
    logger.info(
        "Model family done model=%s series=%s test_mae=%.6f rolling_mean_mae=%.6f elapsed=%.1fs",
        train_model.model_name,
        series_name,
        summary["test_metrics"]["mae"],
        summary["rolling_origin_summary"]["mean_mae"],
        time.perf_counter() - model_start,
    )
    return {
        "summary": summary,
        "comparison_row": {
            "model_name": train_model.model_name,
            "test_mae": summary["test_metrics"]["mae"],
            "test_rmse": summary["test_metrics"]["rmse"],
            "test_smape": summary["test_metrics"]["smape"],
            "num_free_params": summary["complexity"]["num_free_params"],
            "num_compartments": summary["complexity"]["num_compartments"],
        },
    }


def select_delayed_observation_delay(
    y: np.ndarray,
    split: ChronologicalSplit,
    fit_config: FitConfig,
    seed: int,
) -> tuple[int, pd.DataFrame]:
    """Select the delayed-observation lag using validation MAE only."""
    rng = np.random.default_rng(seed)
    records: list[dict[str, float]] = []

    for delay in DelayedObservationSEIRModel.delay_candidates:
        model = DelayedObservationSEIRModel(fit_config, fixed_delay=delay)
        fit = model.fit(y[split.train_slice], rng)
        rollout = model.simulate(fit.raw_params, split.val_end)
        metrics = point_metrics(y[split.val_slice], rollout.predictions[split.val_slice])
        records.append(
            {
                "delay": delay,
                "validation_mae": metrics["mae"],
                "validation_rmse": metrics["rmse"],
                "validation_smape": metrics["smape"],
            }
        )

    table = pd.DataFrame.from_records(records).sort_values(
        ["validation_mae", "validation_rmse", "delay"]
    ).reset_index(drop=True)
    selected_delay = int(table.iloc[0]["delay"])
    return selected_delay, table


def run_delayed_observation_family(
    series_name: str,
    y: np.ndarray,
    split: ChronologicalSplit,
    fit_config: FitConfig,
    horizons: list[int],
    artifact_dir: Path,
    seed: int,
) -> dict[str, Any]:
    """Select the observation delay by validation MAE, then run the fixed-delay family."""
    ensure_dir(artifact_dir)
    selected_delay, selection_table = select_delayed_observation_delay(y, split, fit_config, seed)
    selection_table.to_csv(artifact_dir / "delay_selection.csv", index=False)
    logger.info(
        "Delayed observation selection series=%s selected_delay=%d table=%s",
        series_name,
        selected_delay,
        artifact_dir / "delay_selection.csv",
    )

    result = run_model_family(
        model_factory=lambda: DelayedObservationSEIRModel(fit_config, fixed_delay=selected_delay),
        series_name=series_name,
        y=y,
        split=split,
        horizons=horizons,
        artifact_dir=artifact_dir,
        seed=seed,
    )
    result["summary"]["selected_delay"] = selected_delay
    write_json(result["summary"], artifact_dir / "metrics.json")
    return result


def run_discovery_family(
    y: np.ndarray,
    series_name: str,
    split: ChronologicalSplit,
    fit_config: FitConfig,
    search_config: SearchConfig,
    horizons: list[int],
    artifact_dir: Path,
    seed: int,
) -> dict[str, Any]:
    """Run the constrained search and then evaluate the best discovered model."""
    ensure_dir(artifact_dir)
    discovery_start = time.perf_counter()
    logger.info("Discovery search start series=%s artifacts=%s", series_name, artifact_dir)
    outcome = run_structure_search(
        series_name=series_name,
        y_train=y[split.train_slice],
        y_val=y[split.val_slice],
        fit_config=fit_config,
        search_config=search_config,
        artifact_dir=artifact_dir,
        seed=seed,
    )
    plot_leaderboard(outcome.leaderboard, artifact_dir / "leaderboard.png")
    plot_structure_diagram(outcome.best_spec, artifact_dir / "best_structure.png")
    logger.info(
        "Discovery search done series=%s best_spec=%s elapsed=%.1fs",
        series_name,
        outcome.best_spec.spec_key,
        time.perf_counter() - discovery_start,
    )
    regularization_config = discovery_regularization_config(search_config)

    def model_factory() -> BaseEpidemicModel:
        return DiscoveryCompartmentModel(outcome.best_spec, fit_config, regularization_config)

    run_result = run_model_family(
        model_factory=model_factory,
        series_name=series_name,
        y=y,
        split=split,
        horizons=horizons,
        artifact_dir=artifact_dir,
        seed=seed + 307,
    )
    summary = run_result["summary"]
    summary["model_name"] = "constrained_structure_discovery"
    summary["model_family"] = "structure_discovery"
    summary["best_spec"] = {
        "structure_name": outcome.best_spec.structure_name,
        "fractional": outcome.best_spec.fractional,
        "observation_map": outcome.best_spec.observation_map,
        "delay_weeks": int(outcome.best_spec.delay_weeks),
    }
    summary["search_best_record"] = outcome.best_record
    write_json(summary, artifact_dir / "metrics.json")

    run_result["summary"] = summary
    run_result["comparison_row"]["model_name"] = "constrained_structure_discovery"
    return run_result


def _run_search_outcome_family(
    *,
    model_name: str,
    outcome,
    y: np.ndarray,
    series_name: str,
    split: ChronologicalSplit,
    fit_config: FitConfig,
    search_config: SearchConfig,
    horizons: list[int],
    artifact_dir: Path,
    seed: int,
) -> dict[str, Any]:
    plot_leaderboard(outcome.leaderboard, artifact_dir / "leaderboard.png")
    plot_structure_diagram(outcome.best_spec, artifact_dir / "best_structure.png")
    regularization_config = discovery_regularization_config(search_config)

    def model_factory() -> BaseEpidemicModel:
        return DiscoveryCompartmentModel(outcome.best_spec, fit_config, regularization_config)

    run_result = run_model_family(
        model_factory=model_factory,
        series_name=series_name,
        y=y,
        split=split,
        horizons=horizons,
        artifact_dir=artifact_dir,
        seed=seed,
    )
    summary = run_result["summary"]
    summary["model_name"] = model_name
    summary["model_family"] = "structure_discovery_ablation"
    summary["best_spec"] = {
        "structure_name": outcome.best_spec.structure_name,
        "fractional": outcome.best_spec.fractional,
        "observation_map": outcome.best_spec.observation_map,
        "delay_weeks": int(outcome.best_spec.delay_weeks),
    }
    summary["search_best_record"] = outcome.best_record
    write_json(summary, artifact_dir / "metrics.json")

    run_result["summary"] = summary
    run_result["comparison_row"]["model_name"] = model_name
    return run_result


def run_random_discovery_family(
    y: np.ndarray,
    series_name: str,
    split: ChronologicalSplit,
    fit_config: FitConfig,
    search_config: SearchConfig,
    horizons: list[int],
    artifact_dir: Path,
    seed: int,
) -> dict[str, Any]:
    ensure_dir(artifact_dir)
    outcome = run_random_structure_search(
        series_name=series_name,
        y_train=y[split.train_slice],
        y_val=y[split.val_slice],
        fit_config=fit_config,
        search_config=search_config,
        artifact_dir=artifact_dir,
        seed=seed,
    )
    return _run_search_outcome_family(
        model_name="random_structure_discovery",
        outcome=outcome,
        y=y,
        series_name=series_name,
        split=split,
        fit_config=fit_config,
        search_config=search_config,
        horizons=horizons,
        artifact_dir=artifact_dir,
        seed=seed + 307,
    )


def run_exhaustive_discovery_family(
    y: np.ndarray,
    series_name: str,
    split: ChronologicalSplit,
    fit_config: FitConfig,
    search_config: SearchConfig,
    horizons: list[int],
    artifact_dir: Path,
    seed: int,
) -> dict[str, Any]:
    ensure_dir(artifact_dir)
    outcome = run_exhaustive_structure_search(
        series_name=series_name,
        y_train=y[split.train_slice],
        y_val=y[split.val_slice],
        fit_config=fit_config,
        search_config=search_config,
        artifact_dir=artifact_dir,
        seed=seed,
    )
    return _run_search_outcome_family(
        model_name="exhaustive_structure_discovery",
        outcome=outcome,
        y=y,
        series_name=series_name,
        split=split,
        fit_config=fit_config,
        search_config=search_config,
        horizons=horizons,
        artifact_dir=artifact_dir,
        seed=seed + 307,
    )


def run_validation_only_discovery_family(
    y: np.ndarray,
    series_name: str,
    split: ChronologicalSplit,
    fit_config: FitConfig,
    search_config: SearchConfig,
    horizons: list[int],
    artifact_dir: Path,
    seed: int,
) -> dict[str, Any]:
    ensure_dir(artifact_dir)
    outcome = run_validation_only_structure_selection(
        series_name=series_name,
        y_train=y[split.train_slice],
        y_val=y[split.val_slice],
        fit_config=fit_config,
        search_config=search_config,
        artifact_dir=artifact_dir,
        seed=seed,
    )
    return _run_search_outcome_family(
        model_name="validation_only_structure_selection",
        outcome=outcome,
        y=y,
        series_name=series_name,
        split=split,
        fit_config=fit_config,
        search_config=search_config,
        horizons=horizons,
        artifact_dir=artifact_dir,
        seed=seed + 307,
    )


def run_no_observation_search_discovery_family(
    y: np.ndarray,
    series_name: str,
    split: ChronologicalSplit,
    fit_config: FitConfig,
    search_config: SearchConfig,
    horizons: list[int],
    artifact_dir: Path,
    seed: int,
) -> dict[str, Any]:
    ensure_dir(artifact_dir)
    outcome = run_no_observation_search(
        series_name=series_name,
        y_train=y[split.train_slice],
        y_val=y[split.val_slice],
        fit_config=fit_config,
        search_config=search_config,
        artifact_dir=artifact_dir,
        seed=seed,
    )
    return _run_search_outcome_family(
        model_name="no_observation_search_discovery",
        outcome=outcome,
        y=y,
        series_name=series_name,
        split=split,
        fit_config=fit_config,
        search_config=search_config,
        horizons=horizons,
        artifact_dir=artifact_dir,
        seed=seed + 307,
    )


def run_no_stability_discovery_family(
    y: np.ndarray,
    series_name: str,
    split: ChronologicalSplit,
    fit_config: FitConfig,
    search_config: SearchConfig,
    horizons: list[int],
    artifact_dir: Path,
    seed: int,
) -> dict[str, Any]:
    ensure_dir(artifact_dir)
    outcome = run_no_stability_structure_search(
        series_name=series_name,
        y_train=y[split.train_slice],
        y_val=y[split.val_slice],
        fit_config=fit_config,
        search_config=search_config,
        artifact_dir=artifact_dir,
        seed=seed,
    )
    return _run_search_outcome_family(
        model_name="no_stability_discovery",
        outcome=outcome,
        y=y,
        series_name=series_name,
        split=split,
        fit_config=fit_config,
        search_config=search_config,
        horizons=horizons,
        artifact_dir=artifact_dir,
        seed=seed + 307,
    )
