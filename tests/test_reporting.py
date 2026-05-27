from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.evaluation.reporting import (
    collect_age_group_recommendations,
    collect_benchmark_model_summary,
    collect_benchmark_series_winners,
    collect_probabilistic_calibration_summary,
    write_benchmark_reports,
)
from src.utils.io import write_json


def _write_metrics(
    root: Path,
    series_name: str,
    model_name: str,
    test_mae: float,
    rolling_mean_mae: float,
    discovery_structure_name: str | None = None,
) -> None:
    metrics = {
        "series_name": series_name,
        "model_name": model_name,
        "test_metrics": {"mae": test_mae, "rmse": test_mae + 0.01, "smape": 0.1},
        "rolling_origin_summary": {"mean_mae": rolling_mean_mae, "mean_rmse": rolling_mean_mae + 0.02},
        "complexity": {"num_free_params": 4, "num_compartments": 3},
    }
    if discovery_structure_name is not None:
        metrics["best_spec"] = {
            "structure_name": discovery_structure_name,
            "fractional": False,
            "observation_map": "I",
            "delay_weeks": 0,
        }
    if model_name == "probabilistic_seir":
        metrics["probabilistic_metrics"] = {
            "negative_log_likelihood": 1.23,
            "uncertainty_method": "bootstrap",
            "uncertainty_draws": 30,
        }

    write_json(metrics, root / series_name / model_name / "metrics.json")


def _write_probabilistic_trace(root: Path, series_name: str) -> None:
    frame = pd.DataFrame(
        {
            "t": [0, 1, 2],
            "actual": [0.10, 0.20, 0.15],
            "full_fit_prediction": [0.11, 0.19, 0.16],
            "test_forecast_prediction": [0.11, 0.19, 0.16],
            "segment": ["test", "test", "test"],
            "lower_50": [0.08, 0.17, 0.13],
            "upper_50": [0.14, 0.21, 0.17],
            "lower_80": [0.05, 0.14, 0.10],
            "upper_80": [0.16, 0.24, 0.20],
            "lower_95": [0.03, 0.12, 0.08],
            "upper_95": [0.18, 0.26, 0.22],
        }
    )
    path = root / series_name / "probabilistic_seir" / "forecast_trace.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def test_reporting_collects_summary_and_winners(tmp_path: Path) -> None:
    _write_metrics(tmp_path, "Overall", "deterministic_seir", test_mae=0.10, rolling_mean_mae=0.11)
    _write_metrics(tmp_path, "Overall", "constrained_structure_discovery", test_mae=0.09, rolling_mean_mae=0.12, discovery_structure_name="SIR")
    _write_metrics(tmp_path, "0-4 yr", "deterministic_seir", test_mae=0.20, rolling_mean_mae=0.22)
    _write_metrics(tmp_path, "0-4 yr", "constrained_structure_discovery", test_mae=0.18, rolling_mean_mae=0.17, discovery_structure_name="SEIRS")

    summary = collect_benchmark_model_summary(tmp_path)
    winners = collect_benchmark_series_winners(summary)

    assert sorted(summary["series_name"].unique().tolist()) == ["0-4 yr", "Overall"]
    assert "discovery_structure_name" in summary.columns
    assert winners.loc[winners["series_name"] == "Overall", "best_test_model"].item() == "constrained_structure_discovery"
    assert winners.loc[winners["series_name"] == "0-4 yr", "best_rolling_model"].item() == "constrained_structure_discovery"

    recommendations = collect_age_group_recommendations(summary)
    assert recommendations.loc[recommendations["series_name"] == "Overall", "recommended_model"].item() == "deterministic_seir"
    assert recommendations.loc[recommendations["series_name"] == "0-4 yr", "decision_type"].item() == "consensus"


def test_reporting_includes_discovery_ablation_directories(tmp_path: Path) -> None:
    _write_metrics(tmp_path, "Overall", "random_structure_discovery", test_mae=0.11, rolling_mean_mae=0.12, discovery_structure_name="SEIR")
    _write_metrics(tmp_path, "Overall", "validation_only_structure_selection", test_mae=0.13, rolling_mean_mae=0.14, discovery_structure_name="SIR")

    summary = collect_benchmark_model_summary(tmp_path)

    assert set(summary["model_name"].tolist()) == {"random_structure_discovery", "validation_only_structure_selection"}


def test_collect_probabilistic_calibration_summary(tmp_path: Path) -> None:
    _write_metrics(tmp_path, "Overall", "probabilistic_seir", test_mae=0.12, rolling_mean_mae=0.13)
    _write_probabilistic_trace(tmp_path, "Overall")

    calibration = collect_probabilistic_calibration_summary(tmp_path)

    assert calibration["series_name"].tolist() == ["Overall", "Overall", "Overall"]
    assert calibration["interval_level"].tolist() == [50, 80, 95]
    assert calibration["uncertainty_method"].iloc[0] == "bootstrap"


def test_collect_probabilistic_calibration_summary_handles_empty_reports(tmp_path: Path) -> None:
    write_json(
        {
            "series_name": "Overall",
            "model_name": "probabilistic_seir",
            "validation_raw_interval_summary": {},
            "validation_calibrated_interval_summary": {},
            "test_raw_interval_summary": {},
            "test_calibrated_interval_summary": {},
        },
        tmp_path / "Overall" / "probabilistic_seir" / "calibration_report.json",
    )

    calibration = collect_probabilistic_calibration_summary(tmp_path)

    assert calibration.empty
    assert "series_name" in calibration.columns
    assert "calibration_kind" in calibration.columns


def test_collect_probabilistic_calibration_summary_reads_level_specific_scales(tmp_path: Path) -> None:
    write_json(
        {
            "series_name": "Overall",
            "model_name": "probabilistic_seir",
            "uncertainty_method": "bootstrap",
            "uncertainty_draws": 30,
            "interval_calibration_method": "conformal",
            "interval_calibration_scales": {"80": 0.8, "95": 0.9},
            "validation_raw_interval_summary": {},
            "validation_calibrated_interval_summary": {},
            "test_raw_interval_summary": {
                "80": {
                    "nominal_coverage": 0.8,
                    "empirical_coverage": 1.0,
                    "coverage_gap": 0.2,
                    "average_interval_width": 0.5,
                }
            },
            "test_calibrated_interval_summary": {
                "80": {
                    "nominal_coverage": 0.8,
                    "empirical_coverage": 0.9,
                    "coverage_gap": 0.1,
                    "average_interval_width": 0.4,
                },
                "95": {
                    "nominal_coverage": 0.95,
                    "empirical_coverage": 1.0,
                    "coverage_gap": 0.05,
                    "average_interval_width": 0.6,
                },
            },
        },
        tmp_path / "Overall" / "probabilistic_seir" / "calibration_report.json",
    )

    calibration = collect_probabilistic_calibration_summary(tmp_path)
    calibrated_rows = calibration.loc[
        (calibration["split"] == "test") & (calibration["calibration_kind"] == "calibrated")
    ].sort_values("interval_level")

    assert calibrated_rows["interval_level"].tolist() == [80, 95]
    assert calibrated_rows["interval_calibration_method"].tolist() == ["conformal", "conformal"]
    assert calibrated_rows["interval_calibration_scale"].tolist() == [0.8, 0.9]


def test_reporting_writes_summary_files_and_plots(tmp_path: Path) -> None:
    _write_metrics(tmp_path, "Overall", "deterministic_seir", test_mae=0.10, rolling_mean_mae=0.11)
    _write_metrics(tmp_path, "Overall", "probabilistic_seir", test_mae=0.12, rolling_mean_mae=0.13)
    _write_metrics(tmp_path, "Overall", "fractional_seir", test_mae=0.14, rolling_mean_mae=0.15)
    _write_metrics(tmp_path, "Overall", "constrained_structure_discovery", test_mae=0.09, rolling_mean_mae=0.12, discovery_structure_name="SIR")
    _write_metrics(tmp_path, "0-4 yr", "deterministic_seir", test_mae=0.20, rolling_mean_mae=0.22)
    _write_metrics(tmp_path, "0-4 yr", "probabilistic_seir", test_mae=0.19, rolling_mean_mae=0.21)
    _write_metrics(tmp_path, "0-4 yr", "fractional_seir", test_mae=0.25, rolling_mean_mae=0.26)
    _write_metrics(tmp_path, "0-4 yr", "constrained_structure_discovery", test_mae=0.18, rolling_mean_mae=0.17, discovery_structure_name="SEIRS")
    _write_probabilistic_trace(tmp_path, "Overall")
    _write_probabilistic_trace(tmp_path, "0-4 yr")

    write_benchmark_reports(tmp_path)

    assert (tmp_path / "benchmark_model_summary.csv").exists()
    assert (tmp_path / "benchmark_series_winners.csv").exists()
    assert (tmp_path / "age_group_recommendation.csv").exists()
    assert (tmp_path / "probabilistic_calibration_summary.csv").exists()
    assert (tmp_path / "v3_result_summary.md").exists()
    assert (tmp_path / "benchmark_test_mae_heatmap.png").exists()
    assert (tmp_path / "benchmark_rolling_mae_bars.png").exists()
