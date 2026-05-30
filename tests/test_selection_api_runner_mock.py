import json
import shutil
from pathlib import Path

import pandas as pd

from src.selection.api_proposer import MockStructuredAPIClient, StructuredAPIProposer
from src.selection.api_runner import run_api_proposal_evaluation


def _local_root(name: str) -> Path:
    root = Path(".pytest_tmp") / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _config(output_root: Path, *, enabled: bool = True) -> dict:
    return {
        "data": {"frozen_artifact_root": "artifacts_discovery_ablation"},
        "artifacts": {"root_dir": str(output_root / "api_outputs")},
        "policy": {"epsilon": 0.02, "max_candidates": 6},
        "api": {
            "enabled": enabled,
            "max_candidates": 6,
            "context_rows": 4,
            "objective": "mock proposal evaluation",
            "api_key_env": "MISSING_SELECTION_API_KEY_FOR_TEST",
            "endpoint_env": "MISSING_SELECTION_API_ENDPOINT_FOR_TEST",
            "model_env": "MISSING_SELECTION_API_MODEL_FOR_TEST",
        },
    }


def test_api_runner_mock_writes_verified_compact_outputs():
    response = json.dumps(
        {
            "candidates": [
                {
                    "candidate_id": "api_roll",
                    "family": "forecasting_baseline",
                    "model_name": "rolling_mean_4wk",
                    "observation_label": None,
                    "delay_label": None,
                    "rationale": "allowed simple baseline",
                    "expected_failure_mode": "underfit",
                },
                {
                    "candidate_id": "api_roll",
                    "family": "forecasting_baseline",
                    "model_name": "last_observed",
                    "observation_label": None,
                    "delay_label": None,
                    "rationale": "duplicate id should be caught",
                    "expected_failure_mode": "flat forecast",
                },
                {
                    "candidate_id": "api_struct",
                    "family": "structured_search",
                    "model_name": "constrained_structure_discovery",
                    "observation_label": "delayed_I",
                    "delay_label": "1",
                    "rationale": "allowed structured candidate",
                    "expected_failure_mode": "overfit",
                },
            ]
        }
    )
    output_root = _local_root("api_runner_mock")
    proposer = StructuredAPIProposer(client=MockStructuredAPIClient(response))

    status = run_api_proposal_evaluation(_config(output_root), Path.cwd(), proposer=proposer)
    out = output_root / "api_outputs"

    assert status["api_run_status"] == "completed"
    assert status["external_api_used"] is False
    assert (out / "api_proposal_candidates.csv").exists()
    assert (out / "api_proposal_evaluation.csv").exists()
    assert (out / "api_proposal_status.json").exists()

    candidates = pd.read_csv(out / "api_proposal_candidates.csv")
    metrics = pd.read_csv(out / "api_proposal_evaluation.csv")

    assert len(candidates) == 3
    assert candidates["duplicate"].astype(bool).sum() == 1
    assert metrics.loc[0, "proposal_count"] == 3
    assert metrics.loc[0, "valid_proposal_count"] == 2
    assert 0.0 <= metrics.loc[0, "top_epsilon_useful_rate"] <= 1.0


def test_api_runner_skips_without_credentials(monkeypatch):
    for name in [
        "MISSING_SELECTION_API_KEY_FOR_TEST",
        "MISSING_SELECTION_API_ENDPOINT_FOR_TEST",
        "MISSING_SELECTION_API_MODEL_FOR_TEST",
        "OPENAI_API_KEY",
    ]:
        monkeypatch.delenv(name, raising=False)
    output_root = _local_root("api_runner_skip")

    status = run_api_proposal_evaluation(_config(output_root, enabled=True), Path.cwd())
    out = output_root / "api_outputs"

    assert status["api_run_status"] == "skipped"
    assert status["skip_reason"] == "api_credentials_missing"
    assert status["external_api_used"] is False
    assert (out / "api_proposal_candidates.csv").exists()
    assert pd.read_csv(out / "api_proposal_candidates.csv").empty
