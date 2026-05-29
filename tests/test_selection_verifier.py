from src.selection.schema import BudgetState, CandidateSpec, EvidencePacket
from src.selection.verifier import verify_candidate, verify_evidence


def test_invalid_candidate_is_rejected():
    candidate = CandidateSpec(
        candidate_id="bad",
        family="forecasting_baseline",
        model_name="constrained_structure_discovery",
    )

    result = verify_candidate(candidate)

    assert not result.valid
    assert result.vetoed
    assert "model_name_not_allowed_for_family" in result.reasons


def test_malformed_candidate_missing_required_field_is_rejected():
    candidate = CandidateSpec(
        candidate_id="",
        family="forecasting_baseline",
        model_name="rolling_mean_4wk",
    )

    result = verify_candidate(candidate)

    assert not result.schema_valid
    assert "missing_required_candidate_field" in result.reasons


def test_no_leakage_guard_rejects_test_metric_in_selection_evidence():
    evidence = EvidencePacket(
        candidate_id="c1",
        model_name="rolling_mean_4wk",
        family="forecasting_baseline",
        series_name="Overall",
        selection_metrics={"test_mae": 0.1},
    )

    result = verify_evidence(evidence)

    assert not result.valid
    assert not result.leakage_safe
    assert "test_metric_in_selection_evidence" in result.reasons


def test_posthoc_test_metric_allowed_when_explicitly_marked():
    evidence = EvidencePacket(
        candidate_id="c1",
        model_name="rolling_mean_4wk",
        family="forecasting_baseline",
        series_name="Overall",
        selection_metrics={"test_mae": 0.1},
    )

    result = verify_evidence(evidence, allow_posthoc_selection_metrics=True)

    assert result.valid


def test_numerical_failure_cannot_support_positive_claim():
    evidence = EvidencePacket(
        candidate_id="c1",
        model_name="constrained_structure_discovery",
        family="structured_search",
        series_name=">=65 yr",
        numerical_failure_flag=True,
        supports_positive_claim=True,
    )

    result = verify_evidence(evidence)

    assert not result.claim_safe
    assert "numerical_failure_cannot_support_positive_claim" in result.reasons


def test_duplicate_candidate_id_is_rejected():
    candidate = CandidateSpec(
        candidate_id="dup",
        family="forecasting_baseline",
        model_name="rolling_mean_4wk",
    )

    result = verify_candidate(candidate, seen_candidate_ids={"dup"})

    assert not result.valid
    assert result.duplicate
    assert "duplicate_candidate_id" in result.reasons


def test_budget_and_absolute_path_checks():
    candidate = CandidateSpec(
        candidate_id="c1",
        family="forecasting_baseline",
        model_name="rolling_mean_4wk",
        metadata={"artifact_path": "D:\\temp\\artifact.csv"},
    )

    result = verify_candidate(candidate, budget=BudgetState(max_candidates=1, evaluated_candidates=1))

    assert not result.budget_safe
    assert not result.artifact_safe
    assert "candidate_budget_exhausted" in result.reasons
    assert "absolute_artifact_path_in_metadata" in result.reasons
