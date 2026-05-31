from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.selection.provider_adapters import (
    AnthropicAdapter,
    DeepSeekAdapter,
    GeminiAdapter,
    MockProviderAdapter,
    OpenAIChatAdapter,
    ProviderAdapter,
)


@dataclass(frozen=True)
class ProviderRegistration:
    provider_name: str
    adapter: ProviderAdapter
    config: dict[str, Any]
    available: bool
    skip_reason: str = ""
    model_name: str = ""


def provider_adapter_by_name(provider_name: str, *, mock_payload: dict[str, Any] | None = None) -> ProviderAdapter:
    if provider_name == "openai_gpt":
        return OpenAIChatAdapter()
    if provider_name == "anthropic_claude":
        return AnthropicAdapter()
    if provider_name == "google_gemini":
        return GeminiAdapter()
    if provider_name == "deepseek":
        return DeepSeekAdapter()
    if provider_name == "mock_provider":
        return MockProviderAdapter(response_payload=mock_payload or {})
    raise ValueError(f"Unknown provider_name={provider_name!r}")


def configured_providers(config: dict[str, Any], *, mock_payload: dict[str, Any] | None = None) -> list[ProviderRegistration]:
    rows: list[ProviderRegistration] = []
    for item in config.get("providers", []):
        if isinstance(item, str):
            provider_name = item
            provider_config: dict[str, Any] = {}
        else:
            provider_name = str(item["name"])
            provider_config = dict(item.get("config", {}))
        adapter = provider_adapter_by_name(provider_name, mock_payload=mock_payload)
        available, skip_reason = adapter.available(provider_config)
        model_name = ""
        settings = getattr(adapter, "_settings", lambda cfg: None)(provider_config)
        if settings is not None:
            model_name = str(settings[1])
        elif provider_name == "mock_provider":
            model_name = str(provider_config.get("model_name", "mock-model"))
        rows.append(
            ProviderRegistration(
                provider_name=provider_name,
                adapter=adapter,
                config=provider_config,
                available=available,
                skip_reason=skip_reason,
                model_name=model_name,
            )
        )
    return rows
