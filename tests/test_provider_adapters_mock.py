from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pytest

from src.selection.agent_output_schema import agent_output_schema
from src.selection.agent_prompt_templates import example_initial_output
from src.selection.agent_tasks import AgentTaskType
from src.selection.proposal_prompts import proposal_allowlist_from_config
from src.selection.provider_adapters import (
    AnthropicAdapter,
    DeepSeekAdapter,
    GeminiAdapter,
    MockProviderAdapter,
    OpenAIChatAdapter,
)


@dataclass
class _FakeHTTPResponse:
    payload: dict[str, Any]
    headers: dict[str, str] | None = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def _allowlist():
    return proposal_allowlist_from_config(
        {
            "families": ["forecasting_baseline", "mechanistic_baseline", "structured_search", "ablation"],
            "model_names": [
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
            "observation_labels": ["direct", "lagged", "mixture", "proxy", "not_applicable", "I", "delayed_I"],
        }
    )


def test_mock_provider_parses_valid_candidates() -> None:
    adapter = MockProviderAdapter(response_payload=example_initial_output())
    response = adapter.generate_candidates(
        system_prompt="Return JSON only.",
        task_payload={"user_prompt": "task"},
        output_schema=agent_output_schema(AgentTaskType.INITIAL_CANDIDATE_PROPOSAL),
        provider_config={},
        allowlist=_allowlist(),
    )

    assert response.schema_parse_success
    assert len(response.candidate_specs) == 3


def test_openai_gpt5_payload_uses_max_completion_tokens(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(request, timeout):
        del timeout
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _FakeHTTPResponse({"choices": [{"message": {"content": json.dumps(example_initial_output())}}]}, {"x-request-id": "req"})

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5-mini")
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    response = OpenAIChatAdapter().generate_candidates(
        system_prompt="system",
        task_payload={"user_prompt": "user"},
        output_schema=agent_output_schema(AgentTaskType.INITIAL_CANDIDATE_PROPOSAL),
        provider_config={},
        allowlist=_allowlist(),
    )

    assert response.schema_parse_success
    assert "max_completion_tokens" in captured["body"]
    assert "temperature" not in captured["body"]


def test_deepseek_json_mode_response_parses(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        del request, timeout
        return _FakeHTTPResponse({"choices": [{"message": {"content": json.dumps(example_initial_output())}}]})

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-test")
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    response = DeepSeekAdapter().generate_candidates(
        system_prompt="system",
        task_payload={"user_prompt": "user"},
        output_schema=agent_output_schema(AgentTaskType.INITIAL_CANDIDATE_PROPOSAL),
        provider_config={},
        allowlist=_allowlist(),
    )

    assert response.schema_parse_success


def test_anthropic_tool_use_response_parses(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        del request, timeout
        return _FakeHTTPResponse({"content": [{"type": "tool_use", "input": example_initial_output()}]})

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-test")
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    response = AnthropicAdapter().generate_candidates(
        system_prompt="system",
        task_payload={"user_prompt": "user"},
        output_schema=agent_output_schema(AgentTaskType.INITIAL_CANDIDATE_PROPOSAL),
        provider_config={},
        allowlist=_allowlist(),
    )

    assert response.schema_parse_success


def test_gemini_structured_response_parses(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        del request, timeout
        return _FakeHTTPResponse(
            {"candidates": [{"content": {"parts": [{"text": json.dumps(example_initial_output())}]}}]}
        )

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test")
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    response = GeminiAdapter().generate_candidates(
        system_prompt="system",
        task_payload={"user_prompt": "user"},
        output_schema=agent_output_schema(AgentTaskType.INITIAL_CANDIDATE_PROPOSAL),
        provider_config={},
        allowlist=_allowlist(),
    )

    assert response.schema_parse_success


def test_malformed_json_and_out_of_allowlist_rejected() -> None:
    bad_json = MockProviderAdapter(response_payload={})
    response = bad_json.generate_candidates(
        system_prompt="system",
        task_payload={"user_prompt": "user"},
        output_schema=agent_output_schema(AgentTaskType.INITIAL_CANDIDATE_PROPOSAL),
        provider_config={"response_payload": {"candidates": "not-a-list"}},
        allowlist=_allowlist(),
    )
    assert not response.schema_parse_success

    payload = example_initial_output()
    payload["candidates"][0]["model_name"] = "invented_model"
    response = MockProviderAdapter(response_payload=payload).generate_candidates(
        system_prompt="system",
        task_payload={"user_prompt": "user"},
        output_schema=agent_output_schema(AgentTaskType.INITIAL_CANDIDATE_PROPOSAL),
        provider_config={},
        allowlist=_allowlist(),
    )
    assert not response.schema_parse_success
    assert "outside allowlist" in response.parse_error
