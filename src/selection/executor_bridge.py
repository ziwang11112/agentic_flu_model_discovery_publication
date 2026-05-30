from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.selection.schema import CandidateFamily, CandidateSpec, EvidencePacket
from src.selection.structured_recovery import StructuredCandidate, StructuredToyTask, structured_candidates_for_task
from src.selection.verifier import infer_family


DEFAULT_EXECUTION_ALLOWLIST = (
    "last_observed",
    "rolling_mean_4wk",
    "arima_auto_small",
    "deterministic_seir",
    "delayed_observation_seir",
    "constrained_structure_discovery",
    "no_observation_search_discovery",
    "validation_only_structure_selection",
    "random_structure_discovery",
    "exhaustive_structure_discovery",
)
REALDATA_SERIES_ALIASES = {
    ">=65 yr": ">= 65 yr",
    ">= 65 yr": ">= 65 yr",
    "65+ yr": ">= 65 yr",
}


@dataclass(frozen=True)
class CandidateExecutionRecord:
    spec: CandidateSpec
    evidence: EvidencePacket
    observation_label: str
    delay_label: str
    candidate_family_label: str
    rolling_error: float
    posthoc_test_mae: float | None = None


def stable_int(seed: int, *parts: object) -> int:
    key = ":".join([str(seed), *(str(part) for part in parts)])
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


def allowlist_hash(model_names: list[str] | tuple[str, ...]) -> str:
    payload = json.dumps(sorted(str(value) for value in model_names), separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def normalize_series_name(series_name: str) -> str:
    return REALDATA_SERIES_ALIASES.get(str(series_name), str(series_name))


def prompt_audit_record(
    *,
    series_name: str,
    proposer_type: str,
    prompt_payload: dict[str, Any],
    model_allowlist: list[str] | tuple[str, ...],
) -> dict[str, Any]:
    text = json.dumps(prompt_payload, sort_keys=True).lower()
    contains_test_metric = any(token in text for token in ("test_mae", "test_rmse", "test_smape", "held-out test"))
    contains_test_winner = any(token in text for token in ("test_winner", "best_test", "test rank", "test_rank"))
    contains_posthoc = any(token in text for token in ("posthoc", "post-hoc", "post_selection_test"))
    return {
        "series_name": series_name,
        "proposer_type": proposer_type,
        "prompt_contains_test_metric": bool(contains_test_metric),
        "prompt_contains_test_winner": bool(contains_test_winner),
        "prompt_contains_posthoc_metric": bool(contains_posthoc),
        "allowlist_hash": allowlist_hash(model_allowlist),
        "safe_prompt_passed": not bool(contains_test_metric or contains_test_winner or contains_posthoc),
    }


def synthetic_execution_records(task: StructuredToyTask) -> list[CandidateExecutionRecord]:
    rows: list[CandidateExecutionRecord] = []
    for idx, candidate in enumerate(structured_candidates_for_task(task)):
        spec = CandidateSpec(
            candidate_id=f"{task.task_name}:{task.seed}:{task.noise_level:g}:{candidate.candidate_id}",
            family=candidate.family,
            model_name=candidate.model_name,
            observation_label=candidate.observation_label,
            delay_label=candidate.delay_label,
            round_idx=idx,
            proposer_name="candidate_execution",
            rationale="generic structured time-series candidate",
            metadata={"task_name": task.task_name, "candidate_label": candidate.candidate_id},
        )
        rolling_error = float(np.mean(np.abs(task.observed - candidate.values)))
        evidence = EvidencePacket(
            candidate_id=spec.candidate_id,
            model_name=candidate.model_name,
            family=candidate.family,
            series_name=task.task_name,
            selection_metrics={"selection_score": rolling_error},
            rolling_mean_mae=rolling_error,
            num_free_params=float(candidate.complexity),
            numerical_failure_flag=False,
            supports_positive_claim=False,
            metadata={
                "candidate_label": candidate.candidate_id,
                "observation_label": candidate.observation_label,
                "delay_label": candidate.delay_label,
                "candidate_family_label": candidate.candidate_family_label,
            },
        )
        rows.append(
            CandidateExecutionRecord(
                spec=spec,
                evidence=evidence,
                observation_label=candidate.observation_label,
                delay_label=candidate.delay_label,
                candidate_family_label=candidate.candidate_family_label,
                rolling_error=rolling_error,
            )
        )
    return rows


def synthetic_order(
    proposer_type: str,
    records: list[CandidateExecutionRecord],
    *,
    task: StructuredToyTask,
    seed: int,
) -> list[CandidateExecutionRecord]:
    if proposer_type == "exhaustive_oracle":
        return sorted(records, key=lambda row: (row.rolling_error, row.spec.candidate_id))
    if proposer_type == "random_candidate_proposer":
        return sorted(records, key=lambda row: stable_int(seed, proposer_type, task.task_name, task.seed, task.noise_level, row.spec.candidate_id))
    if proposer_type == "no_observation_label_baseline":
        return [row for row in records if row.observation_label == "direct"]
    if proposer_type == "failure_guided_proposer":
        priority = {"direct": 2, "lagged": 0 if task.task_name.startswith("lagged") else 1, "mixture": 0 if "mixture" in task.task_name else 2, "proxy": 0 if "proxy" in task.task_name else 3}
        return sorted(records, key=lambda row: (priority.get(row.observation_label, 9), row.rolling_error, row.spec.candidate_id))
    if proposer_type == "mock_api_proposer":
        priority_by_task = {
            "direct_signal": ("direct", "lagged", "mixture", "proxy"),
            "lagged_signal_1": ("lagged", "direct", "mixture", "proxy"),
            "lagged_signal_2": ("lagged", "mixture", "direct", "proxy"),
            "mixture_observation": ("mixture", "lagged", "direct", "proxy"),
            "hidden_component_proxy": ("proxy", "mixture", "direct", "lagged"),
        }
        order = {label: idx for idx, label in enumerate(priority_by_task.get(task.task_name, ()))}
        return sorted(records, key=lambda row: (order.get(row.observation_label, 9), row.rolling_error, row.spec.candidate_id))
    # deterministic_seed_proposer and fallback preserve repository candidate order.
    return list(records)


def _real_observation_label(row: pd.Series) -> str:
    value = row.get("discovery_observation_map")
    if pd.notna(value):
        return str(value)
    return "not_applicable"


def _real_delay_label(row: pd.Series) -> str:
    value = row.get("discovery_delay_weeks")
    if pd.notna(value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        return str(int(number)) if abs(number - round(number)) < 1.0e-9 else str(number)
    return ""


def realdata_execution_records(
    model_summary: pd.DataFrame,
    *,
    series_name: str,
    model_allowlist: list[str] | tuple[str, ...] = DEFAULT_EXECUTION_ALLOWLIST,
) -> list[CandidateExecutionRecord]:
    normalized = normalize_series_name(series_name)
    subset = model_summary.loc[model_summary["series_name"].astype(str) == normalized].copy()
    subset = subset.loc[subset["model_name"].astype(str).isin(set(model_allowlist))]
    rows: list[CandidateExecutionRecord] = []
    for _, row in subset.iterrows():
        model_name = str(row["model_name"])
        family = infer_family(model_name)
        observation_label = _real_observation_label(row)
        delay_label = _real_delay_label(row)
        candidate_id = f"{normalized}:{model_name}"
        rolling = float(row["rolling_mean_mae"]) if pd.notna(row.get("rolling_mean_mae")) else float("inf")
        numerical_failure = str(row.get("numerical_failure_flag", "False")).lower() in {"true", "1", "yes"}
        spec = CandidateSpec(
            candidate_id=candidate_id,
            family=family,
            model_name=model_name,
            observation_label=observation_label,
            delay_label=delay_label,
            proposer_name="realdata_replay",
            rationale="present in frozen compact summary",
            metadata={"series_name": normalized, "evidence_mode": "frozen_replay"},
        )
        evidence = EvidencePacket(
            candidate_id=candidate_id,
            model_name=model_name,
            family=family,
            series_name=normalized,
            selection_metrics={"rolling_validation_mae": rolling, "selection_score": rolling},
            posthoc_metrics={"post_selection_test_mae": float(row["test_mae"]) if pd.notna(row.get("test_mae")) else None},
            rolling_mean_mae=rolling,
            num_free_params=float(row["num_free_params"]) if pd.notna(row.get("num_free_params")) else None,
            numerical_failure_flag=numerical_failure,
            supports_positive_claim=False,
            metadata={"evidence_mode": "frozen_replay", "selection_metric_source": "rolling_mean_mae"},
        )
        rows.append(
            CandidateExecutionRecord(
                spec=spec,
                evidence=evidence,
                observation_label=observation_label,
                delay_label=delay_label,
                candidate_family_label=family.value,
                rolling_error=rolling,
                posthoc_test_mae=evidence.posthoc_metrics.get("post_selection_test_mae"),
            )
        )
    return rows


def realdata_order(
    proposer_type: str,
    records: list[CandidateExecutionRecord],
    *,
    series_name: str,
    seed: int,
) -> list[CandidateExecutionRecord]:
    if proposer_type == "oracle_full_candidate_ranking":
        return sorted(records, key=lambda row: (row.rolling_error, row.spec.model_name))
    if proposer_type == "random_candidate_proposer":
        return sorted(records, key=lambda row: stable_int(seed, proposer_type, series_name, row.spec.model_name))
    if proposer_type == "mock_api_proposer":
        preferred = [
            "constrained_structure_discovery",
            "delayed_observation_seir",
            "arima_auto_small",
            "rolling_mean_4wk",
            "no_observation_search_discovery",
            "validation_only_structure_selection",
            "deterministic_seir",
            "last_observed",
            "random_structure_discovery",
            "exhaustive_structure_discovery",
        ]
        priority = {model_name: idx for idx, model_name in enumerate(preferred)}
        return sorted(records, key=lambda row: (priority.get(row.spec.model_name, 99), row.rolling_error, row.spec.model_name))
    # Deterministic seed proposer uses simple-to-complex allowlist order.
    preferred = [
        "last_observed",
        "rolling_mean_4wk",
        "arima_auto_small",
        "deterministic_seir",
        "delayed_observation_seir",
        "constrained_structure_discovery",
        "no_observation_search_discovery",
        "validation_only_structure_selection",
        "random_structure_discovery",
        "exhaustive_structure_discovery",
    ]
    priority = {model_name: idx for idx, model_name in enumerate(preferred)}
    return sorted(records, key=lambda row: (priority.get(row.spec.model_name, 99), row.spec.model_name))
