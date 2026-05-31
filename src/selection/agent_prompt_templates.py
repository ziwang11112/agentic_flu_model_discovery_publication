from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from src.selection.agent_output_schema import agent_output_schema
from src.selection.agent_tasks import (
    AgentTaskType,
    ensure_no_forbidden_context,
    get_agent_task_spec,
)
from src.selection.proposal_prompts import ProposalAllowlist, default_proposal_allowlist


@dataclass(frozen=True)
class AgentPrompt:
    system_prompt: str
    user_prompt: str

    def combined_text(self) -> str:
        return f"{self.system_prompt}\n\n{self.user_prompt}"


def agent_protocol_allowlist(allowlist: ProposalAllowlist | None = None) -> ProposalAllowlist:
    base = allowlist or default_proposal_allowlist()
    delay_labels = tuple(dict.fromkeys((*base.delay_labels, "not_applicable")))
    observation_labels = tuple(dict.fromkeys((*base.observation_labels, "not_applicable", "proxy")))
    return ProposalAllowlist(
        families=base.families,
        models_by_family=base.models_by_family,
        observation_labels=observation_labels,
        delay_labels=delay_labels,
    )


def build_agent_system_prompt() -> str:
    return "\n".join(
        [
            "You are a constrained forecasting-model proposal agent.",
            "Your task is to propose structured candidate models for a partially observed time-series forecasting problem.",
            "Return JSON only. Do not include prose outside JSON.",
            "Use only the provided candidate allowlist.",
            "Do not invent model names, equations, parameters, executable code, or model families.",
            "Do not use final held-out metrics, final winners or ranks, or post-selection comparisons.",
            "Do not make medical, operational, intervention, or deployment recommendations.",
            "Do not claim frontier forecasting status, autonomous discovery, or real-world mechanism recovery.",
            "Your proposals are hypotheses for deterministic verification and evaluation only.",
            "Every candidate you propose will be checked by a verifier before use.",
        ]
    )


def build_agent_task_prompt(
    task_type: AgentTaskType | str,
    *,
    context: dict[str, Any],
    allowlist: ProposalAllowlist | None = None,
) -> AgentPrompt:
    ensure_no_forbidden_context(context)
    task = task_type if isinstance(task_type, AgentTaskType) else AgentTaskType(str(task_type))
    spec = get_agent_task_spec(task)
    normalized_allowlist = agent_protocol_allowlist(allowlist)
    payload = {
        "task_type": task.value,
        "task_title": spec.title,
        "task_purpose": spec.purpose,
        "context": context,
        "candidate_allowlist": normalized_allowlist.to_dict(),
        "output_json_schema": agent_output_schema(task),
        "verifier_expectations": list(spec.verifier_expectations),
        "no_leakage_rule": (
            "The prompt context excludes final held-out evidence; selection may use only non-final validation, "
            "rolling, complexity, numerical-risk, diversity, and verifier-status fields."
        ),
    }
    user_prompt = "\n".join(
        [
            "TASK: Complete the structured candidate-proposal task below.",
            "Return JSON only.",
            json.dumps(payload, indent=2, sort_keys=True),
        ]
    )
    return AgentPrompt(system_prompt=build_agent_system_prompt(), user_prompt=user_prompt)


def example_initial_context() -> dict[str, Any]:
    return {
        "series_name": "0-4 yr",
        "forecasting_target": "weekly rate time series",
        "partial_observation_note": "observed values may be direct, lagged, or proxy observations of latent dynamics",
        "selection_objective": "validation_or_rolling_evidence_only",
        "candidate_budget": 3,
        "allowed_evidence_summary": {
            "simple_baselines_competitive": True,
            "observation_label_uncertainty": True,
            "previous_labels_tried": ["direct"],
            "labels_to_explore": ["lagged"],
            "numerical_risk_note": "avoid unstable rows for positive claims",
        },
    }


def example_initial_output() -> dict[str, Any]:
    return {
        "task_type": AgentTaskType.INITIAL_CANDIDATE_PROPOSAL.value,
        "series_name": "0-4 yr",
        "round_index": 1,
        "proposer_label": "constrained_agentic_proposer",
        "candidates": [
            {
                "candidate_id": "r1_c1",
                "family": "structured_search",
                "model_name": "constrained_structure_discovery",
                "observation_label": "lagged",
                "delay_label": "1",
                "intended_role": "observation_check",
                "rationale": "Tests whether a lagged observation label improves non-final rolling evidence.",
                "expected_failure_mode": "May overfit if lag evidence is unstable.",
                "paired_ablation_target": "no_observation_search_discovery",
            },
            {
                "candidate_id": "r1_c2",
                "family": "ablation",
                "model_name": "no_observation_search_discovery",
                "observation_label": "direct",
                "delay_label": "0",
                "intended_role": "ablation_check",
                "rationale": "Controls for whether observation-label search is useful.",
                "expected_failure_mode": "May underperform if lagged observation is important.",
                "paired_ablation_target": "constrained_structure_discovery",
            },
            {
                "candidate_id": "r1_c3",
                "family": "forecasting_baseline",
                "model_name": "arima_auto_small",
                "observation_label": "not_applicable",
                "delay_label": "not_applicable",
                "intended_role": "accuracy",
                "rationale": "Provides a compact forecasting comparator.",
                "expected_failure_mode": "May not capture observation-process differences.",
                "paired_ablation_target": None,
            },
        ],
        "selection_notes": {
            "diversity_strategy": "Use one structured-search candidate, one observation ablation, and one baseline.",
            "budget_strategy": "Spend the small budget on observation uncertainty and a simple comparator.",
            "claim_boundary": "proposal_only_not_performance_evidence",
        },
    }


def example_refinement_context() -> dict[str, Any]:
    return {
        "series_name": "0-4 yr",
        "candidate_budget_remaining": 2,
        "previous_round": {
            "accepted_candidates": [
                {
                    "candidate_id": "r1_c1",
                    "model_name": "constrained_structure_discovery",
                    "family": "structured_search",
                    "observation_label": "lagged",
                    "rolling_score": 0.1002,
                    "numerical_failure_flag": False,
                }
            ],
            "rejected_candidates": [{"candidate_id": "r1_cx", "rejection_reason": "out_of_allowlist"}],
            "duplicate_candidates": [],
            "non_final_evidence_summary": {
                "best_family_so_far": "structured_search",
                "baseline_sufficient": False,
                "observation_ablation_gap_direction": "observation_search_helpful",
            },
        },
    }


def example_refinement_output() -> dict[str, Any]:
    return {
        "task_type": AgentTaskType.EVIDENCE_AWARE_REFINEMENT.value,
        "series_name": "0-4 yr",
        "round_index": 2,
        "new_candidates": [
            {
                "candidate_id": "r2_c1",
                "family": "mechanistic_baseline",
                "model_name": "delayed_observation_seir",
                "observation_label": "lagged",
                "delay_label": "1",
                "intended_role": "rolling_stability",
                "rationale": "Checks whether a hand-specified delayed-observation comparator matches the search signal.",
                "expected_failure_mode": "May be too rigid if label evidence varies over time.",
                "paired_ablation_target": "constrained_structure_discovery",
                "responds_to_feedback": ["observation_gap"],
            }
        ],
        "refinement_summary": {
            "what_changed_from_previous_round": "Adds a delayed comparator after accepted lagged search evidence.",
            "why_these_candidates_now": "The non-final feedback suggests observation-label uncertainty is worth checking.",
            "claim_boundary": "proposal_only_not_performance_evidence",
        },
    }


def example_failure_output() -> dict[str, Any]:
    return {
        "task_type": AgentTaskType.FAILURE_DIAGNOSIS.value,
        "series_name": "0-4 yr",
        "diagnosis": "Non-final rolling evidence suggests observation-label uncertainty should be isolated.",
        "recommended_ablation": "no_observation_search_discovery",
        "reason": "Compares a fixed direct observation label against the constrained search candidate.",
        "claim_boundary": "ablation_request_only",
    }


def example_claim_output() -> dict[str, Any]:
    return {
        "task_type": AgentTaskType.CLAIM_BOUNDARY_SUMMARY.value,
        "safe_summary": (
            "The verifier-gated proposer can be discussed as proposal-quality and budget-efficiency evidence only; "
            "real-data conclusions remain age- and objective-dependent."
        ),
        "allowed_claims": ["proposal_quality", "budget_efficiency", "generic_structured_recovery"],
        "rejected_claims": ["global forecasting superiority", "autonomous discovery", "real-world mechanism recovery"],
        "required_caveats": [
            "API outputs are verifier-gated structured proposals only.",
            "Synthetic tasks are generic software validation.",
        ],
    }
