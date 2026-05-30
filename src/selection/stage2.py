from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.selection.policies import hard_veto_decision_tree_policy, pareto_epsilon_policy, weighted_score_policy
from src.selection.schema import BudgetState, CandidateSpec, EvidencePacket
from src.selection.toy_tasks import generate_toy_series, score_observation_label_candidates
from src.selection.verifier import infer_family, verify_candidate, verify_evidence
from src.utils.io import ensure_dir
from src.utils.paths import repo_relative_path


REPLAY_POLICIES = ("pareto_epsilon", "weighted_score", "hard_veto_decision_tree", "random_order_baseline")
TOY_POLICIES = ("pareto_epsilon", "weighted_score", "random_label_baseline")
DEFAULT_BUDGETS = (3, 5, 10, 15)
DEFAULT_TOY_SCENARIOS = (
    "direct_signal",
    "lagged_signal_1",
    "lagged_signal_2",
    "mixture_signal",
    "noisy_lagged_signal",
)


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


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or pd.isna(value):
        return False
    return str(value).strip().lower() in {"true", "1", "yes"}


def _candidate_id(series_name: str, model_name: str) -> str:
    safe = series_name.lower().replace(">=", "ge").replace("/", "_").replace(" ", "_").replace("-", "_")
    return f"{safe}:{model_name}"


def _packets_from_summary(summary: pd.DataFrame) -> list[EvidencePacket]:
    packets: list[EvidencePacket] = []
    for row in summary.sort_values(["series_name", "model_name"]).itertuples(index=False):
        model_name = str(row.model_name)
        try:
            family = infer_family(model_name)
        except ValueError:
            continue
        series_name = str(row.series_name)
        rolling = float(row.rolling_mean_mae)
        metadata: dict[str, Any] = {}
        for column in ("model_family", "discovery_structure_name", "discovery_observation_map", "discovery_delay_weeks"):
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
                selection_metrics={"selection_score": rolling, "rolling_mean_mae": rolling},
                posthoc_metrics={"test_mae": float(row.test_mae)},
                rolling_mean_mae=rolling,
                num_free_params=float(row.num_free_params),
                numerical_failure_flag=_as_bool(getattr(row, "numerical_failure_flag", False)),
                metadata=metadata,
            )
        )
    return packets


def _select_by_policy(policy_name: str, packets: list[EvidencePacket], epsilon: float, seed: int) -> EvidencePacket | None:
    safe = [packet for packet in packets if not packet.numerical_failure_flag]
    if not safe:
        return None
    if policy_name == "pareto_epsilon":
        decision = pareto_epsilon_policy(safe, epsilon=epsilon)
    elif policy_name == "weighted_score":
        decision = weighted_score_policy(safe)
    elif policy_name == "hard_veto_decision_tree":
        decision = hard_veto_decision_tree_policy(safe, baseline_epsilon=epsilon)
    elif policy_name == "random_order_baseline":
        selected = sorted(safe, key=lambda packet: (_stable_uint(seed, packet.series_name, packet.candidate_id), packet.candidate_id))[0]
        return selected
    else:
        raise ValueError(f"Unsupported policy: {policy_name}")
    if decision.selected_candidate_id is None:
        return None
    return next((packet for packet in safe if packet.candidate_id == decision.selected_candidate_id), None)


def run_verifier_negative_set() -> pd.DataFrame:
    candidate_cases = [
        (
            "missing_required_fields",
            CandidateSpec(candidate_id="", family="forecasting_baseline", model_name=""),
            {"seen_candidate_ids": set(), "budget": None},
        ),
        (
            "duplicate_candidate_id",
            CandidateSpec(candidate_id="duplicate", family="forecasting_baseline", model_name="rolling_mean_4wk"),
            {"seen_candidate_ids": {"duplicate"}, "budget": None},
        ),
        (
            "absolute_artifact_path",
            CandidateSpec(
                candidate_id="absolute_path",
                family="forecasting_baseline",
                model_name="rolling_mean_4wk",
                metadata={"artifact_path": "D:\\temp\\artifact.csv"},
            ),
            {"seen_candidate_ids": set(), "budget": None},
        ),
        (
            "invalid_observation_label",
            CandidateSpec(
                candidate_id="bad_observation",
                family="forecasting_baseline",
                model_name="rolling_mean_4wk",
                observation_label="not_a_supported_label",
            ),
            {"seen_candidate_ids": set(), "budget": None},
        ),
        (
            "invalid_delay_label",
            CandidateSpec(
                candidate_id="bad_delay",
                family="forecasting_baseline",
                model_name="rolling_mean_4wk",
                delay_label="-2",
            ),
            {"seen_candidate_ids": set(), "budget": None},
        ),
    ]
    rows: list[dict[str, Any]] = []
    for case_id, candidate, kwargs in candidate_cases:
        result = verify_candidate(candidate, **kwargs)
        rows.append(
            {
                "case_id": case_id,
                "case_type": "candidate",
                "valid": result.valid,
                "rejected": result.vetoed,
                "rejection_reasons": ";".join(result.reasons),
            }
        )

    evidence_cases = [
        (
            "selection_evidence_contains_test_metric",
            EvidencePacket(
                candidate_id="leaky",
                model_name="rolling_mean_4wk",
                family="forecasting_baseline",
                series_name="Overall",
                selection_metrics={"test_metric": 1.0},
            ),
        ),
        (
            "flagged_row_supports_positive_claim",
            EvidencePacket(
                candidate_id="flagged_positive",
                model_name="constrained_structure_discovery",
                family="structured_search",
                series_name="0-4 yr",
                numerical_failure_flag=True,
                supports_positive_claim=True,
            ),
        ),
    ]
    for case_id, evidence in evidence_cases:
        result = verify_evidence(evidence)
        rows.append(
            {
                "case_id": case_id,
                "case_type": "evidence",
                "valid": result.valid,
                "rejected": result.vetoed,
                "rejection_reasons": ";".join(result.reasons),
            }
        )

    frame = pd.DataFrame.from_records(rows)
    total = int(len(frame))
    rejected = int(frame["rejected"].astype(bool).sum())
    frame["total_negative_cases"] = total
    frame["rejected_cases"] = rejected
    frame["rejection_rate"] = rejected / total if total else np.nan
    return frame


def run_budgeted_candidate_replay(
    model_summary: pd.DataFrame,
    recommendation_table: pd.DataFrame,
    *,
    budgets: tuple[int, ...] = DEFAULT_BUDGETS,
    epsilon: float = 0.02,
    seed: int = 42,
) -> pd.DataFrame:
    del recommendation_table  # kept in the signature to document the frozen source used by this replay.
    packets = _packets_from_summary(model_summary)
    rows: list[dict[str, Any]] = []
    for series_name in sorted({packet.series_name for packet in packets}):
        series_packets = [packet for packet in packets if packet.series_name == series_name]
        ordered = sorted(series_packets, key=lambda packet: (_stable_uint(seed, series_name, packet.model_name), packet.model_name))
        safe_rollings = [float(packet.rolling_mean_mae) for packet in series_packets if not packet.numerical_failure_flag]
        top_threshold = min(safe_rollings) + epsilon if safe_rollings else np.nan
        for k in budgets:
            available = ordered[: min(k, len(ordered))]
            selected_by_policy: dict[str, str | None] = {}
            for policy_name in REPLAY_POLICIES:
                selected = _select_by_policy(policy_name, available, epsilon, seed)
                selected_by_policy[policy_name] = selected.model_name if selected else None
                rows.append(
                    {
                        "series_name": series_name,
                        "k": int(k),
                        "actual_candidate_count": int(len(available)),
                        "policy_name": policy_name,
                        "selected_model_at_k": selected.model_name if selected else None,
                        "rolling_mean_mae_at_k": selected.rolling_mean_mae if selected else np.nan,
                        "test_mae_at_k": selected.posthoc_metrics.get("test_mae") if selected else np.nan,
                        "test_metric_role": "posthoc_descriptive",
                        "top_epsilon_threshold": top_threshold,
                    }
                )

    frame = pd.DataFrame.from_records(rows)
    counts: dict[tuple[str, str], int | None] = {}
    for (series_name, policy_name), subset in frame.groupby(["series_name", "policy_name"], sort=False):
        hit = subset.loc[subset["rolling_mean_mae_at_k"] <= subset["top_epsilon_threshold"]].sort_values("k")
        counts[(str(series_name), str(policy_name))] = int(hit.iloc[0]["k"]) if not hit.empty else None
    frame["candidate_count_to_top_epsilon"] = [
        counts[(str(row.series_name), str(row.policy_name))] for row in frame.itertuples(index=False)
    ]
    disagreement: dict[tuple[str, int], float] = {}
    for (series_name, k), subset in frame.groupby(["series_name", "k"], sort=False):
        choices = subset["selected_model_at_k"].dropna().astype(str)
        if choices.empty:
            disagreement[(str(series_name), int(k))] = np.nan
        else:
            disagreement[(str(series_name), int(k))] = 1.0 - float(choices.value_counts().max()) / float(len(choices))
    frame["policy_disagreement_rate"] = [
        disagreement[(str(row.series_name), int(row.k))] for row in frame.itertuples(index=False)
    ]
    return frame


def _toy_packets(task: Any) -> list[EvidencePacket]:
    scored = score_observation_label_candidates(task)
    packets: list[EvidencePacket] = []
    for label, values in scored.items():
        rolling_error = float(values["rolling_error"])
        packets.append(
            EvidencePacket(
                candidate_id=f"{task.scenario_name}:{task.seed}:{label}",
                model_name=label,
                family="forecasting_baseline",
                series_name=task.scenario_name,
                selection_metrics={"selection_score": rolling_error},
                rolling_mean_mae=rolling_error,
                num_free_params=0.0 if label == "direct" else 1.0,
                metadata={"observation_label": label, "delay_label": values["delay_label"]},
            )
        )
    return packets


def run_toy_policy_recovery(
    *,
    scenarios: tuple[str, ...] = DEFAULT_TOY_SCENARIOS,
    seeds: tuple[int, ...] = (1, 2, 3),
    epsilon: float = 0.0,
    seed: int = 42,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        for task_seed in seeds:
            task = generate_toy_series(scenario, task_seed)
            packets = _toy_packets(task)
            for policy_name in TOY_POLICIES:
                if policy_name == "pareto_epsilon":
                    decision = pareto_epsilon_policy(packets, epsilon=epsilon)
                    selected = next(packet for packet in packets if packet.candidate_id == decision.selected_candidate_id)
                elif policy_name == "weighted_score":
                    decision = weighted_score_policy(packets)
                    selected = next(packet for packet in packets if packet.candidate_id == decision.selected_candidate_id)
                elif policy_name == "random_label_baseline":
                    selected = sorted(
                        packets,
                        key=lambda packet: (_stable_uint(seed, scenario, task_seed, packet.candidate_id), packet.candidate_id),
                    )[0]
                else:
                    raise ValueError(f"Unsupported toy policy: {policy_name}")
                selected_label = str(selected.metadata["observation_label"])
                selected_delay = str(selected.metadata["delay_label"])
                rows.append(
                    {
                        "scenario_name": scenario,
                        "seed": int(task_seed),
                        "policy_name": policy_name,
                        "true_observation_label": task.true_observation_label,
                        "selected_observation_label": selected_label,
                        "observation_label_recovered": selected_label == task.true_observation_label,
                        "true_delay_label": task.delay_label,
                        "selected_delay_label": selected_delay,
                        "delay_label_recovered": selected_delay == task.delay_label,
                        "rolling_error": selected.rolling_mean_mae,
                    }
                )
    frame = pd.DataFrame.from_records(rows)
    aggregates = (
        frame.groupby("policy_name", as_index=False)
        .agg(
            observation_label_recovery_rate=("observation_label_recovered", "mean"),
            delay_label_recovery_rate=("delay_label_recovered", "mean"),
            mean_rolling_error=("rolling_error", "mean"),
        )
    )
    return frame.merge(aggregates, on="policy_name", how="left")


def run_selection_policy_stage2(config: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    artifact_root = ensure_dir(repo_root / config["artifacts"]["root_dir"])
    frozen_root = repo_root / config["data"]["frozen_artifact_root"]
    policy_config = config.get("policy", {})
    toy_config = config.get("toy_tasks", {})
    seed = int(config.get("seed", 42))
    epsilon = float(policy_config.get("epsilon", 0.02))
    budgets = tuple(int(value) for value in config.get("stage2", {}).get("budgets", DEFAULT_BUDGETS))
    toy_scenarios = tuple(str(value) for value in config.get("stage2", {}).get("toy_scenarios", DEFAULT_TOY_SCENARIOS))
    toy_seeds = tuple(int(value) for value in config.get("stage2", {}).get("toy_seeds", toy_config.get("seeds", [1, 2, 3])))

    model_summary = pd.read_csv(frozen_root / "benchmark_model_summary.csv")
    recommendations = pd.read_csv(frozen_root / "paper_recommendation_table.csv")
    negative = run_verifier_negative_set()
    replay = run_budgeted_candidate_replay(
        model_summary,
        recommendations,
        budgets=budgets,
        epsilon=epsilon,
        seed=seed,
    )
    toy = run_toy_policy_recovery(scenarios=toy_scenarios, seeds=toy_seeds, epsilon=0.0, seed=seed)

    _write_csv(negative, artifact_root / "verifier_negative_set.csv")
    _write_csv(replay, artifact_root / "budgeted_replay_efficiency.csv")
    _write_csv(toy, artifact_root / "toy_observation_recovery_summary.csv")

    run_summary_path = artifact_root / "run_summary.json"
    if run_summary_path.exists():
        run_summary = json.loads(run_summary_path.read_text(encoding="utf-8"))
    else:
        run_summary = {
            "evaluation_type": "deterministic offline selection policy evaluation",
            "external_api_used": False,
            "artifact_root": repo_relative_path(artifact_root, repo_root),
            "frozen_artifact_root": repo_relative_path(frozen_root, repo_root),
        }
    run_summary.update(
        {
            "stage2_enabled": True,
            "stage2_negative_rejection_rate": float(negative["rejection_rate"].iloc[0]) if not negative.empty else None,
            "stage2_budgeted_replay_rows": int(len(replay)),
            "stage2_replay_budgets": list(budgets),
            "stage2_toy_policy_rows": int(len(toy)),
            "stage2_toy_scenarios": list(toy_scenarios),
            "stage2_toy_seeds": list(toy_seeds),
        }
    )
    _write_json_lf(run_summary, run_summary_path)
    return run_summary
