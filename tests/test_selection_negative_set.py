from src.selection.schema import CandidateSpec
from src.selection.stage2 import run_verifier_negative_set
from src.selection.verifier import verify_candidate


def test_verifier_negative_set_rejects_all_cases():
    frame = run_verifier_negative_set()

    assert frame["total_negative_cases"].iloc[0] == len(frame)
    assert frame["rejected_cases"].iloc[0] == len(frame)
    assert frame["rejection_rate"].iloc[0] == 1.0
    assert frame["rejected"].all()


def test_negative_set_includes_required_rejection_reasons():
    frame = run_verifier_negative_set()
    reasons = ";".join(frame["rejection_reasons"].astype(str))

    for expected in [
        "missing_required_candidate_field",
        "duplicate_candidate_id",
        "absolute_artifact_path_in_metadata",
        "test_metric_in_selection_evidence",
        "numerical_failure_cannot_support_positive_claim",
        "invalid_observation_label",
        "invalid_delay_label",
    ]:
        assert expected in reasons


def test_invalid_observation_and_delay_labels_are_rejected():
    bad = CandidateSpec(
        candidate_id="bad",
        family="forecasting_baseline",
        model_name="rolling_mean_4wk",
        observation_label="unsupported",
        delay_label="1.5",
    )

    result = verify_candidate(bad)

    assert not result.valid
    assert "invalid_observation_label" in result.reasons
    assert "invalid_delay_label" in result.reasons
