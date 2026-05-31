from __future__ import annotations

import json
import shutil
import time
from itertools import combinations
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from run_experiment import _fit_config, _model_seed, _run_one_model, _search_config, _slugify
from src.data.loader import SEASON_MODE_POOLED, build_flu_series_frames, load_flu_surv_data, resolve_data_path
from src.data.split import make_chronological_split
from src.selection.api_execution_prompts import (
    build_execution_system_prompt,
    build_execution_user_payload,
    no_test_evidence_context,
    prompt_has_forbidden_test_context,
)
from src.selection.api_proposer import OpenAICompatibleJSONClient, parse_structured_candidate_response
from src.selection.executor_bridge import (
    DEFAULT_EXECUTION_ALLOWLIST,
    CandidateExecutionRecord,
    allowlist_hash,
    normalize_series_name,
    realdata_execution_records,
    stable_int,
)
from src.selection.proposal_prompts import proposal_allowlist_from_config
from src.selection.schema import BudgetState, CandidateSpec, EvidencePacket
from src.selection.verifier import infer_family, verify_candidate, verify_evidence
from src.utils.io import ensure_dir
from src.utils.paths import repo_relative_path


REAL_EXECUTION_ALLOWLIST = (
    "last_observed",
    "rolling_mean_4wk",
    "arima_auto_small",
    "deterministic_seir",
    "delayed_observation_seir",
    "constrained_structure_discovery",
    "no_observation_search_discovery",
    "validation_only_structure_selection",
)
REPLAY_PROPOSERS = (
    "deterministic_seed_proposer",
    "random_candidate_proposer",
    "failure_guided_proposer",
    "oracle_full_candidate_ranking",
)
EXECUTION_PROPOSERS = (
    "deterministic_seed_proposer",
    "random_candidate_proposer",
    "failure_guided_proposer",
    "mock_api_proposer",
    "oracle_full_candidate_ranking",
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


def _validate_execution_allowlist(model_allowlist: list[str]) -> None:
    unsupported = [model_name for model_name in model_allowlist if model_name not in set(REAL_EXECUTION_ALLOWLIST)]
    if unsupported:
        raise ValueError(f"Bounded real execution allowlist contains unsupported models: {unsupported}")
    for model_name in model_allowlist:
        infer_family(model_name)


def _disable_plot_writes() -> None:
    """Suppress per-model diagnostic PNGs while preserving metric artifacts."""

    def _noop(*args: Any, **kwargs: Any) -> None:
        return None

    import src.evaluation.baseline_pipeline as baseline_pipeline
    import src.evaluation.pipeline as pipeline

    baseline_pipeline._write_optional_plots = _noop  # type: ignore[assignment]
    pipeline.plot_full_series_fit = _noop  # type: ignore[assignment]
    pipeline.plot_residuals = _noop  # type: ignore[assignment]
    pipeline.plot_rolling_forecasts = _noop  # type: ignore[assignment]
    pipeline.plot_leaderboard = _noop  # type: ignore[assignment]
    pipeline.plot_structure_diagram = _noop  # type: ignore[assignment]
    pipeline.plot_probabilistic_calibration = _noop  # type: ignore[assignment]


def _safe_remove_temp(path: Path, repo_root: Path) -> bool:
    resolved = path.resolve()
    root = repo_root.resolve()
    try:
        rel = resolved.relative_to(root)
    except ValueError:
        raise ValueError(f"Refusing to remove temporary path outside repo: {resolved}") from None
    if not str(rel).startswith(".codex_real_candidate_execution_tmp"):
        raise ValueError(f"Refusing to remove unexpected temporary path: {rel}")
    if resolved.exists():
        shutil.rmtree(resolved)
        return True
    return False


def _series_aliases(series_name: str) -> set[str]:
    normalized = normalize_series_name(series_name)
    aliases = {series_name, normalized}
    if normalized == ">= 65 yr":
        aliases.add(">=65 yr")
    return {str(value) for value in aliases}


def _selection_metric_from_row(row: pd.Series) -> float:
    value = row.get("rolling_mean_mae")
    return float(value) if pd.notna(value) else float("inf")


def _candidate_spec_for_model(series_name: str, model_name: str, proposer_type: str, idx: int) -> CandidateSpec:
    return CandidateSpec(
        candidate_id=f"{series_name}:{proposer_type}:{idx}:{model_name}",
        family=infer_family(model_name),
        model_name=model_name,
        observation_label="not_applicable",
        delay_label="",
        round_idx=idx,
        proposer_name=proposer_type,
        rationale="bounded real-data candidate execution candidate",
        metadata={"series_name": series_name, "evidence_mode": "bounded_execution"},
    )


def _prompt_audit_row(
    *,
    layer: str,
    series_name: str,
    proposer_type: str,
    repeat_idx: int,
    prompt_payload: dict[str, Any],
    model_allowlist: list[str],
    selection_uses_test_metric: bool = False,
    posthoc_test_metric_only: bool = True,
) -> dict[str, Any]:
    checks = prompt_has_forbidden_test_context(prompt_payload)
    safe_prompt = not any(checks.values())
    safe_selection = not bool(selection_uses_test_metric)
    return {
        "layer": layer,
        "series_name": series_name,
        "proposer_type": proposer_type,
        "repeat_idx": int(repeat_idx),
        **checks,
        "selection_uses_test_metric": bool(selection_uses_test_metric),
        "posthoc_test_metric_only": bool(posthoc_test_metric_only),
        "safe_prompt_passed": bool(safe_prompt),
        "safe_selection_passed": bool(safe_selection),
        "allowlist_hash": allowlist_hash(model_allowlist),
    }


def _build_prompt_payload(
    *,
    model_summary: pd.DataFrame,
    series_name: str,
    model_allowlist: list[str],
    max_candidates: int,
    objective: str,
) -> dict[str, Any]:
    context = no_test_evidence_context(
        model_summary,
        series_names=[normalize_series_name(series_name)],
        model_allowlist=model_allowlist,
        max_rows=40,
    )
    return build_execution_user_payload(
        series_name=series_name,
        evidence_context=context,
        model_allowlist=model_allowlist,
        max_candidates=max_candidates,
        objective=objective,
    )


def _order_records(
    proposer_type: str,
    records: list[CandidateExecutionRecord],
    *,
    series_name: str,
    seed: int,
    repeat_idx: int,
    api_model_names: list[str] | None = None,
) -> list[CandidateExecutionRecord]:
    if proposer_type in {"oracle_full_candidate_ranking", "exhaustive_oracle"}:
        return sorted(records, key=lambda row: (row.rolling_error, row.spec.model_name))
    if proposer_type == "random_candidate_proposer":
        return sorted(records, key=lambda row: stable_int(seed, proposer_type, series_name, repeat_idx, row.spec.model_name))
    if proposer_type == "failure_guided_proposer":
        if normalize_series_name(series_name) == "0-4 yr":
            preferred = [
                "constrained_structure_discovery",
                "no_observation_search_discovery",
                "delayed_observation_seir",
                "arima_auto_small",
                "rolling_mean_4wk",
                "deterministic_seir",
                "last_observed",
                "validation_only_structure_selection",
            ]
        else:
            preferred = [
                "arima_auto_small",
                "rolling_mean_4wk",
                "delayed_observation_seir",
                "deterministic_seir",
                "constrained_structure_discovery",
                "no_observation_search_discovery",
                "validation_only_structure_selection",
                "last_observed",
            ]
        priority = {model_name: idx for idx, model_name in enumerate(preferred)}
        return sorted(records, key=lambda row: (priority.get(row.spec.model_name, 99), row.rolling_error, row.spec.model_name))
    if proposer_type in {"mock_api_proposer", "real_api_proposer"}:
        preferred = api_model_names or [
            "constrained_structure_discovery",
            "delayed_observation_seir",
            "arima_auto_small",
            "rolling_mean_4wk",
            "no_observation_search_discovery",
            "validation_only_structure_selection",
            "deterministic_seir",
            "last_observed",
        ]
        priority = {model_name: idx for idx, model_name in enumerate(preferred)}
        return sorted(records, key=lambda row: (priority.get(row.spec.model_name, 99), row.rolling_error, row.spec.model_name))
    preferred = [
        "last_observed",
        "rolling_mean_4wk",
        "arima_auto_small",
        "deterministic_seir",
        "delayed_observation_seir",
        "constrained_structure_discovery",
        "no_observation_search_discovery",
        "validation_only_structure_selection",
    ]
    priority = {model_name: idx for idx, model_name in enumerate(preferred)}
    return sorted(records, key=lambda row: (priority.get(row.spec.model_name, 99), row.spec.model_name))


def _verify_order(
    ordered: list[CandidateExecutionRecord],
    *,
    max_candidates: int,
) -> tuple[list[CandidateExecutionRecord], float, float, float, float]:
    seen: set[str] = set()
    valid_records: list[CandidateExecutionRecord] = []
    validity: list[bool] = []
    out_of_allowlist = 0
    claim_violations = 0
    for record in ordered:
        candidate_result = verify_candidate(record.spec, budget=BudgetState(max_candidates=max_candidates), seen_candidate_ids=seen)
        evidence_result = verify_evidence(record.evidence)
        valid = bool(candidate_result.valid and evidence_result.valid)
        validity.append(valid)
        if any("not_allowed" in reason or "invalid" in reason for reason in (*candidate_result.reasons, *evidence_result.reasons)):
            out_of_allowlist += 1
        if any("positive_claim" in reason or "claim" in reason for reason in (*candidate_result.reasons, *evidence_result.reasons)):
            claim_violations += 1
        if valid:
            valid_records.append(record)
        seen.add(record.spec.candidate_id)
    duplicate_rate = 1.0 - (len({record.spec.candidate_id for record in ordered}) / len(ordered)) if ordered else 0.0
    valid_rate = float(np.mean(validity)) if validity else 0.0
    denominator = len(ordered) if ordered else 1
    return valid_records, valid_rate, duplicate_rate, out_of_allowlist / denominator, claim_violations / denominator


def _budget_to_top_epsilon(ordered: list[CandidateExecutionRecord], threshold: float, budgets: list[int]) -> int | None:
    for budget in sorted(int(value) for value in budgets):
        available = ordered[: min(budget, len(ordered))]
        if available and min(record.rolling_error for record in available) <= threshold:
            return int(budget)
    return None


def _select_record(ordered: list[CandidateExecutionRecord], budget: int) -> CandidateExecutionRecord | None:
    available = ordered[: min(int(budget), len(ordered))]
    safe = [record for record in available if not record.evidence.numerical_failure_flag]
    pool = safe or available
    if not pool:
        return None
    return min(pool, key=lambda row: (row.rolling_error, row.spec.model_name))


def _jaccard(model_sets: list[set[str]]) -> float:
    if len(model_sets) < 2:
        return 1.0
    scores = []
    for left, right in combinations(model_sets, 2):
        union = left | right
        scores.append(len(left & right) / len(union) if union else 1.0)
    return float(np.mean(scores)) if scores else 1.0


def _agreement(values: list[str]) -> float:
    if len(values) < 2:
        return 1.0
    total = 0
    agree = 0
    for left, right in combinations(values, 2):
        total += 1
        agree += int(left == right)
    return agree / total if total else 1.0


def _api_model_order(
    *,
    config: dict[str, Any],
    model_summary: pd.DataFrame,
    series_name: str,
    model_allowlist: list[str],
    max_candidates: int,
    repeat_idx: int,
) -> tuple[list[str], str, bool, list[str]]:
    api_config = dict(config.get("api", {}))
    if not bool(api_config.get("enabled", False)):
        return [], "api_disabled", False, []
    client = OpenAICompatibleJSONClient()
    if not client.available(api_config):
        return [], "api_credentials_missing", False, []
    allowlist_config = {
        "families": api_config.get("families", ["forecasting_baseline", "mechanistic_baseline", "structured_search", "ablation"]),
        "model_names": model_allowlist,
        "observation_labels": api_config.get("observation_labels", ["direct", "lagged", "mixture", "not_applicable", "I", "delayed_I"]),
    }
    allowlist = proposal_allowlist_from_config(allowlist_config)
    prompt_payload = _build_prompt_payload(
        model_summary=model_summary,
        series_name=series_name,
        model_allowlist=model_allowlist,
        max_candidates=max_candidates,
        objective="propose a verifier-safe ordering of allowlisted candidates using only rolling or validation evidence",
    )
    system_prompt = build_execution_system_prompt(allowlist)
    text = client.complete_json(
        system_prompt=system_prompt,
        user_prompt=json.dumps(prompt_payload, indent=2, sort_keys=True),
        config=api_config,
    )
    parsed = parse_structured_candidate_response(text, allowlist)
    names: list[str] = []
    for candidate in parsed.candidates:
        if candidate.model_name in model_allowlist and candidate.model_name not in names:
            names.append(candidate.model_name)
    return names[:max_candidates], "completed", True, list(parsed.parse_errors)


def _frozen_replay(
    *,
    config: dict[str, Any],
    repo_root: Path,
    model_summary: pd.DataFrame,
    replay_config: dict[str, Any],
    budgets: list[int],
    model_allowlist: list[str],
    epsilon: float,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    series_list = [normalize_series_name(str(value)) for value in replay_config.get("series", [])]
    repeats = int(replay_config.get("repeats", 1))
    proposers = [str(value) for value in replay_config.get("proposers", REPLAY_PROPOSERS)]
    max_budget = max(budgets)
    by_run_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    api_statuses: list[str] = []
    external_api_used = False

    for series_name in series_list:
        records = realdata_execution_records(model_summary, series_name=series_name, model_allowlist=model_allowlist)
        safe_records = [record for record in records if not record.evidence.numerical_failure_flag]
        best_error = min((record.rolling_error for record in safe_records), default=float("inf"))
        threshold = best_error + epsilon
        for proposer_type in proposers:
            run_count = repeats if proposer_type in {"real_api_proposer", "random_candidate_proposer"} else 1
            for repeat_idx in range(run_count):
                api_names: list[str] | None = None
                api_status = ""
                if proposer_type == "real_api_proposer":
                    api_names, api_status, used_api, parse_errors = _api_model_order(
                        config=config,
                        model_summary=model_summary,
                        series_name=series_name,
                        model_allowlist=model_allowlist,
                        max_candidates=max_budget,
                        repeat_idx=repeat_idx,
                    )
                    del parse_errors
                    api_statuses.append(api_status)
                    external_api_used = external_api_used or used_api
                    if api_status != "completed":
                        continue
                ordered = _order_records(
                    proposer_type,
                    records,
                    series_name=series_name,
                    seed=seed,
                    repeat_idx=repeat_idx,
                    api_model_names=api_names,
                )
                prompt_payload = _build_prompt_payload(
                    model_summary=model_summary,
                    series_name=series_name,
                    model_allowlist=model_allowlist,
                    max_candidates=max_budget,
                    objective="rank allowlisted candidates for frozen replay using non-test evidence",
                )
                audit_rows.append(
                    _prompt_audit_row(
                        layer="frozen_replay_repeated",
                        series_name=series_name,
                        proposer_type=proposer_type,
                        repeat_idx=repeat_idx,
                        prompt_payload=prompt_payload,
                        model_allowlist=model_allowlist,
                    )
                )
                valid_ordered, valid_rate, duplicate_rate, out_rate, claim_rate = _verify_order(
                    ordered,
                    max_candidates=max_budget,
                )
                budget_to_top = _budget_to_top_epsilon(valid_ordered, threshold, budgets)
                for budget in budgets:
                    selected = _select_record(valid_ordered, budget)
                    available = valid_ordered[: min(int(budget), len(valid_ordered))]
                    by_run_rows.append(
                        {
                            "layer": "frozen_replay_repeated",
                            "series_name": series_name,
                            "proposer_type": proposer_type,
                            "repeat_idx": int(repeat_idx),
                            "budget": int(budget),
                            "selected_model_at_k": selected.spec.model_name if selected else "",
                            "rolling_score_at_k": selected.rolling_error if selected else np.nan,
                            "post_selection_test_mae": selected.posthoc_test_mae if selected else np.nan,
                            "top_epsilon_hit": bool(selected and selected.rolling_error <= threshold),
                            "budget_to_top_epsilon": budget_to_top,
                            "valid_proposal_rate": valid_rate,
                            "duplicate_rate": duplicate_rate,
                            "out_of_allowlist_rejection_rate": out_rate,
                            "claim_safety_violation_rate": claim_rate,
                            "family_diversity": len({record.spec.normalized_family().value for record in available}),
                            "observation_label_diversity": len({record.observation_label for record in available}),
                            "api_status": api_status,
                            "evidence_mode": "frozen_replay",
                            "selection_metric_source": "rolling_mean_mae",
                            "test_metric_usage": "posthoc_descriptive_only",
                        }
                    )

    by_run = pd.DataFrame.from_records(by_run_rows)
    audit = pd.DataFrame.from_records(audit_rows)
    summary = _replay_summary(by_run)
    status = {
        "external_api_used": bool(external_api_used),
        "api_statuses": sorted(set(api_statuses)),
        "api_repeats_requested": repeats,
        "api_repeats_completed": int(sum(status == "completed" for status in api_statuses)),
    }
    return summary, by_run, audit, status


def _replay_summary(by_run: pd.DataFrame) -> pd.DataFrame:
    if by_run.empty:
        return pd.DataFrame(
            columns=[
                "proposer_type",
                "series_name",
                "valid_proposal_rate",
                "duplicate_rate",
                "out_of_allowlist_rejection_rate",
                "claim_safety_violation_rate",
                "family_diversity",
                "observation_label_diversity",
                "top_epsilon_hit_rate",
                "budget_to_top_epsilon",
                "between_run_jaccard_overlap",
                "selected_model_agreement_rate",
            ]
        )
    rows: list[dict[str, Any]] = []
    for (series_name, proposer_type), subset in by_run.groupby(["series_name", "proposer_type"], sort=False):
        sets = [
            set(group["selected_model_at_k"].dropna().astype(str))
            for _, group in subset.groupby("repeat_idx", sort=False)
        ]
        selected_at_max = subset.loc[subset["budget"] == subset["budget"].max(), "selected_model_at_k"].dropna().astype(str).tolist()
        rows.append(
            {
                "series_name": series_name,
                "proposer_type": proposer_type,
                "valid_proposal_rate": float(subset["valid_proposal_rate"].mean()),
                "duplicate_rate": float(subset["duplicate_rate"].mean()),
                "out_of_allowlist_rejection_rate": float(subset["out_of_allowlist_rejection_rate"].mean()),
                "claim_safety_violation_rate": float(subset["claim_safety_violation_rate"].mean()),
                "family_diversity": float(subset["family_diversity"].mean()),
                "observation_label_diversity": float(subset["observation_label_diversity"].mean()),
                "top_epsilon_hit_rate": float(subset["top_epsilon_hit"].mean()),
                "budget_to_top_epsilon": float(subset["budget_to_top_epsilon"].dropna().mean()) if subset["budget_to_top_epsilon"].notna().any() else np.nan,
                "between_run_jaccard_overlap": _jaccard(sets),
                "selected_model_agreement_rate": _agreement(selected_at_max),
            }
        )
    return pd.DataFrame.from_records(rows)


def _series_frames(config: dict[str, Any], repo_root: Path) -> dict[str, pd.DataFrame]:
    data_config = config["data"]
    raw_csv = resolve_data_path(repo_root, data_config["raw_csv"])
    frame = load_flu_surv_data(raw_csv)
    items = build_flu_series_frames(
        frame=frame,
        include_age_groups=bool(data_config.get("include_age_robustness", True)),
        age_groups=data_config.get("age_groups", []),
        seasons=data_config.get("seasons", []),
        season_mode=str(data_config.get("season_mode", SEASON_MODE_POOLED)),
    )
    result: dict[str, pd.DataFrame] = {}
    for item in items:
        series_name = normalize_series_name(str(item["series_name"]))
        result[series_name] = item["frame"]  # type: ignore[assignment]
    return result


def _execute_models(
    *,
    config: dict[str, Any],
    repo_root: Path,
    series_names: list[str],
    model_names_by_series: dict[str, list[str]],
    temp_root: Path,
) -> tuple[pd.DataFrame, int]:
    _disable_plot_writes()
    fit_config = _fit_config(config)
    search_config = _search_config(config)
    horizons = [int(value) for value in config["evaluation"]["horizons"]]
    frames = _series_frames(config, repo_root)
    rows: list[dict[str, Any]] = []
    unique_executions = 0
    for series_index, requested_name in enumerate(series_names):
        series_name = normalize_series_name(requested_name)
        if series_name not in frames:
            raise ValueError(f"Series not found for bounded execution: {requested_name}")
        y = frames[series_name]["WEEKLY RATE"].to_numpy(dtype=float)
        split = make_chronological_split(len(y))
        for position, model_name in enumerate(model_names_by_series.get(series_name, [])):
            unique_executions += 1
            artifact_dir = temp_root / _slugify(series_name) / model_name
            start = time.perf_counter()
            try:
                result = _run_one_model(
                    model_name=model_name,
                    series_name=series_name,
                    y=y,
                    split=split,
                    fit_config=fit_config,
                    search_config=search_config,
                    horizons=horizons,
                    artifact_dir=artifact_dir,
                    seed=_model_seed(int(config["seed"]) + series_index * 1009, model_name, position),
                    ensemble_members=None,
                )
                summary = result["summary"]
                rows.append(_summary_to_execution_row(series_name, model_name, summary, time.perf_counter() - start))
            except Exception as exc:  # noqa: BLE001 - bounded evaluation records failures compactly.
                rows.append(
                    {
                        "series_name": series_name,
                        "model_name": model_name,
                        "validation_mae": np.nan,
                        "rolling_mean_mae": float("inf"),
                        "posthoc_test_mae": np.nan,
                        "num_free_params": np.nan,
                        "numerical_failure_flag": True,
                        "candidate_failed": True,
                        "failure_reason": exc.__class__.__name__,
                        "runtime_seconds": time.perf_counter() - start,
                    }
                )
    return pd.DataFrame.from_records(rows), unique_executions


def _summary_to_execution_row(series_name: str, model_name: str, summary: dict[str, Any], runtime_seconds: float) -> dict[str, Any]:
    diagnostics = summary.get("numerical_diagnostics", {}) or {}
    return {
        "series_name": series_name,
        "model_name": model_name,
        "validation_mae": float(summary.get("validation_metrics", {}).get("mae", np.nan)),
        "rolling_mean_mae": float(summary.get("rolling_origin_summary", {}).get("mean_mae", np.nan)),
        "posthoc_test_mae": float(summary.get("test_metrics", {}).get("mae", np.nan)),
        "num_free_params": float(summary.get("complexity", {}).get("num_free_params", np.nan)),
        "numerical_failure_flag": bool(diagnostics.get("numerical_failure_flag", False)),
        "candidate_failed": False,
        "failure_reason": "",
        "runtime_seconds": float(runtime_seconds),
    }


def _execution_records_from_metrics(metrics: pd.DataFrame, series_name: str) -> list[CandidateExecutionRecord]:
    records: list[CandidateExecutionRecord] = []
    subset = metrics.loc[metrics["series_name"].astype(str) == normalize_series_name(series_name)]
    for _, row in subset.iterrows():
        model_name = str(row["model_name"])
        spec = _candidate_spec_for_model(normalize_series_name(series_name), model_name, "bounded_execution", len(records))
        rolling = float(row["rolling_mean_mae"]) if pd.notna(row["rolling_mean_mae"]) else float("inf")
        evidence = EvidencePacket(
            candidate_id=spec.candidate_id,
            model_name=model_name,
            family=spec.family,
            series_name=normalize_series_name(series_name),
            selection_metrics={"rolling_mean_mae": rolling},
            posthoc_metrics={"post_selection_test_mae": float(row["posthoc_test_mae"]) if pd.notna(row["posthoc_test_mae"]) else None},
            rolling_mean_mae=rolling,
            num_free_params=float(row["num_free_params"]) if pd.notna(row["num_free_params"]) else None,
            numerical_failure_flag=bool(row["numerical_failure_flag"]),
            supports_positive_claim=False,
            metadata={"evidence_mode": "bounded_real_execution"},
        )
        records.append(
            CandidateExecutionRecord(
                spec=spec,
                evidence=evidence,
                observation_label="not_applicable",
                delay_label="",
                candidate_family_label=spec.normalized_family().value,
                rolling_error=rolling,
                posthoc_test_mae=evidence.posthoc_metrics["post_selection_test_mae"],
            )
        )
    return records


def _bounded_execution(
    *,
    config: dict[str, Any],
    repo_root: Path,
    model_summary: pd.DataFrame,
    execution_config: dict[str, Any],
    budgets: list[int],
    model_allowlist: list[str],
    epsilon: float,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    if not bool(execution_config.get("enabled", True)):
        empty = pd.DataFrame()
        return empty, empty, empty, empty, {"unique_model_executions": 0, "temp_artifacts_removed": False}
    series_list = [normalize_series_name(str(value)) for value in execution_config.get("series", [])]
    proposers = [str(value) for value in execution_config.get("proposers", EXECUTION_PROPOSERS)]
    max_budget = max(budgets)
    model_names_by_series = {series_name: list(model_allowlist) for series_name in series_list}
    temp_root = _repo_path(repo_root, execution_config.get("temp_root", ".codex_real_candidate_execution_tmp/run"))
    if temp_root.exists():
        _safe_remove_temp(temp_root, repo_root)
    ensure_dir(temp_root)
    metrics, unique_executions = _execute_models(
        config=config,
        repo_root=repo_root,
        series_names=series_list,
        model_names_by_series=model_names_by_series,
        temp_root=temp_root,
    )

    rows: list[dict[str, Any]] = []
    selected_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    for series_name in series_list:
        records = _execution_records_from_metrics(metrics, series_name)
        safe_records = [record for record in records if not record.evidence.numerical_failure_flag]
        best_error = min((record.rolling_error for record in safe_records), default=float("inf"))
        threshold = best_error + epsilon
        for proposer_type in proposers:
            ordered = _order_records(
                proposer_type,
                records,
                series_name=series_name,
                seed=seed,
                repeat_idx=0,
                api_model_names=None,
            )
            prompt_payload = _build_prompt_payload(
                model_summary=model_summary,
                series_name=series_name,
                model_allowlist=model_allowlist,
                max_candidates=max_budget,
                objective="rank allowlisted candidates for bounded execution using non-test evidence",
            )
            audit_rows.append(
                _prompt_audit_row(
                    layer="bounded_real_execution",
                    series_name=series_name,
                    proposer_type=proposer_type,
                    repeat_idx=0,
                    prompt_payload=prompt_payload,
                    model_allowlist=model_allowlist,
                )
            )
            valid_ordered, valid_rate, duplicate_rate, out_rate, claim_rate = _verify_order(
                ordered,
                max_candidates=max_budget,
            )
            budget_to_top = _budget_to_top_epsilon(valid_ordered, threshold, budgets)
            for budget in budgets:
                selected = _select_record(valid_ordered, budget)
                available = valid_ordered[: min(int(budget), len(valid_ordered))]
                selected_metrics = metrics.loc[
                    (metrics["series_name"].astype(str) == series_name)
                    & (metrics["model_name"].astype(str) == (selected.spec.model_name if selected else ""))
                ]
                runtime = float(selected_metrics["runtime_seconds"].iloc[0]) if not selected_metrics.empty else np.nan
                candidate_failed = bool(selected_metrics["candidate_failed"].iloc[0]) if not selected_metrics.empty else False
                row = {
                    "series_name": series_name,
                    "proposer_type": proposer_type,
                    "budget": int(budget),
                    "selected_model_at_k": selected.spec.model_name if selected else "",
                    "validation_or_rolling_score_at_k": selected.rolling_error if selected else np.nan,
                    "post_selection_test_mae": selected.posthoc_test_mae if selected else np.nan,
                    "post_selection_rolling_mae": selected.rolling_error if selected else np.nan,
                    "budget_to_top_epsilon": budget_to_top,
                    "top_epsilon_hit": bool(selected and selected.rolling_error <= threshold),
                    "numerical_failure_flag": bool(selected.evidence.numerical_failure_flag) if selected else False,
                    "runtime_seconds": runtime,
                    "candidate_failure_rate": float(metrics.loc[metrics["series_name"].astype(str) == series_name, "candidate_failed"].mean()),
                    "selected_candidate_failed": candidate_failed,
                    "valid_proposal_rate": valid_rate,
                    "duplicate_rate": duplicate_rate,
                    "out_of_allowlist_rejection_rate": out_rate,
                    "claim_safety_violation_rate": claim_rate,
                    "invalid_or_rejected_proposals": int(len(ordered) - len(valid_ordered)),
                    "candidate_diversity": len({record.spec.normalized_family().value for record in available}),
                    "selection_metric_source": "rolling_mean_mae",
                    "test_metric_usage": "posthoc_descriptive_only",
                    "evidence_mode": "bounded_real_execution",
                }
                rows.append(row)
                selected_rows.append(
                    {
                        "series_name": series_name,
                        "proposer_type": proposer_type,
                        "budget": int(budget),
                        "selected_model_at_k": row["selected_model_at_k"],
                        "selection_metric_source": row["selection_metric_source"],
                        "validation_or_rolling_score_at_k": row["validation_or_rolling_score_at_k"],
                        "post_selection_test_mae": row["post_selection_test_mae"],
                        "test_metric_usage": row["test_metric_usage"],
                    }
                )

    keep_temp = bool(execution_config.get("keep_temp_artifacts", False))
    temp_removed = False
    if not keep_temp:
        temp_removed = _safe_remove_temp(temp_root, repo_root)
    by_budget = pd.DataFrame.from_records(rows)
    selected = pd.DataFrame.from_records(selected_rows)
    audit = pd.DataFrame.from_records(audit_rows)
    summary = _bounded_summary(by_budget)
    status = {
        "unique_model_executions": int(unique_executions),
        "temp_artifact_root": repo_relative_path(temp_root, repo_root),
        "temp_artifacts_removed": bool(temp_removed),
    }
    return summary, by_budget, selected, audit, status


def _bounded_summary(by_budget: pd.DataFrame) -> pd.DataFrame:
    if by_budget.empty:
        return pd.DataFrame()
    return by_budget.groupby("proposer_type", as_index=False).agg(
        top_epsilon_hit_rate=("top_epsilon_hit", "mean"),
        mean_rolling_score=("validation_or_rolling_score_at_k", "mean"),
        mean_post_selection_test_mae=("post_selection_test_mae", "mean"),
        mean_budget_to_top_epsilon=("budget_to_top_epsilon", "mean"),
        candidate_failure_rate=("candidate_failure_rate", "mean"),
        valid_proposal_rate=("valid_proposal_rate", "mean"),
        duplicate_rate=("duplicate_rate", "mean"),
        out_of_allowlist_rejection_rate=("out_of_allowlist_rejection_rate", "mean"),
        claim_safety_violation_rate=("claim_safety_violation_rate", "mean"),
    )


def run_real_candidate_execution(config: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    start = time.perf_counter()
    artifact_root = ensure_dir(_repo_path(repo_root, config["artifacts"]["root_dir"]))
    budgets = [int(value) for value in config.get("budgets", [3, 5, 10])]
    epsilon = float(config.get("policy", {}).get("epsilon", 0.01))
    seed = int(config.get("seed", 42))
    replay_allowlist = [str(value) for value in config.get("replay_candidate_allowlist", DEFAULT_EXECUTION_ALLOWLIST)]
    execution_allowlist = [str(value) for value in config.get("execution_candidate_allowlist", REAL_EXECUTION_ALLOWLIST)]
    _validate_execution_allowlist(execution_allowlist)
    frozen_root = _repo_path(repo_root, config["data"]["frozen_artifact_root"])
    model_summary = pd.read_csv(frozen_root / "benchmark_model_summary.csv")

    replay_summary, replay_by_run, replay_audit, replay_status = _frozen_replay(
        config=config,
        repo_root=repo_root,
        model_summary=model_summary,
        replay_config=config.get("repeated_replay", {}),
        budgets=budgets,
        model_allowlist=replay_allowlist,
        epsilon=epsilon,
        seed=seed,
    )
    bounded_summary, bounded_by_budget, selected, bounded_audit, bounded_status = _bounded_execution(
        config=config,
        repo_root=repo_root,
        model_summary=model_summary,
        execution_config=config.get("actual_execution", {}),
        budgets=budgets,
        model_allowlist=execution_allowlist,
        epsilon=epsilon,
        seed=seed,
    )
    audit = pd.concat([replay_audit, bounded_audit], ignore_index=True, sort=False)
    safe_audit = bool(audit["safe_prompt_passed"].all() and audit["safe_selection_passed"].all()) if not audit.empty else True

    _write_csv(replay_summary, artifact_root / "real_api_replay_repeated_summary.csv")
    _write_csv(replay_by_run, artifact_root / "real_api_replay_repeated_by_run.csv")
    _write_csv(bounded_summary, artifact_root / "bounded_real_execution_summary.csv")
    _write_csv(bounded_by_budget, artifact_root / "bounded_real_execution_by_series_budget.csv")
    _write_csv(selected, artifact_root / "selected_models_by_proposer_budget.csv")
    _write_csv(audit, artifact_root / "no_leakage_audit.csv")

    status = {
        "artifact_root": repo_relative_path(artifact_root, repo_root),
        "frozen_artifact_root": repo_relative_path(frozen_root, repo_root),
        "budgets": budgets,
        "replay_rows": int(len(replay_by_run)),
        "bounded_execution_rows": int(len(bounded_by_budget)),
        "selected_rows": int(len(selected)),
        "audit_rows": int(len(audit)),
        "safe_audit_passed": bool(safe_audit),
        "external_api_used": bool(replay_status.get("external_api_used", False)),
        "api_statuses": replay_status.get("api_statuses", []),
        "unique_model_executions": int(bounded_status.get("unique_model_executions", 0)),
        "temp_artifacts_removed": bool(bounded_status.get("temp_artifacts_removed", False)),
        "runtime_seconds": time.perf_counter() - start,
        "test_metric_usage": "posthoc_descriptive_only",
        "selection_metric_source": "rolling_mean_mae",
    }
    _write_json_lf(status, artifact_root / "run_summary.json")
    return status


def build_real_candidate_execution_figures(artifact_root: Path, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    bounded = pd.read_csv(artifact_root / "bounded_real_execution_by_series_budget.csv")
    replay = pd.read_csv(artifact_root / "real_api_replay_repeated_by_run.csv")

    if not bounded.empty:
        fig, ax = plt.subplots(figsize=(8, 4.8))
        grouped = bounded.groupby(["proposer_type", "budget"], as_index=False)["top_epsilon_hit"].mean()
        for proposer, subset in grouped.groupby("proposer_type", sort=False):
            ax.plot(subset["budget"], subset["top_epsilon_hit"], marker="o", label=proposer)
        ax.set_title("Bounded real-data execution by candidate budget")
        ax.set_xlabel("Candidate budget")
        ax.set_ylabel("Top-epsilon hit rate")
        ax.set_ylim(-0.02, 1.02)
        ax.grid(axis="y", alpha=0.25)
        ax.legend(fontsize=8, loc="lower right")
        fig.tight_layout()
        for suffix in ("pdf", "png"):
            path = output_dir / f"fig_bounded_real_execution_budget.{suffix}"
            fig.savefig(path, dpi=180)
            outputs.append(path)
        plt.close(fig)

    if not replay.empty:
        fig, ax = plt.subplots(figsize=(8, 4.8))
        summary = replay.groupby("proposer_type", as_index=False).agg(
            top_epsilon_hit=("top_epsilon_hit", "mean"),
            valid_proposal_rate=("valid_proposal_rate", "mean"),
        )
        x = np.arange(len(summary))
        width = 0.35
        ax.bar(x - width / 2, summary["top_epsilon_hit"], width=width, label="top-epsilon")
        ax.bar(x + width / 2, summary["valid_proposal_rate"], width=width, label="valid")
        ax.set_xticks(x)
        ax.set_xticklabels(summary["proposer_type"], rotation=25, ha="right")
        ax.set_title("Frozen replay proposal stability and validity")
        ax.set_ylim(-0.02, 1.02)
        ax.grid(axis="y", alpha=0.25)
        ax.legend(fontsize=8)
        fig.tight_layout()
        for suffix in ("pdf", "png"):
            path = output_dir / f"fig_real_api_replay_stability.{suffix}"
            fig.savefig(path, dpi=180)
            outputs.append(path)
        plt.close(fig)
    return outputs
