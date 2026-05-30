from src.selection.stage2 import DEFAULT_TOY_SCENARIOS, TOY_POLICIES, run_toy_policy_recovery
from src.selection.toy_tasks import generate_toy_series, score_observation_label_candidates


def test_stage2_toy_scenarios_are_supported():
    for scenario in DEFAULT_TOY_SCENARIOS:
        task = generate_toy_series(scenario, seed=1)
        scores = score_observation_label_candidates(task)

        assert task.observed.shape == task.latent.shape
        assert set(scores) == {"direct", "lagged_1", "lagged_2", "mixture"}
        assert "rolling_error" in scores[task.true_observation_label]


def test_toy_policy_recovery_reports_policy_metrics():
    recovery = run_toy_policy_recovery(scenarios=DEFAULT_TOY_SCENARIOS, seeds=(1, 2), seed=42)

    assert set(recovery["policy_name"]) == set(TOY_POLICIES)
    assert set(recovery["scenario_name"]) == set(DEFAULT_TOY_SCENARIOS)
    assert {
        "observation_label_recovery_rate",
        "delay_label_recovery_rate",
        "mean_rolling_error",
    }.issubset(recovery.columns)
    assert recovery["observation_label_recovery_rate"].between(0.0, 1.0).all()
    assert recovery["delay_label_recovery_rate"].between(0.0, 1.0).all()
    assert recovery["mean_rolling_error"].ge(0.0).all()


def test_pareto_and_weighted_recover_easy_direct_signal():
    recovery = run_toy_policy_recovery(scenarios=("direct_signal",), seeds=(1, 2), seed=42)
    policy_rows = recovery.loc[recovery["policy_name"].isin(["pareto_epsilon", "weighted_score"])]

    assert policy_rows["observation_label_recovered"].all()
    assert policy_rows["delay_label_recovered"].all()
