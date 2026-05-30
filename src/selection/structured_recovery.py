from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.selection.policies import hard_veto_decision_tree_policy, pareto_epsilon_policy, weighted_score_policy
from src.selection.schema import BudgetState, CandidateFamily, CandidateSpec, EvidencePacket
from src.selection.verifier import verify_candidate, verify_evidence
from src.utils.io import ensure_dir
from src.utils.paths import repo_relative_path


DEFAULT_TASKS = (
    "direct_signal",
    "lagged_signal_1",
    "lagged_signal_2",
    "mixture_observation",
    "hidden_component_proxy",
)
DEFAULT_POLICIES = (
    "pareto_epsilon",
    "weighted_score",
    "hard_veto_decision_tree",
    "random_label_baseline",
    "no_observation_label_baseline",
    "deterministic_seed_proposer",
)
DEFAULT_BUDGETS = (3, 5, 10, 20)


@dataclass(frozen=True)
class StructuredToyTask:
    task_name: str
    seed: int
    noise_level: float
    observed: np.ndarray
    latent: np.ndarray
    proxy_component: np.ndarray
    true_candidate_family: str
    true_observation_label: str
    true_delay_label: str


@dataclass(frozen=True)
class StructuredCandidate:
    candidate_id: str
    family: CandidateFamily
    model_name: str
    observation_label: str
    delay_label: str
    candidate_family_label: str
    complexity: float
    values: np.ndarray


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")


def _write_json_lf(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(data, indent=2, sort_keys=True) + "\n")


def _stable_uint(seed: int, *parts: object) -> int:
    key = ":".join([str(seed), *(str(part) for part in parts)])
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


def _lagged(values: np.ndarray, delay: int) -> np.ndarray:
    if delay <= 0:
        return values.copy()
    return np.concatenate([np.repeat(values[0], delay), values[:-delay]])


def generate_structured_toy_task(
    task_name: str,
    *,
    seed: int,
    noise_level: float,
    n: int = 48,
) -> StructuredToyTask:
    rng = np.random.default_rng(seed)
    t = np.arange(n, dtype=float)
    latent = 1.2 + 0.18 * np.sin(2.0 * np.pi * t / 12.0) + 0.012 * t
    proxy_component = 0.85 + 0.12 * np.cos(2.0 * np.pi * (t + 2.0) / 9.0) + 0.008 * t
    noise = rng.normal(0.0, noise_level, size=n)

    if task_name == "direct_signal":
        observed = latent + noise
        return StructuredToyTask(task_name, seed, noise_level, observed, latent, proxy_component, "simple_direct", "direct", "0")
    if task_name == "lagged_signal_1":
        observed = _lagged(latent, 1) + noise
        return StructuredToyTask(task_name, seed, noise_level, observed, latent, proxy_component, "structured_lagged", "lagged", "1")
    if task_name == "lagged_signal_2":
        observed = _lagged(latent, 2) + noise
        return StructuredToyTask(task_name, seed, noise_level, observed, latent, proxy_component, "structured_lagged", "lagged", "2")
    if task_name == "mixture_observation":
        observed = 0.65 * latent + 0.35 * _lagged(latent, 2) + noise
        return StructuredToyTask(task_name, seed, noise_level, observed, latent, proxy_component, "structured_mixture", "mixture", "2")
    if task_name == "hidden_component_proxy":
        observed = 0.35 * latent + 0.65 * proxy_component + noise
        return StructuredToyTask(task_name, seed, noise_level, observed, latent, proxy_component, "structured_proxy", "proxy", "0")
    raise ValueError(f"Unsupported structured toy task: {task_name}")


def structured_candidates_for_task(task: StructuredToyTask) -> list[StructuredCandidate]:
    latent = task.latent
    proxy = task.proxy_component
    candidates = [
        StructuredCandidate(
            "direct",
            CandidateFamily.FORECASTING_BASELINE,
            "rolling_mean_4wk",
            "direct",
            "0",
            "simple_direct",
            1.0,
            latent,
        ),
        StructuredCandidate(
            "no_observation_direct",
            CandidateFamily.ABLATION,
            "no_observation_search_discovery",
            "direct",
            "0",
            "simple_direct",
            2.0,
            latent,
        ),
        StructuredCandidate(
            "lagged_1",
            CandidateFamily.MECHANISTIC_BASELINE,
            "delayed_observation_seir",
            "lagged",
            "1",
            "structured_lagged",
            4.0,
            _lagged(latent, 1),
        ),
        StructuredCandidate(
            "lagged_2",
            CandidateFamily.STRUCTURED_SEARCH,
            "constrained_structure_discovery",
            "lagged",
            "2",
            "structured_lagged",
            5.0,
            _lagged(latent, 2),
        ),
        StructuredCandidate(
            "mixture",
            CandidateFamily.STRUCTURED_SEARCH,
            "constrained_structure_discovery",
            "mixture",
            "2",
            "structured_mixture",
            6.0,
            0.65 * latent + 0.35 * _lagged(latent, 2),
        ),
        StructuredCandidate(
            "proxy",
            CandidateFamily.ABLATION,
            "exhaustive_structure_discovery",
            "proxy",
            "0",
            "structured_proxy",
            6.0,
            0.35 * latent + 0.65 * proxy,
        ),
    ]
    return candidates


def _candidate_spec(task: StructuredToyTask, candidate: StructuredCandidate, *, round_idx: int) -> CandidateSpec:
    return CandidateSpec(
        candidate_id=f"{task.task_name}:{task.seed}:{task.noise_level:g}:{candidate.candidate_id}",
        family=candidate.family,
        model_name=candidate.model_name,
        observation_label=candidate.observation_label,
        delay_label=candidate.delay_label,
        round_idx=round_idx,
        proposer_name="deterministic_seed_proposer",
        rationale="generic structured time-series candidate",
        metadata={"task_name": task.task_name, "candidate_label": candidate.candidate_id},
    )


def _evidence_packet(task: StructuredToyTask, candidate: StructuredCandidate, spec: CandidateSpec) -> EvidencePacket:
    rolling_error = float(np.mean(np.abs(task.observed - candidate.values)))
    return EvidencePacket(
        candidate_id=spec.candidate_id,
        model_name=candidate.model_name,
        family=candidate.family,
        series_name=task.task_name,
        selection_metrics={"selection_score": rolling_error},
        rolling_mean_mae=rolling_error,
        num_free_params=float(candidate.complexity),
        numerical_failure_flag=False,
        supports_positive_claim=False,
        metadata={
            "candidate_label": candidate.candidate_id,
            "observation_label": candidate.observation_label,
            "delay_label": candidate.delay_label,
            "candidate_family_label": candidate.candidate_family_label,
        },
    )


def _verified_packets(task: StructuredToyTask, candidates: list[StructuredCandidate]) -> tuple[list[EvidencePacket], list[dict[str, Any]]]:
    packets: list[EvidencePacket] = []
    verification_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    budget = BudgetState(max_candidates=len(candidates), evaluated_candidates=0)
    for round_idx, candidate in enumerate(candidates):
        spec = _candidate_spec(task, candidate, round_idx=round_idx)
        candidate_result = verify_candidate(spec, budget=budget, seen_candidate_ids=seen)
        evidence = _evidence_packet(task, candidate, spec)
        evidence_result = verify_evidence(evidence)
        valid = bool(candidate_result.valid and evidence_result.valid)
        verification_rows.append(
            {
                "candidate_id": spec.candidate_id,
                "task_name": task.task_name,
                "seed": int(task.seed),
                "noise_level": float(task.noise_level),
                "candidate_label": candidate.candidate_id,
                "valid": valid,
                "candidate_reasons": ";".join(candidate_result.reasons),
                "evidence_reasons": ";".join(evidence_result.reasons),
            }
        )
        if valid:
            packets.append(evidence)
        seen.add(spec.candidate_id)
        budget = BudgetState(max_candidates=len(candidates), evaluated_candidates=round_idx + 1)
    return packets, verification_rows


def _select_packet(
    policy_name: str,
    packets: list[EvidencePacket],
    *,
    epsilon: float,
    seed: int,
    task: StructuredToyTask,
) -> EvidencePacket | None:
    if not packets:
        return None
    if policy_name == "pareto_epsilon":
        decision = pareto_epsilon_policy(packets, epsilon=epsilon)
        return next((packet for packet in packets if packet.candidate_id == decision.selected_candidate_id), None)
    if policy_name == "weighted_score":
        decision = weighted_score_policy(packets)
        return next((packet for packet in packets if packet.candidate_id == decision.selected_candidate_id), None)
    if policy_name == "hard_veto_decision_tree":
        decision = hard_veto_decision_tree_policy(packets, baseline_epsilon=epsilon)
        return next((packet for packet in packets if packet.candidate_id == decision.selected_candidate_id), None)
    if policy_name == "random_label_baseline":
        return sorted(packets, key=lambda packet: (_stable_uint(seed, task.task_name, task.seed, task.noise_level, packet.candidate_id), packet.candidate_id))[0]
    if policy_name == "no_observation_label_baseline":
        direct = [packet for packet in packets if packet.metadata.get("observation_label") == "direct"]
        return sorted(
            direct or packets,
            key=lambda packet: (
                float(packet.rolling_mean_mae) if packet.rolling_mean_mae is not None else np.inf,
                packet.candidate_id,
            ),
        )[0]
    if policy_name == "deterministic_seed_proposer":
        return sorted(
            packets,
            key=lambda packet: (
                float(packet.rolling_mean_mae) if packet.rolling_mean_mae is not None else np.inf,
                packet.candidate_id,
            ),
        )[0]
    raise ValueError(f"Unsupported structured recovery policy: {policy_name}")


def _result_row(
    task: StructuredToyTask,
    policy_name: str,
    budget: int,
    packets: list[EvidencePacket],
    selected: EvidencePacket | None,
    *,
    full_packets: list[EvidencePacket],
    valid_rate: float,
    duplicate_rate: float,
    epsilon: float,
) -> dict[str, Any]:
    if selected is None:
        selected_label = ""
        selected_delay = ""
        selected_family_label = ""
        selected_error = np.nan
    else:
        selected_label = str(selected.metadata.get("observation_label", ""))
        selected_delay = str(selected.metadata.get("delay_label", ""))
        selected_family_label = str(selected.metadata.get("candidate_family_label", ""))
        selected_error = float(selected.rolling_mean_mae) if selected.rolling_mean_mae is not None else np.nan
    best_error = (
        min(float(packet.rolling_mean_mae) for packet in full_packets if packet.rolling_mean_mae is not None)
        if full_packets
        else np.nan
    )
    top_epsilon_hit = bool(np.isfinite(best_error) and np.isfinite(selected_error) and selected_error <= best_error + epsilon)
    return {
        "task_name": task.task_name,
        "seed": int(task.seed),
        "noise_level": float(task.noise_level),
        "budget": int(budget),
        "policy_name": policy_name,
        "true_observation_label": task.true_observation_label,
        "selected_observation_label": selected_label,
        "observation_label_recovered": selected_label == task.true_observation_label,
        "true_delay_label": task.true_delay_label,
        "selected_delay_label": selected_delay,
        "delay_label_recovered": selected_delay == task.true_delay_label,
        "true_candidate_family": task.true_candidate_family,
        "selected_candidate_family": selected_family_label,
        "candidate_family_recovered": selected_family_label == task.true_candidate_family,
        "rolling_error": selected_error,
        "best_available_error": best_error,
        "top_epsilon_hit": top_epsilon_hit,
        "available_candidate_count": int(len(packets)),
        "valid_proposal_rate": float(valid_rate),
        "duplicate_proposal_rate": float(duplicate_rate),
        "claim_safety_violation_count": 0,
    }


def run_structured_recovery(
    *,
    tasks: tuple[str, ...] = DEFAULT_TASKS,
    seeds: tuple[int, ...] = tuple(range(1, 11)),
    noise_levels: tuple[float, ...] = (0.0, 0.05, 0.10),
    budgets: tuple[int, ...] = DEFAULT_BUDGETS,
    policies: tuple[str, ...] = DEFAULT_POLICIES,
    epsilon: float = 0.01,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    verification_rows: list[dict[str, Any]] = []
    budget_values = tuple(sorted({int(value) for value in budgets}))
    for task_name in tasks:
        for task_seed in seeds:
            for noise_level in noise_levels:
                task = generate_structured_toy_task(task_name, seed=int(task_seed), noise_level=float(noise_level))
                candidates = structured_candidates_for_task(task)
                full_packets, task_verifications = _verified_packets(task, candidates)
                verification_rows.extend(task_verifications)
                valid_rate = float(np.mean([row["valid"] for row in task_verifications])) if task_verifications else np.nan
                duplicate_rate = 1.0 - (len({row["candidate_id"] for row in task_verifications}) / len(task_verifications)) if task_verifications else 0.0
                ordered_packets = sorted(
                    full_packets,
                    key=lambda packet: int(packet.metadata.get("candidate_label") not in {"direct", "no_observation_direct", "lagged_1", "lagged_2", "mixture", "proxy"}),
                )
                # Preserve the deterministic proposal order from structured_candidates_for_task.
                order = {candidate.candidate_id: idx for idx, candidate in enumerate(candidates)}
                ordered_packets = sorted(ordered_packets, key=lambda packet: order[str(packet.metadata["candidate_label"])])
                for budget in budget_values:
                    available = ordered_packets[: min(int(budget), len(ordered_packets))]
                    for policy_name in policies:
                        selected = _select_packet(policy_name, available, epsilon=epsilon, seed=seed, task=task)
                        rows.append(
                            _result_row(
                                task,
                                policy_name,
                                int(budget),
                                available,
                                selected,
                                full_packets=full_packets,
                                valid_rate=valid_rate,
                                duplicate_rate=duplicate_rate,
                                epsilon=epsilon,
                            )
                        )
    by_seed = pd.DataFrame.from_records(rows)
    if by_seed.empty:
        summary = pd.DataFrame()
        budget_curve = pd.DataFrame()
    else:
        budget_to_recover = (
            by_seed.loc[by_seed["observation_label_recovered"]]
            .groupby(["task_name", "seed", "noise_level", "policy_name"], as_index=False)["budget"]
            .min()
            .rename(columns={"budget": "budget_to_recover_true_label"})
        )
        by_seed = by_seed.merge(budget_to_recover, on=["task_name", "seed", "noise_level", "policy_name"], how="left")
        summary = (
            by_seed.groupby("policy_name", as_index=False)
            .agg(
                observation_label_recovery_rate=("observation_label_recovered", "mean"),
                delay_label_recovery_rate=("delay_label_recovered", "mean"),
                candidate_family_recovery_rate=("candidate_family_recovered", "mean"),
                mean_rolling_error=("rolling_error", "mean"),
                budget_to_recover_true_label=("budget_to_recover_true_label", "mean"),
                valid_proposal_rate=("valid_proposal_rate", "mean"),
                duplicate_proposal_rate=("duplicate_proposal_rate", "mean"),
                top_epsilon_hit_rate=("top_epsilon_hit", "mean"),
                claim_safety_violation_count=("claim_safety_violation_count", "sum"),
            )
            .sort_values("policy_name")
        )
        budget_curve = (
            by_seed.groupby(["policy_name", "budget"], as_index=False)
            .agg(
                observation_label_recovery_rate=("observation_label_recovered", "mean"),
                delay_label_recovery_rate=("delay_label_recovered", "mean"),
                candidate_family_recovery_rate=("candidate_family_recovered", "mean"),
                mean_rolling_error=("rolling_error", "mean"),
                top_epsilon_hit_rate=("top_epsilon_hit", "mean"),
            )
            .sort_values(["policy_name", "budget"])
        )

    run_summary = {
        "evaluation_type": "local synthetic structured recovery",
        "external_api_used": False,
        "tasks": list(tasks),
        "seeds": [int(value) for value in seeds],
        "noise_levels": [float(value) for value in noise_levels],
        "budgets": [int(value) for value in budget_values],
        "policies": list(policies),
        "by_seed_rows": int(len(by_seed)),
        "summary_rows": int(len(summary)),
        "budget_curve_rows": int(len(budget_curve)),
        "valid_proposal_rate": float(summary["valid_proposal_rate"].mean()) if not summary.empty else None,
        "claim_safety_violation_count": int(summary["claim_safety_violation_count"].sum()) if not summary.empty else 0,
    }
    return summary, by_seed, budget_curve, run_summary


def run_structured_recovery_from_config(config: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    artifact_root = ensure_dir(repo_root / config["artifacts"]["root_dir"])
    stage_config = config.get("synthetic_recovery", {})
    policy_config = config.get("policy", {})
    api_config = config.get("api", {})
    if bool(api_config.get("enabled", False)):
        raise ValueError("API-assisted structured recovery is intentionally disabled for the local Stage 4 runner.")
    summary, by_seed, budget_curve, run_summary = run_structured_recovery(
        tasks=tuple(str(value) for value in stage_config.get("tasks", DEFAULT_TASKS)),
        seeds=tuple(int(value) for value in stage_config.get("seeds", range(1, 11))),
        noise_levels=tuple(float(value) for value in stage_config.get("noise_levels", (0.0, 0.05, 0.10))),
        budgets=tuple(int(value) for value in stage_config.get("budgets", DEFAULT_BUDGETS)),
        policies=tuple(str(value) for value in stage_config.get("policies", DEFAULT_POLICIES)),
        epsilon=float(policy_config.get("epsilon", 0.01)),
        seed=int(config.get("seed", 42)),
    )
    _write_csv(summary, artifact_root / "synthetic_structured_recovery_summary.csv")
    _write_csv(by_seed, artifact_root / "synthetic_structured_recovery_by_seed.csv")
    _write_csv(budget_curve, artifact_root / "synthetic_structured_recovery_budget_curve.csv")

    run_summary.update(
        {
            "artifact_root": repo_relative_path(artifact_root, repo_root),
            "config_scope": str(config.get("scope", "local_synthetic_structured_recovery")),
        }
    )
    _write_json_lf(run_summary, artifact_root / "synthetic_structured_recovery_run_summary.json")
    return run_summary
