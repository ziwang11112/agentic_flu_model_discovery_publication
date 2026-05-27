from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.evaluation.statistical_tests import paired_rolling_error_comparison
from src.utils.io import write_json


def test_paired_rolling_comparison_uses_metrics_identity_and_nested_paths(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    _write_rolling_bundle(
        root / "robustness" / "ge__65_yr" / "folder_a",
        series_name=">= 65 yr",
        model_name="constrained_structure_discovery",
        rows=[
            {"horizon": 1, "target_t": 10, "abs_error": 1.0},
            {"horizon": 2, "target_t": 11, "abs_error": 2.0},
        ],
    )
    _write_rolling_bundle(
        root / "robustness" / "ge__65_yr" / "folder_b",
        series_name=">= 65 yr",
        model_name="random_structure_discovery",
        rows=[
            {"horizon": 1, "target_t": 10, "abs_error": 3.0},
            {"horizon": 2, "target_t": 11, "abs_error": 4.0},
        ],
    )

    comparison = paired_rolling_error_comparison(root, n_bootstrap=20, seed=42)

    row = comparison.iloc[0]
    assert row["series_name"] == ">= 65 yr"
    assert row["challenger_model"] == "random_structure_discovery"
    assert row["n_aligned"] == 2
    assert row["mean_diff_challenger_minus_reference"] == 2.0
    assert row["reference_win_rate"] == 1.0


def test_paired_rolling_comparison_aligns_on_horizon_and_target_t(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    _write_rolling_bundle(
        root / "Overall" / "constrained_structure_discovery",
        "Overall",
        "constrained_structure_discovery",
        [
            {"horizon": 1, "target_t": 10, "abs_error": 1.0},
            {"horizon": 1, "target_t": 11, "abs_error": 10.0},
        ],
    )
    _write_rolling_bundle(
        root / "Overall" / "last_observed",
        "Overall",
        "last_observed",
        [
            {"horizon": 1, "target_t": 10, "abs_error": 2.0},
            {"horizon": 2, "target_t": 11, "abs_error": 2.0},
        ],
    )

    comparison = paired_rolling_error_comparison(root, n_bootstrap=0)

    assert comparison["n_aligned"].tolist() == [1]
    assert comparison["mean_diff_challenger_minus_reference"].tolist() == [1.0]
    assert {"ci95_low", "ci95_high"}.issubset(comparison.columns)


def test_paired_rolling_comparison_skips_missing_or_misaligned_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    write_json(
        {
            "series_name": "Overall",
            "model_name": "constrained_structure_discovery",
            "test_metrics": {"mae": 0.0, "rmse": 0.0, "smape": 0.0},
            "rolling_origin_summary": {"mean_mae": 0.0, "mean_rmse": 0.0},
            "complexity": {"num_free_params": 0, "num_compartments": 0},
        },
        root / "Overall" / "constrained_structure_discovery" / "metrics.json",
    )

    comparison = paired_rolling_error_comparison(root)

    assert comparison.empty
    assert comparison.attrs["skipped_models"]


def _write_rolling_bundle(path: Path, series_name: str, model_name: str, rows: list[dict[str, float]]) -> None:
    write_json(
        {
            "series_name": series_name,
            "model_name": model_name,
            "test_metrics": {"mae": 0.0, "rmse": 0.0, "smape": 0.0},
            "rolling_origin_summary": {"mean_mae": 0.0, "mean_rmse": 0.0},
            "complexity": {"num_free_params": 0, "num_compartments": 0},
        },
        path / "metrics.json",
    )
    frame = pd.DataFrame(rows)
    frame["actual"] = 0.0
    frame["prediction"] = frame["abs_error"]
    frame["error"] = frame["abs_error"]
    frame["origin_end"] = frame["target_t"] - frame["horizon"] + 1
    path.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path / "rolling_origin_forecasts.csv", index=False)
