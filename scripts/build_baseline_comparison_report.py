from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.evaluation.reporting import write_benchmark_reports  # noqa: E402
from src.evaluation.statistical_tests import paired_rolling_error_comparison  # noqa: E402
from src.utils.paths import repo_relative_path  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Build baseline/discovery ablation comparison report.")
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--reference", default="constrained_structure_discovery")
    parser.add_argument("--n-bootstrap", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--report-path", default="reports/baseline_ablation_report.md")
    args = parser.parse_args()

    artifact_root = _repo_path(args.artifact_root)
    if not (artifact_root / "benchmark_model_summary.csv").exists():
        write_benchmark_reports(artifact_root)

    paired = paired_rolling_error_comparison(
        artifact_root=artifact_root,
        reference_model=str(args.reference),
        n_bootstrap=int(args.n_bootstrap),
        seed=int(args.seed),
    )
    paired_path = artifact_root / "paired_rolling_error_comparison.csv"
    paired.to_csv(paired_path, index=False)
    skipped_path = artifact_root / "paired_rolling_error_skipped_models.json"
    skipped_path.write_text(json.dumps(paired.attrs.get("skipped_models", []), indent=2, sort_keys=True), encoding="utf-8")

    summary = pd.read_csv(artifact_root / "benchmark_model_summary.csv")
    report_path = _repo_path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        _build_report(
            artifact_root=artifact_root,
            paired_path=paired_path,
            summary=summary,
            paired=paired,
            reference_model=str(args.reference),
        ),
        encoding="utf-8",
    )


def _repo_path(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def _build_report(
    *,
    artifact_root: Path,
    paired_path: Path,
    summary: pd.DataFrame,
    paired: pd.DataFrame,
    reference_model: str,
) -> str:
    overall = summary.loc[summary["series_name"] == "Overall"].copy()
    ranked = overall if not overall.empty else summary.copy()
    ranked = ranked.sort_values(["test_mae", "rolling_mean_mae", "model_name"]).head(20)
    if "model_family" in summary.columns:
        discovery_rows = summary.loc[summary["model_family"].fillna("").str.contains("structure_discovery", regex=False)].copy()
    else:
        discovery_rows = summary.loc[summary["model_name"].fillna("").str.contains("discovery", regex=False)].copy()
    paired_view = paired.sort_values(["series_name", "mean_diff_challenger_minus_reference"], ascending=[True, False]).head(30)
    lines = [
        "# Baseline and Discovery Ablation Report",
        "",
        f"Artifact root: `{repo_relative_path(artifact_root, REPO_ROOT)}`",
        f"Paired rolling comparison: `{repo_relative_path(paired_path, REPO_ROOT)}`",
        f"Reference model: `{reference_model}`",
        "",
        "This report is a methodological comparison of forecasting baselines and discovery ablations. It is not a FluSight leaderboard claim.",
        "",
        "## Model Ranking",
        "",
        _markdown_table(ranked, ["series_name", "model_name", "test_mae", "rolling_mean_mae", "numerical_failure_flag"]),
        "",
        "## Discovery Ablations",
        "",
        _markdown_table(
            discovery_rows,
            [
                "series_name",
                "model_name",
                "test_mae",
                "rolling_mean_mae",
                "discovery_structure_name",
                "discovery_observation_map",
                "discovery_delay_weeks",
            ],
        ),
        "",
        "## Paired Rolling Comparison",
        "",
        _markdown_table(
            paired_view,
            [
                "series_name",
                "challenger_model",
                "n_aligned",
                "mean_abs_error_reference",
                "mean_abs_error_challenger",
                "mean_diff_challenger_minus_reference",
                "ci95_low",
                "ci95_high",
                "reference_win_rate",
            ],
        ),
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"


def _markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "_None._"
    visible_columns = [column for column in columns if column in frame.columns]
    shown = frame.loc[:, visible_columns].copy()
    lines = [
        "| " + " | ".join(visible_columns) + " |",
        "| " + " | ".join(["---"] * len(visible_columns)) + " |",
    ]
    for _, row in shown.iterrows():
        values = []
        for value in row.tolist():
            if isinstance(value, float):
                values.append(f"{value:.4f}")
            else:
                values.append("" if pd.isna(value) else str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
