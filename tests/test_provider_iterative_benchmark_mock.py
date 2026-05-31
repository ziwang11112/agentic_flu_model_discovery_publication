from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

from src.selection.agent_prompt_templates import example_initial_output
from src.selection.provider_iterative_benchmark import run_provider_iterative_benchmark


def _local_tmp(name: str) -> Path:
    path = Path.cwd() / ".pytest_tmp" / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _config(base: Path) -> dict:
    return {
        "seed": 42,
        "artifacts": {"root_dir": str(base / "artifacts_provider_iterative_benchmark_compact")},
        "data": {"frozen_artifact_root": "artifacts_discovery_ablation"},
        "provider_settings": {
            "providers": [
                {"name": "mock_provider", "config": {"model_name": "mock-a", "response_payload": example_initial_output()}},
            ]
        },
        "allow_provider_skip": True,
        "require_min_real_providers": 1,
        "series": ["0-4 yr"],
        "repeats": 1,
        "rounds": 2,
        "candidates_per_round": 2,
        "budgets": [2, 4],
        "include_baseline_proposers": True,
        "policy": {"epsilon": 0.01},
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


def test_provider_iterative_benchmark_mock_outputs_are_compact() -> None:
    status = run_provider_iterative_benchmark(_config(_local_tmp("provider_iterative_mock")), Path.cwd())
    root = Path(status["artifact_root"])
    if not root.is_absolute():
        root = Path.cwd() / root

    expected = {
        "provider_status.csv",
        "provider_proposal_validity.csv",
        "provider_candidates.csv",
        "provider_by_round.csv",
        "provider_replay_by_budget.csv",
        "provider_stability_by_repeat.csv",
        "provider_prompt_audit.csv",
        "provider_claim_audit.csv",
        "provider_cost_latency.csv",
        "provider_union_execution_summary.csv",
        "provider_union_execution_by_budget.csv",
        "run_summary.json",
    }
    assert expected == {path.name for path in root.iterdir()}
    saved = json.loads((root / "run_summary.json").read_text(encoding="utf-8"))
    audit = pd.read_csv(root / "provider_prompt_audit.csv")
    provider_status = pd.read_csv(root / "provider_status.csv")
    validity = pd.read_csv(root / "provider_proposal_validity.csv")

    assert saved["safe_audit_passed"] is True
    assert saved["sufficient_real_providers_for_cross_provider_evidence"] is True
    assert audit["safe_prompt_passed"].all()
    assert audit["safe_feedback_passed"].all()
    assert provider_status["ran"].all()
    assert not validity.empty
