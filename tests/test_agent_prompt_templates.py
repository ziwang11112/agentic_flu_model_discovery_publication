from __future__ import annotations

import pytest

from src.selection.agent_prompt_templates import (
    build_agent_task_prompt,
    example_initial_context,
)
from src.selection.agent_tasks import AgentTaskType


def test_generated_prompt_excludes_forbidden_field_names() -> None:
    prompt = build_agent_task_prompt(
        AgentTaskType.INITIAL_CANDIDATE_PROPOSAL,
        context=example_initial_context(),
    )
    text = prompt.combined_text().lower()

    for forbidden in [
        "test_mae",
        "test_rank",
        "test_winner",
        "best_test_model",
        "post_selection_test_mae",
    ]:
        assert forbidden not in text


def test_generated_prompt_includes_allowlist_and_json_only_instruction() -> None:
    prompt = build_agent_task_prompt(
        AgentTaskType.INITIAL_CANDIDATE_PROPOSAL,
        context=example_initial_context(),
    )
    text = prompt.combined_text()

    assert "Return JSON only" in text
    assert "arima_auto_small" in text
    assert "constrained_structure_discovery" in text
    assert "candidate_allowlist" in text


def test_prompt_builder_rejects_forbidden_context_field() -> None:
    context = example_initial_context()
    context["test_mae"] = 0.12

    with pytest.raises(ValueError, match="forbidden"):
        build_agent_task_prompt(AgentTaskType.INITIAL_CANDIDATE_PROPOSAL, context=context)


def test_prompt_builder_rejects_forbidden_context_value() -> None:
    context = example_initial_context()
    context["available_metrics"] = ["rolling_mean_mae", "test_mae"]

    with pytest.raises(ValueError, match="forbidden"):
        build_agent_task_prompt(AgentTaskType.INITIAL_CANDIDATE_PROPOSAL, context=context)
