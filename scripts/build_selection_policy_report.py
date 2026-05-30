from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _artifact_path(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def _read_csv(root: Path, name: str) -> pd.DataFrame:
    path = root / name
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def _markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 20) -> str:
    if frame.empty:
        return "_None._"
    shown = frame.loc[:, [column for column in columns if column in frame.columns]].head(max_rows)
    lines = [
        "| " + " | ".join(shown.columns.astype(str)) + " |",
        "| " + " | ".join(["---"] * len(shown.columns)) + " |",
    ]
    for _, row in shown.iterrows():
        values = []
        for value in row.tolist():
            if isinstance(value, float):
                values.append(f"{value:.4f}")
            else:
                values.append("" if pd.isna(value) else str(value))
        lines.append("| " + " | ".join(values) + " |")
    if len(frame) > max_rows:
        lines.append(f"\n_Showing {max_rows} of {len(frame)} rows._")
    return "\n".join(lines)


def build_report(artifact_root: Path, report_path: Path) -> None:
    run_summary = json.loads((artifact_root / "run_summary.json").read_text(encoding="utf-8"))
    recommendations = _read_csv(artifact_root, "policy_recommendations.csv")
    audit = _read_csv(artifact_root, "claim_audit_scores.csv")
    toy = _read_csv(artifact_root, "toy_observation_recovery_summary.csv")
    verified = _read_csv(artifact_root, "verified_candidates.csv")
    negative = _read_csv(artifact_root, "verifier_negative_set.csv") if (artifact_root / "verifier_negative_set.csv").exists() else pd.DataFrame()
    replay = _read_csv(artifact_root, "budgeted_replay_efficiency.csv") if (artifact_root / "budgeted_replay_efficiency.csv").exists() else pd.DataFrame()

    selected = recommendations.loc[
        :,
        ["series_name", "policy_name", "selected_model_name", "rationale"],
    ].sort_values(["series_name", "policy_name"])
    audit_core = audit.loc[audit["audit_label"].isin(
        [
            "no_single_global_winner",
            "age_or_group_specific_signal",
            "simple_baseline_competitive",
            "flagged_rows_descriptive_only",
            "posthoc_comparison_not_selection",
            "multiseason_mixed_if_present",
            "rejected_claim",
            "caveat",
        ]
    )]

    if {"observation_label_recovery_rate", "delay_label_recovery_rate", "mean_rolling_error"}.issubset(toy.columns):
        toy_summary = (
            toy.groupby("policy_name", as_index=False)
            .agg(
                observation_label_recovery_rate=("observation_label_recovery_rate", "first"),
                delay_label_recovery_rate=("delay_label_recovery_rate", "first"),
                mean_rolling_error=("mean_rolling_error", "first"),
            )
            .sort_values("policy_name")
        )
        toy_text = _markdown_table(
            toy_summary,
            ["policy_name", "observation_label_recovery_rate", "delay_label_recovery_rate", "mean_rolling_error"],
            max_rows=10,
        )
    else:
        toy_text = _markdown_table(
            toy,
            ["scenario_name", "seed", "true_observation_label", "selected_observation_label", "recovered"],
        )

    lines = [
        "# Offline Selection Policy Evaluation",
        "",
        "This is a deterministic offline policy evaluation over compact time-series forecasting benchmark summaries.",
        "It does not call external LLM/API services, does not run new model experiments, and does not provide",
        "intervention guidance or operational recommendations.",
        "",
        "## Scope",
        "",
        f"- Frozen artifact root: `{run_summary['frozen_artifact_root']}`.",
        f"- Multi-season artifact root: `{run_summary['multiseason_artifact_root']}`.",
        f"- Candidate records: {run_summary['candidate_count']}.",
        f"- Verified candidates: {run_summary['verified_candidate_count']}.",
        f"- Series audited: {run_summary['series_count']}.",
        "- Main policy: `pareto_epsilon`.",
        "- Ablation policy: deterministic weighted scoring.",
        "- Hard-veto policy: decision-tree safety and simplicity rules.",
        "",
        "## Claim-Boundary Audit",
        "",
        "The audit labels support cautious statements such as no single global winner, group-specific signals,",
        "simple baselines remaining competitive, and flagged rows being descriptive only. It rejects global",
        "structured-search superiority, forecasting state-of-the-art claims, and using flagged rows as positive evidence.",
        "",
        _markdown_table(audit_core, ["audit_label", "value"], max_rows=30),
        "",
        "## Policy Recommendations",
        "",
        _markdown_table(selected, ["series_name", "policy_name", "selected_model_name", "rationale"], max_rows=24),
        "",
        "## Stage 2: Verifier Negative-Set Rejection",
        "",
        "Stage 2 adds a negative set of invalid or misleading candidate/evidence records. The verifier should",
        "reject malformed records, duplicate identifiers, absolute artifact paths, posthoc test metrics used as",
        "selection evidence, flagged rows used for positive claims, and invalid observation or delay labels.",
        "",
        _markdown_table(
            negative,
            ["case_id", "case_type", "rejected", "rejection_reasons", "rejection_rate"],
            max_rows=20,
        ) if not negative.empty else "_Stage 2 negative-set output not found._",
        "",
        "## Stage 2: Budgeted Candidate Replay",
        "",
        "The budgeted replay uses frozen compact rows only. Test MAE is retained only as a posthoc descriptive",
        "column and is not used for selection. Candidate availability is simulated at fixed budgets per series.",
        "",
        _markdown_table(
            replay.loc[replay["k"].isin([3, 10])] if not replay.empty else replay,
            [
                "series_name",
                "k",
                "policy_name",
                "selected_model_at_k",
                "rolling_mean_mae_at_k",
                "candidate_count_to_top_epsilon",
                "policy_disagreement_rate",
            ],
            max_rows=24,
        ) if not replay.empty else "_Stage 2 budgeted replay output not found._",
        "",
        "## Stage 2: Generic Toy Observation-Label Recovery",
        "",
        "The toy task is generic numerical time-series logic only. It checks whether direct versus lagged",
        "or mixture observation labels can be recovered from simple synthetic signals; it is not a domain mechanism simulation.",
        "",
        f"Stage 1 toy recovery rate: {run_summary.get('toy_recovery_rate')}.",
        "",
        toy_text,
        "",
        "## Verifier Summary",
        "",
        _markdown_table(
            verified.groupby(["valid", "vetoed"]).size().reset_index(name="count"),
            ["valid", "vetoed", "count"],
        ),
        "",
        "## Caveats",
        "",
        "- Compact CSVs do not always include validation-only metrics; when absent, policies use rolling-origin MAE and record that limitation.",
        "- Policy outputs are model-selection interpretations over existing artifacts, not new forecasting results.",
        "- The toy task is only a deterministic software check for observation-label logic.",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build offline selection-policy evaluation report.")
    parser.add_argument("--artifact-root", default="artifacts_selection_policy_eval_compact")
    parser.add_argument("--report-path", default="reports/selection_policy_evaluation.md")
    args = parser.parse_args()
    artifact_root = _artifact_path(args.artifact_root)
    report_path = _artifact_path(args.report_path)
    build_report(artifact_root, report_path)
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
