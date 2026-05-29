import shutil
from pathlib import Path

import pandas as pd

from src.selection.orchestrator import run_offline_selection_evaluation
from src.selection.proposer import SeedCandidateProposer


def _local_test_root() -> Path:
    root = Path(".pytest_tmp") / "selection_orchestrator_smoke"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _smoke_config(output_root: Path) -> dict:
    return {
        "data": {
            "frozen_artifact_root": "artifacts_discovery_ablation",
            "multiseason_artifact_root": "artifacts_multiseason_robustness_compact",
        },
        "artifacts": {"root_dir": str(output_root / "selection_outputs")},
        "policy": {"epsilon": 0.02, "max_candidates": 30},
        "toy_tasks": {"scenarios": ["sinusoidal_direct", "lagged_observation"], "seeds": [1, 2]},
    }


def test_deterministic_proposer_stable_output():
    summary = pd.read_csv("artifacts_discovery_ablation/benchmark_model_summary.csv")
    proposer = SeedCandidateProposer()

    first = proposer.propose(summary)
    second = proposer.propose(summary)

    assert [candidate.to_dict() for candidate in first] == [candidate.to_dict() for candidate in second]
    assert first


def test_orchestrator_smoke_writes_compact_outputs():
    output_root = _local_test_root()
    summary = run_offline_selection_evaluation(_smoke_config(output_root), Path.cwd())
    out = output_root / "selection_outputs"

    assert summary["external_api_used"] is False
    assert summary["toy_recovery_rate"] == 1.0
    for name in [
        "policy_recommendations.csv",
        "pareto_frontiers.csv",
        "claim_audit_scores.csv",
        "toy_observation_recovery_summary.csv",
        "iterative_refinement_traces.jsonl",
        "run_summary.json",
    ]:
        assert (out / name).exists()

    recommendations = pd.read_csv(out / "policy_recommendations.csv")
    assert {"pareto_epsilon", "weighted_rubric", "hard_veto_decision_tree"}.issubset(
        set(recommendations["policy_name"])
    )

    heavy_names = {"forecast_trace.csv", "rolling_origin_forecasts.csv", "metrics.json", "leaderboard.csv"}
    assert not any(path.name in heavy_names for path in out.rglob("*"))
