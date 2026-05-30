import pandas as pd

from src.selection.stage2 import REPLAY_POLICIES, run_budgeted_candidate_replay


def test_budgeted_replay_writes_expected_policy_rows():
    summary = pd.read_csv("artifacts_discovery_ablation/benchmark_model_summary.csv")
    recommendations = pd.read_csv("artifacts_discovery_ablation/paper_recommendation_table.csv")

    replay = run_budgeted_candidate_replay(summary, recommendations, budgets=(3, 5), epsilon=0.02, seed=123)

    assert set(replay["policy_name"]) == set(REPLAY_POLICIES)
    assert set(replay["k"]) == {3, 5}
    assert replay["test_metric_role"].eq("posthoc_descriptive").all()
    assert replay["selected_model_at_k"].notna().all()
    assert replay["rolling_mean_mae_at_k"].notna().all()
    assert replay["policy_disagreement_rate"].between(0.0, 1.0).all()


def test_budgeted_replay_is_deterministic_for_fixed_seed():
    summary = pd.read_csv("artifacts_discovery_ablation/benchmark_model_summary.csv")
    recommendations = pd.read_csv("artifacts_discovery_ablation/paper_recommendation_table.csv")

    first = run_budgeted_candidate_replay(summary, recommendations, budgets=(3, 10), epsilon=0.02, seed=99)
    second = run_budgeted_candidate_replay(summary, recommendations, budgets=(3, 10), epsilon=0.02, seed=99)

    pd.testing.assert_frame_equal(first, second)


def test_candidate_count_to_top_epsilon_is_reported():
    summary = pd.read_csv("artifacts_discovery_ablation/benchmark_model_summary.csv")
    recommendations = pd.read_csv("artifacts_discovery_ablation/paper_recommendation_table.csv")

    replay = run_budgeted_candidate_replay(summary, recommendations, budgets=(3, 5, 10, 15), epsilon=0.02, seed=42)

    assert "candidate_count_to_top_epsilon" in replay.columns
    assert replay["candidate_count_to_top_epsilon"].notna().any()
    assert replay["test_mae_at_k"].notna().any()
