from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from src.selection.agent_tasks import forbidden_context_hits
from src.selection.executor_bridge import allowlist_hash


FORBIDDEN_FEEDBACK_TOKENS = (
    "test_mae",
    "test_rmse",
    "test_smape",
    "test_winner",
    "test_rank",
    "best_test",
    "post_selection_test",
    "posthoc",
    "post-hoc",
)


@dataclass(frozen=True)
class RoundFeedback:
    series_name: str
    proposer_type: str
    round_idx: int
    accepted_candidates: tuple[dict[str, Any], ...] = ()
    rejected_candidates: tuple[dict[str, Any], ...] = ()
    duplicate_candidates: tuple[str, ...] = ()
    family_diversity_so_far: int = 0
    observation_labels_tried: tuple[str, ...] = ()
    non_final_evidence_summary: dict[str, Any] = field(default_factory=dict)
    remaining_budget: int = 0
    top_epsilon_hit_so_far: bool = False

    def to_context(self) -> dict[str, Any]:
        return {
            "series_name": self.series_name,
            "candidate_budget_remaining": int(self.remaining_budget),
            "previous_round": {
                "round_idx": int(self.round_idx),
                "accepted_candidates": list(self.accepted_candidates),
                "rejected_candidates": list(self.rejected_candidates),
                "duplicate_candidates": list(self.duplicate_candidates),
                "non_final_evidence_summary": {
                    **self.non_final_evidence_summary,
                    "family_diversity_so_far": int(self.family_diversity_so_far),
                    "observation_labels_tried": list(self.observation_labels_tried),
                    "top_epsilon_hit_so_far": bool(self.top_epsilon_hit_so_far),
                },
            },
        }


def feedback_contains_forbidden_fields(feedback: dict[str, Any]) -> bool:
    if forbidden_context_hits(feedback):
        return True
    text = json.dumps(feedback, sort_keys=True).lower()
    return any(token in text for token in FORBIDDEN_FEEDBACK_TOKENS)


def prompt_audit_row(
    *,
    series_name: str,
    proposer_type: str,
    round_idx: int,
    prompt_payload: dict[str, Any],
    feedback_context: dict[str, Any],
    model_allowlist: list[str] | tuple[str, ...],
    selection_uses_test_metric: bool = False,
    posthoc_test_metric_only: bool = True,
) -> dict[str, Any]:
    prompt_text = json.dumps(prompt_payload, sort_keys=True).lower()
    feedback_text = json.dumps(feedback_context, sort_keys=True).lower()
    prompt_contains_test_metric = any(token in prompt_text for token in ("test_mae", "test_rmse", "test_smape"))
    prompt_contains_test_winner = any(token in prompt_text for token in ("test_winner", "best_test"))
    prompt_contains_test_rank = any(token in prompt_text for token in ("test_rank", "test rank"))
    prompt_contains_posthoc_metric = any(token in prompt_text for token in ("posthoc", "post-hoc", "post_selection_test"))
    feedback_contains_test_metric = any(
        token in feedback_text
        for token in (
            "test_mae",
            "test_rmse",
            "test_smape",
            "test_winner",
            "test_rank",
            "best_test",
            "post_selection_test",
            "posthoc",
            "post-hoc",
        )
    )
    safe_prompt = not (
        prompt_contains_test_metric
        or prompt_contains_test_winner
        or prompt_contains_test_rank
        or prompt_contains_posthoc_metric
    )
    safe_feedback = not feedback_contains_test_metric and not forbidden_context_hits(feedback_context)
    safe_selection = not bool(selection_uses_test_metric)
    return {
        "series_name": series_name,
        "proposer_type": proposer_type,
        "round_idx": int(round_idx),
        "prompt_contains_test_metric": bool(prompt_contains_test_metric),
        "prompt_contains_test_winner": bool(prompt_contains_test_winner),
        "prompt_contains_test_rank": bool(prompt_contains_test_rank),
        "prompt_contains_posthoc_metric": bool(prompt_contains_posthoc_metric),
        "feedback_contains_test_metric": bool(feedback_contains_test_metric),
        "selection_uses_test_metric": bool(selection_uses_test_metric),
        "posthoc_test_metric_only": bool(posthoc_test_metric_only),
        "safe_prompt_passed": bool(safe_prompt),
        "safe_feedback_passed": bool(safe_feedback),
        "safe_selection_passed": bool(safe_selection),
        "allowlist_hash": allowlist_hash(model_allowlist),
    }


def make_round_feedback(
    *,
    series_name: str,
    proposer_type: str,
    round_idx: int,
    accepted_records: list[dict[str, Any]],
    rejected_records: list[dict[str, Any]],
    duplicate_candidates: list[str],
    remaining_budget: int,
    top_epsilon_hit: bool,
) -> RoundFeedback:
    labels = sorted(
        {
            str(row.get("observation_label", ""))
            for row in accepted_records
            if str(row.get("observation_label", "")) not in {"", "nan"}
        }
    )
    families = {
        str(row.get("family", ""))
        for row in accepted_records
        if str(row.get("family", "")) not in {"", "nan"}
    }
    best = min((float(row["rolling_score"]) for row in accepted_records if row.get("rolling_score") is not None), default=None)
    return RoundFeedback(
        series_name=series_name,
        proposer_type=proposer_type,
        round_idx=int(round_idx),
        accepted_candidates=tuple(accepted_records[-6:]),
        rejected_candidates=tuple(rejected_records[-6:]),
        duplicate_candidates=tuple(duplicate_candidates[-6:]),
        family_diversity_so_far=len(families),
        observation_labels_tried=tuple(labels),
        non_final_evidence_summary={
            "best_rolling_score_so_far": best,
            "candidate_count_so_far": int(len(accepted_records)),
            "top_epsilon_hit_so_far": bool(top_epsilon_hit),
            "selection_metric_source": "rolling_mean_mae",
        },
        remaining_budget=int(remaining_budget),
        top_epsilon_hit_so_far=bool(top_epsilon_hit),
    )
