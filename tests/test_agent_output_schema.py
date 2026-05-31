from __future__ import annotations

import pytest

from src.selection.agent_output_schema import AgentOutputValidationError, validate_agent_output
from src.selection.agent_prompt_templates import example_claim_output, example_initial_output


def test_valid_initial_candidate_output_validates() -> None:
    candidates = validate_agent_output(example_initial_output())

    assert len(candidates) == 3
    assert candidates[0].model_name == "constrained_structure_discovery"


def test_unknown_model_name_rejected() -> None:
    payload = example_initial_output()
    payload["candidates"][0]["model_name"] = "invented_model"

    with pytest.raises(AgentOutputValidationError, match="outside allowlist"):
        validate_agent_output(payload)


def test_executable_code_field_rejected() -> None:
    payload = example_initial_output()
    payload["candidates"][0]["model_code"] = "def fit(): pass"

    with pytest.raises(AgentOutputValidationError, match="Executable"):
        validate_agent_output(payload)


def test_required_candidate_fields_enforced() -> None:
    payload = example_initial_output()
    del payload["candidates"][0]["delay_label"]

    with pytest.raises(AgentOutputValidationError, match="missing required"):
        validate_agent_output(payload)


def test_family_model_incompatibility_rejected() -> None:
    payload = example_initial_output()
    payload["candidates"][0]["family"] = "forecasting_baseline"

    with pytest.raises(AgentOutputValidationError, match="outside allowlist"):
        validate_agent_output(payload)


def test_safe_claim_boundary_output_validates() -> None:
    payload = example_claim_output()
    validated = validate_agent_output(payload)

    assert validated["task_type"] == "claim_boundary_summary"


def test_claim_boundary_positive_sota_claim_rejected() -> None:
    payload = example_claim_output()
    payload["safe_summary"] = "The system achieves SOTA forecasting performance."

    with pytest.raises(AgentOutputValidationError, match="Unsafe"):
        validate_agent_output(payload)
