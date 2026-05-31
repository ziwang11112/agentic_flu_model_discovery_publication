from __future__ import annotations

from src.selection.iterative_agent_feedback import (
    feedback_contains_forbidden_fields,
    make_round_feedback,
    prompt_audit_row,
)


def test_round_feedback_excludes_forbidden_test_fields() -> None:
    feedback = make_round_feedback(
        series_name="0-4 yr",
        proposer_type="mock_api_iterative",
        round_idx=1,
        accepted_records=[
            {
                "candidate_id": "c1",
                "model_name": "constrained_structure_discovery",
                "family": "structured_search",
                "observation_label": "lagged",
                "rolling_score": 0.1,
            }
        ],
        rejected_records=[],
        duplicate_candidates=[],
        remaining_budget=6,
        top_epsilon_hit=True,
    ).to_context()

    assert not feedback_contains_forbidden_fields(feedback)
    assert "previous_round" in feedback
    assert feedback["previous_round"]["non_final_evidence_summary"]["top_epsilon_hit_so_far"] is True


def test_feedback_detects_injected_test_metric() -> None:
    feedback = {"previous_round": {"accepted_candidates": [{"test_mae": 0.1}]}}

    assert feedback_contains_forbidden_fields(feedback)


def test_prompt_audit_flags_prompt_and_feedback_leakage() -> None:
    row = prompt_audit_row(
        series_name="0-4 yr",
        proposer_type="mock_api_iterative",
        round_idx=2,
        prompt_payload={"context": {"test_rank": 1}},
        feedback_context={"previous_round": {"post_selection_test_mae": 0.1}},
        model_allowlist=["last_observed"],
    )

    assert row["prompt_contains_test_rank"] is True
    assert row["feedback_contains_test_metric"] is True
    assert row["safe_prompt_passed"] is False
    assert row["safe_feedback_passed"] is False
