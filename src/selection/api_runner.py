from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.selection.api_proposer import OpenAICompatibleJSONClient, StructuredAPIProposer
from src.selection.proposal_prompts import default_proposal_allowlist
from src.selection.schema import BudgetState, CandidateSpec
from src.selection.verifier import verify_candidate
from src.utils.io import ensure_dir
from src.utils.paths import repo_relative_path


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")


def _write_json_lf(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(data, indent=2, sort_keys=True) + "\n")


def _empty_candidate_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "candidate_id",
            "family",
            "model_name",
            "observation_label",
            "delay_label",
            "round_idx",
            "proposer_name",
            "rationale",
            "expected_failure_mode",
            "valid",
            "vetoed",
            "reasons",
            "schema_valid",
            "family_valid",
            "leakage_safe",
            "budget_safe",
            "artifact_safe",
            "claim_safe",
            "duplicate",
            "top_epsilon_any_series",
        ]
    )


def _candidate_usefulness(summary: pd.DataFrame, epsilon: float) -> dict[str, bool]:
    usefulness: dict[str, bool] = {}
    if summary.empty:
        return usefulness
    for _, subset in summary.groupby("series_name", sort=False):
        if "numerical_failure_flag" in subset.columns:
            flag = subset["numerical_failure_flag"].astype(str).str.lower().isin({"true", "1", "yes"})
            safe = subset.loc[~flag]
        else:
            safe = subset
        if safe.empty:
            continue
        threshold = float(safe["rolling_mean_mae"].min()) + float(epsilon)
        for row in safe.itertuples(index=False):
            model_name = str(row.model_name)
            useful = float(row.rolling_mean_mae) <= threshold
            usefulness[model_name] = usefulness.get(model_name, False) or useful
    return usefulness


def evaluate_api_candidates(
    candidates: list[CandidateSpec],
    *,
    model_summary: pd.DataFrame,
    max_candidates: int,
    epsilon: float,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    usefulness = _candidate_usefulness(model_summary, epsilon)
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    budget = BudgetState(max_candidates=max_candidates)
    for candidate in candidates:
        result = verify_candidate(candidate, budget=budget, seen_candidate_ids=seen)
        row = {**candidate.to_dict(), **result.to_dict()}
        row["reasons"] = ";".join(result.reasons)
        row["top_epsilon_any_series"] = bool(usefulness.get(candidate.model_name, False))
        rows.append(row)
        if candidate.candidate_id not in seen:
            seen.add(candidate.candidate_id)
        budget = BudgetState(max_candidates=max_candidates, evaluated_candidates=budget.evaluated_candidates + 1)
    frame = pd.DataFrame.from_records(rows) if rows else _empty_candidate_frame()
    total = int(len(frame))
    valid = int(frame["valid"].astype(bool).sum()) if total else 0
    duplicate = int(frame["duplicate"].astype(bool).sum()) if total else 0
    valid_frame = frame.loc[frame["valid"].astype(bool)].copy() if total else frame
    summary = {
        "proposal_count": total,
        "valid_proposal_count": valid,
        "valid_proposal_rate": valid / total if total else 0.0,
        "duplicate_count": duplicate,
        "duplicate_rate": duplicate / total if total else 0.0,
        "family_diversity": int(valid_frame["family"].nunique()) if not valid_frame.empty else 0,
        "observation_label_diversity": int(valid_frame["observation_label"].dropna().nunique()) if not valid_frame.empty else 0,
        "top_epsilon_useful_count": int(valid_frame["top_epsilon_any_series"].astype(bool).sum()) if not valid_frame.empty else 0,
        "top_epsilon_useful_rate": float(valid_frame["top_epsilon_any_series"].astype(bool).mean()) if not valid_frame.empty else 0.0,
    }
    return frame, summary


def run_api_proposal_evaluation(
    config: dict[str, Any],
    repo_root: Path,
    *,
    proposer: StructuredAPIProposer | None = None,
) -> dict[str, Any]:
    artifact_root = ensure_dir(repo_root / config["artifacts"]["root_dir"])
    frozen_root = repo_root / config["data"]["frozen_artifact_root"]
    api_config = dict(config.get("api", {}))
    policy_config = config.get("policy", {})
    max_candidates = int(api_config.get("max_candidates", policy_config.get("max_candidates", 12)))
    epsilon = float(policy_config.get("epsilon", 0.02))
    model_summary = pd.read_csv(frozen_root / "benchmark_model_summary.csv")
    status_path = artifact_root / "api_proposal_status.json"
    candidates_path = artifact_root / "api_proposal_candidates.csv"
    metrics_path = artifact_root / "api_proposal_evaluation.csv"

    enabled = bool(api_config.get("enabled", False))
    if proposer is None:
        client = OpenAICompatibleJSONClient()
        if not enabled or not client.available(api_config):
            reason = "api_disabled" if not enabled else "api_credentials_missing"
            _write_csv(_empty_candidate_frame(), candidates_path)
            metrics = {
                "api_run_status": "skipped",
                "skip_reason": reason,
                "proposal_count": 0,
                "valid_proposal_count": 0,
                "valid_proposal_rate": 0.0,
                "duplicate_rate": 0.0,
                "family_diversity": 0,
                "observation_label_diversity": 0,
                "top_epsilon_useful_rate": 0.0,
            }
            _write_csv(pd.DataFrame.from_records([metrics]), metrics_path)
            status = {
                "api_run_status": "skipped",
                "skip_reason": reason,
                "artifact_root": repo_relative_path(artifact_root, repo_root),
                "external_api_used": False,
            }
            _write_json_lf(status, status_path)
            return status
        proposer = StructuredAPIProposer(client=client, allowlist=default_proposal_allowlist())

    try:
        parse_result = proposer.propose(
            model_summary=model_summary,
            max_candidates=max_candidates,
            objective=str(api_config.get("objective", "propose diverse allowed candidate records for offline audit")),
            api_config=api_config,
        )
        candidate_frame, metrics = evaluate_api_candidates(
            list(parse_result.candidates),
            model_summary=model_summary,
            max_candidates=max_candidates,
            epsilon=epsilon,
        )
        metrics.update(
            {
                "api_run_status": "completed",
                "skip_reason": "",
                "parse_error_count": int(len(parse_result.parse_errors)),
                "parse_errors": ";".join(parse_result.parse_errors),
                "raw_candidate_count": int(parse_result.raw_candidate_count),
            }
        )
        status = {
            "api_run_status": "completed",
            "artifact_root": repo_relative_path(artifact_root, repo_root),
            "external_api_used": proposer.client.__class__.__name__ != "MockStructuredAPIClient",
            "parse_errors": list(parse_result.parse_errors),
            **metrics,
        }
    except Exception as exc:  # noqa: BLE001 - API failures should become compact status, not crash notebooks/reports.
        candidate_frame = _empty_candidate_frame()
        metrics = {
            "api_run_status": "failed",
            "skip_reason": exc.__class__.__name__,
            "proposal_count": 0,
            "valid_proposal_count": 0,
            "valid_proposal_rate": 0.0,
            "duplicate_rate": 0.0,
            "family_diversity": 0,
            "observation_label_diversity": 0,
            "top_epsilon_useful_rate": 0.0,
        }
        status = {
            "api_run_status": "failed",
            "error": str(exc),
            "artifact_root": repo_relative_path(artifact_root, repo_root),
            "external_api_used": False,
        }

    _write_csv(candidate_frame, candidates_path)
    _write_csv(pd.DataFrame.from_records([metrics]), metrics_path)
    _write_json_lf(status, status_path)
    return status
