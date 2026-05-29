import pandas as pd

from src.selection.evidence_auditor import audit_claim_boundary, flagged_rows_cannot_support_positive_claim
from src.selection.schema import EvidencePacket


def test_flagged_rows_cannot_support_positive_claim():
    packets = [
        EvidencePacket(
            candidate_id="safe",
            model_name="rolling_mean_4wk",
            family="forecasting_baseline",
            series_name="Overall",
        ),
        EvidencePacket(
            candidate_id="bad",
            model_name="constrained_structure_discovery",
            family="structured_search",
            series_name=">=65 yr",
            numerical_failure_flag=True,
            supports_positive_claim=True,
        ),
    ]

    assert not flagged_rows_cannot_support_positive_claim(packets)


def test_claim_boundary_audit_detects_cautious_labels():
    recommendations = pd.DataFrame(
        [
            {
                "series_name": "0-4 yr",
                "recommended_model": "constrained_structure_discovery",
                "best_test_model": "deterministic_seir",
                "best_rolling_model": "constrained_structure_discovery",
                "observation_map": "delayed_I",
            },
            {
                "series_name": ">=65 yr",
                "recommended_model": "rolling_mean_4wk",
                "best_test_model": "rolling_mean_4wk",
                "best_rolling_model": "deterministic_seir",
                "observation_map": "",
            },
        ]
    )
    observation_impact = pd.DataFrame(
        [
            {
                "series_name": "0-4 yr",
                "delta_rolling_mean_mae_no_observation_minus_constrained": 0.3,
            }
        ]
    )
    numerical_summary = pd.DataFrame(
        [{"series_name": ">=65 yr", "model_name": "constrained_structure_discovery", "numerical_failure_flag": True}]
    )
    multiseason = pd.DataFrame([{"age_group": "0-4 yr", "interpretation": "mixed season-dependent evidence"}])

    audit = audit_claim_boundary(
        recommendations=recommendations,
        observation_impact=observation_impact,
        numerical_summary=numerical_summary,
        multiseason_key_findings=multiseason,
    )

    assert audit.no_single_global_winner
    assert audit.age_or_group_specific_signal
    assert audit.simple_baseline_competitive
    assert audit.flagged_rows_descriptive_only
    assert audit.posthoc_comparison_not_selection
    assert audit.multiseason_mixed_if_present is True
    assert "global structured-search superiority" in audit.rejected_claims
