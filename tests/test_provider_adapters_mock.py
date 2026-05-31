from __future__ import annotations

import json
from io import BytesIO
import urllib.error
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
    _sanitize_http_error,
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
    assert captured["body"]["response_format"]["type"] == "json_schema"
    schema = captured["body"]["response_format"]["json_schema"]["schema"]
    assert "forbidden_extra_fields" not in json.dumps(schema)
    assert schema["additionalProperties"] is False


def test_deepseek_json_mode_response_parses(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(request, timeout):
        del timeout
        captured["body"] = json.loads(request.data.decode("utf-8"))
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
    assert captured["body"]["response_format"] == {"type": "json_object"}


def test_anthropic_tool_use_response_parses(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(request, timeout):
        del timeout
        captured["body"] = json.loads(request.data.decode("utf-8"))
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
    tool = captured["body"]["tools"][0]
    assert tool["strict"] is True
    assert "forbidden_extra_fields" not in json.dumps(tool["input_schema"])


def test_gemini_structured_response_parses(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(request, timeout):
        del timeout
        captured["body"] = json.loads(request.data.decode("utf-8"))
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
    response_format = captured["body"]["generationConfig"]["responseFormat"]
    assert response_format["text"]["mimeType"] == "application/json"
    assert "forbidden_extra_fields" not in json.dumps(response_format["text"]["schema"])
    delay_enum = response_format["text"]["schema"]["properties"]["candidates"]["items"]["properties"]["delay_label"]["enum"]
    assert "" not in delay_enum


def test_gemini_legacy_structured_response_fallback(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_urlopen(request, timeout):
        del timeout
        body = json.loads(request.data.decode("utf-8"))
        calls.append(body)
        if len(calls) == 1:
            raise urllib.error.HTTPError(request.full_url, 400, "bad schema envelope", hdrs=None, fp=None)
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
    assert "responseFormat" in calls[0]["generationConfig"]
    assert calls[1]["generationConfig"]["responseMimeType"] == "application/json"
    assert "additionalProperties" not in json.dumps(calls[1]["generationConfig"]["responseSchema"])


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


def test_http_error_sanitizer_redacts_account_and_credential_details() -> None:
    leaked = urllib.error.HTTPError(
        "https://example.test",
        403,
        "Forbidden",
        hdrs=None,
        fp=BytesIO(b'{"error":{"message":"Your API key was reported as leaked. Please rotate it."}}'),
    )
    assert _sanitize_http_error(leaked) == "HTTPError:403:credential_rejected"

    billing = urllib.error.HTTPError(
        "https://example.test",
        400,
        "Bad Request",
        hdrs=None,
        fp=BytesIO(b'{"error":{"message":"Your credit balance is too low to access this API."}}'),
    )
    assert _sanitize_http_error(billing) == "HTTPError:400:account_or_billing_unavailable"
