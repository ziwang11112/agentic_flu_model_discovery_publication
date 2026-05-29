from __future__ import annotations

from collections import defaultdict
from typing import Iterable

import numpy as np

from src.selection.schema import CandidateFamily, EvidencePacket, PolicyDecision


def _finite(value: float | None, fallback: float = float("inf")) -> float:
    if value is None:
        return fallback
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return number if np.isfinite(number) else fallback


def _selection_score(packet: EvidencePacket) -> float:
    if packet.selection_metrics.get("validation_mae") is not None:
        return _finite(packet.selection_metrics.get("validation_mae"))
    if packet.selection_metrics.get("selection_score") is not None:
        return _finite(packet.selection_metrics.get("selection_score"))
    return _finite(packet.rolling_mean_mae)


def _objectives(packet: EvidencePacket) -> tuple[float, float, float, float]:
    return (
        _selection_score(packet),
        _finite(packet.rolling_mean_mae),
        _finite(packet.num_free_params, fallback=0.0),
        1.0 if packet.numerical_failure_flag else 0.0,
    )


def _dominates(left: EvidencePacket, right: EvidencePacket, epsilon: float) -> bool:
    left_obj = _objectives(left)
    right_obj = _objectives(right)
    no_worse = all(l <= r + epsilon for l, r in zip(left_obj, right_obj))
    strictly_better = any(l < r - epsilon for l, r in zip(left_obj, right_obj))
    return no_worse and strictly_better


def pareto_frontier(evidence_packets: Iterable[EvidencePacket], epsilon: float = 0.0) -> list[EvidencePacket]:
    packets = list(evidence_packets)
    frontier: list[EvidencePacket] = []
    for packet in packets:
        if packet.numerical_failure_flag:
            continue
        dominated = any(_dominates(other, packet, epsilon) for other in packets if other.candidate_id != packet.candidate_id)
        if not dominated:
            frontier.append(packet)
    return sorted(
        frontier,
        key=lambda packet: (
            1.0 if packet.numerical_failure_flag else 0.0,
            _finite(packet.rolling_mean_mae),
            _finite(packet.num_free_params, fallback=0.0),
            packet.candidate_id,
        ),
    )


def pareto_epsilon_policy(evidence_packets: Iterable[EvidencePacket], epsilon: float = 0.0) -> PolicyDecision:
    packets = [packet for packet in evidence_packets if not packet.numerical_failure_flag]
    if not packets:
        return PolicyDecision(
            policy_name="pareto_epsilon",
            selected_candidate_id=None,
            selected_model_name=None,
            rationale="no numerically safe candidates",
        )
    frontier = pareto_frontier(packets, epsilon=epsilon)
    selected = frontier[0] if frontier else sorted(packets, key=lambda packet: packet.candidate_id)[0]
    diversity = len({packet.normalized_family().value for packet in packets})
    return PolicyDecision(
        policy_name="pareto_epsilon",
        selected_candidate_id=selected.candidate_id,
        selected_model_name=selected.model_name,
        selected_ids=tuple(packet.candidate_id for packet in frontier),
        rationale="selected deterministic tie-break winner from epsilon Pareto frontier",
        scores={packet.candidate_id: _selection_score(packet) for packet in packets},
        metadata={
            "epsilon": float(epsilon),
            "frontier_size": int(len(frontier)),
            "family_diversity": int(diversity),
            "validation_metric_available": any(packet.selection_metrics.get("validation_mae") is not None for packet in packets),
        },
    )


def _normalized_values(values: dict[str, float]) -> dict[str, float]:
    finite_values = [value for value in values.values() if np.isfinite(value)]
    if not finite_values:
        return {key: 0.0 for key in values}
    low = min(finite_values)
    high = max(finite_values)
    if abs(high - low) < 1.0e-12:
        return {key: 0.0 for key in values}
    return {key: (value - low) / (high - low) if np.isfinite(value) else 1.0 for key, value in values.items()}


def weighted_score_policy(
    evidence_packets: Iterable[EvidencePacket],
    weights: dict[str, float] | None = None,
) -> PolicyDecision:
    weights = weights or {
        "selection_score": 0.35,
        "rolling_mean_mae": 0.35,
        "complexity": 0.15,
        "numerical_risk": 0.15,
    }
    packets = list(evidence_packets)
    if not packets:
        return PolicyDecision("weighted_rubric", None, None, rationale="no candidates")
    columns = {
        "selection_score": {packet.candidate_id: _selection_score(packet) for packet in packets},
        "rolling_mean_mae": {packet.candidate_id: _finite(packet.rolling_mean_mae) for packet in packets},
        "complexity": {packet.candidate_id: _finite(packet.num_free_params, fallback=0.0) for packet in packets},
        "numerical_risk": {packet.candidate_id: 1.0 if packet.numerical_failure_flag else 0.0 for packet in packets},
    }
    normalized = {name: _normalized_values(values) for name, values in columns.items()}
    scores: dict[str, float] = defaultdict(float)
    for name, values in normalized.items():
        for candidate_id, value in values.items():
            scores[candidate_id] += float(weights.get(name, 0.0)) * value
    selected_id = sorted(scores, key=lambda candidate_id: (scores[candidate_id], candidate_id))[0]
    selected = next(packet for packet in packets if packet.candidate_id == selected_id)
    return PolicyDecision(
        policy_name="weighted_rubric",
        selected_candidate_id=selected.candidate_id,
        selected_model_name=selected.model_name,
        selected_ids=(selected.candidate_id,),
        rationale="lowest deterministic weighted normalized score",
        scores=dict(scores),
        metadata={"weights": dict(weights), "ablation_policy": True},
    )


def hard_veto_decision_tree_policy(
    evidence_packets: Iterable[EvidencePacket],
    baseline_epsilon: float = 0.02,
) -> PolicyDecision:
    packets = [packet for packet in evidence_packets if not packet.numerical_failure_flag]
    if not packets:
        return PolicyDecision("hard_veto_decision_tree", None, None, rationale="all candidates vetoed by numerical risk")

    best_rolling = min(_finite(packet.rolling_mean_mae) for packet in packets)
    simple = [
        packet
        for packet in packets
        if packet.normalized_family() == CandidateFamily.FORECASTING_BASELINE
        and _finite(packet.rolling_mean_mae) <= best_rolling + baseline_epsilon
    ]
    if simple:
        selected = sorted(simple, key=lambda packet: (_finite(packet.num_free_params, fallback=0.0), packet.candidate_id))[0]
        return PolicyDecision(
            "hard_veto_decision_tree",
            selected.candidate_id,
            selected.model_name,
            selected_ids=(selected.candidate_id,),
            rationale="baseline_sufficient",
        )

    constrained = [packet for packet in packets if packet.model_name == "constrained_structure_discovery"]
    no_obs = [packet for packet in packets if packet.model_name == "no_observation_search_discovery"]
    if constrained and no_obs:
        constrained_best = min(constrained, key=lambda packet: _finite(packet.rolling_mean_mae))
        no_obs_best = min(no_obs, key=lambda packet: _finite(packet.rolling_mean_mae))
        if _finite(constrained_best.rolling_mean_mae) + baseline_epsilon < _finite(no_obs_best.rolling_mean_mae):
            return PolicyDecision(
                "hard_veto_decision_tree",
                constrained_best.candidate_id,
                constrained_best.model_name,
                selected_ids=(constrained_best.candidate_id,),
                rationale="observation_label_search_preferred",
            )

    manual = [
        packet
        for packet in packets
        if packet.normalized_family() == CandidateFamily.MECHANISTIC_BASELINE
        and _finite(packet.rolling_mean_mae) <= best_rolling + baseline_epsilon
    ]
    if manual:
        selected = sorted(manual, key=lambda packet: (_finite(packet.rolling_mean_mae), packet.candidate_id))[0]
        return PolicyDecision(
            "hard_veto_decision_tree",
            selected.candidate_id,
            selected.model_name,
            selected_ids=(selected.candidate_id,),
            rationale="manual_preferred",
        )

    selected = sorted(packets, key=lambda packet: (_finite(packet.rolling_mean_mae), packet.candidate_id))[0]
    return PolicyDecision(
        "hard_veto_decision_tree",
        selected.candidate_id,
        selected.model_name,
        selected_ids=(selected.candidate_id,),
        rationale="mixed_evidence",
    )
