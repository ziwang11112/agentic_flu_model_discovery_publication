from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.selection.evidence_auditor import audit_frozen_evidence
from src.selection.policies import hard_veto_decision_tree_policy, pareto_epsilon_policy, pareto_frontier, weighted_score_policy
from src.selection.proposer import FailureGuidedRefinementProposer, SeedCandidateProposer
from src.selection.schema import BudgetState, CandidateFamily, EvidencePacket, TraceEvent
from src.selection.toy_tasks import run_toy_recovery
from src.selection.traces import TraceWriter
from src.selection.verifier import infer_family, verify_candidate, verify_evidence
from src.utils.io import ensure_dir, write_json
from src.utils.paths import repo_relative_path


POLICY_NAMES = ("pareto_epsilon", "weighted_rubric", "hard_veto_decision_tree")


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")


def _candidate_id(series_name: str, model_name: str) -> str:
    safe_series = (
        series_name.lower()
        .replace(">=", "ge")
        .replace("/", "_")
        .replace(" ", "_")
        .replace("-", "_")
    )
    return f"{safe_series}:{model_name}"


def _evidence_from_summary(summary: pd.DataFrame) -> list[EvidencePacket]:
    packets: list[EvidencePacket] = []
    for row in summary.sort_values(["series_name", "model_name"]).itertuples(index=False):
        model_name = str(row.model_name)
        try:
            family = infer_family(model_name)
        except ValueError:
            continue
        series_name = str(row.series_name)
        rolling = float(row.rolling_mean_mae)
        numerical_failure = bool(getattr(row, "numerical_failure_flag", False))
        metadata: dict[str, Any] = {}
        for column in ["model_family", "discovery_structure_name", "discovery_observation_map", "discovery_delay_weeks"]:
            if hasattr(row, column):
                value = getattr(row, column)
                if pd.notna(value):
                    metadata[column] = value
        packets.append(
            EvidencePacket(
                candidate_id=_candidate_id(series_name, model_name),
                model_name=model_name,
                family=family,
                series_name=series_name,
                selection_metrics={
                    "rolling_mean_mae": rolling,
                    "selection_score": rolling,
                },
                posthoc_metrics={"test_mae": float(row.test_mae)},
                rolling_mean_mae=rolling,
                num_free_params=float(row.num_free_params),
                numerical_failure_flag=numerical_failure,
                supports_positive_claim=False,
                metadata=metadata,
            )
        )
    return packets


def _policy_decisions_for_series(series_name: str, packets: list[EvidencePacket], epsilon: float) -> list[dict[str, Any]]:
    decisions = [
        pareto_epsilon_policy(packets, epsilon=epsilon),
        weighted_score_policy(packets),
        hard_veto_decision_tree_policy(packets, baseline_epsilon=epsilon),
    ]
    rows: list[dict[str, Any]] = []
    for decision in decisions:
        rows.append(
            {
                "series_name": series_name,
                "policy_name": decision.policy_name,
                "selected_candidate_id": decision.selected_candidate_id,
                "selected_model_name": decision.selected_model_name,
                "rationale": decision.rationale,
                "selected_ids": ";".join(decision.selected_ids),
                "metadata_json": json.dumps(decision.metadata, sort_keys=True),
            }
        )
    return rows


def _frontier_rows(series_name: str, packets: list[EvidencePacket], epsilon: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    frontier_ids = {packet.candidate_id for packet in pareto_frontier(packets, epsilon=epsilon)}
    for packet in packets:
        rows.append(
            {
                "series_name": series_name,
                "candidate_id": packet.candidate_id,
                "model_name": packet.model_name,
                "family": packet.normalized_family().value,
                "rolling_mean_mae": packet.rolling_mean_mae,
                "num_free_params": packet.num_free_params,
                "numerical_failure_flag": packet.numerical_failure_flag,
                "on_pareto_frontier": packet.candidate_id in frontier_ids,
            }
        )
    return rows


def run_offline_selection_evaluation(config: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    artifact_root = ensure_dir(repo_root / config["artifacts"]["root_dir"])
    frozen_root = repo_root / config["data"]["frozen_artifact_root"]
    multiseason_root = repo_root / config["data"].get("multiseason_artifact_root", "")
    epsilon = float(config.get("policy", {}).get("epsilon", 0.02))
    max_candidates = int(config.get("policy", {}).get("max_candidates", 100))
    toy_config = config.get("toy_tasks", {})

    summary = pd.read_csv(frozen_root / "benchmark_model_summary.csv")
    recommendations = pd.read_csv(frozen_root / "paper_recommendation_table.csv")
    observation_impact = pd.read_csv(frozen_root / "observation_search_impact_table.csv")
    numerical_summary = pd.read_csv(frozen_root / "numerical_failure_summary.csv")

    seed_candidates = SeedCandidateProposer().propose(summary, max_candidates=max_candidates)
    refinement_candidates = FailureGuidedRefinementProposer().propose(
        numerical_summary=numerical_summary,
        observation_impact=observation_impact,
        max_candidates=max_candidates,
    )
    candidates = seed_candidates + refinement_candidates

    trace_path = artifact_root / "iterative_refinement_traces.jsonl"
    if trace_path.exists():
        trace_path.unlink()
    trace = TraceWriter(trace_path)

    seen: set[str] = set()
    verification_rows: list[dict[str, Any]] = []
    budget = BudgetState(max_candidates=max_candidates)
    for candidate in candidates:
        result = verify_candidate(candidate, budget=budget, seen_candidate_ids=seen)
        verification_rows.append({**candidate.to_dict(), **result.to_dict()})
        trace.write(TraceEvent("candidate_verified", candidate.candidate_id, candidate.round_idx, result.to_dict()))
        if candidate.candidate_id not in seen:
            seen.add(candidate.candidate_id)
        budget = BudgetState(max_candidates=max_candidates, evaluated_candidates=budget.evaluated_candidates + 1)

    evidence_packets = _evidence_from_summary(summary)
    evidence_rows: list[dict[str, Any]] = []
    for packet in evidence_packets:
        result = verify_evidence(packet)
        evidence_rows.append({**packet.to_dict(), **result.to_dict()})
        trace.write(TraceEvent("evidence_verified", packet.candidate_id, payload=result.to_dict()))

    policy_rows: list[dict[str, Any]] = []
    frontier_rows: list[dict[str, Any]] = []
    for series_name, series_packets in sorted(
        ((name, list(group)) for name, group in _group_packets(evidence_packets).items()),
        key=lambda item: item[0],
    ):
        policy_rows.extend(_policy_decisions_for_series(series_name, series_packets, epsilon))
        frontier_rows.extend(_frontier_rows(series_name, series_packets, epsilon))

    multiseason_arg = multiseason_root if multiseason_root.exists() else None
    audit = audit_frozen_evidence(frozen_root, multiseason_arg)
    trace.write(TraceEvent("claim_boundary_audit", payload=audit.to_dict()))
    audit_rows = [
        {"audit_label": key, "value": value}
        for key, value in audit.to_dict().items()
        if not isinstance(value, (list, dict))
    ]
    for claim in audit.allowed_claims:
        audit_rows.append({"audit_label": "allowed_claim", "value": claim})
    for caveat in audit.caveats:
        audit_rows.append({"audit_label": "caveat", "value": caveat})
    for rejected in audit.rejected_claims:
        audit_rows.append({"audit_label": "rejected_claim", "value": rejected})

    scenarios = [str(value) for value in toy_config.get("scenarios", ["sinusoidal_direct", "lagged_observation"])]
    seeds = [int(value) for value in toy_config.get("seeds", [1, 2])]
    toy_recovery = run_toy_recovery(scenarios, seeds)

    _write_csv(pd.DataFrame.from_records(policy_rows), artifact_root / "policy_recommendations.csv")
    _write_csv(pd.DataFrame.from_records(frontier_rows), artifact_root / "pareto_frontiers.csv")
    _write_csv(pd.DataFrame.from_records(audit_rows), artifact_root / "claim_audit_scores.csv")
    _write_csv(toy_recovery, artifact_root / "toy_observation_recovery_summary.csv")
    _write_csv(pd.DataFrame.from_records(verification_rows), artifact_root / "verified_candidates.csv")
    _write_csv(pd.DataFrame.from_records(evidence_rows), artifact_root / "verified_evidence.csv")

    run_summary = {
        "evaluation_type": "deterministic offline selection policy evaluation",
        "external_api_used": False,
        "frozen_artifact_root": repo_relative_path(frozen_root, repo_root),
        "multiseason_artifact_root": repo_relative_path(multiseason_root, repo_root) if multiseason_root.exists() else None,
        "artifact_root": repo_relative_path(artifact_root, repo_root),
        "candidate_count": int(len(candidates)),
        "verified_candidate_count": int(sum(1 for row in verification_rows if row["valid"])),
        "series_count": int(summary["series_name"].nunique()),
        "policy_names": list(POLICY_NAMES),
        "toy_scenarios": scenarios,
        "toy_seeds": seeds,
        "toy_recovery_rate": float(toy_recovery["recovered"].mean()) if not toy_recovery.empty else None,
    }
    write_json(run_summary, artifact_root / "run_summary.json")
    return run_summary


def _group_packets(packets: list[EvidencePacket]) -> dict[str, list[EvidencePacket]]:
    grouped: dict[str, list[EvidencePacket]] = {}
    for packet in packets:
        grouped.setdefault(packet.series_name, []).append(packet)
    return grouped
