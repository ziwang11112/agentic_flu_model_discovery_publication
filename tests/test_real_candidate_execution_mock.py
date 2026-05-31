from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

from src.selection.real_candidate_execution import (
    REAL_EXECUTION_ALLOWLIST,
    _safe_remove_temp,
    _validate_execution_allowlist,
    run_real_candidate_execution,
)


def _local_tmp(name: str) -> Path:
    path = Path.cwd() / ".pytest_tmp" / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _config(base_path: Path) -> dict:
    return {
        "seed": 42,
        "artifacts": {"root_dir": str(base_path / "artifacts_real_candidate_execution_compact")},
        "data": {
            "raw_csv": "FluSurveillance_Custom_Download_Data.csv",
            "frozen_artifact_root": "artifacts_discovery_ablation",
            "include_age_robustness": True,
            "season_mode": "pooled",
            "seasons": [],
            "age_groups": ["0-4 yr", "18-49 yr", "Overall", ">= 65 yr"],
        },
        "api": {"enabled": False, "use_mock": True},
        "policy": {"epsilon": 0.01},
        "budgets": [3, 5],
        "replay_candidate_allowlist": [
            "last_observed",
            "rolling_mean_4wk",
            "arima_auto_small",
            "deterministic_seir",
            "delayed_observation_seir",
            "constrained_structure_discovery",
            "no_observation_search_discovery",
            "validation_only_structure_selection",
            "random_structure_discovery",
            "exhaustive_structure_discovery",
        ],
        "execution_candidate_allowlist": list(REAL_EXECUTION_ALLOWLIST),
        "repeated_replay": {
            "series": ["Overall"],
            "repeats": 2,
            "proposers": [
                "deterministic_seed_proposer",
                "random_candidate_proposer",
                "failure_guided_proposer",
                "oracle_full_candidate_ranking",
                "real_api_proposer",
            ],
        },
        "actual_execution": {
            "enabled": False,
            "temp_root": str(Path.cwd() / ".codex_real_candidate_execution_tmp" / "unit"),
            "series": [],
            "proposers": [],
        },
        "fitting": {
            "n_restarts": 1,
            "rolling_n_restarts": 0,
            "maxiter": 5,
            "negative_penalty": 10000.0,
            "mass_penalty": 10000.0,
            "prior_weight": 0.001,
            "laplace_draws": 2,
            "uncertainty_method": "bootstrap",
            "bootstrap_draws": 2,
            "bootstrap_n_restarts": 0,
            "calibrate_intervals": False,
            "interval_calibration_method": "conformal",
            "calibration_draws": 2,
            "calibration_scale_min": 0.25,
            "calibration_scale_max": 1.25,
            "calibration_scale_grid_size": 5,
        },
        "uncertainty": {"conformal": {"enabled": False}},
        "evaluation": {"horizons": [1]},
        "discovery": {
            "beam_width": 1,
            "max_rounds": 1,
            "patience": 1,
            "rolling_horizons": [1],
            "multi_split_blocks": 2,
            "random_candidate_budget": 2,
            "random_repeats": 1,
            "exhaustive_max_candidates": 4,
            "allow_truncated_exhaustive": True,
            "score_param_weight": 0.01,
            "score_compartment_weight": 0.02,
            "score_fractional_weight": 0.015,
            "score_observation_weight": 0.005,
            "score_delay_weight": 0.005,
            "score_h_observation_weight": 0.005,
            "score_recurrence_weight": 0.01,
            "score_stability_weight": 0.2,
            "score_multi_split_std_weight": 0.5,
            "raw_l2_weight": 0.0005,
            "seasonality_l2_weight": 0.005,
            "rho_l2_weight": 0.002,
            "init_l2_weight": 0.002,
            "fractional_alpha_weight": 0.002,
            "use_age_prior": True,
            "age_prior_simple_bonus": 0.01,
            "age_prior_recurrence_bonus": 0.01,
            "age_prior_fractional_bonus": 0.005,
        },
    }


def test_replay_skip_missing_api_and_writes_compact_outputs():
    base_path = _local_tmp("real_candidate_execution")
    status = run_real_candidate_execution(_config(base_path), Path.cwd())
    root = Path(status["artifact_root"])
    if not root.is_absolute():
        root = Path.cwd() / root

    assert status["external_api_used"] is False
    assert "api_disabled" in status["api_statuses"]
    assert status["safe_audit_passed"] is True
    assert status["unique_model_executions"] == 0
    expected = {
        "real_api_replay_repeated_summary.csv",
        "real_api_replay_repeated_by_run.csv",
        "bounded_real_execution_summary.csv",
        "bounded_real_execution_by_series_budget.csv",
        "selected_models_by_proposer_budget.csv",
        "no_leakage_audit.csv",
        "run_summary.json",
    }
    assert expected == {path.name for path in root.iterdir()}
    assert not any(path.name in {"metrics.json", "forecast_trace.csv", "rolling_origin_forecasts.csv"} for path in root.iterdir())

    audit = pd.read_csv(root / "no_leakage_audit.csv")
    replay = pd.read_csv(root / "real_api_replay_repeated_by_run.csv")
    saved = json.loads((root / "run_summary.json").read_text(encoding="utf-8"))
    assert audit["safe_prompt_passed"].all()
    assert audit["safe_selection_passed"].all()
    assert set(replay["test_metric_usage"]) == {"posthoc_descriptive_only"}
    assert saved["selection_metric_source"] == "rolling_mean_mae"


def test_execution_allowlist_is_bounded():
    assert set(REAL_EXECUTION_ALLOWLIST) == {
        "last_observed",
        "rolling_mean_4wk",
        "arima_auto_small",
        "deterministic_seir",
        "delayed_observation_seir",
        "constrained_structure_discovery",
        "no_observation_search_discovery",
        "validation_only_structure_selection",
    }
    _validate_execution_allowlist(list(REAL_EXECUTION_ALLOWLIST))
    try:
        _validate_execution_allowlist(["random_structure_discovery"])
    except ValueError as exc:
        assert "unsupported" in str(exc)
    else:
        raise AssertionError("unsupported execution model was accepted")


def test_safe_temp_prune_requires_codex_prefix():
    good = Path.cwd() / ".codex_real_candidate_execution_tmp" / "unit_test"
    good.mkdir(parents=True, exist_ok=True)
    assert _safe_remove_temp(good, Path.cwd()) is True

    bad = Path.cwd() / ".pytest_tmp" / "not_stage7_tmp"
    bad.mkdir(parents=True, exist_ok=True)
    try:
        _safe_remove_temp(bad, Path.cwd())
    except ValueError as exc:
        assert "outside repo" in str(exc) or "unexpected temporary path" in str(exc)
    else:
        raise AssertionError("unsafe temp path was removed")
