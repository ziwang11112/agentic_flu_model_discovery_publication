from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from src.selection.agent_tasks import AgentTaskType
from src.selection.proposal_prompts import ProposalAllowlist, default_proposal_allowlist
from src.selection.schema import CandidateFamily, CandidateSpec


class AgentOutputValidationError(ValueError):
    """Raised when a structured proposer response violates the protocol."""


CANDIDATE_REQUIRED_FIELDS = (
    "candidate_id",
    "family",
    "model_name",
    "observation_label",
    "delay_label",
)

EXECUTABLE_CODE_FIELDS = {
    "code",
    "python",
    "python_code",
    "script",
    "notebook",
    "function_body",
    "model_code",
    "equation",
    "equations",
    "parameters",
    "new_model_definition",
}

CLAIM_UNSAFE_TERMS = (
    "sota",
    "state-of-the-art",
    "autonomous scientist",
    "autonomous science",
    "real-world mechanism recovery",
    "mechanism discovery",
    "api improves forecasting",
    "improves forecasting performance",
)


def _agent_allowlist(allowlist: ProposalAllowlist | None = None) -> ProposalAllowlist:
    base = allowlist or default_proposal_allowlist()
    delay_labels = tuple(dict.fromkeys((*base.delay_labels, "not_applicable")))
    observation_labels = tuple(dict.fromkeys((*base.observation_labels, "not_applicable", "proxy")))
    return ProposalAllowlist(
        families=base.families,
        models_by_family=base.models_by_family,
        observation_labels=observation_labels,
        delay_labels=delay_labels,
    )


def agent_output_schema(task_type: AgentTaskType | str) -> dict[str, Any]:
    task = task_type if isinstance(task_type, AgentTaskType) else AgentTaskType(str(task_type))
    candidate_schema = {
        "type": "object",
        "required": list(CANDIDATE_REQUIRED_FIELDS),
        "forbidden_extra_fields": sorted(EXECUTABLE_CODE_FIELDS),
        "properties": {
            "candidate_id": {"type": "string"},
            "family": {"type": "string"},
            "model_name": {"type": "string"},
            "observation_label": {"type": "string"},
            "delay_label": {"type": "string"},
            "intended_role": {"type": "string"},
            "rationale": {"type": "string"},
            "expected_failure_mode": {"type": "string"},
            "paired_ablation_target": {"type": ["string", "null"]},
        },
    }
    if task == AgentTaskType.INITIAL_CANDIDATE_PROPOSAL:
        return {
            "type": "object",
            "required": ["task_type", "series_name", "round_index", "proposer_label", "candidates", "selection_notes"],
            "properties": {"candidates": {"type": "array", "items": candidate_schema}},
        }
    if task == AgentTaskType.EVIDENCE_AWARE_REFINEMENT:
        return {
            "type": "object",
            "required": ["task_type", "series_name", "round_index", "new_candidates", "refinement_summary"],
            "properties": {"new_candidates": {"type": "array", "items": candidate_schema}},
        }
    if task == AgentTaskType.FAILURE_DIAGNOSIS:
        return {
            "type": "object",
            "required": ["task_type", "series_name", "diagnosis", "recommended_ablation", "reason", "claim_boundary"],
        }
    if task == AgentTaskType.CLAIM_BOUNDARY_SUMMARY:
        return {
            "type": "object",
            "required": ["task_type", "safe_summary", "allowed_claims", "rejected_claims", "required_caveats"],
        }
    raise AgentOutputValidationError(f"Unsupported task_type={task_type!r}")


def _walk_keys_and_values(value: Any) -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield str(key), item
            yield from _walk_keys_and_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys_and_values(item)


def _reject_executable_fields(payload: Mapping[str, Any]) -> None:
    for key, _ in _walk_keys_and_values(payload):
        if key.lower() in EXECUTABLE_CODE_FIELDS:
            raise AgentOutputValidationError(f"Executable or model-definition field is not allowed: {key}")


def _require_fields(payload: Mapping[str, Any], fields: Iterable[str], *, label: str) -> None:
    missing = [field for field in fields if field not in payload or payload[field] in (None, "")]
    if missing:
        raise AgentOutputValidationError(f"{label} missing required fields: {', '.join(missing)}")


def _candidate_list(payload: Mapping[str, Any], task: AgentTaskType) -> list[dict[str, Any]]:
    key = "new_candidates" if task == AgentTaskType.EVIDENCE_AWARE_REFINEMENT else "candidates"
    candidates = payload.get(key)
    if not isinstance(candidates, list):
        raise AgentOutputValidationError(f"{key} must be a list")
    return candidates


def _validate_candidate(candidate: Mapping[str, Any], allowlist: ProposalAllowlist) -> CandidateSpec:
    _require_fields(candidate, CANDIDATE_REQUIRED_FIELDS, label="candidate")
    family = str(candidate["family"])
    model_name = str(candidate["model_name"])
    observation_label = str(candidate["observation_label"])
    delay_label = str(candidate["delay_label"])

    if family not in allowlist.families:
        raise AgentOutputValidationError(f"Family is outside allowlist: {family}")
    if model_name not in allowlist.models_by_family.get(family, ()):
        raise AgentOutputValidationError(f"Model is outside allowlist for family {family}: {model_name}")
    if observation_label not in allowlist.observation_labels:
        raise AgentOutputValidationError(f"Observation label is outside allowlist: {observation_label}")
    if delay_label not in allowlist.delay_labels:
        raise AgentOutputValidationError(f"Delay label is outside allowlist: {delay_label}")

    normalized_delay = None if delay_label == "not_applicable" else delay_label
    return CandidateSpec(
        candidate_id=str(candidate["candidate_id"]),
        family=CandidateFamily(family),
        model_name=model_name,
        observation_label=observation_label,
        delay_label=normalized_delay,
        round_idx=int(candidate.get("round_index", candidate.get("round_idx", 0)) or 0),
        proposer_name=str(candidate.get("proposer_label", candidate.get("proposer_name", "agent_protocol"))),
        rationale=str(candidate.get("rationale", "")),
        expected_failure_mode=str(candidate.get("expected_failure_mode", "")),
        metadata={
            "intended_role": candidate.get("intended_role", ""),
            "paired_ablation_target": candidate.get("paired_ablation_target"),
        },
    )


def _unsafe_claim_text(payload: Any) -> str | None:
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if str(key) == "rejected_claims":
                continue
            hit = _unsafe_claim_text(value)
            if hit:
                return hit
    elif isinstance(payload, list):
        for item in payload:
            hit = _unsafe_claim_text(item)
            if hit:
                return hit
    elif isinstance(payload, str):
        lower = payload.lower()
        for term in CLAIM_UNSAFE_TERMS:
            if term in lower:
                return term
    return None


def validate_agent_output(
    payload: Mapping[str, Any],
    *,
    allowlist: ProposalAllowlist | None = None,
) -> tuple[CandidateSpec, ...] | dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise AgentOutputValidationError("Agent output must be a JSON object")
    _reject_executable_fields(payload)
    if "task_type" not in payload:
        raise AgentOutputValidationError("Agent output missing task_type")
    task = AgentTaskType(str(payload["task_type"]))
    schema = agent_output_schema(task)
    _require_fields(payload, schema["required"], label="agent output")

    normalized_allowlist = _agent_allowlist(allowlist)
    if task in (AgentTaskType.INITIAL_CANDIDATE_PROPOSAL, AgentTaskType.EVIDENCE_AWARE_REFINEMENT):
        candidates = tuple(_validate_candidate(candidate, normalized_allowlist) for candidate in _candidate_list(payload, task))
        ids = [candidate.candidate_id for candidate in candidates]
        if len(ids) != len(set(ids)):
            raise AgentOutputValidationError("Duplicate candidate_id values are not allowed")
        return candidates

    if task == AgentTaskType.FAILURE_DIAGNOSIS:
        recommended = str(payload["recommended_ablation"])
        allowed_ablation_models = normalized_allowlist.models_by_family.get(CandidateFamily.ABLATION.value, ())
        if recommended not in allowed_ablation_models:
            raise AgentOutputValidationError(f"Recommended ablation is outside allowlist: {recommended}")
        return dict(payload)

    if task == AgentTaskType.CLAIM_BOUNDARY_SUMMARY:
        hit = _unsafe_claim_text(payload)
        if hit:
            raise AgentOutputValidationError(f"Unsafe positive claim term is not allowed in claim summary: {hit}")
        return dict(payload)

    raise AgentOutputValidationError(f"Unsupported task_type={task.value!r}")
