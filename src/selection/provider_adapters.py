from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol

from src.selection.agent_output_schema import AgentOutputValidationError, validate_agent_output
from src.selection.proposal_prompts import ProposalAllowlist
from src.selection.schema import CandidateSpec


def _extract_json(text: str) -> Any:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    return json.loads(stripped)


def _token_estimate(text: str) -> int:
    return max(1, int(len(text) / 4))


@dataclass(frozen=True)
class ProviderResponse:
    provider_name: str
    model_name: str
    raw_status: str
    parsed_json: dict[str, Any] | None = None
    candidate_specs: tuple[CandidateSpec, ...] = ()
    parse_error: str = ""
    latency_seconds: float = 0.0
    estimated_input_tokens: int | None = None
    estimated_output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    request_id: str | None = None

    @property
    def schema_parse_success(self) -> bool:
        return self.raw_status == "completed" and not self.parse_error and self.parsed_json is not None


class ProviderAdapter(Protocol):
    provider_name: str

    def available(self, provider_config: dict[str, Any]) -> tuple[bool, str]:
        ...

    def generate_candidates(
        self,
        *,
        system_prompt: str,
        task_payload: dict[str, Any],
        output_schema: dict[str, Any],
        provider_config: dict[str, Any],
        allowlist: ProposalAllowlist,
    ) -> ProviderResponse:
        ...


@dataclass(frozen=True)
class BaseProviderAdapter:
    provider_name: str
    api_key_env: str
    model_env: str
    base_url_env: str
    default_base_url: str
    timeout_seconds: int = 60

    def _settings(self, provider_config: dict[str, Any]) -> tuple[str, str, str] | None:
        api_key = os.getenv(str(provider_config.get("api_key_env", self.api_key_env)))
        model = os.getenv(str(provider_config.get("model_env", self.model_env)))
        base_url = os.getenv(str(provider_config.get("base_url_env", self.base_url_env))) or str(
            provider_config.get("base_url", self.default_base_url)
        )
        if not api_key or not model or not base_url:
            return None
        return api_key, model, base_url

    def available(self, provider_config: dict[str, Any]) -> tuple[bool, str]:
        settings = self._settings(provider_config)
        if settings is None:
            missing = []
            if not os.getenv(str(provider_config.get("api_key_env", self.api_key_env))):
                missing.append(self.api_key_env)
            if not os.getenv(str(provider_config.get("model_env", self.model_env))):
                missing.append(self.model_env)
            return False, "missing_env:" + ",".join(missing)
        return True, ""

    def _parse_payload(
        self,
        *,
        text: str,
        model_name: str,
        start_time: float,
        system_prompt: str,
        user_prompt: str,
        allowlist: ProposalAllowlist,
        request_id: str | None = None,
    ) -> ProviderResponse:
        latency = time.perf_counter() - start_time
        try:
            parsed = _extract_json(text)
            candidates = validate_agent_output(parsed, allowlist=allowlist)
            if not isinstance(candidates, tuple):
                raise AgentOutputValidationError("provider response did not contain candidate records")
            return ProviderResponse(
                provider_name=self.provider_name,
                model_name=model_name,
                raw_status="completed",
                parsed_json=dict(parsed),
                candidate_specs=candidates,
                latency_seconds=latency,
                estimated_input_tokens=_token_estimate(system_prompt + "\n" + user_prompt),
                estimated_output_tokens=_token_estimate(text),
                request_id=request_id,
            )
        except (json.JSONDecodeError, TypeError, AgentOutputValidationError, ValueError) as exc:
            return ProviderResponse(
                provider_name=self.provider_name,
                model_name=model_name,
                raw_status="parse_failed",
                parse_error=f"{exc.__class__.__name__}:{str(exc)[:180]}",
                latency_seconds=latency,
                estimated_input_tokens=_token_estimate(system_prompt + "\n" + user_prompt),
                estimated_output_tokens=_token_estimate(text),
                request_id=request_id,
            )


@dataclass(frozen=True)
class OpenAIChatAdapter(BaseProviderAdapter):
    provider_name: str = "openai_gpt"
    api_key_env: str = "OPENAI_API_KEY"
    model_env: str = "OPENAI_MODEL"
    base_url_env: str = "OPENAI_BASE_URL"
    default_base_url: str = "https://api.openai.com/v1/chat/completions"

    def generate_candidates(
        self,
        *,
        system_prompt: str,
        task_payload: dict[str, Any],
        output_schema: dict[str, Any],
        provider_config: dict[str, Any],
        allowlist: ProposalAllowlist,
    ) -> ProviderResponse:
        del output_schema
        settings = self._settings(provider_config)
        if settings is None:
            return ProviderResponse(self.provider_name, "", "skipped", parse_error="credentials_or_model_missing")
        api_key, model, endpoint = settings
        user_prompt = str(task_payload.get("user_prompt", json.dumps(task_payload, sort_keys=True)))
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "response_format": {"type": "json_object"},
        }
        if not model.startswith("gpt-5"):
            body["temperature"] = float(provider_config.get("temperature", 0.0))
        token_key = "max_completion_tokens" if model.startswith("gpt-5") else "max_tokens"
        body[token_key] = int(provider_config.get("max_tokens", provider_config.get("max_completion_tokens", 1400)))
        start = time.perf_counter()
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=int(provider_config.get("timeout_seconds", self.timeout_seconds))) as response:
                payload = json.loads(response.read().decode("utf-8"))
                request_id = (getattr(response, "headers", None) or {}).get("x-request-id")
            text = str(payload["choices"][0]["message"]["content"])
        except (urllib.error.URLError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            return ProviderResponse(self.provider_name, model, "request_failed", parse_error=exc.__class__.__name__, latency_seconds=time.perf_counter() - start)
        return self._parse_payload(
            text=text,
            model_name=model,
            start_time=start,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            allowlist=allowlist,
            request_id=request_id,
        )


@dataclass(frozen=True)
class DeepSeekAdapter(OpenAIChatAdapter):
    provider_name: str = "deepseek"
    api_key_env: str = "DEEPSEEK_API_KEY"
    model_env: str = "DEEPSEEK_MODEL"
    base_url_env: str = "DEEPSEEK_BASE_URL"
    default_base_url: str = "https://api.deepseek.com/chat/completions"


@dataclass(frozen=True)
class AnthropicAdapter(BaseProviderAdapter):
    provider_name: str = "anthropic_claude"
    api_key_env: str = "ANTHROPIC_API_KEY"
    model_env: str = "ANTHROPIC_MODEL"
    base_url_env: str = "ANTHROPIC_BASE_URL"
    default_base_url: str = "https://api.anthropic.com/v1/messages"

    def generate_candidates(
        self,
        *,
        system_prompt: str,
        task_payload: dict[str, Any],
        output_schema: dict[str, Any],
        provider_config: dict[str, Any],
        allowlist: ProposalAllowlist,
    ) -> ProviderResponse:
        settings = self._settings(provider_config)
        if settings is None:
            return ProviderResponse(self.provider_name, "", "skipped", parse_error="credentials_or_model_missing")
        api_key, model, endpoint = settings
        user_prompt = str(task_payload.get("user_prompt", json.dumps(task_payload, sort_keys=True)))
        body = {
            "model": model,
            "max_tokens": int(provider_config.get("max_tokens", 1400)),
            "temperature": float(provider_config.get("temperature", 0.0)),
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "tools": [
                {
                    "name": "submit_candidates",
                    "description": "Submit the JSON candidate proposal payload.",
                    "input_schema": output_schema,
                }
            ],
            "tool_choice": {"type": "tool", "name": "submit_candidates"},
        }
        start = time.perf_counter()
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "x-api-key": api_key,
                "anthropic-version": str(provider_config.get("anthropic_version", "2023-06-01")),
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=int(provider_config.get("timeout_seconds", self.timeout_seconds))) as response:
                payload = json.loads(response.read().decode("utf-8"))
                request_id = (getattr(response, "headers", None) or {}).get("request-id")
            content = payload.get("content", [])
            tool_inputs = [item.get("input") for item in content if isinstance(item, dict) and item.get("type") == "tool_use"]
            if tool_inputs:
                text = json.dumps(tool_inputs[0])
            else:
                text_items = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"]
                text = "\n".join(str(item) for item in text_items)
        except (urllib.error.URLError, KeyError, TypeError, json.JSONDecodeError) as exc:
            return ProviderResponse(self.provider_name, model, "request_failed", parse_error=exc.__class__.__name__, latency_seconds=time.perf_counter() - start)
        return self._parse_payload(
            text=text,
            model_name=model,
            start_time=start,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            allowlist=allowlist,
            request_id=request_id,
        )


@dataclass(frozen=True)
class GeminiAdapter(BaseProviderAdapter):
    provider_name: str = "google_gemini"
    api_key_env: str = "GEMINI_API_KEY"
    model_env: str = "GEMINI_MODEL"
    base_url_env: str = "GEMINI_BASE_URL"
    default_base_url: str = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def generate_candidates(
        self,
        *,
        system_prompt: str,
        task_payload: dict[str, Any],
        output_schema: dict[str, Any],
        provider_config: dict[str, Any],
        allowlist: ProposalAllowlist,
    ) -> ProviderResponse:
        settings = self._settings(provider_config)
        if settings is None:
            return ProviderResponse(self.provider_name, "", "skipped", parse_error="credentials_or_model_missing")
        api_key, model, endpoint_template = settings
        user_prompt = str(task_payload.get("user_prompt", json.dumps(task_payload, sort_keys=True)))
        endpoint = endpoint_template.format(model=urllib.parse.quote(model, safe=""))
        separator = "&" if "?" in endpoint else "?"
        endpoint = f"{endpoint}{separator}key={urllib.parse.quote(api_key)}"
        body = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": float(provider_config.get("temperature", 0.0)),
                "responseMimeType": "application/json",
                "responseSchema": output_schema,
                "maxOutputTokens": int(provider_config.get("max_tokens", 1400)),
            },
        }
        start = time.perf_counter()
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=int(provider_config.get("timeout_seconds", self.timeout_seconds))) as response:
                payload = json.loads(response.read().decode("utf-8"))
                request_id = (getattr(response, "headers", None) or {}).get("x-request-id")
            text = str(payload["candidates"][0]["content"]["parts"][0]["text"])
        except (urllib.error.URLError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            return ProviderResponse(self.provider_name, model, "request_failed", parse_error=exc.__class__.__name__, latency_seconds=time.perf_counter() - start)
        return self._parse_payload(
            text=text,
            model_name=model,
            start_time=start,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            allowlist=allowlist,
            request_id=request_id,
        )


@dataclass(frozen=True)
class MockProviderAdapter(BaseProviderAdapter):
    provider_name: str = "mock_provider"
    api_key_env: str = "MOCK_API_KEY"
    model_env: str = "MOCK_MODEL"
    base_url_env: str = "MOCK_BASE_URL"
    default_base_url: str = "mock://local"
    response_payload: dict[str, Any] = field(default_factory=dict)

    def available(self, provider_config: dict[str, Any]) -> tuple[bool, str]:
        del provider_config
        return True, ""

    def generate_candidates(
        self,
        *,
        system_prompt: str,
        task_payload: dict[str, Any],
        output_schema: dict[str, Any],
        provider_config: dict[str, Any],
        allowlist: ProposalAllowlist,
    ) -> ProviderResponse:
        del output_schema
        payload = provider_config.get("response_payload") or self.response_payload
        text = json.dumps(payload)
        model = str(provider_config.get("model_name", "mock-model"))
        start = time.perf_counter()
        return self._parse_payload(
            text=text,
            model_name=model,
            start_time=start,
            system_prompt=system_prompt,
            user_prompt=str(task_payload.get("user_prompt", "")),
            allowlist=allowlist,
            request_id="mock-request",
        )
