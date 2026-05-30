import json

import pandas as pd

from src.selection.api_proposer import (
    MockStructuredAPIClient,
    StructuredAPIProposer,
    parse_structured_candidate_response,
)
from src.selection.proposal_prompts import build_system_prompt, default_proposal_allowlist


def test_parse_structured_candidate_response_accepts_allowlisted_json():
    response = json.dumps(
        {
            "candidates": [
                {
                    "candidate_id": "c1",
                    "family": "forecasting_baseline",
                    "model_name": "rolling_mean_4wk",
                    "observation_label": None,
                    "delay_label": None,
                    "rationale": "simple stable comparator",
                    "expected_failure_mode": "underfits sharp changes",
                },
                {
                    "candidate_id": "c2",
                    "family": "structured_search",
                    "model_name": "constrained_structure_discovery",
                    "observation_label": "delayed_I",
                    "delay_label": "1",
                    "rationale": "checks observation-label search",
                    "expected_failure_mode": "overfits compact evidence",
                },
            ]
        }
    )

    parsed = parse_structured_candidate_response(response)

    assert len(parsed.candidates) == 2
    assert parsed.parse_errors == ()
    assert parsed.candidates[0].proposer_name == "api_structured"
    assert parsed.candidates[1].observation_label == "delayed_I"


def test_parse_structured_candidate_response_rejects_not_allowlisted_values():
    response = json.dumps(
        {
            "candidates": [
                {
                    "candidate_id": "bad",
                    "family": "forecasting_baseline",
                    "model_name": "new_unlisted_model",
                    "observation_label": None,
                    "delay_label": None,
                },
                {
                    "candidate_id": "bad2",
                    "family": "structured_search",
                    "model_name": "constrained_structure_discovery",
                    "observation_label": "unsupported_label",
                    "delay_label": "1",
                },
            ]
        }
    )

    parsed = parse_structured_candidate_response(response)

    assert parsed.candidates == ()
    assert "0:model_name_not_allowlisted" in parsed.parse_errors
    assert "1:observation_label_not_allowlisted" in parsed.parse_errors


def test_parse_structured_candidate_response_rejects_unknown_keys_and_invalid_json():
    with_unknown = json.dumps(
        {
            "candidates": [
                {
                    "candidate_id": "bad",
                    "family": "forecasting_baseline",
                    "model_name": "rolling_mean_4wk",
                    "new_code": "print('no')",
                }
            ]
        }
    )

    parsed = parse_structured_candidate_response(with_unknown)
    invalid = parse_structured_candidate_response("not json")

    assert parsed.candidates == ()
    assert parsed.parse_errors == ("0:unknown_keys:new_code",)
    assert invalid.candidates == ()
    assert invalid.parse_errors[0].startswith("invalid_json")


def test_structured_api_proposer_uses_mock_json_client():
    response = json.dumps(
        {
            "candidates": [
                {
                    "candidate_id": "mock1",
                    "family": "mechanistic_baseline",
                    "model_name": "deterministic_seir",
                    "observation_label": None,
                    "delay_label": None,
                    "rationale": "manual comparator",
                    "expected_failure_mode": "missed observation lag",
                }
            ]
        }
    )
    summary = pd.read_csv("artifacts_discovery_ablation/benchmark_model_summary.csv")
    proposer = StructuredAPIProposer(client=MockStructuredAPIClient(response))

    parsed = proposer.propose(
        model_summary=summary,
        max_candidates=3,
        objective="mock objective",
        api_config={"context_rows": 4},
    )

    assert len(parsed.candidates) == 1
    assert parsed.candidates[0].model_name == "deterministic_seir"


def test_prompt_contains_allowlist_and_json_only_instruction():
    prompt = build_system_prompt(default_proposal_allowlist())

    assert "Return JSON only" in prompt
    assert "rolling_mean_4wk" in prompt
    assert "constrained_structure_discovery" in prompt
