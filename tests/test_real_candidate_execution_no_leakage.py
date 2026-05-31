from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.selection.api_execution_prompts import (
    build_execution_user_payload,
    no_test_evidence_context,
    prompt_has_forbidden_test_context,
)
from src.selection.real_candidate_execution import _prompt_audit_row
from src.selection.schema import CandidateSpec
from src.selection.verifier import verify_candidate


def test_no_test_context_removes_forbidden_columns():
    summary = pd.DataFrame(
        [
            {
                "series_name": "Overall",
                "model_name": "last_observed",
                "model_family": "forecast_baseline",
                "rolling_mean_mae": 0.2,
                "test_mae": 0.1,
                "best_test_model": "last_observed",
                "recommended_model": "last_observed",
            }
        ]
    )

    context = no_test_evidence_context(summary, series_names=["Overall"], model_allowlist=["last_observed"])
    text = str(context).lower()

    assert context == [
        {
            "series_name": "Overall",
            "model_name": "last_observed",
            "model_family": "forecast_baseline",
            "rolling_mean_mae": 0.2,
        }
    ]
    assert "test_mae" not in text
    assert "best_test" not in text
    assert "recommended_model" not in text


def test_prompt_audit_catches_injected_test_metric():
    payload = build_execution_user_payload(
        series_name="Overall",
        evidence_context=[{"series_name": "Overall", "model_name": "last_observed", "test_mae": 0.1}],
        model_allowlist=["last_observed"],
        max_candidates=3,
        objective="rank candidates",
    )
    checks = prompt_has_forbidden_test_context(payload)
    audit = _prompt_audit_row(
        layer="unit",
        series_name="Overall",
        proposer_type="mock",
        repeat_idx=0,
        prompt_payload=payload,
        model_allowlist=["last_observed"],
    )

    assert checks["prompt_contains_test_metric"] is True
    assert audit["safe_prompt_passed"] is False


def test_out_of_allowlist_candidate_rejected():
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


def test_local_api_config_pattern_is_ignored():
    assert Path("configs/real_candidate_execution_api.local.yaml").match("configs/*.local.yaml")
