from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from src.selection.structured_recovery import (
    DEFAULT_POLICIES,
    _candidate_spec,
    generate_structured_toy_task,
    run_structured_recovery,
    run_structured_recovery_from_config,
    structured_candidates_for_task,
)
from src.selection.verifier import verify_candidate


def test_structured_tasks_have_known_observation_labels():
    task = generate_structured_toy_task("lagged_signal_2", seed=1, noise_level=0.0)
    candidates = structured_candidates_for_task(task)

    assert task.true_observation_label == "lagged"
    assert task.true_delay_label == "2"
    assert task.observed.shape == task.latent.shape
    assert {candidate.observation_label for candidate in candidates} >= {"direct", "lagged", "mixture", "proxy"}


def test_structured_candidates_pass_generic_verifier():
    task = generate_structured_toy_task("hidden_component_proxy", seed=2, noise_level=0.05)
    candidates = structured_candidates_for_task(task)

    for index, candidate in enumerate(candidates):
        result = verify_candidate(candidate=_candidate_spec(task, candidate, round_idx=index))
        assert result.valid, result.reasons


def test_pareto_beats_random_and_no_observation_on_recovery():
    summary, by_seed, curve, run_summary = run_structured_recovery(
        tasks=("direct_signal", "lagged_signal_2", "mixture_observation", "hidden_component_proxy"),
        seeds=(1, 2, 3, 4),
        noise_levels=(0.0, 0.05),
        budgets=(3, 5, 10),
        policies=DEFAULT_POLICIES,
        epsilon=0.01,
        seed=42,
    )

    rates = summary.set_index("policy_name")["observation_label_recovery_rate"]
    assert rates["pareto_epsilon"] > rates["random_label_baseline"]
    assert rates["pareto_epsilon"] > rates["no_observation_label_baseline"]
    delay_rates = summary.set_index("policy_name")["delay_label_recovery_rate"]
    assert delay_rates["pareto_epsilon"] > delay_rates["random_label_baseline"]
    assert run_summary["claim_safety_violation_count"] == 0
    assert summary["valid_proposal_rate"].min() == 1.0
    assert not by_seed.empty
    assert not curve.empty


def test_budget_curve_reports_recovery_progression():
    _, _, curve, _ = run_structured_recovery(
        tasks=("lagged_signal_2",),
        seeds=(1, 2),
        noise_levels=(0.0,),
        budgets=(3, 5, 10),
        policies=("pareto_epsilon", "no_observation_label_baseline"),
        epsilon=0.01,
        seed=42,
    )

    pareto = curve.loc[curve["policy_name"] == "pareto_epsilon"].sort_values("budget")
    no_obs = curve.loc[curve["policy_name"] == "no_observation_label_baseline"].sort_values("budget")
    assert pareto["observation_label_recovery_rate"].iloc[-1] >= pareto["observation_label_recovery_rate"].iloc[0]
    assert no_obs["observation_label_recovery_rate"].iloc[-1] == 0.0


def test_config_runner_writes_compact_outputs():
    local_tmp = Path(".pytest_tmp_structured_recovery")
    if local_tmp.exists():
        shutil.rmtree(local_tmp)
    config = {
        "seed": 42,
        "scope": "test_synthetic_structured_recovery",
        "artifacts": {"root_dir": str(local_tmp / "artifacts")},
        "policy": {"epsilon": 0.01},
        "api": {"enabled": False},
        "synthetic_recovery": {
            "tasks": ["direct_signal", "lagged_signal_2"],
            "seeds": [1],
            "noise_levels": [0.0],
            "budgets": [3, 5],
            "policies": ["pareto_epsilon", "random_label_baseline", "no_observation_label_baseline"],
        },
    }

    summary = run_structured_recovery_from_config(config, Path.cwd())
    root = Path(summary["artifact_root"])
    if not root.is_absolute():
        root = Path.cwd() / root

    expected = {
        "synthetic_structured_recovery_summary.csv",
        "synthetic_structured_recovery_by_seed.csv",
        "synthetic_structured_recovery_budget_curve.csv",
        "synthetic_structured_recovery_run_summary.json",
    }
    assert expected == {path.name for path in root.iterdir()}
    compact = pd.read_csv(root / "synthetic_structured_recovery_summary.csv")
    assert {"observation_label_recovery_rate", "delay_label_recovery_rate", "top_epsilon_hit_rate"}.issubset(compact.columns)
    shutil.rmtree(local_tmp)
