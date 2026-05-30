from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.selection.executor_bridge import (
    DEFAULT_EXECUTION_ALLOWLIST,
    CandidateExecutionRecord,
    prompt_audit_record,
    realdata_execution_records,
    realdata_order,
    synthetic_execution_records,
    synthetic_order,
)
from src.selection.schema import BudgetState
from src.selection.structured_recovery import generate_structured_toy_task
from src.selection.verifier import verify_candidate, verify_evidence
from src.utils.io import ensure_dir
from src.utils.paths import repo_relative_path


SYNTHETIC_PROPOSERS = (
    "mock_api_proposer",
    "deterministic_seed_proposer",
    "random_candidate_proposer",
    "failure_guided_proposer",
    "no_observation_label_baseline",
    "exhaustive_oracle",
)
REALDATA_PROPOSERS = (
    "mock_api_proposer",
    "deterministic_seed_proposer",
    "random_candidate_proposer",
    "oracle_full_candidate_ranking",
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


def _candidate_is_valid(record: CandidateExecutionRecord, seen: set[str], max_candidates: int) -> tuple[bool, str]:
    budget = BudgetState(max_candidates=max_candidates, evaluated_candidates=len(seen))
    candidate_result = verify_candidate(record.spec, budget=budget, seen_candidate_ids=seen)
    evidence_result = verify_evidence(record.evidence)
    reasons = list(candidate_result.reasons) + list(evidence_result.reasons)
    return bool(candidate_result.valid and evidence_result.valid), ";".join(reasons)


def _budget_to_threshold(ordered: list[CandidateExecutionRecord], threshold: float, budgets: list[int]) -> int | None:
    for budget in sorted(budgets):
        available = ordered[: min(budget, len(ordered))]
        if available and min(row.rolling_error for row in available) <= threshold:
            return int(budget)
    return None


def _synthetic_budget_rows(
    *,
    task_name: str,
    seed: int,
    noise_level: float,
    budgets: list[int],
    proposers: list[str],
    epsilon: float,
    random_seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    task = generate_structured_toy_task(task_name, seed=seed, noise_level=noise_level)
    all_records = synthetic_execution_records(task)
    best_error = min(record.rolling_error for record in all_records)
    top_threshold = best_error + epsilon
    rows: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    for proposer in proposers:
        ordered = synthetic_order(proposer, all_records, task=task, seed=random_seed)
        prompt_payload = {
            "task_name": task_name,
            "noise_level": noise_level,
            "candidate_allowlist": [record.spec.model_name for record in all_records],
            "selection_metric": "rolling_validation_error",
            "metadata": {"layer": "synthetic_execution"},
        }
        audits.append(
            prompt_audit_record(
                series_name=task_name,
                proposer_type=proposer,
                prompt_payload=prompt_payload,
                model_allowlist=[record.spec.model_name for record in all_records],
            )
        )
        seen: set[str] = set()
        validity: list[bool] = []
        rejection_reasons: list[str] = []
        for record in ordered:
            valid, reasons = _candidate_is_valid(record, seen, max_candidates=max(budgets))
            validity.append(valid)
            if reasons:
                rejection_reasons.append(reasons)
            seen.add(record.spec.candidate_id)
        valid_ordered = [record for record, valid in zip(ordered, validity) if valid]
        duplicate_rate = 1.0 - (len({record.spec.candidate_id for record in ordered}) / len(ordered)) if ordered else 0.0
        out_of_allowlist = sum("not_allowed" in reason or "invalid" in reason for reason in rejection_reasons)
        for budget in budgets:
            available = valid_ordered[: min(int(budget), len(valid_ordered))]
            if available:
                selected = min(available, key=lambda record: (record.rolling_error, record.spec.candidate_id))
                best_after_k = float(selected.rolling_error)
                obs_recovered = selected.observation_label == task.true_observation_label
                delay_recovered = selected.delay_label == task.true_delay_label
                family_recovered = selected.candidate_family_label == task.true_candidate_family
                top_epsilon_hit = best_after_k <= top_threshold
            else:
                selected = None
                best_after_k = np.nan
                obs_recovered = False
                delay_recovered = False
                family_recovered = False
                top_epsilon_hit = False
            rows.append(
                {
                    "layer": "synthetic_execution",
                    "task_name": task_name,
                    "seed": int(seed),
                    "noise_level": float(noise_level),
                    "proposer_type": proposer,
                    "budget": int(budget),
                    "selected_candidate_id": selected.spec.candidate_id if selected else "",
                    "selected_model_name": selected.spec.model_name if selected else "",
                    "selected_observation_label": selected.observation_label if selected else "",
                    "selected_delay_label": selected.delay_label if selected else "",
                    "observation_label_recovered": bool(obs_recovered),
                    "delay_label_recovered": bool(delay_recovered),
                    "candidate_family_recovered": bool(family_recovered),
                    "best_rolling_error_after_k": best_after_k,
                    "top_epsilon_hit": bool(top_epsilon_hit),
                    "valid_proposal_rate": float(np.mean(validity)) if validity else 0.0,
                    "duplicate_rate": float(duplicate_rate),
                    "out_of_allowlist_rejection_rate": float(out_of_allowlist / len(ordered)) if ordered else 0.0,
                    "claim_safety_violation_rate": 0.0,
                    "budget_to_recover_true_label": _budget_to_recover(ordered, task.true_observation_label, budgets),
                    "budget_to_top_epsilon": _budget_to_threshold(valid_ordered, top_threshold, budgets),
                }
            )
        traces.append(
            {
                "event_type": "synthetic_proposer_order",
                "task_name": task_name,
                "seed": int(seed),
                "noise_level": float(noise_level),
                "proposer_type": proposer,
                "ordered_candidate_ids": [record.spec.candidate_id for record in ordered],
            }
        )
    return rows, audits, traces


def _budget_to_recover(ordered: list[CandidateExecutionRecord], true_observation_label: str, budgets: list[int]) -> int | None:
    for budget in sorted(budgets):
        available = ordered[: min(int(budget), len(ordered))]
        if any(record.observation_label == true_observation_label for record in available):
            return int(budget)
    return None


def _realdata_budget_rows(
    *,
    model_summary: pd.DataFrame,
    series_name: str,
    budgets: list[int],
    proposers: list[str],
    epsilon: float,
    random_seed: int,
    model_allowlist: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    all_records = realdata_execution_records(model_summary, series_name=series_name, model_allowlist=model_allowlist)
    safe_records = [record for record in all_records if not record.evidence.numerical_failure_flag]
    best_error = min((record.rolling_error for record in safe_records), default=np.nan)
    top_threshold = best_error + epsilon if np.isfinite(best_error) else np.nan
    rows: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    for proposer in proposers:
        ordered = realdata_order(proposer, all_records, series_name=series_name, seed=random_seed)
        prompt_payload = {
            "series_name": series_name,
            "candidate_allowlist": model_allowlist,
            "selection_metric": "rolling_validation_mae",
            "selection_fields": ["rolling_mean_mae", "num_free_params", "numerical_failure_flag"],
            "metadata": {"layer": "frozen_replay"},
        }
        audits.append(
            prompt_audit_record(
                series_name=series_name,
                proposer_type=proposer,
                prompt_payload=prompt_payload,
                model_allowlist=model_allowlist,
            )
        )
        seen: set[str] = set()
        validity: list[bool] = []
        rejection_reasons: list[str] = []
        for record in ordered:
            valid, reasons = _candidate_is_valid(record, seen, max_candidates=max(budgets))
            validity.append(valid)
            if reasons:
                rejection_reasons.append(reasons)
            seen.add(record.spec.candidate_id)
        valid_ordered = [record for record, valid in zip(ordered, validity) if valid]
        duplicate_rate = 1.0 - (len({record.spec.candidate_id for record in ordered}) / len(ordered)) if ordered else 0.0
        out_of_allowlist = sum("not_allowed" in reason or "invalid" in reason for reason in rejection_reasons)
        for budget in budgets:
            available = valid_ordered[: min(int(budget), len(valid_ordered))]
            if available:
                selected = min(available, key=lambda record: (record.rolling_error, record.spec.model_name))
                best_after_k = float(selected.rolling_error)
                top_epsilon_hit = bool(np.isfinite(top_threshold) and best_after_k <= top_threshold)
            else:
                selected = None
                best_after_k = np.nan
                top_epsilon_hit = False
            rows.append(
                {
                    "layer": "frozen_replay",
                    "series_name": series_name,
                    "proposer_type": proposer,
                    "budget": int(budget),
                    "selected_model_at_k": selected.spec.model_name if selected else "",
                    "best_rolling_score_after_k": best_after_k,
                    "post_selection_test_mae": selected.posthoc_test_mae if selected else np.nan,
                    "budget_to_top_epsilon_full_candidate_set": _budget_to_threshold(valid_ordered, top_threshold, budgets) if np.isfinite(top_threshold) else None,
                    "candidate_diversity": len({record.spec.normalized_family().value for record in available}) if available else 0,
                    "invalid_or_rejected_proposals": int(len(ordered) - sum(validity)),
                    "valid_proposal_rate": float(np.mean(validity)) if validity else 0.0,
                    "duplicate_rate": float(duplicate_rate),
                    "out_of_allowlist_rejection_rate": float(out_of_allowlist / len(ordered)) if ordered else 0.0,
                    "claim_safety_violation_rate": 0.0,
                    "top_epsilon_hit": top_epsilon_hit,
                    "evidence_mode": "frozen_replay",
                    "selection_metric_source": "rolling_mean_mae",
                    "test_metric_usage": "posthoc_descriptive_only",
                }
            )
        traces.append(
            {
                "event_type": "realdata_replay_order",
                "series_name": series_name,
                "proposer_type": proposer,
                "ordered_model_names": [record.spec.model_name for record in ordered],
            }
        )
    return rows, audits, traces


def run_api_candidate_execution(config: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    artifact_root = ensure_dir(repo_root / config["artifacts"]["root_dir"])
    budgets = [int(value) for value in config.get("budgets", [3, 5, 10, 20])]
    epsilon = float(config.get("policy", {}).get("epsilon", 0.01))
    random_seed = int(config.get("seed", 42))
    api_config = config.get("api", {})
    if bool(api_config.get("enabled", False)) and not bool(api_config.get("use_mock", False)):
        raise ValueError("Real API candidate execution is intentionally disabled in committed configs.")

    synthetic_config = config.get("synthetic", {})
    realdata_config = config.get("realdata", {})
    model_allowlist = [str(value) for value in config.get("candidate_allowlist", DEFAULT_EXECUTION_ALLOWLIST)]

    synthetic_rows: list[dict[str, Any]] = []
    realdata_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []

    if bool(synthetic_config.get("enabled", True)):
        for task_name in synthetic_config.get("tasks", []):
            for seed in synthetic_config.get("seeds", []):
                for noise_level in synthetic_config.get("noise_levels", []):
                    rows, audits, traces = _synthetic_budget_rows(
                        task_name=str(task_name),
                        seed=int(seed),
                        noise_level=float(noise_level),
                        budgets=budgets,
                        proposers=[str(value) for value in synthetic_config.get("proposers", SYNTHETIC_PROPOSERS)],
                        epsilon=epsilon,
                        random_seed=random_seed,
                    )
                    synthetic_rows.extend(rows)
                    audit_rows.extend(audits)
                    trace_rows.extend(traces)

    if bool(realdata_config.get("enabled", True)):
        frozen_root = repo_root / str(realdata_config.get("frozen_artifact_root", "artifacts_discovery_ablation"))
        model_summary = pd.read_csv(frozen_root / "benchmark_model_summary.csv")
        for series_name in realdata_config.get("series", []):
            rows, audits, traces = _realdata_budget_rows(
                model_summary=model_summary,
                series_name=str(series_name),
                budgets=budgets,
                proposers=[str(value) for value in realdata_config.get("proposers", REALDATA_PROPOSERS)],
                epsilon=epsilon,
                random_seed=random_seed,
                model_allowlist=model_allowlist,
            )
            realdata_rows.extend(rows)
            audit_rows.extend(audits)
            trace_rows.extend(traces)

    synthetic_frame = pd.DataFrame.from_records(synthetic_rows)
    realdata_frame = pd.DataFrame.from_records(realdata_rows)
    audit_frame = pd.DataFrame.from_records(audit_rows).drop_duplicates() if audit_rows else pd.DataFrame()
    by_budget = _build_by_budget(synthetic_frame, realdata_frame)
    summary = _build_summary(synthetic_frame, realdata_frame)

    _write_csv(summary, artifact_root / "api_candidate_execution_summary.csv")
    _write_csv(by_budget, artifact_root / "api_candidate_execution_by_budget.csv")
    _write_csv(synthetic_frame, artifact_root / "api_candidate_execution_synthetic_recovery.csv")
    _write_csv(realdata_frame, artifact_root / "api_candidate_execution_realdata_replay.csv")
    _write_csv(audit_frame, artifact_root / "api_candidate_prompt_audit.csv")
    _write_jsonl(trace_rows, artifact_root / "api_candidate_execution_traces.jsonl")

    status = {
        "artifact_root": repo_relative_path(artifact_root, repo_root),
        "external_api_used": False,
        "api_enabled": bool(api_config.get("enabled", False)),
        "api_use_mock": bool(api_config.get("use_mock", True)),
        "budgets": budgets,
        "synthetic_rows": int(len(synthetic_frame)),
        "realdata_rows": int(len(realdata_frame)),
        "prompt_audit_rows": int(len(audit_frame)),
        "safe_prompt_passed": bool(audit_frame["safe_prompt_passed"].all()) if not audit_frame.empty else True,
        "selection_metric_sources": sorted(realdata_frame["selection_metric_source"].dropna().unique().tolist()) if not realdata_frame.empty else [],
        "test_metric_usage": sorted(realdata_frame["test_metric_usage"].dropna().unique().tolist()) if not realdata_frame.empty else [],
    }
    _write_json_lf(status, artifact_root / "api_candidate_execution_status.json")
    return status


def _build_summary(synthetic_frame: pd.DataFrame, realdata_frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    if not synthetic_frame.empty:
        rows.append(
            synthetic_frame.groupby("proposer_type", as_index=False).agg(
                layer=("layer", "first"),
                observation_label_recovery_rate=("observation_label_recovered", "mean"),
                delay_label_recovery_rate=("delay_label_recovered", "mean"),
                candidate_family_recovery_rate=("candidate_family_recovered", "mean"),
                best_rolling_error_after_k=("best_rolling_error_after_k", "mean"),
                budget_to_recover_true_label=("budget_to_recover_true_label", "mean"),
                budget_to_top_epsilon=("budget_to_top_epsilon", "mean"),
                valid_proposal_rate=("valid_proposal_rate", "mean"),
                duplicate_rate=("duplicate_rate", "mean"),
                out_of_allowlist_rejection_rate=("out_of_allowlist_rejection_rate", "mean"),
                claim_safety_violation_rate=("claim_safety_violation_rate", "mean"),
                top_epsilon_hit_rate=("top_epsilon_hit", "mean"),
            )
        )
    if not realdata_frame.empty:
        rows.append(
            realdata_frame.groupby("proposer_type", as_index=False).agg(
                layer=("layer", "first"),
                best_rolling_score_after_k=("best_rolling_score_after_k", "mean"),
                post_selection_test_mae=("post_selection_test_mae", "mean"),
                budget_to_top_epsilon=("budget_to_top_epsilon_full_candidate_set", "mean"),
                candidate_diversity=("candidate_diversity", "mean"),
                valid_proposal_rate=("valid_proposal_rate", "mean"),
                duplicate_rate=("duplicate_rate", "mean"),
                out_of_allowlist_rejection_rate=("out_of_allowlist_rejection_rate", "mean"),
                claim_safety_violation_rate=("claim_safety_violation_rate", "mean"),
                top_epsilon_hit_rate=("top_epsilon_hit", "mean"),
            )
        )
    return pd.concat(rows, ignore_index=True, sort=False) if rows else pd.DataFrame()


def _build_by_budget(synthetic_frame: pd.DataFrame, realdata_frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    if not synthetic_frame.empty:
        rows.append(
            synthetic_frame.groupby(["layer", "proposer_type", "budget"], as_index=False).agg(
                observation_label_recovery_rate=("observation_label_recovered", "mean"),
                delay_label_recovery_rate=("delay_label_recovered", "mean"),
                candidate_family_recovery_rate=("candidate_family_recovered", "mean"),
                best_rolling_error_after_k=("best_rolling_error_after_k", "mean"),
                top_epsilon_hit_rate=("top_epsilon_hit", "mean"),
            )
        )
    if not realdata_frame.empty:
        rows.append(
            realdata_frame.groupby(["layer", "proposer_type", "budget"], as_index=False).agg(
                best_rolling_score_after_k=("best_rolling_score_after_k", "mean"),
                post_selection_test_mae=("post_selection_test_mae", "mean"),
                candidate_diversity=("candidate_diversity", "mean"),
                top_epsilon_hit_rate=("top_epsilon_hit", "mean"),
            )
        )
    return pd.concat(rows, ignore_index=True, sort=False) if rows else pd.DataFrame()
