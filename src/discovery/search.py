from __future__ import annotations

from dataclasses import dataclass
import hashlib
import logging
from pathlib import Path
import time
from typing import Any

import numpy as np
import pandas as pd

from src.discovery.candidates import enumerate_valid_structure_specs
from src.discovery.model import DiscoveryCompartmentModel, DiscoveryRegularizationConfig
from src.discovery.rules import StructureSpec, generate_neighbors, observation_family, validate_structure
from src.evaluation.metrics import point_metrics
from src.evaluation.rolling import (
    rolling_blocked_metric_summary,
    mean_rolling_metric,
    rolling_error_stability,
    rolling_metrics_by_horizon,
    rolling_origin_forecasts,
)
from src.models.base import FitConfig
from src.utils.io import ensure_dir, write_json, write_yaml

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchConfig:
    beam_width: int = 5
    max_rounds: int = 20
    patience: int = 5
    rolling_horizons: tuple[int, ...] = (1, 2, 4)
    multi_split_blocks: int = 3
    score_param_weight: float = 0.01
    score_compartment_weight: float = 0.02
    score_fractional_weight: float = 0.015
    score_observation_weight: float = 0.005
    score_delay_weight: float = 0.005
    score_h_observation_weight: float = 0.005
    score_recurrence_weight: float = 0.01
    score_stability_weight: float = 0.2
    score_multi_split_std_weight: float = 0.5
    raw_l2_weight: float = 5.0e-4
    seasonality_l2_weight: float = 5.0e-3
    rho_l2_weight: float = 2.0e-3
    init_l2_weight: float = 2.0e-3
    fractional_alpha_weight: float = 2.0e-3
    use_age_prior: bool = True
    age_prior_simple_bonus: float = 0.01
    age_prior_recurrence_bonus: float = 0.01
    age_prior_fractional_bonus: float = 0.005
    random_candidate_budget: int | None = None
    random_repeats: int = 1
    exhaustive_max_candidates: int | None = None
    allow_truncated_exhaustive: bool = False


@dataclass
class SearchOutcome:
    best_spec: StructureSpec
    leaderboard: pd.DataFrame
    best_record: dict[str, Any]


def _stable_seed(seed: int, key: str) -> int:
    digest = hashlib.sha256(f"{seed}:{key}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False) % (2**32 - 1)


def discovery_regularization_config(search_config: SearchConfig) -> DiscoveryRegularizationConfig:
    """Build discovery fit regularization from search config."""
    return DiscoveryRegularizationConfig(
        raw_l2_weight=search_config.raw_l2_weight,
        seasonality_l2_weight=search_config.seasonality_l2_weight,
        rho_l2_weight=search_config.rho_l2_weight,
        init_l2_weight=search_config.init_l2_weight,
        fractional_alpha_weight=search_config.fractional_alpha_weight,
    )


def discovery_complexity_penalty(
    spec: StructureSpec,
    param_count: int,
    num_compartments: int,
    search_config: SearchConfig,
) -> float:
    """Structured validation-time penalty for flexible discovered models."""
    components = discovery_complexity_penalty_components(spec, param_count, num_compartments, search_config)
    return float(components["complexity_penalty"])


def discovery_complexity_penalty_components(
    spec: StructureSpec,
    param_count: int,
    num_compartments: int,
    search_config: SearchConfig,
) -> dict[str, float]:
    """Return named complexity-penalty components for one candidate."""
    param_penalty = search_config.score_param_weight * param_count
    compartment_penalty = search_config.score_compartment_weight * num_compartments
    fractional_penalty = search_config.score_fractional_weight if spec.fractional else 0.0
    observation_penalty = search_config.score_observation_weight if spec.observation_map == "I+H" else 0.0
    h_observation_penalty = search_config.score_h_observation_weight if spec.observation_map == "H" else 0.0
    delay_penalty = search_config.score_delay_weight * float(spec.delay_weeks) if spec.observation_map == "delayed_I" else 0.0
    recurrence_penalty = search_config.score_recurrence_weight if spec.structure_name == "SEIRS" else 0.0
    penalty = param_penalty + compartment_penalty + fractional_penalty + observation_penalty + h_observation_penalty + delay_penalty + recurrence_penalty
    return {
        "param_penalty": float(param_penalty),
        "compartment_penalty": float(compartment_penalty),
        "fractional_penalty": float(fractional_penalty),
        "observation_penalty": float(observation_penalty),
        "h_observation_penalty": float(h_observation_penalty),
        "delay_penalty": float(delay_penalty),
        "recurrence_penalty": float(recurrence_penalty),
        "complexity_penalty": float(penalty),
    }


def age_structure_prior_penalty(
    series_name: str,
    spec: StructureSpec,
    search_config: SearchConfig,
) -> float:
    """Age-group-specific score adjustment for discovery candidates."""
    if not search_config.use_age_prior:
        return 0.0
    age_key = series_name.split(" / ", 1)[1] if " / " in series_name else series_name

    simple_bonus = search_config.age_prior_simple_bonus
    recurrence_bonus = search_config.age_prior_recurrence_bonus
    fractional_bonus = search_config.age_prior_fractional_bonus

    if age_key in {"Overall", "18-49 yr", "50-64 yr"}:
        penalty = 0.0
        if spec.structure_name == "SIR":
            penalty -= simple_bonus
        elif spec.structure_name == "SEIR":
            penalty -= 0.5 * simple_bonus
        if spec.structure_name == "SEIRS":
            penalty += recurrence_bonus
        if spec.fractional:
            penalty += fractional_bonus
        return float(penalty)

    if age_key == "0-4 yr":
        penalty = 0.0
        if spec.structure_name == "SEIRS":
            penalty -= recurrence_bonus
        elif spec.structure_name == "SEIR":
            penalty -= 0.5 * recurrence_bonus
        if spec.fractional:
            penalty += 0.5 * fractional_bonus
        return float(penalty)

    if age_key == "5-17 yr":
        penalty = 0.0
        if spec.structure_name == "SEIRS":
            penalty -= recurrence_bonus
        if spec.fractional:
            penalty -= 0.5 * fractional_bonus
        return float(penalty)

    if age_key == ">= 65 yr":
        penalty = 0.0
        if spec.structure_name == "SEIRS":
            penalty -= 0.5 * recurrence_bonus
        if spec.fractional:
            penalty -= 0.5 * fractional_bonus
        if spec.structure_name == "SIR":
            penalty += 0.5 * simple_bonus
        return float(penalty)

    return 0.0


def _score_policy_metadata(policy: str) -> dict[str, Any]:
    if policy == "stability_aware":
        return {
            "score_formula": "multi_split_mean_mae + multi_split_penalty + stability_penalty + complexity_penalty + age_prior_penalty",
            "score_used_val_mae": False,
            "score_used_multi_split": True,
            "score_used_stability": True,
            "score_used_complexity": True,
            "score_used_age_prior": True,
        }
    if policy == "validation_only":
        return {
            "score_formula": "val_mae",
            "score_used_val_mae": True,
            "score_used_multi_split": False,
            "score_used_stability": False,
            "score_used_complexity": False,
            "score_used_age_prior": False,
        }
    if policy == "no_stability":
        return {
            "score_formula": "multi_split_mean_mae + multi_split_penalty + complexity_penalty + age_prior_penalty",
            "score_used_val_mae": False,
            "score_used_multi_split": True,
            "score_used_stability": False,
            "score_used_complexity": True,
            "score_used_age_prior": True,
        }
    raise ValueError(f"Unsupported discovery score policy: {policy}")


def _score_candidate(
    *,
    policy: str,
    val_mae: float,
    multi_split_mean_mae: float,
    multi_split_penalty: float,
    stability_penalty: float,
    complexity_penalty: float,
    age_prior_penalty: float,
) -> float:
    if policy == "stability_aware":
        return float(multi_split_mean_mae + multi_split_penalty + stability_penalty + complexity_penalty + age_prior_penalty)
    if policy == "validation_only":
        return float(val_mae)
    if policy == "no_stability":
        return float(multi_split_mean_mae + multi_split_penalty + complexity_penalty + age_prior_penalty)
    raise ValueError(f"Unsupported discovery score policy: {policy}")


def evaluate_structure_candidate(
    *,
    series_name: str,
    spec: StructureSpec,
    y_train: np.ndarray,
    y_val: np.ndarray,
    fit_config: FitConfig,
    search_config: SearchConfig,
    regularization_config: DiscoveryRegularizationConfig,
    seed: int,
    score_policy: str = "stability_aware",
    round_idx: int | None = None,
    repeat_idx: int | None = None,
) -> dict[str, Any]:
    """Fit and score one valid discovery candidate using train/validation data only."""
    validation = validate_structure(spec)
    if not validation.valid:
        raise ValueError(f"Invalid discovery structure {spec.spec_key}: {validation.reason}")

    seed_key = f"{repeat_idx}:{spec.spec_key}" if repeat_idx is not None else spec.spec_key
    candidate_rng = np.random.default_rng(_stable_seed(seed, seed_key))
    combined_series = np.concatenate([y_train, y_val])
    model_factory = lambda: DiscoveryCompartmentModel(spec, fit_config, regularization_config)

    model = model_factory()
    fit_result = model.fit(y_train, candidate_rng)
    rollout = model.simulate(fit_result.raw_params, len(combined_series))
    train_pred = rollout.predictions[: len(y_train)]
    val_pred = rollout.predictions[len(y_train) :]
    train_metrics = point_metrics(y_train, train_pred)
    val_metrics = point_metrics(y_val, val_pred)

    rolling_frame = rolling_origin_forecasts(
        model_factory=model_factory,
        y=combined_series,
        horizons=list(search_config.rolling_horizons),
        seed=_stable_seed(seed + 991, seed_key),
        initial_train_size=len(y_train),
    )
    rolling_metrics = rolling_metrics_by_horizon(rolling_frame)
    rolling_mean_mae = mean_rolling_metric(rolling_frame, "mae")
    rolling_mean_rmse = mean_rolling_metric(rolling_frame, "rmse")
    blocked_summary = rolling_blocked_metric_summary(
        rolling_frame,
        metric_name="mae",
        num_blocks=search_config.multi_split_blocks,
    )
    multi_split_mean_mae = blocked_summary["mean"]
    multi_split_std_mae = blocked_summary["std"]
    rolling_error_std = rolling_error_stability(rolling_frame)
    multi_split_penalty = search_config.score_multi_split_std_weight * multi_split_std_mae
    stability_penalty = search_config.score_stability_weight * rolling_error_std
    complexity_components = discovery_complexity_penalty_components(
        spec=spec,
        param_count=fit_result.param_count,
        num_compartments=len(model.compartment_names),
        search_config=search_config,
    )
    complexity_penalty = float(complexity_components["complexity_penalty"])
    age_prior_penalty = age_structure_prior_penalty(series_name, spec, search_config)
    score = _score_candidate(
        policy=score_policy,
        val_mae=val_metrics["mae"],
        multi_split_mean_mae=multi_split_mean_mae,
        multi_split_penalty=multi_split_penalty,
        stability_penalty=stability_penalty,
        complexity_penalty=complexity_penalty,
        age_prior_penalty=age_prior_penalty,
    )
    score_metadata = _score_policy_metadata(score_policy)

    record = {
        "round": round_idx,
        "repeat": repeat_idx,
        "record_key": f"{repeat_idx}:{spec.spec_key}" if repeat_idx is not None else spec.spec_key,
        "spec_key": spec.spec_key,
        "structure_name": spec.structure_name,
        "fractional": spec.fractional,
        "observation_map": spec.observation_map,
        "delay_weeks": int(spec.delay_weeks),
        "observation_family": observation_family(spec),
        "num_free_params": fit_result.param_count,
        "num_compartments": len(model.compartment_names),
        "train_objective": fit_result.objective,
        "train_mae": train_metrics["mae"],
        "train_rmse": train_metrics["rmse"],
        "val_mae": val_metrics["mae"],
        "val_rmse": val_metrics["rmse"],
        "val_smape": val_metrics["smape"],
        "rolling_val_mean_mae": rolling_mean_mae,
        "rolling_val_mean_rmse": rolling_mean_rmse,
        "multi_split_blocks": search_config.multi_split_blocks,
        "multi_split_val_mean_mae": multi_split_mean_mae,
        "multi_split_val_std_mae": multi_split_std_mae,
        "multi_split_penalty": multi_split_penalty,
        "rolling_val_error_std": rolling_error_std,
        "rolling_val_metrics": rolling_metrics,
        "stability_penalty": stability_penalty,
        "complexity_penalty": complexity_penalty,
        "complexity_penalty_params": complexity_components["param_penalty"],
        "complexity_penalty_compartments": complexity_components["compartment_penalty"],
        "complexity_penalty_fractional": complexity_components["fractional_penalty"],
        "complexity_penalty_observation": complexity_components["observation_penalty"],
        "complexity_penalty_h_observation": complexity_components["h_observation_penalty"],
        "complexity_penalty_delay": complexity_components["delay_penalty"],
        "complexity_penalty_recurrence": complexity_components["recurrence_penalty"],
        "age_prior_penalty": age_prior_penalty,
        "score_policy": score_policy,
        "score_formula": score_metadata["score_formula"],
        "score": score,
        "score_used_val_mae": score_metadata["score_used_val_mae"],
        "score_used_multi_split": score_metadata["score_used_multi_split"],
        "score_used_stability": score_metadata["score_used_stability"],
        "score_used_complexity": score_metadata["score_used_complexity"],
        "score_used_age_prior": score_metadata["score_used_age_prior"],
        "params": fit_result.params,
    }
    return record


def _search_outcome_from_records(
    *,
    records: list[dict[str, Any]],
    artifact_dir: Path,
    search_metadata: dict[str, Any] | None = None,
) -> SearchOutcome:
    if not records:
        raise RuntimeError("Structure discovery did not evaluate any valid candidate.")

    leaderboard = pd.DataFrame.from_records(records).sort_values(
        ["score", "spec_key", "record_key"],
        ascending=[True, True, True],
    ).reset_index(drop=True)
    best_record = _json_safe(dict(leaderboard.iloc[0].to_dict()))
    if search_metadata:
        best_record["search_metadata"] = search_metadata
        for key, value in search_metadata.items():
            if key not in leaderboard.columns:
                leaderboard[key] = value

    best_spec = StructureSpec(
        structure_name=str(best_record["structure_name"]),
        fractional=bool(best_record["fractional"]),
        observation_map=str(best_record["observation_map"]),
        delay_weeks=int(best_record.get("delay_weeks", 0)),
    )

    ensure_dir(artifact_dir)
    leaderboard.to_csv(artifact_dir / "leaderboard.csv", index=False)
    write_json(best_record, artifact_dir / "best_model_spec.json")
    write_yaml(best_record, artifact_dir / "best_model_spec.yaml")
    logger.info("Search finished best_spec=%s leaderboard=%s", best_spec.spec_key, artifact_dir / "leaderboard.csv")
    return SearchOutcome(best_spec=best_spec, leaderboard=leaderboard, best_record=best_record)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    try:
        if not isinstance(value, (dict, list, tuple, np.ndarray)) and pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _evaluate_candidate_list(
    *,
    series_name: str,
    candidates: list[StructureSpec],
    y_train: np.ndarray,
    y_val: np.ndarray,
    fit_config: FitConfig,
    search_config: SearchConfig,
    artifact_dir: Path,
    seed: int,
    score_policy: str,
    search_name: str,
    search_metadata: dict[str, Any] | None = None,
) -> SearchOutcome:
    ensure_dir(artifact_dir)
    regularization_config = discovery_regularization_config(search_config)
    records: list[dict[str, Any]] = []
    metadata = dict(search_metadata or {})
    metadata.setdefault("search_name", search_name)
    metadata.setdefault("score_policy", score_policy)
    metadata.setdefault("candidate_count", int(len(candidates)))

    for index, spec in enumerate(candidates, start=1):
        logger.info("Search candidate start search=%s index=%d spec=%s", search_name, index, spec.spec_key)
        record = evaluate_structure_candidate(
            series_name=series_name,
            spec=spec,
            y_train=y_train,
            y_val=y_val,
            fit_config=fit_config,
            search_config=search_config,
            regularization_config=regularization_config,
            seed=seed,
            score_policy=score_policy,
            round_idx=1,
        )
        records.append(record)

    return _search_outcome_from_records(records=records, artifact_dir=artifact_dir, search_metadata=metadata)


def run_exhaustive_structure_search(
    series_name: str,
    y_train: np.ndarray,
    y_val: np.ndarray,
    fit_config: FitConfig,
    search_config: SearchConfig,
    artifact_dir: Path,
    seed: int,
    score_policy: str = "stability_aware",
    search_name: str = "exhaustive_structure_discovery",
) -> SearchOutcome:
    """Evaluate every valid structure spec, with optional guardrails."""
    universe = enumerate_valid_structure_specs()
    max_candidates = search_config.exhaustive_max_candidates
    truncated = False
    if max_candidates is not None and len(universe) > max_candidates:
        if not search_config.allow_truncated_exhaustive:
            raise ValueError(
                f"Exhaustive discovery candidate universe has {len(universe)} candidates, "
                f"exceeding exhaustive_max_candidates={max_candidates}."
            )
        universe = universe[: int(max_candidates)]
        truncated = True

    return _evaluate_candidate_list(
        series_name=series_name,
        candidates=universe,
        y_train=y_train,
        y_val=y_val,
        fit_config=fit_config,
        search_config=search_config,
        artifact_dir=artifact_dir,
        seed=seed,
        score_policy=score_policy,
        search_name=search_name,
        search_metadata={
            "candidate_universe_size": int(len(enumerate_valid_structure_specs())),
            "candidate_budget_actual": int(len(universe)),
            "exhaustive_max_candidates": max_candidates,
            "allow_truncated_exhaustive": bool(search_config.allow_truncated_exhaustive),
            "truncated": bool(truncated),
        },
    )


def run_validation_only_structure_selection(
    series_name: str,
    y_train: np.ndarray,
    y_val: np.ndarray,
    fit_config: FitConfig,
    search_config: SearchConfig,
    artifact_dir: Path,
    seed: int,
) -> SearchOutcome:
    """Select from the full grammar using validation MAE only."""
    return run_exhaustive_structure_search(
        series_name=series_name,
        y_train=y_train,
        y_val=y_val,
        fit_config=fit_config,
        search_config=search_config,
        artifact_dir=artifact_dir,
        seed=seed,
        score_policy="validation_only",
        search_name="validation_only_structure_selection",
    )


def run_no_observation_search(
    series_name: str,
    y_train: np.ndarray,
    y_val: np.ndarray,
    fit_config: FitConfig,
    search_config: SearchConfig,
    artifact_dir: Path,
    seed: int,
) -> SearchOutcome:
    """Select from specs restricted to direct infectious observation."""
    candidates = [spec for spec in enumerate_valid_structure_specs() if spec.observation_map == "I"]
    return _evaluate_candidate_list(
        series_name=series_name,
        candidates=candidates,
        y_train=y_train,
        y_val=y_val,
        fit_config=fit_config,
        search_config=search_config,
        artifact_dir=artifact_dir,
        seed=seed,
        score_policy="stability_aware",
        search_name="no_observation_search_discovery",
        search_metadata={
            "candidate_universe_size": int(len(enumerate_valid_structure_specs())),
            "candidate_budget_actual": int(len(candidates)),
            "observation_map_filter": "I",
        },
    )


def run_no_stability_structure_search(
    series_name: str,
    y_train: np.ndarray,
    y_val: np.ndarray,
    fit_config: FitConfig,
    search_config: SearchConfig,
    artifact_dir: Path,
    seed: int,
) -> SearchOutcome:
    """Select from the full grammar while excluding the rolling stability penalty from score."""
    return run_exhaustive_structure_search(
        series_name=series_name,
        y_train=y_train,
        y_val=y_val,
        fit_config=fit_config,
        search_config=search_config,
        artifact_dir=artifact_dir,
        seed=seed,
        score_policy="no_stability",
        search_name="no_stability_discovery",
    )


def run_random_structure_search(
    series_name: str,
    y_train: np.ndarray,
    y_val: np.ndarray,
    fit_config: FitConfig,
    search_config: SearchConfig,
    artifact_dir: Path,
    seed: int,
) -> SearchOutcome:
    """Evaluate a deterministic random sample of valid structure specs."""
    ensure_dir(artifact_dir)
    universe = enumerate_valid_structure_specs()
    requested_budget = search_config.random_candidate_budget
    fallback_budget = min(len(universe), search_config.beam_width * search_config.max_rounds * 3)
    budget = fallback_budget if requested_budget is None else min(int(requested_budget), len(universe))
    repeats = max(1, int(search_config.random_repeats))
    regularization_config = discovery_regularization_config(search_config)
    records: list[dict[str, Any]] = []

    for repeat_idx in range(repeats):
        rng = np.random.default_rng(_stable_seed(seed, f"random_structure_discovery:{repeat_idx}"))
        indices = rng.permutation(len(universe))[:budget]
        for draw_idx, candidate_index in enumerate(indices, start=1):
            spec = universe[int(candidate_index)]
            logger.info(
                "Random search candidate start repeat=%d draw=%d spec=%s",
                repeat_idx,
                draw_idx,
                spec.spec_key,
            )
            record = evaluate_structure_candidate(
                series_name=series_name,
                spec=spec,
                y_train=y_train,
                y_val=y_val,
                fit_config=fit_config,
                search_config=search_config,
                regularization_config=regularization_config,
                seed=seed,
                score_policy="stability_aware",
                round_idx=draw_idx,
                repeat_idx=repeat_idx,
            )
            record["random_draw_index"] = int(draw_idx)
            records.append(record)

    metadata = {
        "search_name": "random_structure_discovery",
        "candidate_budget_requested": requested_budget,
        "candidate_budget_actual": int(budget),
        "candidate_universe_size": int(len(universe)),
        "random_repeats": int(repeats),
        "random_seed": int(seed),
    }
    for record in records:
        record.update(metadata)

    return _search_outcome_from_records(records=records, artifact_dir=artifact_dir, search_metadata=metadata)


def run_structure_search(
    series_name: str,
    y_train: np.ndarray,
    y_val: np.ndarray,
    fit_config: FitConfig,
    search_config: SearchConfig,
    artifact_dir: Path,
    seed: int,
) -> SearchOutcome:
    """Run the constrained propose-fit-verify-refine loop."""
    ensure_dir(artifact_dir)
    start_spec = StructureSpec("SEIR", fractional=False, observation_map="I", delay_weeks=0)
    beam = [start_spec]
    expanded: set[str] = set()
    evaluated_records: dict[str, dict[str, Any]] = {}
    regularization_config = discovery_regularization_config(search_config)

    best_score = float("inf")
    best_record: dict[str, Any] | None = None
    stagnant_rounds = 0
    logger.info(
        "Search start series=%s train_obs=%d val_obs=%d beam_width=%d max_rounds=%d",
        series_name,
        len(y_train),
        len(y_val),
        search_config.beam_width,
        search_config.max_rounds,
    )

    for round_idx in range(1, search_config.max_rounds + 1):
        round_start_best = best_score
        candidate_specs: list[StructureSpec] = []
        for spec in beam:
            if spec.spec_key not in expanded:
                candidate_specs.append(spec)
                candidate_specs.extend(generate_neighbors(spec))

        unique_candidates = {candidate.spec_key: candidate for candidate in candidate_specs}.values()
        any_new = False
        logger.info(
            "Search round=%d beam=%s candidate_count=%d",
            round_idx,
            [spec.spec_key for spec in beam],
            len(list({candidate.spec_key: candidate for candidate in candidate_specs}.values())),
        )

        for spec in unique_candidates:
            if spec.spec_key in evaluated_records:
                continue
            validation = validate_structure(spec)
            if not validation.valid:
                continue

            any_new = True
            candidate_start = time.perf_counter()
            logger.info("Search candidate start round=%d spec=%s", round_idx, spec.spec_key)
            record = evaluate_structure_candidate(
                series_name=series_name,
                spec=spec,
                y_train=y_train,
                y_val=y_val,
                fit_config=fit_config,
                search_config=search_config,
                regularization_config=regularization_config,
                seed=seed,
                score_policy="stability_aware",
                round_idx=round_idx,
            )
            evaluated_records[spec.spec_key] = record
            logger.info(
                "Search candidate done round=%d spec=%s score=%.6f multi_split_mae=%.6f multi_split_std=%.6f rolling_mae=%.6f stability=%.6f val_mae=%.6f age_prior=%.4f elapsed=%.1fs",
                round_idx,
                spec.spec_key,
                record["score"],
                record["multi_split_val_mean_mae"],
                record["multi_split_val_std_mae"],
                record["rolling_val_mean_mae"],
                record["rolling_val_error_std"],
                record["val_mae"],
                record["age_prior_penalty"],
                time.perf_counter() - candidate_start,
            )

            if record["score"] < best_score:
                best_score = record["score"]
                best_record = record

        for spec in beam:
            expanded.add(spec.spec_key)

        if not any_new:
            stagnant_rounds += 1
        elif best_score < round_start_best - 1.0e-12:
            stagnant_rounds = 0
        else:
            stagnant_rounds += 1

        leaderboard = pd.DataFrame(evaluated_records.values()).sort_values("score", ascending=True).reset_index(drop=True)
        if leaderboard.empty:
            raise RuntimeError("Structure discovery did not evaluate any valid candidate.")

        beam = [
            StructureSpec(
                structure_name=row["structure_name"],
                fractional=bool(row["fractional"]),
                observation_map=row["observation_map"],
                delay_weeks=int(row.get("delay_weeks", 0)),
            )
            for _, row in leaderboard.head(search_config.beam_width).iterrows()
        ]
        logger.info(
            "Search round=%d complete best_score=%.6f next_beam=%s",
            round_idx,
            best_score,
            [spec.spec_key for spec in beam],
        )

        if stagnant_rounds >= search_config.patience:
            logger.info("Search early stop round=%d stagnant_rounds=%d", round_idx, stagnant_rounds)
            break

    if best_record is None:
        raise RuntimeError("Structure discovery failed to find a best candidate.")

    leaderboard = pd.DataFrame(evaluated_records.values()).sort_values("score", ascending=True).reset_index(drop=True)
    best_spec = StructureSpec(
        structure_name=str(best_record["structure_name"]),
        fractional=bool(best_record["fractional"]),
        observation_map=str(best_record["observation_map"]),
        delay_weeks=int(best_record.get("delay_weeks", 0)),
    )

    leaderboard.to_csv(artifact_dir / "leaderboard.csv", index=False)
    write_json(best_record, artifact_dir / "best_model_spec.json")
    write_yaml(best_record, artifact_dir / "best_model_spec.yaml")
    logger.info("Search finished best_spec=%s leaderboard=%s", best_spec.spec_key, artifact_dir / "leaderboard.csv")
    return SearchOutcome(best_spec=best_spec, leaderboard=leaderboard, best_record=best_record)
