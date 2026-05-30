from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.selection.api_execution import run_api_candidate_execution


def _test_config(tmp_path: Path) -> dict:
    return {
        "seed": 42,
        "artifacts": {"root_dir": str(tmp_path / "artifacts_api_candidate_execution_compact")},
        "api": {"enabled": False, "use_mock": True},
        "policy": {"epsilon": 0.01},
        "budgets": [3, 5],
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
        "synthetic": {
            "enabled": True,
            "tasks": ["direct_signal", "lagged_signal_2"],
            "seeds": [1, 2],
            "noise_levels": [0.0],
            "proposers": [
                "mock_api_proposer",
                "deterministic_seed_proposer",
                "random_candidate_proposer",
                "failure_guided_proposer",
                "no_observation_label_baseline",
                "exhaustive_oracle",
            ],
        },
        "realdata": {
            "enabled": True,
            "frozen_artifact_root": "artifacts_discovery_ablation",
            "series": ["Overall", "0-4 yr"],
            "proposers": [
                "mock_api_proposer",
                "deterministic_seed_proposer",
                "random_candidate_proposer",
                "oracle_full_candidate_ranking",
            ],
        },
    }


def test_mock_api_candidate_execution_writes_compact_outputs(tmp_path: Path):
    status = run_api_candidate_execution(_test_config(tmp_path), Path.cwd())
    root = Path(status["artifact_root"])
    if not root.is_absolute():
        root = Path.cwd() / root

    expected = {
        "api_candidate_execution_summary.csv",
        "api_candidate_execution_by_budget.csv",
        "api_candidate_execution_synthetic_recovery.csv",
        "api_candidate_execution_realdata_replay.csv",
        "api_candidate_prompt_audit.csv",
        "api_candidate_execution_status.json",
        "api_candidate_execution_traces.jsonl",
    }
    assert expected == {path.name for path in root.iterdir()}
    assert status["external_api_used"] is False
    assert status["safe_prompt_passed"] is True

    summary = pd.read_csv(root / "api_candidate_execution_summary.csv")
    synthetic = pd.read_csv(root / "api_candidate_execution_synthetic_recovery.csv")
    realdata = pd.read_csv(root / "api_candidate_execution_realdata_replay.csv")
    audit = pd.read_csv(root / "api_candidate_prompt_audit.csv")

    assert not summary.empty
    assert not synthetic.empty
    assert not realdata.empty
    assert audit["safe_prompt_passed"].all()
    assert {"mock_api_proposer", "random_candidate_proposer"}.issubset(set(summary["proposer_type"]))


def test_synthetic_execution_produces_recovery_metrics(tmp_path: Path):
    status = run_api_candidate_execution(_test_config(tmp_path), Path.cwd())
    root = Path(status["artifact_root"])
    if not root.is_absolute():
        root = Path.cwd() / root
    synthetic = pd.read_csv(root / "api_candidate_execution_synthetic_recovery.csv")

    assert {
        "observation_label_recovered",
        "delay_label_recovered",
        "candidate_family_recovered",
        "best_rolling_error_after_k",
        "budget_to_recover_true_label",
        "budget_to_top_epsilon",
    }.issubset(synthetic.columns)
    rates = synthetic.groupby("proposer_type")["observation_label_recovered"].mean()
    assert rates["mock_api_proposer"] >= rates["random_candidate_proposer"]


def test_status_json_records_no_external_api(tmp_path: Path):
    status = run_api_candidate_execution(_test_config(tmp_path), Path.cwd())
    root = Path(status["artifact_root"])
    if not root.is_absolute():
        root = Path.cwd() / root
    saved = json.loads((root / "api_candidate_execution_status.json").read_text(encoding="utf-8"))

    assert saved["external_api_used"] is False
    assert saved["api_enabled"] is False
    assert saved["api_use_mock"] is True
