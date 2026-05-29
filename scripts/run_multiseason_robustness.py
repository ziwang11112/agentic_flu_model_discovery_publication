from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "agentic_flu_model_discovery_matplotlib"))

from run_experiment import _fit_config, _model_seed, _run_one_model, _search_config, _slugify  # noqa: E402
from src.data.loader import SEASON_MODE_SEPARATE, build_flu_series_frames, load_flu_surv_data, resolve_data_path  # noqa: E402
from src.data.split import make_chronological_split  # noqa: E402
from src.evaluation.reporting import (  # noqa: E402
    collect_age_group_recommendations,
    collect_benchmark_model_summary,
)
from src.utils.io import ensure_dir, write_json  # noqa: E402
from src.utils.logging_utils import configure_logging  # noqa: E402
from src.utils.paths import repo_relative_path  # noqa: E402

logger = logging.getLogger(__name__)


def _repo_path(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def _load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _disable_plot_writes() -> None:
    """Avoid per-model PNG diagnostics while preserving metric/artifact generation."""

    def _noop(*args: Any, **kwargs: Any) -> None:
        return None

    import src.evaluation.baseline_pipeline as baseline_pipeline
    import src.evaluation.pipeline as pipeline

    baseline_pipeline._write_optional_plots = _noop  # type: ignore[assignment]
    pipeline.plot_full_series_fit = _noop  # type: ignore[assignment]
    pipeline.plot_residuals = _noop  # type: ignore[assignment]
    pipeline.plot_rolling_forecasts = _noop  # type: ignore[assignment]
    pipeline.plot_leaderboard = _noop  # type: ignore[assignment]
    pipeline.plot_structure_diagram = _noop  # type: ignore[assignment]
    pipeline.plot_probabilistic_calibration = _noop  # type: ignore[assignment]


def _completed_seasons(config: dict[str, Any]) -> list[str]:
    data_config = config["data"]
    completed_path = _repo_path(data_config["completed_seasons_path"])
    frame = pd.read_csv(completed_path)
    complete = frame.loc[frame["status"].astype(str).str.lower() == "complete"].copy()
    available = complete["season"].astype(str).tolist()
    requested = data_config.get("seasons") or available
    selected = [str(season) for season in requested if str(season) in set(available)]
    if not selected:
        raise RuntimeError(f"No requested completed seasons found in {completed_path}")
    missing = [str(season) for season in requested if str(season) not in set(available)]
    if missing:
        logger.warning("Ignoring non-completed or unavailable seasons: %s", ", ".join(missing))
    return selected


def _model_names(config: dict[str, Any]) -> list[str]:
    models = [str(value) for value in config.get("benchmark", {}).get("models", [])]
    if not models:
        raise ValueError("multiseason robustness config must provide benchmark.models")
    return models


def _parse_series_name(series_name: str) -> tuple[str, str]:
    if " / " not in series_name:
        return "", series_name
    season, age_group = series_name.split(" / ", 1)
    return season, age_group


def _json_load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_search_metadata(summary: pd.DataFrame, temp_root: Path) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for _, row in summary.iterrows():
        artifact_dir = temp_root / str(row["artifact_dir"])
        metrics_path = artifact_dir / "metrics.json"
        metrics = _json_load(metrics_path) if metrics_path.exists() else {}
        best_record = metrics.get("search_best_record", {}) or {}
        best_spec = metrics.get("best_spec", {}) or {}
        records.append(
            {
                "series_name": row["series_name"],
                "model_name": row["model_name"],
                "structure_name": best_spec.get("structure_name") or row.get("discovery_structure_name"),
                "fractional": best_spec.get("fractional", row.get("discovery_fractional")),
                "observation_map": best_spec.get("observation_map") or row.get("discovery_observation_map"),
                "delay_weeks": best_spec.get("delay_weeks", row.get("discovery_delay_weeks")),
                "score_policy": best_record.get("score_policy"),
                "score": best_record.get("score"),
                "score_formula": best_record.get("score_formula"),
            }
        )
    return pd.DataFrame.from_records(records)


def _ranked_model_summary(summary: pd.DataFrame, temp_root: Path) -> pd.DataFrame:
    ranked = summary.copy()
    parsed = ranked["series_name"].map(_parse_series_name)
    ranked.insert(0, "season", parsed.map(lambda item: item[0]))
    ranked.insert(1, "age_group", parsed.map(lambda item: item[1]))
    ranked["test_rank"] = ranked.groupby("series_name")["test_mae"].rank(method="dense", ascending=True).astype(int)
    ranked["rolling_rank"] = ranked.groupby("series_name")["rolling_mean_mae"].rank(method="dense", ascending=True).astype(int)
    ranked["rank_score"] = ranked["test_rank"] + ranked["rolling_rank"]

    metadata = _extract_search_metadata(summary, temp_root)
    ranked = ranked.merge(metadata, on=["series_name", "model_name"], how="left", suffixes=("", "_meta"))
    for column in ["structure_name", "fractional", "observation_map", "delay_weeks"]:
        meta_column = f"{column}_meta"
        if meta_column in ranked.columns:
            ranked[column] = ranked[column].combine_first(ranked[meta_column])
            ranked = ranked.drop(columns=[meta_column])

    recommendations = collect_age_group_recommendations(summary)
    recommendation_cols = [
        "series_name",
        "recommended_model",
        "decision_type",
        "best_test_model",
        "best_rolling_model",
    ]
    ranked = ranked.merge(recommendations.loc[:, recommendation_cols], on="series_name", how="left")

    columns = [
        "season",
        "age_group",
        "series_name",
        "model_name",
        "model_family",
        "test_mae",
        "rolling_mean_mae",
        "test_rank",
        "rolling_rank",
        "rank_score",
        "recommended_model",
        "decision_type",
        "best_test_model",
        "best_rolling_model",
        "structure_name",
        "fractional",
        "observation_map",
        "delay_weeks",
        "score_policy",
        "score",
        "score_formula",
        "numerical_failure_flag",
    ]
    available_columns = [column for column in columns if column in ranked.columns]
    return ranked.loc[:, available_columns].sort_values(["season", "age_group", "test_rank", "model_name"]).reset_index(drop=True)


def _season_level_recommendations(summary: pd.DataFrame) -> pd.DataFrame:
    recommendations = collect_age_group_recommendations(summary)
    parsed = recommendations["series_name"].map(_parse_series_name)
    recommendations.insert(0, "season", parsed.map(lambda item: item[0]))
    recommendations.insert(1, "age_group", parsed.map(lambda item: item[1]))
    columns = [
        "season",
        "age_group",
        "series_name",
        "recommended_model",
        "decision_type",
        "recommended_test_rank",
        "recommended_rolling_rank",
        "rank_score",
        "best_test_model",
        "best_test_mae",
        "best_rolling_model",
        "best_rolling_mean_mae",
        "recommended_discovery_structure_name",
        "recommended_discovery_fractional",
        "recommended_discovery_observation_map",
        "recommended_discovery_delay_weeks",
    ]
    return recommendations.loc[:, columns].sort_values(["season", "age_group"]).reset_index(drop=True)


def _observation_map_by_season(model_summary: pd.DataFrame) -> pd.DataFrame:
    discovery_rows = model_summary.loc[model_summary["model_name"].astype(str).str.contains("discovery|selection")].copy()
    columns = [
        "season",
        "age_group",
        "series_name",
        "model_name",
        "structure_name",
        "fractional",
        "observation_map",
        "delay_weeks",
        "score_policy",
        "test_mae",
        "rolling_mean_mae",
    ]
    return discovery_rows.loc[:, columns].sort_values(["season", "age_group", "model_name"]).reset_index(drop=True)


def _observation_search_impact(model_summary: pd.DataFrame) -> pd.DataFrame:
    constrained = model_summary.loc[model_summary["model_name"] == "constrained_structure_discovery"].copy()
    fixed = model_summary.loc[model_summary["model_name"] == "no_observation_search_discovery"].copy()
    keys = ["season", "age_group", "series_name"]
    left = constrained.loc[
        :,
        keys + ["test_mae", "rolling_mean_mae", "structure_name", "observation_map", "delay_weeks"],
    ].rename(
        columns={
            "test_mae": "constrained_test_mae",
            "rolling_mean_mae": "constrained_rolling_mean_mae",
            "structure_name": "constrained_structure",
            "observation_map": "constrained_observation_map",
            "delay_weeks": "constrained_delay_weeks",
        }
    )
    right = fixed.loc[
        :,
        keys + ["test_mae", "rolling_mean_mae", "structure_name", "observation_map", "delay_weeks"],
    ].rename(
        columns={
            "test_mae": "no_observation_test_mae",
            "rolling_mean_mae": "no_observation_rolling_mean_mae",
            "structure_name": "no_observation_structure",
            "observation_map": "no_observation_observation_map",
            "delay_weeks": "no_observation_delay_weeks",
        }
    )
    impact = left.merge(right, on=keys, how="inner")
    impact["delta_test_mae"] = impact["no_observation_test_mae"] - impact["constrained_test_mae"]
    impact["delta_rolling_mean_mae"] = (
        impact["no_observation_rolling_mean_mae"] - impact["constrained_rolling_mean_mae"]
    )
    return impact.sort_values(["season", "age_group"]).reset_index(drop=True)


def _mode_and_frequency(values: list[str]) -> tuple[str | None, float]:
    if not values:
        return None, 0.0
    winner, count = Counter(values).most_common(1)[0]
    return winner, count / len(values)


def _recommendation_modes(
    recommendations: pd.DataFrame,
    model_summary: pd.DataFrame,
    observation_impact: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for age_group, subset in recommendations.groupby("age_group", sort=True):
        rec_mode, rec_freq = _mode_and_frequency(subset["recommended_model"].astype(str).tolist())
        test_mode, test_freq = _mode_and_frequency(subset["best_test_model"].astype(str).tolist())
        rolling_mode, rolling_freq = _mode_and_frequency(subset["best_rolling_model"].astype(str).tolist())
        constrained = model_summary.loc[
            (model_summary["age_group"] == age_group)
            & (model_summary["model_name"] == "constrained_structure_discovery")
        ].copy()
        impact = observation_impact.loc[observation_impact["age_group"] == age_group].copy()
        rows.append(
            {
                "age_group": age_group,
                "num_seasons": int(subset["season"].nunique()),
                "recommended_model_mode": rec_mode,
                "recommended_model_frequency": rec_freq,
                "best_test_model_mode": test_mode,
                "best_test_model_frequency": test_freq,
                "best_rolling_model_mode": rolling_mode,
                "best_rolling_model_frequency": rolling_freq,
                "constrained_discovery_recommended_count": int(
                    (subset["recommended_model"] == "constrained_structure_discovery").sum()
                ),
                "delayed_I_selected_count": int((constrained["observation_map"] == "delayed_I").sum()),
                "positive_observation_search_delta_count": int((impact["delta_rolling_mean_mae"] > 0.0).sum()),
            }
        )
    return pd.DataFrame.from_records(rows).sort_values("age_group").reset_index(drop=True)


def _key_findings(modes: pd.DataFrame, impact: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in modes.iterrows():
        age_group = str(row["age_group"])
        num_seasons = int(row["num_seasons"])
        age_impact = impact.loc[impact["age_group"] == age_group]
        positive_count = int(row["positive_observation_search_delta_count"])
        delayed_count = int(row["delayed_I_selected_count"])
        mean_delta = float(age_impact["delta_rolling_mean_mae"].mean()) if not age_impact.empty else float("nan")
        if age_group == "0-4 yr" and (positive_count >= max(1, num_seasons // 2) or delayed_count >= max(1, num_seasons // 2)):
            interpretation = "supports pediatric observation-aware discovery robustness under reduced-budget appendix"
        elif positive_count > 0 or delayed_count > 0:
            interpretation = "mixed season-dependent evidence"
        else:
            interpretation = "does not strengthen observation-aware discovery evidence"
        rows.append(
            {
                "age_group": age_group,
                "num_seasons": num_seasons,
                "recommended_model_mode": row["recommended_model_mode"],
                "constrained_discovery_recommended_count": int(row["constrained_discovery_recommended_count"]),
                "delayed_I_selected_count": delayed_count,
                "positive_observation_search_delta_count": positive_count,
                "mean_delta_rolling_mean_mae": mean_delta,
                "interpretation": interpretation,
            }
        )
    return pd.DataFrame.from_records(rows).sort_values("age_group").reset_index(drop=True)


def _safe_remove_temp(path: Path) -> bool:
    resolved = path.resolve()
    root = REPO_ROOT.resolve()
    if not str(resolved).startswith(str(root)):
        raise ValueError(f"Refusing to remove temp root outside repo: {resolved}")
    if ".codex_multiseason_tmp" not in resolved.parts:
        raise ValueError(f"Refusing to remove unexpected temp root: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
        return True
    return False


def run_multiseason(
    config: dict[str, Any],
    keep_temp_artifacts: bool = False,
    resume_temp_artifacts: bool = False,
) -> dict[str, Any]:
    _disable_plot_writes()
    start = time.perf_counter()
    data_config = config["data"]
    artifact_root = ensure_dir(_repo_path(config["artifacts"]["root_dir"]))
    temp_root = ensure_dir(_repo_path(config["artifacts"].get("temp_root", ".codex_multiseason_tmp/full")))
    raw_csv = resolve_data_path(REPO_ROOT, data_config["raw_csv"])
    seasons = _completed_seasons(config)
    age_groups = [str(value) for value in data_config.get("age_groups", [])]
    model_names = _model_names(config)
    fit_config = _fit_config(config)
    search_config = _search_config(config)
    horizons = [int(value) for value in config["evaluation"]["horizons"]]

    if temp_root.exists() and not resume_temp_artifacts:
        _safe_remove_temp(temp_root)
    ensure_dir(temp_root)

    frame = load_flu_surv_data(raw_csv)
    series_items = build_flu_series_frames(
        frame=frame,
        include_age_groups=bool(data_config.get("include_age_robustness", True)),
        age_groups=age_groups,
        seasons=seasons,
        season_mode=SEASON_MODE_SEPARATE,
    )
    logger.info(
        "Running compact multi-season robustness series=%d models=%d temp=%s",
        len(series_items),
        len(model_names),
        temp_root,
    )

    for series_index, item in enumerate(series_items):
        series_name = str(item["series_name"])
        series_frame = item["frame"]
        if bool(series_frame.empty):  # type: ignore[union-attr]
            logger.warning("Skipping empty multi-season series=%s", series_name)
            continue
        y = series_frame["WEEKLY RATE"].to_numpy(dtype=float)  # type: ignore[union-attr]
        split = make_chronological_split(len(y))
        series_root = ensure_dir(temp_root / _slugify(series_name))
        for position, model_name in enumerate(model_names):
            model_artifact_dir = series_root / model_name
            if resume_temp_artifacts and (model_artifact_dir / "metrics.json").exists():
                logger.info("Skipping existing temp metrics series=%s model=%s", series_name, model_name)
                continue
            logger.info("Series=%s model=%s", series_name, model_name)
            _run_one_model(
                model_name=model_name,
                series_name=series_name,
                y=y,
                split=split,
                fit_config=fit_config,
                search_config=search_config,
                horizons=horizons,
                artifact_dir=model_artifact_dir,
                seed=_model_seed(int(config["seed"]) + series_index * 1009, model_name, position),
                ensemble_members=None,
            )

    summary = collect_benchmark_model_summary(temp_root)
    if summary.empty:
        raise RuntimeError(f"No model metrics found under temporary root {temp_root}")

    recommendations = _season_level_recommendations(summary)
    model_summary = _ranked_model_summary(summary, temp_root)
    observation_maps = _observation_map_by_season(model_summary)
    observation_impact = _observation_search_impact(model_summary)
    modes = _recommendation_modes(recommendations, model_summary, observation_impact)
    key_findings = _key_findings(modes, observation_impact)

    model_summary.to_csv(artifact_root / "multiseason_model_summary.csv", index=False)
    recommendations.to_csv(artifact_root / "season_level_recommendations.csv", index=False)
    modes.to_csv(artifact_root / "multiseason_recommendation_modes.csv", index=False)
    observation_maps.to_csv(artifact_root / "observation_map_by_season.csv", index=False)
    observation_impact.to_csv(artifact_root / "observation_search_impact_by_season.csv", index=False)
    key_findings.to_csv(artifact_root / "multiseason_key_findings.csv", index=False)

    temp_removed = False
    if not keep_temp_artifacts:
        temp_removed = _safe_remove_temp(temp_root)

    run_summary = {
        "data_source": "CDC RESP-NET dataset kvib-3txy transformed to FluSurv-NET hospitalization rates",
        "data_attribution": "Centers for Disease Control and Prevention, RESP-NET/FluSurv-NET",
        "raw_csv": repo_relative_path(raw_csv, REPO_ROOT),
        "completed_seasons_path": repo_relative_path(_repo_path(data_config["completed_seasons_path"]), REPO_ROOT),
        "excluded_seasons": {
            "2020-21": "incomplete required age-group coverage",
            "2025-26": "preliminary current surveillance season",
        },
        "seasons": seasons,
        "age_groups": ["Overall", *age_groups] if bool(data_config.get("include_age_robustness", True)) else ["Overall"],
        "models": model_names,
        "evaluation_design": "each completed season is evaluated as its own within-season trajectory",
        "not_transfer_forecasting": True,
        "reduced_budget": True,
        "fitting": {
            "n_restarts": int(config["fitting"]["n_restarts"]),
            "rolling_n_restarts": int(config["fitting"]["rolling_n_restarts"]),
            "maxiter": int(config["fitting"]["maxiter"]),
        },
        "discovery": {
            "beam_width": int(config["discovery"]["beam_width"]),
            "max_rounds": int(config["discovery"]["max_rounds"]),
            "exhaustive_max_candidates": config["discovery"].get("exhaustive_max_candidates"),
            "allow_truncated_exhaustive": bool(config["discovery"].get("allow_truncated_exhaustive", False)),
        },
        "horizons": horizons,
        "series_count": int(model_summary["series_name"].nunique()),
        "model_rows": int(len(model_summary)),
        "artifact_root": repo_relative_path(artifact_root, REPO_ROOT),
        "temporary_artifact_root": repo_relative_path(temp_root, REPO_ROOT),
        "temporary_artifacts_removed": bool(temp_removed),
        "elapsed_seconds": round(time.perf_counter() - start, 3),
    }
    write_json(run_summary, artifact_root / "run_summary.json")
    return run_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a compact FluSurv-NET multi-season robustness appendix.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--keep-temp-artifacts", action="store_true")
    parser.add_argument("--resume-temp-artifacts", action="store_true")
    args = parser.parse_args()
    configure_logging(args.log_level)
    config = _load_config(REPO_ROOT / args.config)
    summary = run_multiseason(
        config,
        keep_temp_artifacts=bool(args.keep_temp_artifacts),
        resume_temp_artifacts=bool(args.resume_temp_artifacts),
    )
    logger.info(
        "Compact multi-season robustness complete artifact_root=%s rows=%d elapsed=%.1fs",
        summary["artifact_root"],
        summary["model_rows"],
        summary["elapsed_seconds"],
    )


if __name__ == "__main__":
    main()
