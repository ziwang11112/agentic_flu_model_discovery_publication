from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import yaml

from run_experiment import CORE_BENCHMARK_MODELS, _benchmark_model_names
from src.evaluation.reporting import collect_benchmark_model_summary
from src.discovery.search import _stable_seed
from src.utils.io import write_json
from src.utils.paths import repo_relative_path


def test_stable_seed_uses_sha256_deterministically() -> None:
    expected = int.from_bytes(hashlib.sha256("42:series-a".encode("utf-8")).digest()[:8], "big") % (2**32 - 1)

    assert _stable_seed(42, "series-a") == expected
    assert _stable_seed(42, "series-a") == _stable_seed(42, "series-a")
    assert _stable_seed(42, "series-a") != _stable_seed(42, "series-b")


def test_repo_relative_path_avoids_absolute_paths_for_repo_internal_files(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    target = repo_root / "artifacts" / "run_summary.json"
    target.parent.mkdir(parents=True)
    target.write_text("{}", encoding="utf-8")

    relative = repo_relative_path(target, repo_root)

    assert not Path(relative).is_absolute()
    assert "artifacts" in relative
    assert "run_summary.json" in relative


def test_collect_benchmark_model_summary_handles_old_and_new_metrics_schema(tmp_path: Path) -> None:
    write_json(
        {
            "series_name": "Overall",
            "model_name": "deterministic_seir",
            "test_metrics": {"mae": 0.1, "rmse": 0.2, "smape": 0.3},
            "rolling_origin_summary": {"mean_mae": 0.11, "mean_rmse": 0.21},
            "complexity": {"num_free_params": 4, "num_compartments": 3},
        },
        tmp_path / "Overall" / "deterministic_seir" / "metrics.json",
    )
    write_json(
        {
            "series_name": "Overall",
            "model_name": "last_observed",
            "model_family": "forecast_baseline",
            "test_metrics": {"mae": 0.2, "rmse": 0.3, "smape": 0.4},
            "rolling_origin_summary": {"mean_mae": 0.22, "mean_rmse": 0.32},
            "complexity": {"num_free_params": 0, "num_compartments": 0},
            "fit_status": {
                "train_success": True,
                "train_plus_validation_success": True,
                "full_success": True,
            },
            "numerical_diagnostics": {
                "numerical_failure_flag": False,
                "max_abs_test_prediction": 1.0,
                "max_abs_full_prediction": 1.5,
            },
        },
        tmp_path / "Overall" / "last_observed" / "metrics.json",
    )

    summary = collect_benchmark_model_summary(tmp_path)
    old_row = summary.loc[summary["model_name"] == "deterministic_seir"].iloc[0]
    new_row = summary.loc[summary["model_name"] == "last_observed"].iloc[0]

    assert pd.isna(old_row["model_family"])
    assert pd.isna(old_row["numerical_failure_flag"])
    assert new_row["model_family"] == "forecast_baseline"
    assert new_row["numerical_failure_flag"] is False
    assert new_row["train_success"] is True
    assert not Path(str(new_row["artifact_dir"])).is_absolute()


def test_default_config_uses_historical_six_model_list_when_benchmark_models_absent() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((repo_root / "configs" / "default.yaml").read_text(encoding="utf-8"))

    assert "models" not in config.get("benchmark", {})
    assert _benchmark_model_names(config) == CORE_BENCHMARK_MODELS
