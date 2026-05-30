from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.selection.api_execution import run_api_candidate_execution
from src.selection.executor_bridge import DEFAULT_EXECUTION_ALLOWLIST, prompt_audit_record
from src.selection.schema import CandidateSpec, EvidencePacket
from src.selection.verifier import verify_candidate, verify_evidence


def test_prompt_audit_detects_test_metric_leakage():
    audit = prompt_audit_record(
        series_name="Overall",
        proposer_type="mock_api_proposer",
        prompt_payload={
            "series_name": "Overall",
            "candidate_allowlist": list(DEFAULT_EXECUTION_ALLOWLIST),
            "selection_metric": "rolling_validation_mae",
            "test_mae": 0.123,
        },
        model_allowlist=list(DEFAULT_EXECUTION_ALLOWLIST),
    )

    assert audit["prompt_contains_test_metric"] is True
    assert audit["safe_prompt_passed"] is False


def test_out_of_allowlist_candidate_rejected():
    result = verify_candidate(
        CandidateSpec(
            candidate_id="bad-model",
            family="forecasting_baseline",
            model_name="invented_forecaster",
            observation_label="direct",
            delay_label="0",
        )
    )

    assert not result.valid
    assert "model_name_not_allowed_for_family" in result.reasons


def test_selection_evidence_rejects_test_metric():
    evidence = EvidencePacket(
        candidate_id="leaky",
        model_name="last_observed",
        family="forecasting_baseline",
        series_name="Overall",
        selection_metrics={"test_mae": 0.1},
        rolling_mean_mae=0.2,
    )

    result = verify_evidence(evidence)
    assert not result.valid
    assert "test_metric_in_selection_evidence" in result.reasons


def test_realdata_replay_marks_test_metrics_posthoc_only(tmp_path: Path):
    config = {
        "seed": 42,
        "artifacts": {"root_dir": str(tmp_path / "artifacts")},
        "api": {"enabled": False, "use_mock": True},
        "policy": {"epsilon": 0.01},
        "budgets": [3],
        "candidate_allowlist": list(DEFAULT_EXECUTION_ALLOWLIST),
        "synthetic": {"enabled": False, "tasks": [], "seeds": [], "noise_levels": []},
        "realdata": {
            "enabled": True,
            "frozen_artifact_root": "artifacts_discovery_ablation",
            "series": ["Overall"],
            "proposers": ["mock_api_proposer", "random_candidate_proposer"],
        },
    }
    status = run_api_candidate_execution(config, Path.cwd())
    root = Path(status["artifact_root"])
    if not root.is_absolute():
        root = Path.cwd() / root
    replay = pd.read_csv(root / "api_candidate_execution_realdata_replay.csv")
    audit = pd.read_csv(root / "api_candidate_prompt_audit.csv")

    assert set(replay["evidence_mode"]) == {"frozen_replay"}
    assert set(replay["selection_metric_source"]) == {"rolling_mean_mae"}
    assert set(replay["test_metric_usage"]) == {"posthoc_descriptive_only"}
    assert "post_selection_test_mae" in replay.columns
    assert audit["safe_prompt_passed"].all()
