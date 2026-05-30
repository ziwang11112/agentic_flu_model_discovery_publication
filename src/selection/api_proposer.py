from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd

from src.selection.proposal_prompts import (
    ProposalAllowlist,
    build_system_prompt,
    build_user_prompt,
    compact_evidence_context,
    default_proposal_allowlist,
)
from src.selection.schema import CandidateSpec


class JSONProposalClient(Protocol):
    def complete_json(self, *, system_prompt: str, user_prompt: str, config: dict[str, Any]) -> str:
        ...


@dataclass(frozen=True)
class ProposalParseResult:
    candidates: tuple[CandidateSpec, ...]
    parse_errors: tuple[str, ...] = ()
    raw_candidate_count: int = 0


def _extract_json(text: str) -> Any:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    return json.loads(stripped)


def _is_allowed(record: dict[str, Any], allowlist: ProposalAllowlist) -> tuple[bool, str | None]:
    family = record.get("family")
    model_name = record.get("model_name")
    observation_label = record.get("observation_label")
    delay_label = record.get("delay_label")
    if family not in allowlist.families:
        return False, "family_not_allowlisted"
    if model_name not in allowlist.models_by_family.get(str(family), ()):
        return False, "model_name_not_allowlisted"
    if observation_label is not None and str(observation_label) not in allowlist.observation_labels:
        return False, "observation_label_not_allowlisted"
    if delay_label is not None and str(delay_label) not in allowlist.delay_labels:
        return False, "delay_label_not_allowlisted"
    return True, None


def parse_structured_candidate_response(text: str, allowlist: ProposalAllowlist | None = None) -> ProposalParseResult:
    allowlist = allowlist or default_proposal_allowlist()
    errors: list[str] = []
    try:
        payload = _extract_json(text)
    except (json.JSONDecodeError, TypeError) as exc:
        return ProposalParseResult(candidates=(), parse_errors=(f"invalid_json:{exc.__class__.__name__}",))

    records = payload.get("candidates") if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        return ProposalParseResult(candidates=(), parse_errors=("missing_candidates_list",))

    candidates: list[CandidateSpec] = []
    allowed_keys = {
        "candidate_id",
        "family",
        "model_name",
        "observation_label",
        "delay_label",
        "round_idx",
        "rationale",
        "expected_failure_mode",
    }
    for idx, item in enumerate(records):
        if not isinstance(item, dict):
            errors.append(f"{idx}:candidate_not_object")
            continue
        unknown = sorted(set(item) - allowed_keys)
        if unknown:
            errors.append(f"{idx}:unknown_keys:{','.join(unknown)}")
            continue
        allowed, reason = _is_allowed(item, allowlist)
        if not allowed:
            errors.append(f"{idx}:{reason}")
            continue
        candidate_id = str(item.get("candidate_id") or f"api_candidate_{idx}")
        candidates.append(
            CandidateSpec(
                candidate_id=candidate_id,
                family=str(item["family"]),
                model_name=str(item["model_name"]),
                observation_label=None if item.get("observation_label") is None else str(item.get("observation_label")),
                delay_label=None if item.get("delay_label") is None else str(item.get("delay_label")),
                round_idx=int(item.get("round_idx", 0)),
                proposer_name="api_structured",
                rationale=str(item.get("rationale", ""))[:500],
                expected_failure_mode=str(item.get("expected_failure_mode", ""))[:200],
                metadata={"source": "api_json_allowlisted"},
            )
        )
    return ProposalParseResult(candidates=tuple(candidates), parse_errors=tuple(errors), raw_candidate_count=len(records))


@dataclass(frozen=True)
class OpenAICompatibleJSONClient:
    """Minimal optional JSON client for OpenAI-compatible chat-completion APIs."""

    api_key_env: str = "SELECTION_API_KEY"
    endpoint_env: str = "SELECTION_API_ENDPOINT"
    model_env: str = "SELECTION_API_MODEL"
    timeout_seconds: int = 60

    def _settings(self, config: dict[str, Any]) -> tuple[str, str, str] | None:
        api_key = os.getenv(str(config.get("api_key_env", self.api_key_env)))
        endpoint = os.getenv(str(config.get("endpoint_env", self.endpoint_env)))
        model = os.getenv(str(config.get("model_env", self.model_env)))
        if not endpoint and os.getenv("OPENAI_API_KEY"):
            endpoint = "https://api.openai.com/v1/chat/completions"
            api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not endpoint or not model:
            return None
        return api_key, endpoint, model

    def available(self, config: dict[str, Any]) -> bool:
        return self._settings(config) is not None

    def complete_json(self, *, system_prompt: str, user_prompt: str, config: dict[str, Any]) -> str:
        settings = self._settings(config)
        if settings is None:
            raise RuntimeError("api_credentials_missing")
        api_key, endpoint, model = settings
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        if not model.startswith("gpt-5"):
            body["temperature"] = float(config.get("temperature", 0.0))
        token_limit_key = "max_completion_tokens" if model.startswith("gpt-5") else "max_tokens"
        body[token_limit_key] = int(config.get("max_tokens", config.get("max_completion_tokens", 1200)))
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"api_request_failed:{exc.__class__.__name__}") from exc
        try:
            return str(payload["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("api_response_missing_message_content") from exc


@dataclass(frozen=True)
class StructuredAPIProposer:
    client: JSONProposalClient
    allowlist: ProposalAllowlist = default_proposal_allowlist()

    def propose(
        self,
        *,
        model_summary: pd.DataFrame,
        max_candidates: int,
        objective: str,
        api_config: dict[str, Any],
    ) -> ProposalParseResult:
        context = compact_evidence_context(model_summary, max_rows=int(api_config.get("context_rows", 24)))
        system_prompt = build_system_prompt(self.allowlist)
        user_prompt = build_user_prompt(
            evidence_context=context,
            max_candidates=max_candidates,
            objective=objective,
        )
        text = self.client.complete_json(system_prompt=system_prompt, user_prompt=user_prompt, config=api_config)
        result = parse_structured_candidate_response(text, self.allowlist)
        return ProposalParseResult(
            candidates=result.candidates[:max_candidates],
            parse_errors=result.parse_errors,
            raw_candidate_count=result.raw_candidate_count,
        )


@dataclass(frozen=True)
class MockStructuredAPIClient:
    response_text: str

    def complete_json(self, *, system_prompt: str, user_prompt: str, config: dict[str, Any]) -> str:
        del system_prompt, user_prompt, config
        return self.response_text
