from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.evaluation.metrics import interval_level_summary_from_frame
from src.plotting.robustness_plots import plot_metric_bars, plot_metric_heatmap


MODEL_DIRECTORIES = {
    "last_observed",
    "rolling_mean_2wk",
    "rolling_mean_4wk",
    "arima_auto_small",
    "lagged_ridge",
    "lagged_gradient_boosting",
    "deterministic_seir",
    "probabilistic_seir",
    "hospitalized_seihr",
    "delayed_observation_seir",
    "fractional_seir",
    "constrained_structure_discovery",
    "random_structure_discovery",
    "exhaustive_structure_discovery",
    "validation_only_structure_selection",
    "no_observation_search_discovery",
    "no_stability_discovery",
    "equal_weight_point_ensemble",
}


def _artifact_relative_path(path: Path, artifact_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(artifact_root.resolve()))
    except ValueError:
        return str(path)


def collect_benchmark_model_summary(artifact_root: Path) -> pd.DataFrame:
    """Collect per-series per-model metrics from benchmark artifacts."""
    records: list[dict[str, object]] = []

    for metrics_path in sorted(artifact_root.glob("**/metrics.json")):
        model_dir = metrics_path.parent.name
        if model_dir not in MODEL_DIRECTORIES:
            continue

        data = json.loads(metrics_path.read_text(encoding="utf-8"))
        fit_status = data.get("fit_status", {})
        numerical_diagnostics = data.get("numerical_diagnostics", {})
        row: dict[str, object] = {
            "series_name": data["series_name"],
            "model_name": data["model_name"],
            "model_family": data.get("model_family"),
            "test_mae": data["test_metrics"]["mae"],
            "test_rmse": data["test_metrics"]["rmse"],
            "test_smape": data["test_metrics"]["smape"],
            "rolling_mean_mae": data["rolling_origin_summary"]["mean_mae"],
            "rolling_mean_rmse": data["rolling_origin_summary"]["mean_rmse"],
            "num_free_params": data["complexity"]["num_free_params"],
            "num_compartments": data["complexity"]["num_compartments"],
            "artifact_dir": _artifact_relative_path(metrics_path.parent, artifact_root),
            "numerical_failure_flag": numerical_diagnostics.get("numerical_failure_flag"),
            "max_abs_test_prediction": numerical_diagnostics.get("max_abs_test_prediction"),
            "max_abs_full_prediction": numerical_diagnostics.get("max_abs_full_prediction"),
            "train_success": fit_status.get("train_success"),
            "train_plus_validation_success": fit_status.get("train_plus_validation_success"),
            "full_success": fit_status.get("full_success"),
        }

        best_spec = data.get("best_spec")
        if best_spec is not None:
            row["discovery_structure_name"] = best_spec["structure_name"]
            row["discovery_fractional"] = best_spec["fractional"]
            row["discovery_observation_map"] = best_spec["observation_map"]
            row["discovery_delay_weeks"] = best_spec.get("delay_weeks")
        else:
            row["discovery_structure_name"] = None
            row["discovery_fractional"] = None
            row["discovery_observation_map"] = None
            row["discovery_delay_weeks"] = None

        records.append(row)

    summary = pd.DataFrame.from_records(records)
    if summary.empty:
        return summary

    summary = summary.sort_values(["series_name", "test_mae", "rolling_mean_mae", "model_name"]).reset_index(drop=True)
    return summary


def collect_benchmark_series_winners(summary: pd.DataFrame) -> pd.DataFrame:
    """Summarize best models per series for point and rolling metrics."""
    winners: list[dict[str, object]] = []

    for series_name, subset in summary.groupby("series_name"):
        best_test = subset.sort_values(["test_mae", "test_rmse"]).iloc[0]
        best_rolling = subset.sort_values(["rolling_mean_mae", "rolling_mean_rmse"]).iloc[0]
        winners.append(
            {
                "series_name": series_name,
                "best_test_model": best_test["model_name"],
                "best_test_mae": best_test["test_mae"],
                "best_rolling_model": best_rolling["model_name"],
                "best_rolling_mean_mae": best_rolling["rolling_mean_mae"],
            }
        )

    return pd.DataFrame(winners).sort_values("series_name").reset_index(drop=True)


def collect_age_group_recommendations(summary: pd.DataFrame) -> pd.DataFrame:
    """Build one recommendation row per series using balanced test/rolling ranks."""
    recommendations: list[dict[str, object]] = []

    for series_name, subset in summary.groupby("series_name"):
        ranked = subset.copy()
        ranked["test_rank"] = ranked["test_mae"].rank(method="dense", ascending=True)
        ranked["rolling_rank"] = ranked["rolling_mean_mae"].rank(method="dense", ascending=True)
        ranked["rank_score"] = ranked["test_rank"] + ranked["rolling_rank"]
        recommended = ranked.sort_values(
            ["rank_score", "rolling_rank", "test_rank", "rolling_mean_mae", "test_mae", "model_name"]
        ).iloc[0]
        best_test = ranked.sort_values(["test_mae", "test_rmse", "model_name"]).iloc[0]
        best_rolling = ranked.sort_values(["rolling_mean_mae", "rolling_mean_rmse", "model_name"]).iloc[0]

        if best_test["model_name"] == best_rolling["model_name"] == recommended["model_name"]:
            decision_type = "consensus"
        elif recommended["model_name"] == best_rolling["model_name"]:
            decision_type = "stability_preferred"
        elif recommended["model_name"] == best_test["model_name"]:
            decision_type = "test_preferred"
        else:
            decision_type = "balanced_tradeoff"

        recommendations.append(
            {
                "series_name": series_name,
                "recommended_model": recommended["model_name"],
                "decision_type": decision_type,
                "recommended_test_rank": int(recommended["test_rank"]),
                "recommended_rolling_rank": int(recommended["rolling_rank"]),
                "rank_score": float(recommended["rank_score"]),
                "best_test_model": best_test["model_name"],
                "best_test_mae": best_test["test_mae"],
                "best_rolling_model": best_rolling["model_name"],
                "best_rolling_mean_mae": best_rolling["rolling_mean_mae"],
                "recommended_discovery_structure_name": recommended["discovery_structure_name"],
                "recommended_discovery_fractional": recommended["discovery_fractional"],
                "recommended_discovery_observation_map": recommended["discovery_observation_map"],
                "recommended_discovery_delay_weeks": recommended["discovery_delay_weeks"],
            }
        )

    return pd.DataFrame(recommendations).sort_values("series_name").reset_index(drop=True)


def collect_probabilistic_calibration_summary(artifact_root: Path) -> pd.DataFrame:
    """Collect interval calibration summaries for probabilistic models."""
    columns = [
        "series_name",
        "model_name",
        "split",
        "calibration_kind",
        "interval_level",
        "nominal_coverage",
        "empirical_coverage",
        "coverage_gap",
        "average_interval_width",
        "uncertainty_method",
        "uncertainty_draws",
        "interval_calibration_method",
        "interval_calibration_scale",
        "artifact_dir",
    ]
    records: list[dict[str, object]] = []

    calibration_paths = sorted(artifact_root.glob("**/calibration_report.json"))
    if calibration_paths:
        for calibration_path in calibration_paths:
            report = json.loads(calibration_path.read_text(encoding="utf-8"))
            scale_map = report.get("interval_calibration_scales", {})
            shared_scale = report.get("interval_calibration_scale")
            for split_name, summary_key in (
                ("validation", "validation_raw_interval_summary"),
                ("validation", "validation_calibrated_interval_summary"),
                ("test", "test_raw_interval_summary"),
                ("test", "test_calibrated_interval_summary"),
            ):
                summary = report.get(summary_key, {})
                calibration_kind = "raw" if "raw" in summary_key else "calibrated"
                for level, values in summary.items():
                    records.append(
                        {
                            "series_name": report["series_name"],
                            "model_name": report["model_name"],
                            "split": split_name,
                            "calibration_kind": calibration_kind,
                            "interval_level": int(level),
                            "nominal_coverage": values["nominal_coverage"],
                            "empirical_coverage": values["empirical_coverage"],
                            "coverage_gap": values["coverage_gap"],
                            "average_interval_width": values["average_interval_width"],
                            "uncertainty_method": report.get("uncertainty_method"),
                            "uncertainty_draws": report.get("uncertainty_draws"),
                            "interval_calibration_method": report.get("interval_calibration_method"),
                            "interval_calibration_scale": scale_map.get(level, shared_scale),
                            "artifact_dir": _artifact_relative_path(calibration_path.parent, artifact_root),
                        }
                    )

        if not records:
            return pd.DataFrame(columns=columns)

        return pd.DataFrame.from_records(records).sort_values(
            ["series_name", "split", "calibration_kind", "interval_level"]
        ).reset_index(drop=True)

    for forecast_path in sorted(artifact_root.glob("**/forecast_trace.csv")):
        if forecast_path.parent.name != "probabilistic_seir":
            continue

        metrics_path = forecast_path.parent / "metrics.json"
        if not metrics_path.exists():
            continue

        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        forecast_frame = pd.read_csv(forecast_path)
        test_frame = forecast_frame.loc[forecast_frame["segment"] == "test"].copy()
        interval_summary = interval_level_summary_from_frame(test_frame)
        if not interval_summary:
            continue

        probabilistic_metrics = metrics.get("probabilistic_metrics", {})
        scale_map = probabilistic_metrics.get("interval_calibration_scales", {})
        shared_scale = probabilistic_metrics.get("interval_calibration_scale")
        for level, values in interval_summary.items():
            records.append(
                {
                    "series_name": metrics["series_name"],
                    "model_name": metrics["model_name"],
                    "interval_level": int(level),
                    "nominal_coverage": values["nominal_coverage"],
                    "empirical_coverage": values["empirical_coverage"],
                    "coverage_gap": values["coverage_gap"],
                    "average_interval_width": values["average_interval_width"],
                    "negative_log_likelihood": probabilistic_metrics.get("negative_log_likelihood"),
                    "uncertainty_method": probabilistic_metrics.get("uncertainty_method"),
                    "uncertainty_draws": probabilistic_metrics.get("uncertainty_draws"),
                    "interval_calibration_method": probabilistic_metrics.get("interval_calibration_method"),
                    "split": "test",
                    "calibration_kind": "raw",
                    "interval_calibration_scale": scale_map.get(level, shared_scale),
                    "artifact_dir": _artifact_relative_path(forecast_path.parent, artifact_root),
                }
            )

    if not records:
        return pd.DataFrame(columns=columns)

    return pd.DataFrame.from_records(records).sort_values(["series_name", "interval_level"]).reset_index(drop=True)


def _format_float(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{float(value):.4f}"


def _markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    subset = frame.loc[:, columns].copy()
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows = []
    for _, row in subset.iterrows():
        values = []
        for value in row.tolist():
            if isinstance(value, float):
                values.append(_format_float(value))
            else:
                values.append("" if value is None else str(value))
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join([header, separator, *rows])


def write_v3_result_summary(
    artifact_root: Path,
    summary: pd.DataFrame,
    winners: pd.DataFrame,
    recommendations: pd.DataFrame,
    calibration_summary: pd.DataFrame,
) -> Path:
    """Write a markdown summary for the current benchmark run."""
    overall = summary.loc[summary["series_name"] == "Overall"].copy()
    recommendation_counts = recommendations["recommended_model"].value_counts().to_dict()
    lines = [
        "# V3 Result Summary",
        "",
        "This report summarizes the current benchmark outputs for the reproducible influenza forecasting pipeline.",
        "",
        "## Headline",
        "",
        "The current results support age-aware model selection rather than a single globally best model family.",
        "",
        "## Overall Series Ranking",
        "",
    ]

    if not overall.empty:
        overall_table = overall.sort_values(["test_mae", "rolling_mean_mae"]).copy()
        overall_table["test_mae"] = overall_table["test_mae"].map(_format_float)
        overall_table["rolling_mean_mae"] = overall_table["rolling_mean_mae"].map(_format_float)
        lines.append(
            _markdown_table(
                overall_table,
                ["model_name", "test_mae", "rolling_mean_mae", "num_free_params", "num_compartments"],
            )
        )
    else:
        lines.append("No overall-series summary was found.")

    if len(winners) > 1:
        lines.extend(
            [
                "",
                "## Age-Group Winners",
                "",
                _markdown_table(
                    winners.copy(),
                    ["series_name", "best_test_model", "best_test_mae", "best_rolling_model", "best_rolling_mean_mae"],
                ),
                "",
                "## Recommended Models",
                "",
                _markdown_table(
                    recommendations.copy(),
                    ["series_name", "recommended_model", "decision_type", "best_test_model", "best_rolling_model"],
                ),
                "",
                "## Recommendation Tally",
                "",
            ]
        )
        for model_name, count in sorted(recommendation_counts.items()):
            lines.append(f"- `{model_name}` recommended for {count} series")

    if not calibration_summary.empty:
        coverage_rows = calibration_summary.loc[
            calibration_summary["interval_level"].isin([80, 95])
        ].copy()
        if "split" in coverage_rows.columns:
            calibrated_rows = coverage_rows.loc[
                (coverage_rows["split"] == "test") & (coverage_rows["calibration_kind"] == "calibrated")
            ].copy()
            coverage_rows = calibrated_rows if not calibrated_rows.empty else coverage_rows.loc[
                coverage_rows["split"] == "test"
            ].copy()
        lines.extend(
            [
                "",
                "## Probabilistic Calibration",
                "",
                _markdown_table(
                    coverage_rows,
                    ["series_name", "interval_level", "empirical_coverage", "nominal_coverage", "coverage_gap", "average_interval_width"],
                ),
            ]
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `deterministic_seir` remains the strongest default baseline for the overall series and several adult groups.",
            "- `constrained_structure_discovery` is already useful in selected age groups, especially when simpler discovered structures outperform larger hand-specified models.",
            "- `probabilistic_seir` is best interpreted as a stability and uncertainty baseline rather than the primary point-forecast winner.",
            "- The next research step is to strengthen stability-aware selection across multiple validation splits rather than further increasing raw structural flexibility.",
            "",
        ]
    )

    summary_path = artifact_root / "v3_result_summary.md"
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    return summary_path


def write_benchmark_reports(artifact_root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Write benchmark-wide summary tables and cross-series plots."""
    summary = collect_benchmark_model_summary(artifact_root)
    if summary.empty:
        raise RuntimeError(f"No benchmark metrics found under {artifact_root}")

    winners = collect_benchmark_series_winners(summary)
    recommendations = collect_age_group_recommendations(summary)
    calibration_summary = collect_probabilistic_calibration_summary(artifact_root)
    summary.to_csv(artifact_root / "benchmark_model_summary.csv", index=False)
    winners.to_csv(artifact_root / "benchmark_series_winners.csv", index=False)
    recommendations.to_csv(artifact_root / "age_group_recommendation.csv", index=False)
    if not calibration_summary.empty:
        calibration_summary.to_csv(artifact_root / "probabilistic_calibration_summary.csv", index=False)
    write_v3_result_summary(artifact_root, summary, winners, recommendations, calibration_summary)

    if summary["series_name"].nunique() > 1:
        plot_metric_heatmap(
            summary=summary,
            metric_column="test_mae",
            title="Age-Group Benchmark | Test MAE",
            path=artifact_root / "benchmark_test_mae_heatmap.png",
        )
        plot_metric_heatmap(
            summary=summary,
            metric_column="rolling_mean_mae",
            title="Age-Group Benchmark | Rolling Mean MAE",
            path=artifact_root / "benchmark_rolling_mae_heatmap.png",
        )
        plot_metric_bars(
            summary=summary,
            metric_column="test_mae",
            title="Age-Group Benchmark | Test MAE",
            path=artifact_root / "benchmark_test_mae_bars.png",
        )
        plot_metric_bars(
            summary=summary,
            metric_column="rolling_mean_mae",
            title="Age-Group Benchmark | Rolling Mean MAE",
            path=artifact_root / "benchmark_rolling_mae_bars.png",
        )

    return summary, winners, recommendations, calibration_summary
