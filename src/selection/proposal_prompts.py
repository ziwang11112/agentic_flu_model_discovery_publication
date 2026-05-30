from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.selection.verifier import ALLOWED_MODELS_BY_FAMILY, ALLOWED_OBSERVATION_LABELS


@dataclass(frozen=True)
class ProposalAllowlist:
    families: tuple[str, ...]
    models_by_family: dict[str, tuple[str, ...]]
    observation_labels: tuple[str, ...]
    delay_labels: tuple[str, ...] = ("", "0", "0.0", "1", "1.0", "2", "2.0", "3", "3.0", "mixed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "families": list(self.families),
            "models_by_family": {key: list(values) for key, values in self.models_by_family.items()},
            "observation_labels": list(self.observation_labels),
            "delay_labels": list(self.delay_labels),
        }


def default_proposal_allowlist() -> ProposalAllowlist:
    models_by_family = {
        family.value: tuple(sorted(model_names))
        for family, model_names in sorted(ALLOWED_MODELS_BY_FAMILY.items(), key=lambda item: item[0].value)
    }
    return ProposalAllowlist(
        families=tuple(models_by_family),
        models_by_family=models_by_family,
        observation_labels=tuple(sorted(ALLOWED_OBSERVATION_LABELS)),
    )


def proposal_allowlist_from_config(config: dict[str, Any] | None) -> ProposalAllowlist:
    if not config:
        return default_proposal_allowlist()
    requested_families = tuple(str(value) for value in config.get("families", ()))
    requested_models = set(str(value) for value in config.get("model_names", ()))
    requested_observation_labels = tuple(str(value) for value in config.get("observation_labels", ()))
    default = default_proposal_allowlist()
    families = requested_families or default.families
    models_by_family: dict[str, tuple[str, ...]] = {}
    for family in families:
        allowed_models = default.models_by_family.get(family, ())
        if requested_models:
            allowed_models = tuple(model for model in allowed_models if model in requested_models)
        models_by_family[family] = tuple(sorted(allowed_models))
    return ProposalAllowlist(
        families=tuple(families),
        models_by_family=models_by_family,
        observation_labels=tuple(sorted(requested_observation_labels or default.observation_labels)),
        delay_labels=default.delay_labels,
    )


def compact_evidence_context(model_summary: pd.DataFrame, *, max_rows: int = 24) -> list[dict[str, Any]]:
    columns = [
        "series_name",
        "model_name",
        "model_family",
        "rolling_mean_mae",
        "test_mae",
        "num_free_params",
        "numerical_failure_flag",
        "discovery_observation_map",
        "discovery_delay_weeks",
    ]
    available = [column for column in columns if column in model_summary.columns]
    ordered = model_summary.sort_values(["series_name", "rolling_mean_mae", "model_name"]).loc[:, available]
    records: list[dict[str, Any]] = []
    for _, row in ordered.head(max_rows).iterrows():
        record: dict[str, Any] = {}
        for key, value in row.items():
            if pd.isna(value):
                continue
            if isinstance(value, float):
                record[key] = round(float(value), 6)
            else:
                record[key] = value
        records.append(record)
    return records


def build_system_prompt(allowlist: ProposalAllowlist) -> str:
    return "\n".join(
        [
            "You propose structured candidate records for an offline time-series model-selection audit.",
            "Return JSON only. Do not include prose outside JSON.",
            "Do not propose new model code, new model families, intervention guidance, or operational recommendations.",
            "Every candidate must use only the provided allowlist.",
            "The response schema is: {\"candidates\": [{\"candidate_id\": str, \"family\": str, \"model_name\": str, \"observation_label\": str|null, \"delay_label\": str|null, \"rationale\": str, \"expected_failure_mode\": str}]}",
            "Allowed values:",
            json.dumps(allowlist.to_dict(), sort_keys=True),
        ]
    )


def build_user_prompt(
    *,
    evidence_context: list[dict[str, Any]],
    max_candidates: int,
    objective: str,
) -> str:
    payload = {
        "objective": objective,
        "max_candidates": int(max_candidates),
        "evidence_context": evidence_context,
        "instructions": [
            "Prefer a diverse set of allowed candidate families when justified by the compact evidence.",
            "Keep candidate_id values short and deterministic-looking.",
            "Use null for observation_label or delay_label when not applicable.",
            "Do not use held-out test metrics as selection evidence in rationales.",
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True)
