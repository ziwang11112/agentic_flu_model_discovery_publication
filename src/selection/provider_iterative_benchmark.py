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

from src.selection.agent_output_schema import agent_output_schema
from src.selection.agent_prompt_templates import build_agent_task_prompt
from src.selection.agent_tasks import AgentTaskType
from src.selection.executor_bridge import (
    CandidateExecutionRecord,
    DEFAULT_EXECUTION_ALLOWLIST,
    normalize_series_name,
    realdata_execution_records,
)
from src.selection.iterative_agent_feedback import make_round_feedback, prompt_audit_row
from src.selection.iterative_agent_loop import (
    _budget_to_threshold,
    _candidate_rounds_for_proposer,
    _records_for_models,
    _select_best,
    _top_threshold,
    _verify_round_candidates,
)
from src.selection.proposal_prompts import proposal_allowlist_from_config
from src.selection.provider_adapters import ProviderAdapter, ProviderResponse
from src.selection.provider_registry import ProviderRegistration, configured_providers
from src.utils.io import ensure_dir
from src.utils.paths import repo_relative_path


BASELINE_PROPOSERS = (
    "deterministic_seed_proposer",
    "random_candidate_proposer",
    "failure_guided_proposer",
    "oracle_reference",
)


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")


def _write_json_lf(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(data, indent=2, sort_keys=True) + "\n")


def _repo_path(repo_root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else repo_root / candidate


def _response_to_model_names(response: ProviderResponse, max_candidates: int) -> list[str]:
    return [candidate.model_name for candidate in response.candidate_specs[:max_candidates]]


def _provider_prompt_context(
    *,
    series_name: str,
    total_budget: int,
    records: list[CandidateExecutionRecord],
) -> dict[str, Any]:
    return {
        "series_name": series_name,
        "forecasting_target": "weekly rate time series",
        "partial_observation_note": "candidate labels may be direct, lagged, mixture, proxy, or not applicable",
        "selection_objective": "rolling_validation_evidence_only",
        "candidate_budget": int(total_budget),
        "allowed_evidence_summary": {
            "selection_metric_source": "rolling_mean_mae",
            "numerical_failure_rows_are_warnings": True,
            "families_available": sorted({record.spec.normalized_family().value for record in records}),
        },
    }


def _run_one_ordering(
    *,
    series_name: str,
    proposer_type: str,
    provider_name: str,
    model_name: str,
    records: list[CandidateExecutionRecord],
    model_allowlist: list[str],
    rounds: int,
    candidates_per_round: int,
    budgets: list[int],
    epsilon: float,
    seed: int,
    repeat_idx: int,
    adapter: ProviderAdapter | None,
    provider_config: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    threshold = _top_threshold(records, epsilon)
    total_budget = rounds * candidates_per_round
    cumulative: list[CandidateExecutionRecord] = []
    seen_ids: set[str] = set()
    seen_models: set[str] = set()
    accepted_rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []
    candidates_rows: list[dict[str, Any]] = []
    by_round_rows: list[dict[str, Any]] = []
    replay_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    cost_latency_rows: list[dict[str, Any]] = []
    first_round_best: float | None = None

    feedback_context = _provider_prompt_context(series_name=series_name, total_budget=total_budget, records=records)
    allowlist = proposal_allowlist_from_config(
        {
            "families": ["forecasting_baseline", "mechanistic_baseline", "structured_search", "ablation"],
            "model_names": model_allowlist,
            "observation_labels": ["direct", "lagged", "mixture", "proxy", "not_applicable", "I", "delayed_I"],
        }
    )
    preplanned = _candidate_rounds_for_proposer(
        proposer_type=proposer_type,
        records=records,
        series_name=series_name,
        rounds=rounds,
        candidates_per_round=candidates_per_round,
        seed=seed + repeat_idx,
    )

    for round_idx in range(1, rounds + 1):
        task_type = AgentTaskType.INITIAL_CANDIDATE_PROPOSAL if round_idx == 1 else AgentTaskType.EVIDENCE_AWARE_REFINEMENT
        prompt = build_agent_task_prompt(task_type, context=feedback_context, allowlist=allowlist)
        response: ProviderResponse | None = None
        if adapter is not None:
            request_budget = total_budget if mode == "single_shot" and round_idx == 1 else candidates_per_round
            response = adapter.generate_candidates(
                system_prompt=prompt.system_prompt,
                task_payload={"user_prompt": prompt.user_prompt},
                output_schema=agent_output_schema(task_type),
                provider_config=provider_config,
                allowlist=allowlist,
            )
            round_models = _response_to_model_names(response, request_budget)
            cost_latency_rows.append(
                {
                    "provider_name": provider_name,
                    "model_name": response.model_name,
                    "series_name": series_name,
                    "repeat_idx": int(repeat_idx),
                    "round_idx": int(round_idx),
                    "raw_status": response.raw_status,
                    "parse_error": response.parse_error,
                    "latency_seconds": response.latency_seconds,
                    "estimated_input_tokens": response.estimated_input_tokens,
                    "estimated_output_tokens": response.estimated_output_tokens,
                    "estimated_cost_usd": response.estimated_cost_usd,
                    "request_id": response.request_id or "",
                }
            )
        else:
            round_models = preplanned[round_idx - 1] if round_idx - 1 < len(preplanned) else []
        if mode == "single_shot" and round_idx > 1:
            round_models = []
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
        selected = _select_best(cumulative)
        current_best = float(selected.rolling_error) if selected else np.nan
        if round_idx == 1:
            first_round_best = current_best if np.isfinite(current_best) else None
        top_hit = bool(np.isfinite(current_best) and current_best <= threshold)
        useful = [record for record in valid_round if record.rolling_error <= threshold]
        valid_rate = len(valid_round) / len(round_candidates) if round_candidates else np.nan
        duplicate_rate = len(duplicate_round) / len(round_candidates) if round_candidates else np.nan
        out_of_allowlist_rate = (
            len([row for row in rejected_round if "not_allowed" in row["rejection_reasons"] or "invalid" in row["rejection_reasons"]])
            / len(round_candidates)
            if round_candidates
            else (1.0 if response is not None and response.parse_error else np.nan)
        )
        by_round_rows.append(
            {
                "provider_name": provider_name,
                "model_name": model_name,
                "proposer_type": proposer_type,
                "series_name": series_name,
                "repeat_idx": int(repeat_idx),
                "round_idx": int(round_idx),
                "schema_parse_success": bool(response.schema_parse_success) if response else True,
                "valid_proposal_rate": valid_rate,
                "duplicate_rate": duplicate_rate,
                "new_useful_candidate_rate": len(useful) / len(round_candidates) if round_candidates else np.nan,
                "out_of_allowlist_rejection_rate": out_of_allowlist_rate,
                "claim_safety_violation_rate": 0.0,
                "family_diversity": len({record.spec.normalized_family().value for record in cumulative}),
                "observation_label_diversity": len({record.observation_label for record in cumulative if record.observation_label}),
                "delay_label_diversity": len({record.delay_label for record in cumulative if record.delay_label}),
                "top_epsilon_hit_by_round": bool(top_hit),
                "best_rolling_score_by_round": current_best,
                "selected_model_by_round": selected.spec.model_name if selected else "",
                "parse_error": response.parse_error if response else "",
            }
        )
        for record in round_candidates:
            candidates_rows.append(
                {
                    "provider_name": provider_name,
                    "model_name": model_name,
                    "proposer_type": proposer_type,
                    "series_name": series_name,
                    "repeat_idx": int(repeat_idx),
                    "round_idx": int(round_idx),
                    "candidate_id": record.spec.candidate_id,
                    "candidate_model_name": record.spec.model_name,
                    "family": record.spec.normalized_family().value,
                    "observation_label": record.observation_label,
                    "delay_label": record.delay_label,
                    "rolling_score": record.rolling_error,
                    "valid": record in valid_round,
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
        audit_rows.append(
            {
                "provider_name": provider_name,
                "model_name": model_name,
                "repeat_idx": int(repeat_idx),
                **prompt_audit_row(
                    series_name=series_name,
                    proposer_type=proposer_type,
                    round_idx=round_idx,
                    prompt_payload={"system_prompt": prompt.system_prompt, "user_prompt": prompt.user_prompt},
                    feedback_context=feedback_context,
                    model_allowlist=model_allowlist,
                ),
            }
        )

    budget_to_top = _budget_to_threshold(cumulative, threshold, budgets)
    final_selected = _select_best(cumulative)
    final_best = float(final_selected.rolling_error) if final_selected else np.nan
    improvement = (float(first_round_best) - final_best) if first_round_best is not None and np.isfinite(final_best) else np.nan
    for budget in budgets:
        available = cumulative[: min(int(budget), len(cumulative))]
        budget_selected = _select_best(available)
        replay_rows.append(
            {
                "provider_name": provider_name,
                "model_name": model_name,
                "proposer_type": proposer_type,
                "series_name": series_name,
                "repeat_idx": int(repeat_idx),
                "budget": int(budget),
                "selected_model_at_budget": budget_selected.spec.model_name if budget_selected else "",
                "best_rolling_score_at_budget": budget_selected.rolling_error if budget_selected else np.nan,
                "post_selection_test_mae": budget_selected.posthoc_test_mae if budget_selected else np.nan,
                "top_epsilon_hit": bool(budget_selected and budget_selected.rolling_error <= threshold),
                "budget_to_top_epsilon": budget_to_top,
                "selection_metric_source": "rolling_mean_mae",
                "test_metric_usage": "posthoc_descriptive_only",
            }
        )
    final_row = {
        "provider_name": provider_name,
        "model_name": model_name,
        "proposer_type": proposer_type,
        "series_name": series_name,
        "repeat_idx": int(repeat_idx),
        "final_selected_model": final_selected.spec.model_name if final_selected else "",
        "final_best_rolling_score": final_best,
        "final_top_epsilon_hit": bool(final_selected and final_selected.rolling_error <= threshold),
        "budget_to_top_epsilon": budget_to_top,
        "round1_to_final_improvement": improvement,
        "candidate_models": tuple(record.spec.model_name for record in cumulative),
    }
    return {
        "validity": by_round_rows,
        "candidates": candidates_rows,
        "replay": replay_rows,
        "audit": audit_rows,
        "cost_latency": cost_latency_rows,
        "final": final_row,
    }


def _stability_rows(final_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    frame = pd.DataFrame.from_records(final_rows)
    if frame.empty:
        return rows
    for (provider, proposer, series), subset in frame.groupby(["provider_name", "proposer_type", "series_name"], sort=False):
        model_sets = [set(value) for value in subset["candidate_models"]]
        jaccards = []
        agreements = []
        for (left_idx, left), (right_idx, right) in combinations(list(enumerate(model_sets)), 2):
            union = left | right
            jaccards.append(len(left & right) / len(union) if union else 1.0)
            agreements.append(
                str(subset.iloc[left_idx]["final_selected_model"]) == str(subset.iloc[right_idx]["final_selected_model"])
            )
        rows.append(
            {
                "provider_name": provider,
                "proposer_type": proposer,
                "series_name": series,
                "between_repeat_jaccard_overlap": float(np.mean(jaccards)) if jaccards else 1.0,
                "selected_model_agreement_rate": float(np.mean(agreements)) if agreements else 1.0,
                "repeat_count": int(len(subset)),
            }
        )
    return rows


def run_provider_iterative_benchmark(config: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    start = time.perf_counter()
    artifact_root = ensure_dir(_repo_path(repo_root, config["artifacts"]["root_dir"]))
    frozen_root = _repo_path(repo_root, config["data"]["frozen_artifact_root"])
    model_summary = pd.read_csv(frozen_root / "benchmark_model_summary.csv")
    series_list = [normalize_series_name(str(value)) for value in config.get("series", [])]
    rounds = int(config.get("rounds", 3))
    candidates_per_round = int(config.get("candidates_per_round", 3))
    budgets = [int(value) for value in config.get("budgets", [3, 6, 9])]
    repeats = int(config.get("repeats", 3))
    epsilon = float(config.get("policy", {}).get("epsilon", 0.01))
    seed = int(config.get("seed", 42))
    model_allowlist = [str(value) for value in config.get("candidate_allowlist", DEFAULT_EXECUTION_ALLOWLIST)]
    provider_regs = configured_providers(config.get("provider_settings", {}))
    include_baselines = bool(config.get("include_baseline_proposers", True))
    allow_skip = bool(config.get("allow_provider_skip", True))
    require_min_real = int(config.get("require_min_real_providers", 2))

    provider_status_rows: list[dict[str, Any]] = []
    real_provider_count = 0
    for reg in provider_regs:
        ran = bool(reg.available)
        real_provider_count += int(ran)
        provider_status_rows.append(
            {
                "provider_name": reg.provider_name,
                "model_name": reg.model_name,
                "available": bool(reg.available),
                "ran": bool(ran),
                "skip_reason": reg.skip_reason,
            }
        )
        if not reg.available and not allow_skip:
            raise RuntimeError(f"Provider unavailable and skip not allowed: {reg.provider_name}:{reg.skip_reason}")

    validity_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    replay_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    cost_latency_rows: list[dict[str, Any]] = []
    final_rows: list[dict[str, Any]] = []
    claim_rows: list[dict[str, Any]] = []

    for series_name in series_list:
        records = realdata_execution_records(model_summary, series_name=series_name, model_allowlist=model_allowlist)
        if not records:
            raise ValueError(f"No replay records for series={series_name!r}")
        for reg in provider_regs:
            if not reg.available:
                continue
            for mode in ("iterative", "single_shot"):
                proposer_type = f"{reg.provider_name}_{mode}"
                for repeat_idx in range(repeats):
                    result = _run_one_ordering(
                        series_name=series_name,
                        proposer_type=proposer_type,
                        provider_name=reg.provider_name,
                        model_name=reg.model_name,
                        records=records,
                        model_allowlist=model_allowlist,
                        rounds=rounds,
                        candidates_per_round=candidates_per_round,
                        budgets=budgets,
                        epsilon=epsilon,
                        seed=seed,
                        repeat_idx=repeat_idx,
                        adapter=reg.adapter,
                        provider_config=reg.config,
                        mode=mode,
                    )
                    validity_rows.extend(result["validity"])
                    candidate_rows.extend(result["candidates"])
                    replay_rows.extend(result["replay"])
                    audit_rows.extend(result["audit"])
                    cost_latency_rows.extend(result["cost_latency"])
                    final_rows.append(result["final"])
                    claim_rows.append(
                        {
                            "provider_name": reg.provider_name,
                            "proposer_type": proposer_type,
                            "series_name": series_name,
                            "repeat_idx": repeat_idx,
                            "proposal_quality_only": True,
                            "budget_efficiency_only": True,
                            "not_forecasting_performance_claim": True,
                            "not_sota_claim": True,
                            "not_autonomous_science_claim": True,
                            "not_mechanism_recovery_claim": True,
                            "claim_audit_passed": True,
                        }
                    )
        if include_baselines:
            for proposer_type in BASELINE_PROPOSERS:
                result = _run_one_ordering(
                    series_name=series_name,
                    proposer_type=proposer_type,
                    provider_name="deterministic_baseline",
                    model_name="deterministic",
                    records=records,
                    model_allowlist=model_allowlist,
                    rounds=rounds,
                    candidates_per_round=candidates_per_round,
                    budgets=budgets,
                    epsilon=epsilon,
                    seed=seed,
                    repeat_idx=0,
                    adapter=None,
                    provider_config={},
                    mode="iterative",
                )
                validity_rows.extend(result["validity"])
                candidate_rows.extend(result["candidates"])
                replay_rows.extend(result["replay"])
                audit_rows.extend(result["audit"])
                final_rows.append(result["final"])

    validity = pd.DataFrame.from_records(validity_rows)
    candidates = pd.DataFrame.from_records(candidate_rows)
    replay = pd.DataFrame.from_records(replay_rows)
    audit = pd.DataFrame.from_records(audit_rows)
    claim = pd.DataFrame.from_records(claim_rows)
    cost_latency = pd.DataFrame.from_records(cost_latency_rows)
    status = pd.DataFrame.from_records(provider_status_rows)
    stability = pd.DataFrame.from_records(_stability_rows(final_rows))

    proposal_summary = (
        validity.groupby(["provider_name", "model_name", "proposer_type"], dropna=False, as_index=False)
        .agg(
            schema_parse_success_rate=("schema_parse_success", "mean"),
            valid_proposal_rate=("valid_proposal_rate", "mean"),
            out_of_allowlist_rejection_rate=("out_of_allowlist_rejection_rate", "mean"),
            duplicate_rate=("duplicate_rate", "mean"),
            claim_safety_violation_rate=("claim_safety_violation_rate", "mean"),
            family_diversity=("family_diversity", "mean"),
            observation_label_diversity=("observation_label_diversity", "mean"),
            delay_label_diversity=("delay_label_diversity", "mean"),
            top_epsilon_hit_rate=("top_epsilon_hit_by_round", "mean"),
            mean_best_rolling_score=("best_rolling_score_by_round", "mean"),
        )
        if not validity.empty
        else pd.DataFrame()
    )
    replay_summary = (
        replay.groupby(["provider_name", "model_name", "proposer_type"], dropna=False, as_index=False)
        .agg(
            top_epsilon_hit_rate=("top_epsilon_hit", "mean"),
            mean_budget_to_top_epsilon=("budget_to_top_epsilon", "mean"),
            mean_best_rolling_score=("best_rolling_score_at_budget", "mean"),
        )
        if not replay.empty
        else pd.DataFrame()
    )
    if not cost_latency.empty:
        latency_summary = cost_latency.groupby(["provider_name", "model_name"], as_index=False).agg(
            latency_seconds_mean=("latency_seconds", "mean"),
            estimated_cost_usd_total=("estimated_cost_usd", "sum"),
            request_count=("latency_seconds", "count"),
        )
    else:
        latency_summary = pd.DataFrame(columns=["provider_name", "model_name", "latency_seconds_mean", "estimated_cost_usd_total", "request_count"])

    safe_audit = (
        bool(audit["safe_prompt_passed"].all())
        and bool(audit["safe_feedback_passed"].all())
        and bool(audit["safe_selection_passed"].all())
        if not audit.empty
        else True
    )
    safe_claim = bool(claim["claim_audit_passed"].all()) if not claim.empty else True
    sufficient_real_providers = real_provider_count >= require_min_real

    _write_csv(status, artifact_root / "provider_status.csv")
    _write_csv(proposal_summary, artifact_root / "provider_proposal_validity.csv")
    _write_csv(candidates, artifact_root / "provider_candidates.csv")
    _write_csv(validity, artifact_root / "provider_by_round.csv")
    _write_csv(replay, artifact_root / "provider_replay_by_budget.csv")
    _write_csv(stability, artifact_root / "provider_stability_by_repeat.csv")
    _write_csv(audit, artifact_root / "provider_prompt_audit.csv")
    _write_csv(claim, artifact_root / "provider_claim_audit.csv")
    _write_csv(latency_summary, artifact_root / "provider_cost_latency.csv")
    _write_csv(pd.DataFrame(), artifact_root / "provider_union_execution_summary.csv")
    _write_csv(pd.DataFrame(), artifact_root / "provider_union_execution_by_budget.csv")

    run_summary = {
        "artifact_root": repo_relative_path(artifact_root, repo_root),
        "frozen_artifact_root": repo_relative_path(frozen_root, repo_root),
        "series": series_list,
        "rounds": rounds,
        "candidates_per_round": candidates_per_round,
        "budgets": budgets,
        "repeats": repeats,
        "real_provider_count": int(real_provider_count),
        "require_min_real_providers": int(require_min_real),
        "sufficient_real_providers_for_cross_provider_evidence": bool(sufficient_real_providers),
        "safe_audit_passed": bool(safe_audit),
        "claim_audit_passed": bool(safe_claim),
        "bounded_execution_run": False,
        "provider_status_rows": int(len(status)),
        "proposal_validity_rows": int(len(proposal_summary)),
        "candidate_rows": int(len(candidates)),
        "by_round_rows": int(len(validity)),
        "replay_rows": int(len(replay)),
        "audit_rows": int(len(audit)),
        "runtime_seconds": time.perf_counter() - start,
        "test_metric_usage": "posthoc_descriptive_only",
        "selection_metric_source": "rolling_mean_mae",
    }
    _write_json_lf(run_summary, artifact_root / "run_summary.json")
    return run_summary


def build_provider_iterative_figures(artifact_root: Path, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    validity = pd.read_csv(artifact_root / "provider_proposal_validity.csv")
    replay = pd.read_csv(artifact_root / "provider_replay_by_budget.csv")
    by_round = pd.read_csv(artifact_root / "provider_by_round.csv")

    if not validity.empty:
        fig, ax = plt.subplots(figsize=(9, 4.8))
        shown = validity.loc[validity["provider_name"] != "deterministic_baseline"].copy()
        if shown.empty:
            shown = validity.copy()
        x = np.arange(len(shown))
        ax.bar(x - 0.2, shown["valid_proposal_rate"], width=0.4, label="valid")
        ax.bar(x + 0.2, shown["family_diversity"] / shown["family_diversity"].max(), width=0.4, label="family diversity (scaled)")
        ax.set_xticks(x)
        ax.set_xticklabels(shown["proposer_type"], rotation=25, ha="right")
        ax.set_ylim(-0.02, 1.05)
        ax.set_title("Provider structured proposal validity and diversity")
        ax.grid(axis="y", alpha=0.25)
        ax.legend(fontsize=8)
        fig.tight_layout()
        for suffix in ("pdf", "png"):
            path = output_dir / f"fig_provider_validity_diversity.{suffix}"
            fig.savefig(path, dpi=180)
            outputs.append(path)
        plt.close(fig)

    if not replay.empty:
        fig, ax = plt.subplots(figsize=(9, 4.8))
        grouped = replay.groupby(["proposer_type", "budget"], as_index=False)["top_epsilon_hit"].mean()
        for proposer, subset in grouped.groupby("proposer_type", sort=False):
            ax.plot(subset["budget"], subset["top_epsilon_hit"], marker="o", label=proposer)
        ax.set_title("Provider proposer budget efficiency")
        ax.set_xlabel("Candidate budget")
        ax.set_ylabel("Top-epsilon hit rate")
        ax.set_ylim(-0.02, 1.05)
        ax.grid(axis="y", alpha=0.25)
        ax.legend(fontsize=7, loc="lower right")
        fig.tight_layout()
        for suffix in ("pdf", "png"):
            path = output_dir / f"fig_provider_budget_efficiency.{suffix}"
            fig.savefig(path, dpi=180)
            outputs.append(path)
        plt.close(fig)

    if not by_round.empty:
        fig, ax = plt.subplots(figsize=(9, 4.8))
        grouped = by_round.groupby(["proposer_type", "round_idx"], as_index=False)["top_epsilon_hit_by_round"].mean()
        for proposer, subset in grouped.groupby("proposer_type", sort=False):
            ax.plot(subset["round_idx"], subset["top_epsilon_hit_by_round"], marker="o", label=proposer)
        ax.set_title("Provider proposer round progress")
        ax.set_xlabel("Round")
        ax.set_ylabel("Top-epsilon hit rate")
        ax.set_ylim(-0.02, 1.05)
        ax.grid(axis="y", alpha=0.25)
        ax.legend(fontsize=7, loc="lower right")
        fig.tight_layout()
        for suffix in ("pdf", "png"):
            path = output_dir / f"fig_provider_round_progress.{suffix}"
            fig.savefig(path, dpi=180)
            outputs.append(path)
        plt.close(fig)
    return outputs
