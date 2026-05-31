from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class AgentTaskType(str, Enum):
    INITIAL_CANDIDATE_PROPOSAL = "initial_candidate_proposal"
    EVIDENCE_AWARE_REFINEMENT = "evidence_aware_refinement"
    FAILURE_DIAGNOSIS = "failure_diagnosis"
    CLAIM_BOUNDARY_SUMMARY = "claim_boundary_summary"


ALLOWED_CONTEXT_FIELDS = {
    "series_name",
    "forecasting_target",
    "partial_observation_note",
    "selection_objective",
    "candidate_budget",
    "candidate_budget_remaining",
    "candidate_allowlist",
    "available_metrics",
    "forbidden_metrics",
    "rolling_mean_mae",
    "validation_mae",
    "validation_mae_if_available",
    "numerical_failure_flag",
    "model_complexity",
    "candidate_family",
    "previous_feedback",
    "accepted_candidates",
    "rejected_candidates",
    "duplicate_candidates",
    "non_test_evidence_summary",
    "best_family_so_far",
    "baseline_sufficient",
    "observation_ablation_gap_direction",
    "rolling_stability_issue",
    "allowed_ablation_models",
    "audit_labels",
    "allowed_claims",
    "rejected_claims",
}

FORBIDDEN_CONTEXT_FIELDS = {
    "test_mae",
    "test_rmse",
    "test_smape",
    "test_rank",
    "test_winner",
    "best_test_model",
    "best_test_mae",
    "post_selection_test_mae",
    "post_selection_test_comparison",
    "paper_recommendation",
    "recommended_model",
}

NO_LEAKAGE_AUDIT_FIELDS = (
    "prompt_contains_test_metric",
    "prompt_contains_test_winner",
    "prompt_contains_posthoc_metric",
    "safe_prompt_passed",
    "allowlist_hash",
)


@dataclass(frozen=True)
class AgentTaskSpec:
    task_type: AgentTaskType
    title: str
    purpose: str
    allowed_context_fields: tuple[str, ...] = field(default_factory=lambda: tuple(sorted(ALLOWED_CONTEXT_FIELDS)))
    forbidden_context_fields: tuple[str, ...] = field(default_factory=lambda: tuple(sorted(FORBIDDEN_CONTEXT_FIELDS)))
    required_output_fields: tuple[str, ...] = ()
    verifier_expectations: tuple[str, ...] = ()
    no_leakage_audit_fields: tuple[str, ...] = NO_LEAKAGE_AUDIT_FIELDS

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["task_type"] = self.task_type.value
        return data


def agent_task_specs() -> dict[AgentTaskType, AgentTaskSpec]:
    return {
        AgentTaskType.INITIAL_CANDIDATE_PROPOSAL: AgentTaskSpec(
            task_type=AgentTaskType.INITIAL_CANDIDATE_PROPOSAL,
            title="Initial Candidate Proposal",
            purpose="Propose a compact, diverse allowlisted candidate set for the first evaluation round.",
            required_output_fields=(
                "task_type",
                "series_name",
                "round_index",
                "proposer_label",
                "candidates",
                "selection_notes",
            ),
            verifier_expectations=(
                "candidate_id is unique",
                "family and model_name are allowlist-compatible",
                "observation_label and delay_label are allowlisted",
                "no executable code or arbitrary equation fields are present",
                "claim_boundary remains proposal-only",
            ),
        ),
        AgentTaskType.EVIDENCE_AWARE_REFINEMENT: AgentTaskSpec(
            task_type=AgentTaskType.EVIDENCE_AWARE_REFINEMENT,
            title="Evidence-Aware Refinement",
            purpose="Use verifier and non-test evaluator feedback to propose the next candidate round.",
            required_output_fields=(
                "task_type",
                "series_name",
                "round_index",
                "new_candidates",
                "refinement_summary",
            ),
            verifier_expectations=(
                "new candidate ids do not duplicate accepted prior ids",
                "response cites allowed feedback categories only",
                "rejected invalid candidates are not repeated",
                "no test evidence is referenced",
            ),
        ),
        AgentTaskType.FAILURE_DIAGNOSIS: AgentTaskSpec(
            task_type=AgentTaskType.FAILURE_DIAGNOSIS,
            title="Failure Diagnosis / Ablation Request",
            purpose="Convert non-test failure evidence into a structured ablation request.",
            required_output_fields=("task_type", "series_name", "diagnosis", "recommended_ablation", "reason", "claim_boundary"),
            verifier_expectations=(
                "recommended_ablation is in the allowed ablation model list",
                "diagnosis does not claim real-world mechanism recovery",
                "claim_boundary is ablation_request_only",
            ),
        ),
        AgentTaskType.CLAIM_BOUNDARY_SUMMARY: AgentTaskSpec(
            task_type=AgentTaskType.CLAIM_BOUNDARY_SUMMARY,
            title="Claim-Boundary Summary",
            purpose="Summarize deterministic audit labels without expanding the allowed claim boundary.",
            required_output_fields=("task_type", "safe_summary", "allowed_claims", "rejected_claims", "required_caveats"),
            verifier_expectations=(
                "safe_summary rejects SOTA and autonomous-science claims",
                "flagged rows are descriptive only",
                "API outputs are proposal-quality evidence only",
            ),
        ),
    }


def get_agent_task_spec(task_type: AgentTaskType | str) -> AgentTaskSpec:
    normalized = task_type if isinstance(task_type, AgentTaskType) else AgentTaskType(str(task_type))
    return agent_task_specs()[normalized]


def forbidden_context_hits(context: dict[str, Any]) -> list[str]:
    hits: list[str] = []

    def visit(prefix: str, value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                lower_key = str(key).lower()
                if lower_key in FORBIDDEN_CONTEXT_FIELDS:
                    hits.append(f"{prefix}{key}")
                visit(f"{prefix}{key}.", item)
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                visit(f"{prefix}{idx}.", item)
        elif isinstance(value, str) and value.lower() in FORBIDDEN_CONTEXT_FIELDS:
            hits.append(prefix.rstrip("."))

    visit("", context)
    return hits


def ensure_no_forbidden_context(context: dict[str, Any]) -> None:
    hits = forbidden_context_hits(context)
    if hits:
        joined = ", ".join(sorted(hits))
        raise ValueError(f"Agent prompt context contains forbidden held-out evidence fields: {joined}")
