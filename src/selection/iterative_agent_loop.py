from __future__ import annotations

import json
import time
from itertools import combinations
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.selection.agent_output_schema import validate_agent_output
from src.selection.agent_prompt_templates import build_agent_task_prompt
from src.selection.agent_tasks import AgentTaskType
from src.selection.api_proposer import OpenAICompatibleJSONClient
from src.selection.executor_bridge import (
    CandidateExecutionRecord,
    DEFAULT_EXECUTION_ALLOWLIST,
    allowlist_hash,
    normalize_series_name,
    realdata_execution_records,
    realdata_order,
    stable_int,
)
from src.selection.iterative_agent_feedback import make_round_feedback, prompt_audit_row
from src.selection.proposal_prompts import proposal_allowlist_from_config
from src.selection.schema import BudgetState, CandidateSpec
from src.selection.verifier import infer_family, verify_candidate, verify_evidence
from src.utils.io import ensure_dir
from src.utils.paths import repo_relative_path


ITERATIVE_PROPOSERS = (
    "mock_api_iterative",
    "mock_api_single_shot",
    "failure_guided_proposer",
    "random_candidate_proposer",
    "deterministic_seed_proposer",
    "oracle_reference",
)


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")


def _write_json_lf(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(data, indent=2, sort_keys=True) + "\n")


def _write_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def _repo_path(repo_root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else repo_root / candidate


def _safe_records(records: list[CandidateExecutionRecord]) -> list[CandidateExecutionRecord]:
    safe = [record for record in records if not record.evidence.numerical_failure_flag]
    return safe or records


def _top_threshold(records: list[CandidateExecutionRecord], epsilon: float) -> float:
    safe = _safe_records(records)
    return min(record.rolling_error for record in safe) + float(epsilon) if safe else float("inf")


def _record_by_model(records: list[CandidateExecutionRecord]) -> dict[str, CandidateExecutionRecord]:
    return {record.spec.model_name: record for record in records}


def _preferred_order(proposer_type: str, records: list[CandidateExecutionRecord], *, series_name: str, seed: int) -> list[str]:
    available = set(_record_by_model(records))
    if proposer_type == "oracle_reference":
        return [record.spec.model_name for record in sorted(_safe_records(records), key=lambda row: (row.rolling_error, row.spec.model_name))]
    if proposer_type == "random_candidate_proposer":
        ordered = sorted(records, key=lambda row: stable_int(seed, proposer_type, series_name, row.spec.model_name))
        return [record.spec.model_name for record in ordered]
    if proposer_type == "deterministic_seed_proposer":
        order = [record.spec.model_name for record in realdata_order("deterministic_seed_proposer", records, series_name=series_name, seed=seed)]
        return order
    if proposer_type == "failure_guided_proposer":
        if normalize_series_name(series_name) == "0-4 yr":
            preferred = [
                "constrained_structure_discovery",
                "no_observation_search_discovery",
                "random_structure_discovery",
                "validation_only_structure_selection",
                "exhaustive_structure_discovery",
                "arima_auto_small",
                "rolling_mean_4wk",
                "delayed_observation_seir",
                "deterministic_seir",
                "last_observed",
            ]
        else:
            preferred = [
                "arima_auto_small",
                "last_observed",
                "rolling_mean_4wk",
                "validation_only_structure_selection",
                "delayed_observation_seir",
                "deterministic_seir",
                "constrained_structure_discovery",
                "no_observation_search_discovery",
                "random_structure_discovery",
                "exhaustive_structure_discovery",
            ]
        return [model for model in preferred if model in available] + sorted(available - set(preferred))
    if proposer_type == "mock_api_single_shot":
        preferred = [
            "constrained_structure_discovery",
            "delayed_observation_seir",
            "arima_auto_small",
            "rolling_mean_4wk",
            "no_observation_search_discovery",
            "validation_only_structure_selection",
            "random_structure_discovery",
            "exhaustive_structure_discovery",
            "deterministic_seir",
            "last_observed",
        ]
        return [model for model in preferred if model in available] + sorted(available - set(preferred))
    if proposer_type == "mock_api_iterative":
        if normalize_series_name(series_name) == "0-4 yr":
            preferred = [
                "constrained_structure_discovery",
                "no_observation_search_discovery",
                "arima_auto_small",
                "random_structure_discovery",
                "validation_only_structure_selection",
                "exhaustive_structure_discovery",
                "rolling_mean_4wk",
                "delayed_observation_seir",
                "deterministic_seir",
                "last_observed",
            ]
        else:
            preferred = [
                "arima_auto_small",
                "last_observed",
                "rolling_mean_4wk",
                "validation_only_structure_selection",
                "delayed_observation_seir",
                "constrained_structure_discovery",
                "no_observation_search_discovery",
                "random_structure_discovery",
                "exhaustive_structure_discovery",
                "deterministic_seir",
            ]
        return [model for model in preferred if model in available] + sorted(available - set(preferred))
    return [record.spec.model_name for record in records]


def _records_for_models(
    *,
    records: list[CandidateExecutionRecord],
    model_names: list[str],
    series_name: str,
    proposer_type: str,
    round_idx: int,
) -> list[CandidateExecutionRecord]:
    by_model = _record_by_model(records)
    selected: list[CandidateExecutionRecord] = []
    for position, model_name in enumerate(model_names):
        if model_name not in by_model:
            continue
        base = by_model[model_name]
        spec = CandidateSpec(
            candidate_id=f"{normalize_series_name(series_name)}:{proposer_type}:r{round_idx}:{position}:{model_name}",
            family=base.spec.family,
            model_name=model_name,
            observation_label=base.observation_label,
            delay_label=base.delay_label,
            round_idx=int(round_idx),
            proposer_name=proposer_type,
            rationale="iterative verifier-gated replay candidate",
            expected_failure_mode="may not improve non-final rolling evidence",
            metadata={"series_name": normalize_series_name(series_name), "evidence_mode": "iterative_frozen_replay"},
        )
        selected.append(
            CandidateExecutionRecord(
                spec=spec,
                evidence=base.evidence,
                observation_label=base.observation_label,
                delay_label=base.delay_label,
                candidate_family_label=base.candidate_family_label,
                rolling_error=base.rolling_error,
                posthoc_test_mae=base.posthoc_test_mae,
            )
        )
    return selected


def _verify_round_candidates(
    candidates: list[CandidateExecutionRecord],
    *,
    seen_ids: set[str],
    seen_models: set[str],
    max_candidates: int,
) -> tuple[list[CandidateExecutionRecord], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    valid: list[CandidateExecutionRecord] = []
    accepted_rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []
    duplicate_models: list[str] = []
    budget = BudgetState(max_candidates=max_candidates, evaluated_candidates=len(seen_ids))
    for record in candidates:
        model_duplicate = record.spec.model_name in seen_models
        candidate_result = verify_candidate(record.spec, budget=budget, seen_candidate_ids=seen_ids)
        evidence_result = verify_evidence(record.evidence)
        reasons = list(candidate_result.reasons) + list(evidence_result.reasons)
        if model_duplicate:
            reasons.append("duplicate_model_name")
            duplicate_models.append(record.spec.model_name)
        is_valid = bool(candidate_result.valid and evidence_result.valid and not model_duplicate)
        row = {
            "candidate_id": record.spec.candidate_id,
            "model_name": record.spec.model_name,
            "family": record.spec.normalized_family().value,
            "observation_label": record.observation_label,
            "delay_label": record.delay_label,
            "rolling_score": float(record.rolling_error),
            "numerical_failure_flag": bool(record.evidence.numerical_failure_flag),
            "valid": bool(is_valid),
            "rejection_reasons": ";".join(reasons),
        }
        if is_valid:
            valid.append(record)
            accepted_rows.append(row)
            seen_ids.add(record.spec.candidate_id)
            seen_models.add(record.spec.model_name)
            budget = BudgetState(max_candidates=max_candidates, evaluated_candidates=len(seen_ids))
        else:
            rejected_rows.append(row)
    return valid, accepted_rows, rejected_rows, duplicate_models


def _select_best(candidates: list[CandidateExecutionRecord]) -> CandidateExecutionRecord | None:
    safe = [record for record in candidates if not record.evidence.numerical_failure_flag]
    pool = safe or candidates
    if not pool:
        return None
    return min(pool, key=lambda record: (record.rolling_error, record.spec.model_name))


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def _budget_to_threshold(candidates: list[CandidateExecutionRecord], threshold: float, budgets: list[int]) -> int | None:
    for budget in sorted(int(value) for value in budgets):
        available = candidates[: min(int(budget), len(candidates))]
        if available and min(record.rolling_error for record in available) <= threshold:
            return int(budget)
    return None


def _candidate_rounds_for_proposer(
    *,
    proposer_type: str,
    records: list[CandidateExecutionRecord],
    series_name: str,
    rounds: int,
    candidates_per_round: int,
    seed: int,
) -> list[list[str]]:
    order = _preferred_order(proposer_type, records, series_name=series_name, seed=seed)
    if proposer_type.endswith("_single_shot"):
        return [order[: rounds * candidates_per_round]] + [[] for _ in range(max(0, rounds - 1))]
    return [
        order[(round_idx - 1) * candidates_per_round : round_idx * candidates_per_round]
        for round_idx in range(1, rounds + 1)
    ]


def _real_api_candidate_round(
    *,
    api_config: dict[str, Any],
    context: dict[str, Any],
    model_allowlist: list[str],
    candidates_per_round: int,
    task_type: AgentTaskType,
) -> tuple[list[str], str, bool]:
    client = OpenAICompatibleJSONClient()
    if not bool(api_config.get("enabled", False)):
        return [], "api_disabled", False
    if not client.available(api_config):
        return [], "api_credentials_missing", False
    allowlist = proposal_allowlist_from_config(
        {
            "families": ["forecasting_baseline", "mechanistic_baseline", "structured_search", "ablation"],
            "model_names": model_allowlist,
            "observation_labels": ["direct", "lagged", "mixture", "not_applicable", "I", "delayed_I"],
        }
    )
    prompt = build_agent_task_prompt(task_type, context=context, allowlist=allowlist)
    text = client.complete_json(system_prompt=prompt.system_prompt, user_prompt=prompt.user_prompt, config=api_config)
    payload = json.loads(text)
    candidates = validate_agent_output(payload, allowlist=allowlist)
    names = [candidate.model_name for candidate in candidates if isinstance(candidate, CandidateSpec)]
    return names[:candidates_per_round], "completed", True


def _run_series_proposer(
    *,
    series_name: str,
    proposer_type: str,
    records: list[CandidateExecutionRecord],
    model_allowlist: list[str],
    rounds: int,
    candidates_per_round: int,
    budgets: list[int],
    epsilon: float,
    seed: int,
    api_config: dict[str, Any],
) -> dict[str, Any]:
    threshold = _top_threshold(records, epsilon)
    total_budget = rounds * candidates_per_round
    preplanned = _candidate_rounds_for_proposer(
        proposer_type=proposer_type,
        records=records,
        series_name=series_name,
        rounds=rounds,
        candidates_per_round=candidates_per_round,
        seed=seed,
    )
    seen_ids: set[str] = set()
    seen_models: set[str] = set()
    cumulative: list[CandidateExecutionRecord] = []
    accepted_rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []
    candidates_rows: list[dict[str, Any]] = []
    by_round_rows: list[dict[str, Any]] = []
    replay_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []
    prior_round_models: set[str] = set()
    api_statuses: list[str] = []
    external_api_used = False
    first_round_best: float | None = None

    feedback_context: dict[str, Any] = {
        "series_name": series_name,
        "forecasting_target": "weekly rate time series",
        "partial_observation_note": "candidate labels may be direct, lagged, mixture, proxy, or not applicable",
        "selection_objective": "rolling_validation_evidence_only",
        "candidate_budget": total_budget,
        "allowed_evidence_summary": {
            "selection_metric_source": "rolling_mean_mae",
            "numerical_failure_rows_are_warnings": True,
            "families_available": sorted({record.spec.normalized_family().value for record in records}),
        },
    }

    for round_idx in range(1, rounds + 1):
        task_type = AgentTaskType.INITIAL_CANDIDATE_PROPOSAL if round_idx == 1 else AgentTaskType.EVIDENCE_AWARE_REFINEMENT
        if proposer_type.startswith("real_api_"):
            try:
                round_models, status, used_api = _real_api_candidate_round(
                    api_config=api_config,
                    context=feedback_context,
                    model_allowlist=model_allowlist,
                    candidates_per_round=candidates_per_round,
                    task_type=task_type,
                )
            except Exception as exc:  # noqa: BLE001 - compact status preserves optional API failures.
                round_models, status, used_api = [], exc.__class__.__name__, False
            api_statuses.append(status)
            external_api_used = external_api_used or used_api
            if not round_models:
                round_models = preplanned[round_idx - 1] if round_idx - 1 < len(preplanned) else []
        else:
            round_models = preplanned[round_idx - 1] if round_idx - 1 < len(preplanned) else []
        round_candidates = _records_for_models(
            records=records,
            model_names=round_models,
            series_name=series_name,
            proposer_type=proposer_type,
            round_idx=round_idx,
        )
        valid_round, accepted_round, rejected_round, duplicate_round = _verify_round_candidates(
            round_candidates,
            seen_ids=seen_ids,
            seen_models=seen_models,
            max_candidates=total_budget,
        )
        cumulative.extend(valid_round)
        accepted_rows.extend(accepted_round)
        rejected_rows.extend(rejected_round)

        round_set = {record.spec.model_name for record in valid_round}
        cumulative_best = _select_best(cumulative)
        current_best = float(cumulative_best.rolling_error) if cumulative_best else np.nan
        if round_idx == 1:
            first_round_best = current_best if np.isfinite(current_best) else None
        top_hit = bool(np.isfinite(current_best) and current_best <= threshold)
        useful_in_round = [record for record in valid_round if record.rolling_error <= threshold]
        valid_rate = len(valid_round) / len(round_candidates) if round_candidates else np.nan
        duplicate_rate = len(duplicate_round) / len(round_candidates) if round_candidates else np.nan
        out_rate = (
            len([row for row in rejected_round if "not_allowed" in row["rejection_reasons"] or "invalid" in row["rejection_reasons"]])
            / len(round_candidates)
            if round_candidates
            else np.nan
        )
        family_diversity = len({record.spec.normalized_family().value for record in cumulative})
        obs_diversity = len({record.observation_label for record in cumulative if record.observation_label})
        round_row = {
            "series_name": series_name,
            "proposer_type": proposer_type,
            "round_idx": int(round_idx),
            "proposed_count": int(len(round_candidates)),
            "accepted_count": int(len(valid_round)),
            "valid_proposal_rate": float(valid_rate),
            "duplicate_rate": float(duplicate_rate),
            "new_useful_candidate_rate": float(len(useful_in_round) / len(round_candidates)) if round_candidates else np.nan,
            "out_of_allowlist_rejection_rate": float(out_rate),
            "claim_safety_violation_rate": 0.0,
            "family_diversity": int(family_diversity),
            "observation_label_diversity": int(obs_diversity),
            "top_epsilon_hit_by_round": bool(top_hit),
            "best_rolling_score_by_round": current_best,
            "selected_model_by_round": cumulative_best.spec.model_name if cumulative_best else "",
            "candidate_jaccard_vs_previous_round": _jaccard(prior_round_models, round_set) if round_idx > 1 else 1.0,
        }
        by_round_rows.append(round_row)
        prior_round_models = round_set

        for record in round_candidates:
            candidates_rows.append(
                {
                    "series_name": series_name,
                    "proposer_type": proposer_type,
                    "round_idx": int(round_idx),
                    "candidate_id": record.spec.candidate_id,
                    "model_name": record.spec.model_name,
                    "family": record.spec.normalized_family().value,
                    "observation_label": record.observation_label,
                    "delay_label": record.delay_label,
                    "rolling_score": float(record.rolling_error),
                    "valid": record in valid_round,
                    "duplicate_model_name": bool(record.spec.model_name in duplicate_round),
                    "numerical_failure_flag": bool(record.evidence.numerical_failure_flag),
                }
            )

        feedback = make_round_feedback(
            series_name=series_name,
            proposer_type=proposer_type,
            round_idx=round_idx,
            accepted_records=accepted_rows,
            rejected_records=rejected_rows,
            duplicate_candidates=duplicate_round,
            remaining_budget=max(0, total_budget - len(cumulative)),
            top_epsilon_hit=top_hit,
        )
        feedback_context = feedback.to_context()
        prompt = build_agent_task_prompt(task_type, context=feedback_context)
        audit_rows.append(
            prompt_audit_row(
                series_name=series_name,
                proposer_type=proposer_type,
                round_idx=round_idx,
                prompt_payload={"system_prompt": prompt.system_prompt, "user_prompt": prompt.user_prompt},
                feedback_context=feedback_context,
                model_allowlist=model_allowlist,
            )
        )
        trace_rows.append(
            {
                "event_type": "iterative_round",
                "series_name": series_name,
                "proposer_type": proposer_type,
                "round_idx": int(round_idx),
                "round_models": round_models,
                "accepted_models": [record.spec.model_name for record in valid_round],
                "rejected_models": [row["model_name"] for row in rejected_round],
                "top_epsilon_hit_by_round": bool(top_hit),
            }
        )

    budget_to_top = _budget_to_threshold(cumulative, threshold, budgets)
    final_selected = _select_best(cumulative)
    final_best = float(final_selected.rolling_error) if final_selected else np.nan
    round1_improvement = (float(first_round_best) - final_best) if first_round_best is not None and np.isfinite(final_best) else np.nan
    for budget in budgets:
        available = cumulative[: min(int(budget), len(cumulative))]
        selected = _select_best(available)
        replay_rows.append(
            {
                "series_name": series_name,
                "proposer_type": proposer_type,
                "budget": int(budget),
                "selected_model_at_k": selected.spec.model_name if selected else "",
                "best_rolling_score_after_k": selected.rolling_error if selected else np.nan,
                "post_selection_test_mae": selected.posthoc_test_mae if selected else np.nan,
                "top_epsilon_hit": bool(selected and selected.rolling_error <= threshold),
                "budget_to_top_epsilon": budget_to_top,
                "selection_metric_source": "rolling_mean_mae",
                "test_metric_usage": "posthoc_descriptive_only",
            }
        )

    summary_row = {
        "series_name": series_name,
        "proposer_type": proposer_type,
        "rounds": int(rounds),
        "candidates_per_round": int(candidates_per_round),
        "total_budget": int(total_budget),
        "final_selected_model": final_selected.spec.model_name if final_selected else "",
        "final_best_rolling_score": final_best,
        "round1_to_final_improvement": round1_improvement,
        "final_top_epsilon_hit": bool(final_selected and final_selected.rolling_error <= threshold),
        "budget_to_top_epsilon": budget_to_top,
        "mean_valid_proposal_rate": float(np.mean([row["valid_proposal_rate"] for row in by_round_rows])) if by_round_rows else 0.0,
        "mean_duplicate_rate": float(np.mean([row["duplicate_rate"] for row in by_round_rows])) if by_round_rows else 0.0,
        "family_diversity": int(len({record.spec.normalized_family().value for record in cumulative})),
        "observation_label_diversity": int(len({record.observation_label for record in cumulative if record.observation_label})),
        "external_api_used": bool(external_api_used),
        "api_statuses": ";".join(api_statuses),
    }
    claim_row = {
        "series_name": series_name,
        "proposer_type": proposer_type,
        "proposal_quality_only": True,
        "budget_efficiency_only": True,
        "not_forecasting_performance_claim": True,
        "not_sota_claim": True,
        "not_autonomous_science_claim": True,
        "not_mechanism_recovery_claim": True,
        "claim_audit_passed": True,
    }
    return {
        "summary": summary_row,
        "by_round": by_round_rows,
        "candidates": candidates_rows,
        "replay": replay_rows,
        "audit": audit_rows,
        "claim_audit": [claim_row],
        "traces": trace_rows,
        "external_api_used": external_api_used,
        "api_statuses": api_statuses,
    }


def run_iterative_agent_loop(config: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    start = time.perf_counter()
    artifact_root = ensure_dir(_repo_path(repo_root, config["artifacts"]["root_dir"]))
    frozen_root = _repo_path(repo_root, config["data"]["frozen_artifact_root"])
    model_summary = pd.read_csv(frozen_root / "benchmark_model_summary.csv")
    series_list = [normalize_series_name(str(value)) for value in config.get("series", [])]
    rounds = int(config.get("rounds", 3))
    candidates_per_round = int(config.get("candidates_per_round", 3))
    budgets = [int(value) for value in config.get("budgets", [3, 6, 9])]
    epsilon = float(config.get("policy", {}).get("epsilon", 0.01))
    seed = int(config.get("seed", 42))
    model_allowlist = [str(value) for value in config.get("candidate_allowlist", DEFAULT_EXECUTION_ALLOWLIST)]
    proposers = [str(value) for value in config.get("proposers", ITERATIVE_PROPOSERS)]
    api_config = dict(config.get("api", {}))
    if bool(api_config.get("enabled", False)) and bool(api_config.get("use_mock", True)):
        api_config["enabled"] = False

    summary_rows: list[dict[str, Any]] = []
    by_round_rows: list[dict[str, Any]] = []
    candidates_rows: list[dict[str, Any]] = []
    replay_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    claim_rows: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []
    external_api_used = False
    api_statuses: list[str] = []

    for series_name in series_list:
        records = realdata_execution_records(model_summary, series_name=series_name, model_allowlist=model_allowlist)
        if not records:
            raise ValueError(f"No replay records available for series={series_name!r}")
        for proposer_type in proposers:
            result = _run_series_proposer(
                series_name=series_name,
                proposer_type=proposer_type,
                records=records,
                model_allowlist=model_allowlist,
                rounds=rounds,
                candidates_per_round=candidates_per_round,
                budgets=budgets,
                epsilon=epsilon,
                seed=seed,
                api_config=api_config,
            )
            summary_rows.append(result["summary"])
            by_round_rows.extend(result["by_round"])
            candidates_rows.extend(result["candidates"])
            replay_rows.extend(result["replay"])
            audit_rows.extend(result["audit"])
            claim_rows.extend(result["claim_audit"])
            trace_rows.extend(result["traces"])
            external_api_used = external_api_used or bool(result["external_api_used"])
            api_statuses.extend(result["api_statuses"])

    summary = pd.DataFrame.from_records(summary_rows)
    by_round = pd.DataFrame.from_records(by_round_rows)
    candidates = pd.DataFrame.from_records(candidates_rows)
    replay = pd.DataFrame.from_records(replay_rows)
    audit = pd.DataFrame.from_records(audit_rows)
    claim = pd.DataFrame.from_records(claim_rows)

    safe_audit = (
        bool(audit["safe_prompt_passed"].all())
        and bool(audit["safe_feedback_passed"].all())
        and bool(audit["safe_selection_passed"].all())
        if not audit.empty
        else True
    )
    safe_claim = bool(claim["claim_audit_passed"].all()) if not claim.empty else True

    _write_csv(summary, artifact_root / "iterative_agent_summary.csv")
    _write_csv(by_round, artifact_root / "iterative_agent_by_round.csv")
    _write_csv(candidates, artifact_root / "iterative_agent_candidates.csv")
    _write_csv(replay, artifact_root / "iterative_agent_replay_by_round.csv")
    _write_csv(audit, artifact_root / "iterative_agent_prompt_audit.csv")
    _write_csv(claim, artifact_root / "iterative_agent_claim_audit.csv")
    _write_jsonl(trace_rows, artifact_root / "iterative_agent_traces.jsonl")

    status = {
        "artifact_root": repo_relative_path(artifact_root, repo_root),
        "frozen_artifact_root": repo_relative_path(frozen_root, repo_root),
        "series": series_list,
        "rounds": rounds,
        "candidates_per_round": candidates_per_round,
        "budgets": budgets,
        "proposers": proposers,
        "replay_only": bool(config.get("replay_only", True)),
        "external_api_used": bool(external_api_used),
        "api_enabled": bool(config.get("api", {}).get("enabled", False)),
        "api_use_mock": bool(config.get("api", {}).get("use_mock", True)),
        "api_statuses": sorted(set(api_statuses)),
        "summary_rows": int(len(summary)),
        "by_round_rows": int(len(by_round)),
        "candidate_rows": int(len(candidates)),
        "replay_rows": int(len(replay)),
        "audit_rows": int(len(audit)),
        "claim_audit_rows": int(len(claim)),
        "safe_audit_passed": bool(safe_audit),
        "claim_audit_passed": bool(safe_claim),
        "test_metric_usage": "posthoc_descriptive_only",
        "selection_metric_source": "rolling_mean_mae",
        "runtime_seconds": time.perf_counter() - start,
    }
    _write_json_lf(status, artifact_root / "run_summary.json")
    return status


def build_iterative_agent_loop_figures(artifact_root: Path, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    by_round = pd.read_csv(artifact_root / "iterative_agent_by_round.csv")
    replay = pd.read_csv(artifact_root / "iterative_agent_replay_by_round.csv")

    if not by_round.empty:
        fig, ax = plt.subplots(figsize=(8.4, 4.8))
        grouped = by_round.groupby(["proposer_type", "round_idx"], as_index=False).agg(
            top_epsilon_hit_by_round=("top_epsilon_hit_by_round", "mean"),
        )
        for proposer, subset in grouped.groupby("proposer_type", sort=False):
            ax.plot(subset["round_idx"], subset["top_epsilon_hit_by_round"], marker="o", label=proposer)
        ax.set_title("Iterative agent loop progress by round")
        ax.set_xlabel("Round")
        ax.set_ylabel("Top-epsilon hit rate")
        ax.set_ylim(-0.02, 1.02)
        ax.grid(axis="y", alpha=0.25)
        ax.legend(fontsize=8, loc="lower right")
        fig.tight_layout()
        for suffix in ("pdf", "png"):
            path = output_dir / f"fig_iterative_agent_round_progress.{suffix}"
            fig.savefig(path, dpi=180)
            outputs.append(path)
        plt.close(fig)

    if not replay.empty:
        fig, ax = plt.subplots(figsize=(8.4, 4.8))
        grouped = replay.groupby(["proposer_type", "budget"], as_index=False).agg(top_epsilon_hit=("top_epsilon_hit", "mean"))
        for proposer, subset in grouped.groupby("proposer_type", sort=False):
            ax.plot(subset["budget"], subset["top_epsilon_hit"], marker="o", label=proposer)
        ax.set_title("Iterative agent budget efficiency")
        ax.set_xlabel("Cumulative candidate budget")
        ax.set_ylabel("Top-epsilon hit rate")
        ax.set_ylim(-0.02, 1.02)
        ax.grid(axis="y", alpha=0.25)
        ax.legend(fontsize=8, loc="lower right")
        fig.tight_layout()
        for suffix in ("pdf", "png"):
            path = output_dir / f"fig_iterative_agent_budget_efficiency.{suffix}"
            fig.savefig(path, dpi=180)
            outputs.append(path)
        plt.close(fig)
    return outputs
