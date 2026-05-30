from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
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


def _markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 24) -> str:
    if frame.empty:
        return "_None._"
    shown = frame.loc[:, [column for column in columns if column in frame.columns]].head(max_rows)
    lines = [
        "| " + " | ".join(shown.columns.astype(str)) + " |",
        "| " + " | ".join(["---"] * len(shown.columns)) + " |",
    ]
    for _, row in shown.iterrows():
        values: list[str] = []
        for value in row.tolist():
            if pd.isna(value):
                values.append("")
            elif isinstance(value, float):
                values.append(f"{value:.4f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    if len(frame) > max_rows:
        lines.append(f"\n_Showing {max_rows} of {len(frame)} rows._")
    return "\n".join(lines)


def _save_figure(fig: plt.Figure, output_dir: Path, stem: str) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = [output_dir / f"{stem}.pdf", output_dir / f"{stem}.png"]
    for output in outputs:
        fig.savefig(output, bbox_inches="tight", dpi=220)
    plt.close(fig)
    return outputs


def _build_budget_figure(by_budget: pd.DataFrame, output_dir: Path) -> list[Path]:
    synthetic = by_budget.loc[by_budget["layer"] == "synthetic_execution"].copy()
    realdata = by_budget.loc[by_budget["layer"] == "frozen_replay"].copy()
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.8))
    palette = {
        "mock_api_proposer": "#1b9e77",
        "deterministic_seed_proposer": "#66a61e",
        "random_candidate_proposer": "#666666",
        "failure_guided_proposer": "#7570b3",
        "no_observation_label_baseline": "#e7298a",
        "exhaustive_oracle": "#d95f02",
        "oracle_full_candidate_ranking": "#d95f02",
    }
    for proposer, subset in synthetic.groupby("proposer_type", sort=True):
        axes[0].plot(
            subset.sort_values("budget")["budget"],
            subset.sort_values("budget")["observation_label_recovery_rate"],
            marker="o",
            linewidth=2,
            label=proposer,
            color=palette.get(str(proposer)),
        )
    axes[0].set_title("Synthetic execution", weight="semibold")
    axes[0].set_xlabel("Candidate budget")
    axes[0].set_ylabel("Observation-label recovery")
    axes[0].set_ylim(0, 1.08)
    axes[0].grid(alpha=0.25)
    for proposer, subset in realdata.groupby("proposer_type", sort=True):
        axes[1].plot(
            subset.sort_values("budget")["budget"],
            subset.sort_values("budget")["top_epsilon_hit_rate"],
            marker="o",
            linewidth=2,
            label=proposer,
            color=palette.get(str(proposer)),
        )
    axes[1].set_title("Frozen real-data replay", weight="semibold")
    axes[1].set_xlabel("Candidate budget")
    axes[1].set_ylabel("Top-epsilon hit rate")
    axes[1].set_ylim(0, 1.08)
    axes[1].grid(alpha=0.25)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=8, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.02))
    fig.subplots_adjust(bottom=0.25, wspace=0.28)
    return _save_figure(fig, output_dir, "fig_api_candidate_execution_budget")


def _build_synthetic_comparison_figure(summary: pd.DataFrame, output_dir: Path) -> list[Path]:
    synthetic = summary.loc[summary["layer"] == "synthetic_execution"].sort_values("observation_label_recovery_rate", ascending=False)
    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    x = range(len(synthetic))
    width = 0.25
    ax.bar([i - width for i in x], synthetic["observation_label_recovery_rate"], width=width, label="Observation", color="#1b9e77")
    ax.bar(list(x), synthetic["delay_label_recovery_rate"], width=width, label="Delay", color="#7570b3")
    ax.bar([i + width for i in x], synthetic["top_epsilon_hit_rate"], width=width, label="Top-epsilon", color="#d95f02")
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Rate")
    ax.set_title("API/mock candidate execution: synthetic recovery", weight="semibold")
    ax.set_xticks(list(x))
    ax.set_xticklabels([label.replace("_", "\n") for label in synthetic["proposer_type"]], fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.14))
    return _save_figure(fig, output_dir, "fig_api_synthetic_recovery_comparison")


def build_report(artifact_root: Path, report_path: Path, write_figures: bool = True) -> list[Path]:
    status = json.loads((artifact_root / "api_candidate_execution_status.json").read_text(encoding="utf-8"))
    summary = _read_csv(artifact_root, "api_candidate_execution_summary.csv")
    by_budget = _read_csv(artifact_root, "api_candidate_execution_by_budget.csv")
    synthetic = _read_csv(artifact_root, "api_candidate_execution_synthetic_recovery.csv")
    realdata = _read_csv(artifact_root, "api_candidate_execution_realdata_replay.csv")
    audit = _read_csv(artifact_root, "api_candidate_prompt_audit.csv")

    lines = [
        "# Verifier-Gated API/Mock Candidate Execution Replay",
        "",
        "This Stage 6 evaluation measures proposal ordering and candidate-budget efficiency. The synthetic layer",
        "uses generic toy tasks with deterministic scoring. The real-data layer is replay-only over frozen compact",
        "summary rows. No real-data model refitting is performed, no external API is called in the committed config,",
        "and API/mock output cannot generate or execute model code.",
        "",
        "## Scope",
        "",
        f"- External API used: {status.get('external_api_used', False)}.",
        f"- Synthetic rows: {status.get('synthetic_rows', 0)}.",
        f"- Frozen replay rows: {status.get('realdata_rows', 0)}.",
        f"- Prompt audit rows: {status.get('prompt_audit_rows', 0)}.",
        f"- Prompt audit passed: {status.get('safe_prompt_passed', False)}.",
        "- Test metrics are post-hoc descriptive only in frozen replay rows.",
        "- Real-data refitting is deferred to an optional Stage 6b.",
        "",
        "## Summary Metrics",
        "",
        _markdown_table(
            summary,
            [
                "layer",
                "proposer_type",
                "observation_label_recovery_rate",
                "delay_label_recovery_rate",
                "top_epsilon_hit_rate",
                "best_rolling_error_after_k",
                "best_rolling_score_after_k",
                "post_selection_test_mae",
                "valid_proposal_rate",
                "duplicate_rate",
                "out_of_allowlist_rejection_rate",
            ],
            max_rows=20,
        ),
        "",
        "## Budget Curves",
        "",
        _markdown_table(
            by_budget,
            [
                "layer",
                "proposer_type",
                "budget",
                "observation_label_recovery_rate",
                "best_rolling_score_after_k",
                "top_epsilon_hit_rate",
            ],
            max_rows=36,
        ),
        "",
        "## Synthetic Execution",
        "",
        _markdown_table(
            synthetic,
            [
                "task_name",
                "proposer_type",
                "budget",
                "observation_label_recovered",
                "delay_label_recovered",
                "top_epsilon_hit",
                "best_rolling_error_after_k",
            ],
            max_rows=36,
        ),
        "",
        "## Frozen Real-Data Replay",
        "",
        _markdown_table(
            realdata,
            [
                "series_name",
                "proposer_type",
                "budget",
                "selected_model_at_k",
                "best_rolling_score_after_k",
                "post_selection_test_mae",
                "test_metric_usage",
            ],
            max_rows=36,
        ),
        "",
        "## No-Leakage Prompt Audit",
        "",
        _markdown_table(
            audit,
            [
                "series_name",
                "proposer_type",
                "prompt_contains_test_metric",
                "prompt_contains_test_winner",
                "prompt_contains_posthoc_metric",
                "safe_prompt_passed",
            ],
            max_rows=36,
        ),
        "",
        "## Claim Boundary",
        "",
        "- This supports proposal-quality and candidate-budget-efficiency claims only.",
        "- It does not support forecasting-performance, state-of-the-art, mechanism-discovery, or autonomous-science claims.",
        "- Synthetic execution uses generic structured time-series tasks.",
        "- Frozen real-data replay uses existing compact rows and does not refit models.",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")

    outputs: list[Path] = []
    if write_figures:
        figure_dir = REPO_ROOT / "paper_draft" / "figures"
        outputs.extend(_build_budget_figure(by_budget, figure_dir))
        outputs.extend(_build_synthetic_comparison_figure(summary, figure_dir))
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Build API/mock candidate execution replay report.")
    parser.add_argument("--artifact-root", default="artifacts_api_candidate_execution_compact")
    parser.add_argument("--report-path", default="reports/api_candidate_execution_report.md")
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args()
    artifact_root = _artifact_path(args.artifact_root)
    report_path = _artifact_path(args.report_path)
    figures = build_report(artifact_root, report_path, write_figures=not args.no_figures)
    print(f"Wrote {report_path}")
    for figure in figures:
        print(f"Wrote {figure}")


if __name__ == "__main__":
    main()
