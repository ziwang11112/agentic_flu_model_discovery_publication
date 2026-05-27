from __future__ import annotations

import argparse
import logging
import shutil
import time
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.baselines.forecasting import FORECAST_BASELINE_NAMES, create_forecast_baseline
from src.data.loader import (
    SEASON_MODE_POOLED,
    build_flu_series_frames,
    build_processed_series,
    load_flu_surv_data,
    resolve_data_path,
    save_processed_outputs,
)
from src.data.split import make_chronological_split
from src.discovery.search import SearchConfig
from src.evaluation.baseline_pipeline import run_equal_weight_point_ensemble_family, run_forecast_baseline_family
from src.evaluation.pipeline import (
    run_delayed_observation_family,
    run_discovery_family,
    run_exhaustive_discovery_family,
    run_model_family,
    run_no_observation_search_discovery_family,
    run_no_stability_discovery_family,
    run_random_discovery_family,
    run_validation_only_discovery_family,
)
from src.evaluation.reporting import write_benchmark_reports
from src.models.base import FitConfig
from src.models.seihr_hospitalized import HospitalizedSEIHRModel
from src.models.seir_delayed_observation import DelayedObservationSEIRModel
from src.models.seir_deterministic import DeterministicSEIRModel
from src.models.seir_fractional import FractionalSEIRModel
from src.models.seir_probabilistic import ProbabilisticSEIRModel
from src.plotting.plots import plot_model_comparison
from src.utils.io import ensure_dir, write_json
from src.utils.logging_utils import configure_logging
from src.utils.paths import repo_relative_path
from src.utils.random import set_global_seed

logger = logging.getLogger(__name__)


CORE_BENCHMARK_MODELS = [
    "deterministic_seir",
    "probabilistic_seir",
    "hospitalized_seihr",
    "delayed_observation_seir",
    "fractional_seir",
    "constrained_structure_discovery",
]

MODEL_SEED_OFFSETS = {
    "deterministic_seir": 0,
    "probabilistic_seir": 11,
    "hospitalized_seihr": 17,
    "delayed_observation_seir": 19,
    "fractional_seir": 23,
    "constrained_structure_discovery": 37,
}


def _load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _benchmark_level_conformal_enabled(config: dict[str, Any]) -> bool:
    conformal = config.get("uncertainty", {}).get("conformal", {})
    return bool(conformal.get("enabled", False))


def _fit_config(config: dict[str, Any]) -> FitConfig:
    fitting = config["fitting"]
    calibrate_intervals = bool(fitting.get("calibrate_intervals", True))
    if _benchmark_level_conformal_enabled(config) and calibrate_intervals:
        calibrate_intervals = False
    return FitConfig(
        n_restarts=int(fitting["n_restarts"]),
        rolling_n_restarts=int(fitting["rolling_n_restarts"]),
        maxiter=int(fitting["maxiter"]),
        negative_penalty=float(fitting["negative_penalty"]),
        mass_penalty=float(fitting["mass_penalty"]),
        prior_weight=float(fitting["prior_weight"]),
        laplace_draws=int(fitting["laplace_draws"]),
        uncertainty_method=str(fitting.get("uncertainty_method", "laplace")),
        bootstrap_draws=int(fitting.get("bootstrap_draws", 40)),
        bootstrap_n_restarts=int(fitting.get("bootstrap_n_restarts", 0)),
        calibrate_intervals=calibrate_intervals,
        interval_calibration_method=str(fitting.get("interval_calibration_method", "conformal")),
        calibration_draws=int(fitting.get("calibration_draws", 12)),
        calibration_scale_min=float(fitting.get("calibration_scale_min", 0.25)),
        calibration_scale_max=float(fitting.get("calibration_scale_max", 1.25)),
        calibration_scale_grid_size=int(fitting.get("calibration_scale_grid_size", 41)),
        seed=int(config["seed"]),
    )


def _search_config(config: dict[str, Any]) -> SearchConfig:
    discovery = config["discovery"]
    return SearchConfig(
        beam_width=int(discovery["beam_width"]),
        max_rounds=int(discovery["max_rounds"]),
        patience=int(discovery["patience"]),
        rolling_horizons=tuple(int(value) for value in discovery["rolling_horizons"]),
        multi_split_blocks=int(discovery.get("multi_split_blocks", 3)),
        score_param_weight=float(discovery["score_param_weight"]),
        score_compartment_weight=float(discovery["score_compartment_weight"]),
        score_fractional_weight=float(discovery["score_fractional_weight"]),
        score_observation_weight=float(discovery["score_observation_weight"]),
        score_delay_weight=float(discovery.get("score_delay_weight", 0.005)),
        score_h_observation_weight=float(discovery.get("score_h_observation_weight", 0.005)),
        score_recurrence_weight=float(discovery["score_recurrence_weight"]),
        score_stability_weight=float(discovery["score_stability_weight"]),
        score_multi_split_std_weight=float(discovery.get("score_multi_split_std_weight", 0.5)),
        raw_l2_weight=float(discovery["raw_l2_weight"]),
        seasonality_l2_weight=float(discovery["seasonality_l2_weight"]),
        rho_l2_weight=float(discovery["rho_l2_weight"]),
        init_l2_weight=float(discovery["init_l2_weight"]),
        fractional_alpha_weight=float(discovery["fractional_alpha_weight"]),
        use_age_prior=bool(discovery.get("use_age_prior", True)),
        age_prior_simple_bonus=float(discovery["age_prior_simple_bonus"]),
        age_prior_recurrence_bonus=float(discovery["age_prior_recurrence_bonus"]),
        age_prior_fractional_bonus=float(discovery["age_prior_fractional_bonus"]),
        random_candidate_budget=(
            None
            if discovery.get("random_candidate_budget") is None
            else int(discovery["random_candidate_budget"])
        ),
        random_repeats=int(discovery.get("random_repeats", 1)),
        exhaustive_max_candidates=(
            None
            if discovery.get("exhaustive_max_candidates") is None
            else int(discovery["exhaustive_max_candidates"])
        ),
        allow_truncated_exhaustive=bool(discovery.get("allow_truncated_exhaustive", False)),
    )


def _slugify(text: str) -> str:
    return (
        text.lower()
        .replace(">=", "ge_")
        .replace("<", "lt_")
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
    )


def _benchmark_model_names(config: dict[str, Any]) -> list[str]:
    configured = config.get("benchmark", {}).get("models")
    if configured is None:
        return list(CORE_BENCHMARK_MODELS)

    model_names = [str(value) for value in configured]
    if "equal_weight_point_ensemble" in model_names and model_names[-1] != "equal_weight_point_ensemble":
        logger.warning("Moving equal_weight_point_ensemble to the end of benchmark.models so member artifacts exist.")
        model_names = [name for name in model_names if name != "equal_weight_point_ensemble"]
        model_names.append("equal_weight_point_ensemble")
    return model_names


def _benchmark_ensemble_members(config: dict[str, Any]) -> list[str] | None:
    configured = config.get("benchmark", {}).get("ensemble_members")
    if configured is None:
        return None
    return [str(value) for value in configured]


def _model_seed(base_seed: int, model_name: str, position: int) -> int:
    return base_seed + MODEL_SEED_OFFSETS.get(model_name, position * 101)


def _run_one_model(
    *,
    model_name: str,
    series_name: str,
    y,
    split,
    fit_config: FitConfig,
    search_config: SearchConfig,
    horizons: list[int],
    artifact_dir: Path,
    seed: int,
    ensemble_members: list[str] | None = None,
) -> dict[str, Any]:
    if model_name in FORECAST_BASELINE_NAMES:
        return run_forecast_baseline_family(
            baseline_factory=lambda model_name=model_name, seed=seed: create_forecast_baseline(model_name, seed=seed),
            series_name=series_name,
            y=y,
            split=split,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
        )
    if model_name == "equal_weight_point_ensemble":
        return run_equal_weight_point_ensemble_family(
            series_name=series_name,
            y=y,
            split=split,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
            ensemble_members=ensemble_members,
        )
    if model_name == "deterministic_seir":
        return run_model_family(
            model_factory=lambda: DeterministicSEIRModel(fit_config),
            series_name=series_name,
            y=y,
            split=split,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
        )
    if model_name == "probabilistic_seir":
        return run_model_family(
            model_factory=lambda: ProbabilisticSEIRModel(fit_config),
            series_name=series_name,
            y=y,
            split=split,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
        )
    if model_name == "hospitalized_seihr":
        return run_model_family(
            model_factory=lambda: HospitalizedSEIHRModel(fit_config),
            series_name=series_name,
            y=y,
            split=split,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
        )
    if model_name == "delayed_observation_seir":
        return run_delayed_observation_family(
            series_name=series_name,
            y=y,
            split=split,
            fit_config=fit_config,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
        )
    if model_name == "fractional_seir":
        return run_model_family(
            model_factory=lambda: FractionalSEIRModel(fit_config),
            series_name=series_name,
            y=y,
            split=split,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
        )
    if model_name == "constrained_structure_discovery":
        return run_discovery_family(
            y=y,
            series_name=series_name,
            split=split,
            fit_config=fit_config,
            search_config=search_config,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
        )
    if model_name == "random_structure_discovery":
        return run_random_discovery_family(
            y=y,
            series_name=series_name,
            split=split,
            fit_config=fit_config,
            search_config=search_config,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
        )
    if model_name == "exhaustive_structure_discovery":
        return run_exhaustive_discovery_family(
            y=y,
            series_name=series_name,
            split=split,
            fit_config=fit_config,
            search_config=search_config,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
        )
    if model_name == "validation_only_structure_selection":
        return run_validation_only_discovery_family(
            y=y,
            series_name=series_name,
            split=split,
            fit_config=fit_config,
            search_config=search_config,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
        )
    if model_name == "no_observation_search_discovery":
        return run_no_observation_search_discovery_family(
            y=y,
            series_name=series_name,
            split=split,
            fit_config=fit_config,
            search_config=search_config,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
        )
    if model_name == "no_stability_discovery":
        return run_no_stability_discovery_family(
            y=y,
            series_name=series_name,
            split=split,
            fit_config=fit_config,
            search_config=search_config,
            horizons=horizons,
            artifact_dir=artifact_dir,
            seed=seed,
        )
    raise ValueError(f"Unsupported benchmark model: {model_name}")


def _run_series_benchmark(
    series_name: str,
    series_frame: pd.DataFrame,
    fit_config: FitConfig,
    search_config: SearchConfig,
    artifact_root: Path,
    horizons: list[int],
    seed: int,
    model_names: list[str],
    ensemble_members: list[str] | None,
) -> pd.DataFrame:
    y = series_frame["WEEKLY RATE"].to_numpy(dtype=float)
    split = make_chronological_split(len(y))
    series_artifact_root = ensure_dir(artifact_root / _slugify(series_name))
    series_start = time.perf_counter()
    logger.info(
        "Starting series=%s n_obs=%d train_end=%d val_end=%d artifacts=%s",
        series_name,
        len(y),
        split.train_end,
        split.val_end,
        series_artifact_root,
    )

    results = []
    for position, model_name in enumerate(model_names):
        logger.info("Running model=%s series=%s", model_name, series_name)
        result = _run_one_model(
            model_name=model_name,
            series_name=series_name,
            y=y,
            split=split,
            fit_config=fit_config,
            search_config=search_config,
            horizons=horizons,
            artifact_dir=series_artifact_root / model_name,
            seed=_model_seed(seed, model_name, position),
            ensemble_members=ensemble_members,
        )
        results.append(result["comparison_row"])
        logger.info(
            "Completed model=%s series=%s test_mae=%.6f",
            model_name,
            series_name,
            result["comparison_row"]["test_mae"],
        )

    leaderboard = pd.DataFrame(results).sort_values(["test_mae", "test_rmse"], ascending=[True, True]).reset_index(drop=True)
    leaderboard.insert(0, "series_name", series_name)
    leaderboard.to_csv(series_artifact_root / "leaderboard.csv", index=False)
    plot_model_comparison(leaderboard, series_artifact_root / "model_comparison.png")
    logger.info(
        "Finished series=%s winner=%s elapsed=%.1fs leaderboard=%s",
        series_name,
        leaderboard.iloc[0]["model_name"],
        time.perf_counter() - series_start,
        series_artifact_root / "leaderboard.csv",
    )
    return leaderboard


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the influenza forecasting benchmark.")
    parser.add_argument("--config", type=str, required=True, help="Path to the YAML config.")
    parser.add_argument("--log-level", type=str, default="INFO", help="Logging verbosity: DEBUG, INFO, WARNING.")
    args = parser.parse_args()
    configure_logging(args.log_level)

    repo_root = Path(__file__).resolve().parent
    logger.info("Benchmark start config=%s repo_root=%s", args.config, repo_root)
    config = _load_config(repo_root / args.config)
    set_global_seed(int(config["seed"]))
    logger.info("Global seed=%d", int(config["seed"]))

    raw_csv_path = resolve_data_path(repo_root, config["data"]["raw_csv"])
    raw_output_dir = ensure_dir(repo_root / "data" / "raw")
    copied_raw_csv = raw_output_dir / raw_csv_path.name
    if raw_csv_path.exists() and raw_csv_path.resolve() != copied_raw_csv.resolve():
        shutil.copy2(raw_csv_path, copied_raw_csv)

    data_config = config["data"]
    seasons = data_config.get("seasons")
    season_mode = str(data_config.get("season_mode", SEASON_MODE_POOLED))
    frame = load_flu_surv_data(raw_csv_path)
    processed = build_processed_series(
        frame=frame,
        include_age_groups=bool(data_config["include_age_robustness"]),
        age_groups=data_config["age_groups"],
        seasons=seasons,
        season_mode=season_mode,
    )
    save_processed_outputs(processed, repo_root / data_config["processed_dir"])
    logger.info(
        "Processed data saved to %s with series=%s seasons=%s season_mode=%s",
        repo_root / data_config["processed_dir"],
        sorted(processed["series_name"].unique().tolist()),
        sorted(processed["season"].unique().tolist()),
        season_mode,
    )

    if _benchmark_level_conformal_enabled(config) and bool(config["fitting"].get("calibrate_intervals", True)):
        logger.info(
            "Benchmark-level conformal postprocess is enabled; disabling fitting-level interval calibration to avoid double calibration."
        )

    fit_config = _fit_config(config)
    search_config = _search_config(config)
    horizons = [int(value) for value in config["evaluation"]["horizons"]]
    model_names = _benchmark_model_names(config)
    ensemble_members = _benchmark_ensemble_members(config)
    artifact_root = ensure_dir(repo_root / config["artifacts"]["root_dir"])

    benchmark_leaderboards = []
    series_items = build_flu_series_frames(
        frame=frame,
        include_age_groups=bool(data_config["include_age_robustness"]),
        age_groups=data_config["age_groups"],
        seasons=seasons,
        season_mode=season_mode,
    )
    for item in series_items:
        series_name = str(item["series_name"])
        if bool(item["frame"].empty):  # type: ignore[union-attr]
            logger.warning("Skipping empty series=%s seasons=%s", series_name, item["seasons"])
            continue
        is_robustness = bool(item["is_robustness"])
        if is_robustness:
            series_artifact_parent = artifact_root / "robustness"
        else:
            series_artifact_parent = artifact_root
        if season_mode != SEASON_MODE_POOLED:
            series_artifact_parent = series_artifact_parent / "seasons"
        if season_mode == SEASON_MODE_POOLED and not is_robustness and series_name == "Overall":
            series_seed = int(config["seed"])
        else:
            series_seed = int(config["seed"]) + 1000 + len(benchmark_leaderboards)
        logger.info("Starting benchmark series=%s seasons=%s", series_name, item["seasons"])
        board = _run_series_benchmark(
            series_name=series_name,
            series_frame=item["frame"],  # type: ignore[arg-type]
            fit_config=fit_config,
            search_config=search_config,
            artifact_root=series_artifact_parent,
            horizons=horizons,
            seed=series_seed,
            model_names=model_names,
            ensemble_members=ensemble_members,
        )
        benchmark_leaderboards.append(board)
        combined_so_far = pd.concat(benchmark_leaderboards, ignore_index=True)
        combined_so_far.to_csv(artifact_root / "benchmark_leaderboard_partial.csv", index=False)
        logger.info(
            "Completed series=%s partial_leaderboard=%s",
            series_name,
            artifact_root / "benchmark_leaderboard_partial.csv",
        )

    combined_board = pd.concat(benchmark_leaderboards, ignore_index=True)
    combined_board.to_csv(artifact_root / "benchmark_leaderboard.csv", index=False)
    summary_frame, winners_frame, recommendation_frame, calibration_frame = write_benchmark_reports(artifact_root)
    write_json(
        {
            "seed": int(config["seed"]),
            "series_evaluated": combined_board["series_name"].unique().tolist(),
            "leaderboard_path": repo_relative_path(artifact_root / "benchmark_leaderboard.csv", repo_root),
            "summary_path": repo_relative_path(artifact_root / "benchmark_model_summary.csv", repo_root),
            "winners_path": repo_relative_path(artifact_root / "benchmark_series_winners.csv", repo_root),
            "recommendation_path": repo_relative_path(artifact_root / "age_group_recommendation.csv", repo_root),
            "v3_summary_path": repo_relative_path(artifact_root / "v3_result_summary.md", repo_root),
            "probabilistic_calibration_path": repo_relative_path(
                artifact_root / "probabilistic_calibration_summary.csv",
                repo_root,
            ),
        },
        artifact_root / "run_summary.json",
    )
    logger.info(
        "Benchmark completed series_count=%d leaderboard=%s summary=%s winners=%s recommendations=%s v3_summary=%s",
        len(combined_board["series_name"].unique()),
        artifact_root / "benchmark_leaderboard.csv",
        artifact_root / "benchmark_model_summary.csv",
        artifact_root / "benchmark_series_winners.csv",
        artifact_root / "age_group_recommendation.csv",
        artifact_root / "v3_result_summary.md",
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("Benchmark interrupted by user.")
        raise
    except Exception:
        logger.exception("Benchmark failed.")
        raise
