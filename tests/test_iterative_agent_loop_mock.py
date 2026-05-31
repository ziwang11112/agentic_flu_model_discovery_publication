from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

from src.selection.iterative_agent_loop import run_iterative_agent_loop


def _local_tmp(name: str) -> Path:
    path = Path.cwd() / ".pytest_tmp" / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _config(tmp_path: Path) -> dict:
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
        "proposers": [
            "mock_api_iterative",
            "mock_api_single_shot",
            "random_candidate_proposer",
            "deterministic_seed_proposer",
        ],
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


def test_mock_iterative_loop_writes_compact_outputs() -> None:
    status = run_iterative_agent_loop(_config(_local_tmp("iterative_loop_mock")), Path.cwd())
    root = Path(status["artifact_root"])
    if not root.is_absolute():
        root = Path.cwd() / root

    expected = {
        "iterative_agent_summary.csv",
        "iterative_agent_by_round.csv",
        "iterative_agent_candidates.csv",
        "iterative_agent_replay_by_round.csv",
        "iterative_agent_prompt_audit.csv",
        "iterative_agent_claim_audit.csv",
        "iterative_agent_traces.jsonl",
        "run_summary.json",
    }
    assert expected == {path.name for path in root.iterdir()}
    assert status["external_api_used"] is False
    assert status["safe_audit_passed"] is True

    summary = pd.read_csv(root / "iterative_agent_summary.csv")
    by_round = pd.read_csv(root / "iterative_agent_by_round.csv")
    audit = pd.read_csv(root / "iterative_agent_prompt_audit.csv")
    saved = json.loads((root / "run_summary.json").read_text(encoding="utf-8"))

    assert {"mock_api_iterative", "random_candidate_proposer"}.issubset(set(summary["proposer_type"]))
    assert by_round["round_idx"].max() == 2
    assert audit["safe_prompt_passed"].all()
    assert audit["safe_feedback_passed"].all()
    assert saved["replay_only"] is True


def test_round_two_contains_feedback_from_round_one() -> None:
    status = run_iterative_agent_loop(_config(_local_tmp("iterative_loop_feedback")), Path.cwd())
    root = Path(status["artifact_root"])
    if not root.is_absolute():
        root = Path.cwd() / root
    traces = [
        json.loads(line)
        for line in (root / "iterative_agent_traces.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    round_two = [row for row in traces if row["proposer_type"] == "mock_api_iterative" and row["round_idx"] == 2]
    assert round_two
    assert round_two[0]["accepted_models"]
