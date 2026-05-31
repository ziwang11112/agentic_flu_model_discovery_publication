from __future__ import annotations

import json
from typing import Any

import pandas as pd

from src.selection.proposal_prompts import ProposalAllowlist
from src.selection.executor_bridge import allowlist_hash


FORBIDDEN_PROMPT_COLUMNS = {
    "test_mae",
    "test_rmse",
    "test_smape",
    "best_test_model",
    "best_test_mae",
    "test_rank",
    "rank_score",
    "recommended_model",
    "post_selection_test_mae",
}


def no_test_evidence_context(
    model_summary: pd.DataFrame,
    *,
    series_names: list[str] | tuple[str, ...] | None = None,
    model_allowlist: list[str] | tuple[str, ...] | None = None,
    max_rows: int = 40,
) -> list[dict[str, Any]]:
    """Build compact API context without held-out test or recommendation fields."""
    frame = model_summary.copy()
    if series_names:
        wanted = {str(value) for value in series_names}
        frame = frame.loc[frame["series_name"].astype(str).isin(wanted)]
    if model_allowlist:
        allowed = {str(value) for value in model_allowlist}
        frame = frame.loc[frame["model_name"].astype(str).isin(allowed)]

    columns = [
        "series_name",
        "model_name",
        "model_family",
        "rolling_mean_mae",
        "rolling_mean_rmse",
        "num_free_params",
        "num_compartments",
        "numerical_failure_flag",
        "discovery_structure_name",
        "discovery_observation_map",
        "discovery_delay_weeks",
    ]
    available = [column for column in columns if column in frame.columns and column not in FORBIDDEN_PROMPT_COLUMNS]
    ordered = frame.sort_values(["series_name", "rolling_mean_mae", "model_name"]).loc[:, available]
    records: list[dict[str, Any]] = []
    for _, row in ordered.head(max_rows).iterrows():
        record: dict[str, Any] = {}
        for key, value in row.items():
            if key in FORBIDDEN_PROMPT_COLUMNS or pd.isna(value):
                continue
            if isinstance(value, float):
                record[key] = round(float(value), 6)
            else:
                record[key] = value
        records.append(record)
    return records


def build_execution_system_prompt(allowlist: ProposalAllowlist) -> str:
    return "\n".join(
        [
            "You propose structured candidate records for an offline time-series candidate-budget audit.",
            "Return JSON only. Do not include prose outside JSON.",
            "Do not propose new model code, equations, interventions, operational guidance, or new model families.",
            "Every candidate must use only the explicit allowlist.",
            "Do not use or infer final held-out evaluation metrics.",
            "The response schema is: {\"candidates\": [{\"candidate_id\": str, \"family\": str, \"model_name\": str, \"observation_label\": str|null, \"delay_label\": str|null, \"rationale\": str, \"expected_failure_mode\": str}]}",
            "Allowed values:",
            json.dumps(allowlist.to_dict(), sort_keys=True),
        ]
    )


def build_execution_user_payload(
    *,
    series_name: str,
    evidence_context: list[dict[str, Any]],
    model_allowlist: list[str] | tuple[str, ...],
    max_candidates: int,
    objective: str,
) -> dict[str, Any]:
    return {
        "series_name": series_name,
        "objective": objective,
        "max_candidates": int(max_candidates),
        "candidate_allowlist": list(model_allowlist),
        "allowlist_hash": allowlist_hash(model_allowlist),
        "selection_metric": "rolling_validation_or_rolling_mae",
        "evidence_context": evidence_context,
        "instructions": [
            "Return only allowlisted candidate records.",
            "Use rolling/validation evidence, complexity, numerical risk, and diversity only.",
            "Do not include final held-out metrics, final winners, final ranks, or post-selection comparisons.",
            "Use null for observation_label or delay_label when not applicable.",
        ],
    }


def prompt_has_forbidden_test_context(payload: dict[str, Any]) -> dict[str, bool]:
    text = json.dumps(payload, sort_keys=True).lower()
    prompt_contains_test_metric = any(
        token in text
        for token in (
            "test_mae",
            "test_rmse",
            "test_smape",
            "held-out test",
            "held out test",
        )
    )
    prompt_contains_test_winner = any(
        token in text
        for token in (
            "test_winner",
            "best_test",
            "test rank",
            "test_rank",
        )
    )
    prompt_contains_posthoc_metric = any(
        token in text
        for token in (
            "posthoc",
            "post-hoc",
            "post_selection_test",
        )
    )
    return {
        "prompt_contains_test_metric": bool(prompt_contains_test_metric),
        "prompt_contains_test_winner": bool(prompt_contains_test_winner),
        "prompt_contains_posthoc_metric": bool(prompt_contains_posthoc_metric),
    }
