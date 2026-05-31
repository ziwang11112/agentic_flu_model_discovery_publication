from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from src.selection.iterative_agent_loop import run_iterative_agent_loop
from src.selection.verifier import verify_candidate
from src.selection.schema import CandidateSpec


def _local_tmp(name: str) -> Path:
    path = Path.cwd() / ".pytest_tmp" / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _minimal_config(tmp_path: Path) -> dict:
    return {
        "seed": 42,
        "artifacts": {"root_dir": str(tmp_path / "artifacts_iterative_agent_loop_compact")},
        "data": {"frozen_artifact_root": "artifacts_discovery_ablation"},
        "api": {"enabled": False, "use_mock": True},
        "policy": {"epsilon": 0.01},
        "series": ["0-4 yr"],
        "rounds": 2,
        "candidates_per_round": 2,
        "budgets": [2, 4],
        "replay_only": True,
        "proposers": ["mock_api_iterative", "deterministic_seed_proposer"],
        "candidate_allowlist": [
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
    }


def test_no_leakage_audit_passes_for_all_rounds() -> None:
    status = run_iterative_agent_loop(_minimal_config(_local_tmp("iterative_loop_no_leakage")), Path.cwd())
    root = Path(status["artifact_root"])
    if not root.is_absolute():
        root = Path.cwd() / root
    audit = pd.read_csv(root / "iterative_agent_prompt_audit.csv")
    replay = pd.read_csv(root / "iterative_agent_replay_by_round.csv")

    assert audit["safe_prompt_passed"].all()
    assert audit["safe_feedback_passed"].all()
    assert audit["safe_selection_passed"].all()
    assert set(replay["test_metric_usage"]) == {"posthoc_descriptive_only"}
    assert set(replay["selection_metric_source"]) == {"rolling_mean_mae"}


def test_out_of_allowlist_candidate_rejected() -> None:
    result = verify_candidate(
        CandidateSpec(
            candidate_id="bad",
            family="forecasting_baseline",
            model_name="invented_model",
            observation_label="direct",
            delay_label="0",
        )
    )

    assert not result.valid
    assert "model_name_not_allowed_for_family" in result.reasons


def test_missing_api_credentials_skip_gracefully(monkeypatch) -> None:
    for name in ("SELECTION_API_KEY", "SELECTION_API_ENDPOINT", "SELECTION_API_MODEL", "OPENAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    config = _minimal_config(_local_tmp("iterative_loop_api_skip"))
    config["api"] = {"enabled": True, "use_mock": False}
    config["proposers"] = ["real_api_iterative"]

    status = run_iterative_agent_loop(config, Path.cwd())

    assert status["external_api_used"] is False
    assert "api_credentials_missing" in status["api_statuses"] or "api_disabled" in status["api_statuses"]
