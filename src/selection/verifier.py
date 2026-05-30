from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Iterable

from src.selection.schema import BudgetState, CandidateFamily, CandidateSpec, EvidencePacket, VerificationResult


FORECASTING_BASELINES = {
    "last_observed",
    "rolling_mean_2wk",
    "rolling_mean_4wk",
    "arima_auto_small",
    "lagged_ridge",
    "lagged_gradient_boosting",
}
MECHANISTIC_BASELINES = {
    "deterministic_seir",
    "probabilistic_seir",
    "hospitalized_seihr",
    "delayed_observation_seir",
    "fractional_seir",
}
STRUCTURED_SEARCH_MODELS = {"constrained_structure_discovery"}
ABLATION_MODELS = {
    "random_structure_discovery",
    "exhaustive_structure_discovery",
    "validation_only_structure_selection",
    "no_observation_search_discovery",
    "no_stability_discovery",
}
ENSEMBLE_MODELS = {"equal_weight_point_ensemble"}
ALLOWED_OBSERVATION_LABELS = {
    "",
    "direct",
    "lagged_1",
    "lagged_2",
    "mixture",
    "I",
    "H",
    "I+H",
    "delayed_I",
}

ALLOWED_MODELS_BY_FAMILY = {
    CandidateFamily.FORECASTING_BASELINE: FORECASTING_BASELINES,
    CandidateFamily.MECHANISTIC_BASELINE: MECHANISTIC_BASELINES,
    CandidateFamily.STRUCTURED_SEARCH: STRUCTURED_SEARCH_MODELS,
    CandidateFamily.ABLATION: ABLATION_MODELS,
    CandidateFamily.ENSEMBLE: ENSEMBLE_MODELS,
}


def infer_family(model_name: str) -> CandidateFamily:
    for family, names in ALLOWED_MODELS_BY_FAMILY.items():
        if model_name in names:
            return family
    raise ValueError(f"Unsupported model_name={model_name!r}")


def _has_absolute_path(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_has_absolute_path(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_has_absolute_path(item) for item in value)
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text:
        return False
    return PureWindowsPath(text).is_absolute() or PurePosixPath(text).is_absolute()


def _result(candidate_id: str, checks: dict[str, bool], reasons: list[str], duplicate: bool = False) -> VerificationResult:
    valid = all(checks.values()) and not duplicate
    return VerificationResult(
        candidate_id=candidate_id,
        valid=valid,
        vetoed=not valid,
        reasons=tuple(reasons),
        schema_valid=checks.get("schema_valid", True),
        family_valid=checks.get("family_valid", True),
        leakage_safe=checks.get("leakage_safe", True),
        budget_safe=checks.get("budget_safe", True),
        artifact_safe=checks.get("artifact_safe", True),
        claim_safe=checks.get("claim_safe", True),
        duplicate=duplicate,
    )


def verify_candidate(
    candidate: CandidateSpec,
    *,
    budget: BudgetState | None = None,
    seen_candidate_ids: Iterable[str] | None = None,
) -> VerificationResult:
    reasons: list[str] = []
    checks = {
        "schema_valid": True,
        "family_valid": True,
        "leakage_safe": True,
        "budget_safe": True,
        "artifact_safe": True,
        "claim_safe": True,
    }

    if not candidate.candidate_id or not candidate.model_name:
        checks["schema_valid"] = False
        reasons.append("missing_required_candidate_field")

    try:
        family = candidate.normalized_family()
    except ValueError:
        checks["family_valid"] = False
        reasons.append("invalid_candidate_family")
        family = None

    if family is not None and candidate.model_name not in ALLOWED_MODELS_BY_FAMILY.get(family, set()):
        checks["family_valid"] = False
        reasons.append("model_name_not_allowed_for_family")

    if candidate.observation_label is not None and str(candidate.observation_label) not in ALLOWED_OBSERVATION_LABELS:
        checks["schema_valid"] = False
        reasons.append("invalid_observation_label")

    if candidate.delay_label is not None and str(candidate.delay_label).strip() != "":
        try:
            delay_value = float(candidate.delay_label)
        except (TypeError, ValueError):
            checks["schema_valid"] = False
            reasons.append("invalid_delay_label")
        else:
            if delay_value < 0 or abs(delay_value - round(delay_value)) > 1.0e-9:
                checks["schema_valid"] = False
                reasons.append("invalid_delay_label")

    if _has_absolute_path(candidate.metadata):
        checks["artifact_safe"] = False
        reasons.append("absolute_artifact_path_in_metadata")

    if budget is not None and budget.evaluated_candidates >= budget.max_candidates:
        checks["budget_safe"] = False
        reasons.append("candidate_budget_exhausted")

    duplicate = candidate.candidate_id in set(seen_candidate_ids or [])
    if duplicate:
        reasons.append("duplicate_candidate_id")

    return _result(candidate.candidate_id, checks, reasons, duplicate=duplicate)


def verify_evidence(
    evidence: EvidencePacket,
    *,
    allow_posthoc_selection_metrics: bool = False,
) -> VerificationResult:
    reasons: list[str] = []
    checks = {
        "schema_valid": True,
        "family_valid": True,
        "leakage_safe": True,
        "budget_safe": True,
        "artifact_safe": True,
        "claim_safe": True,
    }

    if not evidence.candidate_id or not evidence.model_name or not evidence.series_name:
        checks["schema_valid"] = False
        reasons.append("missing_required_evidence_field")

    try:
        family = evidence.normalized_family()
    except ValueError:
        checks["family_valid"] = False
        reasons.append("invalid_evidence_family")
        family = None

    if family is not None and evidence.model_name not in ALLOWED_MODELS_BY_FAMILY.get(family, set()):
        checks["family_valid"] = False
        reasons.append("model_name_not_allowed_for_family")

    if not allow_posthoc_selection_metrics:
        leaked_keys = [key for key in evidence.selection_metrics if "test" in key.lower()]
        if leaked_keys:
            checks["leakage_safe"] = False
            reasons.append("test_metric_in_selection_evidence")

    if _has_absolute_path(evidence.metadata):
        checks["artifact_safe"] = False
        reasons.append("absolute_artifact_path_in_metadata")

    if evidence.numerical_failure_flag and evidence.supports_positive_claim:
        checks["claim_safe"] = False
        reasons.append("numerical_failure_cannot_support_positive_claim")

    return _result(evidence.candidate_id, checks, reasons)
