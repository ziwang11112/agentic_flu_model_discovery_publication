from src.selection.schema import BudgetState, CandidateFamily, CandidateSpec
from src.selection.toy_tasks import generate_toy_series, run_toy_recovery


def test_candidate_family_normalizes_from_string():
    candidate = CandidateSpec(
        candidate_id="c1",
        family="forecasting_baseline",
        model_name="rolling_mean_4wk",
    )

    assert candidate.normalized_family() == CandidateFamily.FORECASTING_BASELINE
    assert candidate.to_dict()["family"] == "forecasting_baseline"


def test_budget_remaining_is_nonnegative():
    assert BudgetState(max_candidates=3, evaluated_candidates=1).remaining == 2
    assert BudgetState(max_candidates=3, evaluated_candidates=5).remaining == 0


def test_toy_tasks_are_generic_numerical_time_series():
    task = generate_toy_series("lagged_observation", seed=7)

    assert task.true_observation_label == "lagged_2"
    assert task.observed.shape == task.latent.shape
    assert task.scenario_name == "lagged_observation"


def test_toy_recovery_returns_expected_columns():
    summary = run_toy_recovery(["sinusoidal_direct", "lagged_observation"], [1])

    assert set(summary["true_observation_label"]) == {"direct", "lagged_2"}
    assert {"scenario_name", "selected_observation_label", "recovered"}.issubset(summary.columns)
