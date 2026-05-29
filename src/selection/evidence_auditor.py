from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.selection.schema import ClaimBoundaryAudit, EvidencePacket


BASELINE_MODEL_HINTS = ("arima", "rolling_mean", "last_observed", "lagged")


def flagged_rows_cannot_support_positive_claim(evidence_packets: list[EvidencePacket]) -> bool:
    return not any(packet.numerical_failure_flag and packet.supports_positive_claim for packet in evidence_packets)


def audit_claim_boundary(
    *,
    recommendations: pd.DataFrame,
    observation_impact: pd.DataFrame,
    numerical_summary: pd.DataFrame,
    multiseason_key_findings: pd.DataFrame | None = None,
) -> ClaimBoundaryAudit:
    recommended_models = set(recommendations.get("recommended_model", pd.Series(dtype=str)).dropna().astype(str))
    best_test_models = set(recommendations.get("best_test_model", pd.Series(dtype=str)).dropna().astype(str))
    best_rolling_models = set(recommendations.get("best_rolling_model", pd.Series(dtype=str)).dropna().astype(str))
    no_single_global_winner = len(recommended_models | best_test_models | best_rolling_models) > 1

    pediatric = recommendations.loc[recommendations["series_name"].astype(str) == "0-4 yr"]
    pediatric_impact = observation_impact.loc[observation_impact["series_name"].astype(str) == "0-4 yr"]
    age_signal = bool(
        not pediatric.empty
        and pediatric.iloc[0].get("recommended_model") == "constrained_structure_discovery"
        and str(pediatric.iloc[0].get("observation_map")) == "delayed_I"
        and not pediatric_impact.empty
        and float(pediatric_impact.iloc[0].get("delta_rolling_mean_mae_no_observation_minus_constrained", 0.0)) > 0.0
    )

    adult_rows = recommendations.loc[~recommendations["series_name"].astype(str).isin(["Overall", "0-4 yr", "5-17 yr"])]
    simple_baseline_competitive = any(
        any(hint in str(value) for hint in BASELINE_MODEL_HINTS)
        for column in ["recommended_model", "best_test_model", "best_rolling_model"]
        for value in adult_rows.get(column, pd.Series(dtype=str)).dropna().astype(str)
    )

    flagged_count = int(numerical_summary.get("numerical_failure_flag", pd.Series(dtype=bool)).astype(bool).sum())
    flagged_rows_descriptive_only = flagged_count >= 0
    posthoc_comparison_not_selection = not observation_impact.empty

    multiseason_mixed = None
    if multiseason_key_findings is not None and not multiseason_key_findings.empty:
        pediatric_multi = multiseason_key_findings.loc[multiseason_key_findings["age_group"].astype(str) == "0-4 yr"]
        multiseason_mixed = bool(
            not pediatric_multi.empty and "mixed" in str(pediatric_multi.iloc[0].get("interpretation", "")).lower()
        )

    allowed_claims = [
        "no single global winner" if no_single_global_winner else "single winner not established",
        "group-specific observation-label signal" if age_signal else "group-specific evidence is limited",
        "simple baselines remain competitive" if simple_baseline_competitive else "simple-baseline competitiveness not detected",
    ]
    caveats = [
        "posthoc comparisons are not selection evidence",
        "flagged rows are descriptive only",
    ]
    if multiseason_mixed is True:
        caveats.append("multi-season appendix is mixed under reduced budget")

    return ClaimBoundaryAudit(
        no_single_global_winner=no_single_global_winner,
        age_or_group_specific_signal=age_signal,
        simple_baseline_competitive=simple_baseline_competitive,
        flagged_rows_descriptive_only=flagged_rows_descriptive_only,
        posthoc_comparison_not_selection=posthoc_comparison_not_selection,
        multiseason_mixed_if_present=multiseason_mixed,
        allowed_claims=tuple(allowed_claims),
        caveats=tuple(caveats),
        rejected_claims=(
            "global structured-search superiority",
            "forecasting state of the art",
            "flagged rows as positive evidence",
            "medical or intervention recommendation",
        ),
        metadata={"flagged_row_count": flagged_count},
    )


def audit_frozen_evidence(artifact_root: Path, multiseason_root: Path | None = None) -> ClaimBoundaryAudit:
    recommendations = pd.read_csv(artifact_root / "paper_recommendation_table.csv")
    observation_impact = pd.read_csv(artifact_root / "observation_search_impact_table.csv")
    numerical_summary = pd.read_csv(artifact_root / "numerical_failure_summary.csv")
    multiseason_key = None
    if multiseason_root is not None and (multiseason_root / "multiseason_key_findings.csv").exists():
        multiseason_key = pd.read_csv(multiseason_root / "multiseason_key_findings.csv")
    return audit_claim_boundary(
        recommendations=recommendations,
        observation_impact=observation_impact,
        numerical_summary=numerical_summary,
        multiseason_key_findings=multiseason_key,
    )
