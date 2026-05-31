from __future__ import annotations

import json
import http.client
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


PROVIDER_TRANSPORT_ERRORS = (
    urllib.error.URLError,
    TimeoutError,
    OSError,
    http.client.HTTPException,
)


def _extract_json(text: str) -> Any:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    if start < 0:
        return json.loads(stripped)
    depth = 0
    in_string = False
    escaped = False
    for idx, char in enumerate(stripped[start:], start=start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(stripped[start : idx + 1])
    return json.loads(stripped)


def _token_estimate(text: str) -> int:
    return max(1, int(len(text) / 4))


def _max_tokens(provider_config: dict[str, Any], default: int = 3200) -> int:
    return int(provider_config.get("max_tokens", provider_config.get("max_completion_tokens", default)))


def _schema_guided_user_prompt(user_prompt: str) -> str:
    """Remove duplicated schema text when the provider receives a native schema."""

    marker = "{"
    start = user_prompt.find(marker)
    if start < 0:
        return user_prompt
    try:
        payload = json.loads(user_prompt[start:])
    except json.JSONDecodeError:
        return user_prompt
    if not isinstance(payload, dict):
        return user_prompt
    payload.pop("output_json_schema", None)
    payload["schema_delivery"] = "Use the provider response schema supplied outside this prompt."
    payload["brevity_rules"] = [
        "Keep rationale fields under 12 words.",
        "Keep expected_failure_mode fields under 10 words.",
        "Return compact strings only; no markdown or explanatory prose.",
    ]
    return "\n".join(
        [
            "TASK: Complete the structured candidate-proposal task below.",
            "Return JSON only using the provider response schema.",
            json.dumps(payload, indent=2, sort_keys=True),
        ]
    )


def _candidate_model_values(allowlist: ProposalAllowlist) -> list[str]:
    values: list[str] = []
    for family in allowlist.families:
        values.extend(allowlist.models_by_family.get(family, ()))
    return sorted(dict.fromkeys(values))


def _candidate_schema(allowlist: ProposalAllowlist) -> dict[str, Any]:
    provider_delay_labels = [label for label in allowlist.delay_labels if label != ""]
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "candidate_id",
            "family",
            "model_name",
            "observation_label",
            "delay_label",
            "intended_role",
            "rationale",
            "expected_failure_mode",
            "paired_ablation_target",
        ],
        "properties": {
            "candidate_id": {"type": "string"},
            "family": {"type": "string", "enum": list(allowlist.families)},
            "model_name": {"type": "string", "enum": _candidate_model_values(allowlist)},
            "observation_label": {"type": "string", "enum": list(allowlist.observation_labels)},
            "delay_label": {"type": "string", "enum": provider_delay_labels},
            "intended_role": {
                "type": "string",
                "enum": ["accuracy", "rolling_stability", "parsimony", "observation_check", "ablation_check"],
            },
            "rationale": {"type": "string"},
            "expected_failure_mode": {"type": "string"},
            "paired_ablation_target": {"type": ["string", "null"]},
            "responds_to_feedback": {"type": "array", "items": {"type": "string"}},
        },
    }


def provider_json_schema(output_schema: dict[str, Any], allowlist: ProposalAllowlist) -> dict[str, Any]:
    """Compile the internal task schema into provider-safe JSON Schema.

    The internal schema includes local-only metadata used by tests and the
    deterministic verifier. Provider APIs expect ordinary JSON Schema, so this
    adapter layer keeps the wire schema small while preserving strict local
    verification after parsing.
    """

    required = set(output_schema.get("required", ()))
    is_refinement = "new_candidates" in required
    candidate_key = "new_candidates" if is_refinement else "candidates"
    task_enum = ["evidence_aware_refinement"] if is_refinement else ["initial_candidate_proposal"]
    if is_refinement:
        summary_key = "refinement_summary"
        summary_schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["what_changed_from_previous_round", "why_these_candidates_now", "claim_boundary"],
            "properties": {
                "what_changed_from_previous_round": {"type": "string"},
                "why_these_candidates_now": {"type": "string"},
                "claim_boundary": {"type": "string"},
            },
        }
    else:
        summary_key = "selection_notes"
        summary_schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["diversity_strategy", "budget_strategy", "claim_boundary"],
            "properties": {
                "diversity_strategy": {"type": "string"},
                "budget_strategy": {"type": "string"},
                "claim_boundary": {"type": "string"},
            },
        }
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": list(output_schema.get("required", [])),
        "properties": {
            "task_type": {"type": "string", "enum": task_enum},
            "series_name": {"type": "string"},
            "round_index": {"type": "integer"},
            "proposer_label": {"type": "string"},
            candidate_key: {
                "type": "array",
                "minItems": 1,
                "items": _candidate_schema(allowlist),
            },
            summary_key: summary_schema,
        },
    }
    if is_refinement:
        schema["properties"].pop("proposer_label", None)
    return schema


def _normalize_provider_payload(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    normalized = dict(payload)
    for key in ("candidates", "new_candidates"):
        candidates = normalized.get(key)
        if not isinstance(candidates, list):
            continue
        normalized_candidates = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                normalized_candidates.append(candidate)
                continue
            item = dict(candidate)
            for label_key in ("observation_label", "delay_label"):
                if item.get(label_key) in (None, ""):
                    item[label_key] = "not_applicable"
                else:
                    item[label_key] = str(item[label_key])
            normalized_candidates.append(item)
        normalized[key] = normalized_candidates
    return normalized


def _sanitize_http_error(exc: urllib.error.HTTPError) -> str:
    detail = ""
    try:
        raw = exc.read().decode("utf-8", errors="replace")
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            error = parsed.get("error", parsed)
            if isinstance(error, dict):
                detail = str(error.get("message", error.get("type", "")))
            else:
                detail = str(error)
        else:
            detail = str(parsed)
    except Exception:
        detail = ""
    detail = re.sub(r"(?i)(api[_-]?key|key)=([A-Za-z0-9_\-]+)", r"\1=<redacted>", detail)
    lower = detail.lower()
    if "credit balance" in lower or "billing" in lower or "quota" in lower:
        detail = "account_or_billing_unavailable"
    elif "api key" in lower or "apikey" in lower or "credential" in lower or "authentication" in lower:
        detail = "credential_rejected"
    return f"HTTPError:{exc.code}:{detail[:180]}" if detail else f"HTTPError:{exc.code}"


def _gemini_legacy_schema(schema: Any) -> Any:
    """Convert JSON Schema into Gemini legacy responseSchema's smaller subset."""

    if isinstance(schema, list):
        return [_gemini_legacy_schema(item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    converted: dict[str, Any] = {}
    for key, value in schema.items():
        if key == "additionalProperties":
            continue
        if key == "type" and isinstance(value, list):
            non_null = [item for item in value if item != "null"]
            converted["type"] = non_null[0] if non_null else "string"
            if "null" in value:
                converted["nullable"] = True
            continue
        converted[key] = _gemini_legacy_schema(value)
    return converted


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
            parsed = _normalize_provider_payload(_extract_json(text))
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
        settings = self._settings(provider_config)
        if settings is None:
            return ProviderResponse(self.provider_name, "", "skipped", parse_error="credentials_or_model_missing")
        api_key, model, endpoint = settings
        user_prompt = str(task_payload.get("user_prompt", json.dumps(task_payload, sort_keys=True)))
        wire_schema = provider_json_schema(output_schema, allowlist)
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "response_format": {"type": "json_object"},
        }
        if self.provider_name == "openai_gpt":
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "candidate_proposal_payload", "strict": True, "schema": wire_schema},
            }
        if not model.startswith("gpt-5"):
            body["temperature"] = float(provider_config.get("temperature", 0.0))
        token_key = "max_completion_tokens" if model.startswith("gpt-5") else "max_tokens"
        body[token_key] = _max_tokens(provider_config)
        start = time.perf_counter()
        try:
            payload, request_id = self._post_chat_completion(endpoint, api_key, body, provider_config)
        except urllib.error.HTTPError:
            body["response_format"] = {"type": "json_object"}
            try:
                payload, request_id = self._post_chat_completion(endpoint, api_key, body, provider_config)
            except urllib.error.HTTPError as exc:
                return ProviderResponse(
                    self.provider_name,
                    model,
                    "request_failed",
                    parse_error=_sanitize_http_error(exc),
                    latency_seconds=time.perf_counter() - start,
                )
            except (*PROVIDER_TRANSPORT_ERRORS, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
                return ProviderResponse(self.provider_name, model, "request_failed", parse_error=exc.__class__.__name__, latency_seconds=time.perf_counter() - start)
        except (*PROVIDER_TRANSPORT_ERRORS, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            return ProviderResponse(self.provider_name, model, "request_failed", parse_error=exc.__class__.__name__, latency_seconds=time.perf_counter() - start)
        try:
            message = payload["choices"][0]["message"]
            text = message.get("content")
            if not text and message.get("tool_calls"):
                text = message["tool_calls"][0]["function"]["arguments"]
            text = str(text)
        except (KeyError, IndexError, TypeError) as exc:
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

    def _post_chat_completion(
        self,
        endpoint: str,
        api_key: str,
        body: dict[str, Any],
        provider_config: dict[str, Any],
    ) -> tuple[dict[str, Any], str | None]:
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=int(provider_config.get("timeout_seconds", self.timeout_seconds))) as response:
            payload = json.loads(response.read().decode("utf-8"))
            request_id = (getattr(response, "headers", None) or {}).get("x-request-id")
        return payload, request_id


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
        wire_schema = provider_json_schema(output_schema, allowlist)
        body = {
            "model": model,
            "max_tokens": _max_tokens(provider_config),
            "temperature": float(provider_config.get("temperature", 0.0)),
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "tools": [
                {
                    "name": "submit_candidates",
                    "description": "Submit the JSON candidate proposal payload.",
                    "input_schema": wire_schema,
                    "strict": True,
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
        except urllib.error.HTTPError as exc:
            return ProviderResponse(
                self.provider_name,
                model,
                "request_failed",
                parse_error=_sanitize_http_error(exc),
                latency_seconds=time.perf_counter() - start,
            )
        except (*PROVIDER_TRANSPORT_ERRORS, KeyError, TypeError, json.JSONDecodeError) as exc:
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
        user_prompt = _schema_guided_user_prompt(str(task_payload.get("user_prompt", json.dumps(task_payload, sort_keys=True))))
        endpoint = endpoint_template.format(model=urllib.parse.quote(model, safe=""))
        separator = "&" if "?" in endpoint else "?"
        endpoint = f"{endpoint}{separator}key={urllib.parse.quote(api_key)}"
        wire_schema = provider_json_schema(output_schema, allowlist)
        body = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": float(provider_config.get("temperature", 0.0)),
                "responseMimeType": "application/json",
                "responseSchema": _gemini_legacy_schema(wire_schema),
                "maxOutputTokens": _max_tokens(provider_config, default=8192),
            },
        }
        start = time.perf_counter()
        try:
            payload, request_id = self._post_gemini(endpoint, body, provider_config)
        except urllib.error.HTTPError:
            legacy_body = dict(body)
            legacy_body["generationConfig"] = {
                "temperature": float(provider_config.get("temperature", 0.0)),
                "responseFormat": {"text": {"mimeType": "application/json", "schema": wire_schema}},
                "maxOutputTokens": _max_tokens(provider_config, default=8192),
            }
            try:
                payload, request_id = self._post_gemini(endpoint, legacy_body, provider_config)
            except urllib.error.HTTPError as exc:
                return ProviderResponse(
                    self.provider_name,
                    model,
                    "request_failed",
                    parse_error=_sanitize_http_error(exc),
                    latency_seconds=time.perf_counter() - start,
                )
            except (*PROVIDER_TRANSPORT_ERRORS, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
                return ProviderResponse(self.provider_name, model, "request_failed", parse_error=exc.__class__.__name__, latency_seconds=time.perf_counter() - start)
        except (*PROVIDER_TRANSPORT_ERRORS, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            return ProviderResponse(self.provider_name, model, "request_failed", parse_error=exc.__class__.__name__, latency_seconds=time.perf_counter() - start)
        try:
            text = str(payload["candidates"][0]["content"]["parts"][0]["text"])
        except (KeyError, IndexError, TypeError) as exc:
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

    def _post_gemini(
        self,
        endpoint: str,
        body: dict[str, Any],
        provider_config: dict[str, Any],
    ) -> tuple[dict[str, Any], str | None]:
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=int(provider_config.get("timeout_seconds", self.timeout_seconds))) as response:
            payload = json.loads(response.read().decode("utf-8"))
            request_id = (getattr(response, "headers", None) or {}).get("x-request-id")
        return payload, request_id


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
