from src.selection.policies import hard_veto_decision_tree_policy, pareto_epsilon_policy, pareto_frontier, weighted_score_policy
from src.selection.schema import EvidencePacket


def _packet(
    candidate_id: str,
    model_name: str,
    family: str,
    rolling: float,
    complexity: float,
    *,
    failure: bool = False,
    validation: float | None = None,
) -> EvidencePacket:
    metrics = {"validation_mae": validation} if validation is not None else {"selection_score": rolling}
    return EvidencePacket(
        candidate_id=candidate_id,
        model_name=model_name,
        family=family,
        series_name="Overall",
        selection_metrics=metrics,
        rolling_mean_mae=rolling,
        num_free_params=complexity,
        numerical_failure_flag=failure,
    )


def test_pareto_frontier_excludes_flagged_candidate():
    packets = [
        _packet("a", "rolling_mean_4wk", "forecasting_baseline", 1.0, 0.0),
        _packet("b", "deterministic_seir", "mechanistic_baseline", 0.9, 8.0),
        _packet("c", "constrained_structure_discovery", "structured_search", 0.1, 4.0, failure=True),
    ]

    frontier = pareto_frontier(packets)

    assert {packet.candidate_id for packet in frontier} == {"a", "b"}


def test_pareto_policy_has_deterministic_tie_break():
    packets = [
        _packet("b", "deterministic_seir", "mechanistic_baseline", 1.0, 3.0),
        _packet("a", "rolling_mean_4wk", "forecasting_baseline", 1.0, 1.0),
    ]

    decision = pareto_epsilon_policy(packets, epsilon=0.0)

    assert decision.selected_candidate_id == "a"
    assert decision.metadata["frontier_size"] == 1


def test_weighted_score_policy_is_deterministic():
    packets = [
        _packet("a", "rolling_mean_4wk", "forecasting_baseline", 1.0, 0.0),
        _packet("b", "deterministic_seir", "mechanistic_baseline", 0.5, 8.0),
    ]

    first = weighted_score_policy(packets)
    second = weighted_score_policy(list(reversed(packets)))

    assert first.selected_candidate_id == second.selected_candidate_id
    assert first.scores == second.scores


def test_hard_veto_decision_tree_prefers_simple_baseline_within_epsilon():
    packets = [
        _packet("baseline", "rolling_mean_4wk", "forecasting_baseline", 1.01, 0.0),
        _packet("manual", "deterministic_seir", "mechanistic_baseline", 1.0, 8.0),
    ]

    decision = hard_veto_decision_tree_policy(packets, baseline_epsilon=0.02)

    assert decision.selected_candidate_id == "baseline"
    assert decision.rationale == "baseline_sufficient"


def test_hard_veto_decision_tree_prefers_observation_label_search_when_better():
    packets = [
        _packet("constrained", "constrained_structure_discovery", "structured_search", 0.7, 4.0),
        _packet("no_obs", "no_observation_search_discovery", "ablation", 1.0, 4.0),
    ]

    decision = hard_veto_decision_tree_policy(packets, baseline_epsilon=0.02)

    assert decision.selected_candidate_id == "constrained"
    assert decision.rationale == "observation_label_search_preferred"
