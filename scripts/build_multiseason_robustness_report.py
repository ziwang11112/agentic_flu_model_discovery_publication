from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _artifact_path(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def _format_float(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{float(value):.4f}"


def _markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 24) -> str:
    if frame.empty:
        return "_None._"
    shown = frame.loc[:, [column for column in columns if column in frame.columns]].head(max_rows).copy()
    lines = [
        "| " + " | ".join(shown.columns.astype(str)) + " |",
        "| " + " | ".join(["---"] * len(shown.columns)) + " |",
    ]
    for _, row in shown.iterrows():
        values: list[str] = []
        for value in row.tolist():
            if isinstance(value, float):
                values.append(_format_float(value))
            else:
                values.append("" if pd.isna(value) else str(value))
        lines.append("| " + " | ".join(values) + " |")
    if len(frame) > max_rows:
        lines.append(f"\n_Showing {max_rows} of {len(frame)} rows._")
    return "\n".join(lines)


def _read_csv(root: Path, name: str) -> pd.DataFrame:
    path = root / name
    if not path.exists():
        raise FileNotFoundError(f"Missing compact multi-season artifact: {path}")
    return pd.read_csv(path)


def _write_recommendation_mode_figure(modes: pd.DataFrame, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    colors = {
        "constrained_structure_discovery": "#0072B2",
        "delayed_observation_seir": "#009E73",
        "deterministic_seir": "#D55E00",
        "rolling_mean_4wk": "#CC79A7",
        "last_observed": "#999999",
        "arima_auto_small": "#E69F00",
        "validation_only_structure_selection": "#56B4E9",
        "no_observation_search_discovery": "#F0E442",
    }
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    x = range(len(modes))
    bar_colors = [colors.get(str(model), "#666666") for model in modes["recommended_model_mode"]]
    ax.bar(x, modes["recommended_model_frequency"], color=bar_colors, edgecolor="#222222", linewidth=0.7)
    ax.set_xticks(list(x), modes["age_group"], rotation=0)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Recommendation mode frequency")
    ax.set_title("Multi-season recommendation modes")
    for idx, row in modes.iterrows():
        ax.text(
            idx,
            float(row["recommended_model_frequency"]) + 0.03,
            str(row["recommended_model_mode"]).replace("_", "\n"),
            ha="center",
            va="bottom",
            fontsize=8,
        )
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    paths = [
        output_dir / "fig_multiseason_recommendation_modes.pdf",
        output_dir / "fig_multiseason_recommendation_modes.png",
    ]
    for path in paths:
        fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return paths


def _write_observation_impact_figure(impact: pd.DataFrame, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_frame = impact.sort_values(["age_group", "season"]).copy()
    labels = plot_frame["season"].astype(str) + " / " + plot_frame["age_group"].astype(str)
    values = plot_frame["delta_rolling_mean_mae"].astype(float)
    colors = ["#0072B2" if value >= 0 else "#D55E00" for value in values]
    height = max(4.5, 0.32 * len(plot_frame) + 1.4)
    fig, ax = plt.subplots(figsize=(8.5, height))
    ax.barh(range(len(plot_frame)), values, color=colors, edgecolor="#222222", linewidth=0.5)
    ax.axvline(0.0, color="#333333", linewidth=1.0)
    ax.set_yticks(range(len(plot_frame)), labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Delta rolling MAE: no-observation-search minus constrained discovery")
    ax.set_title("Multi-season observation-search impact")
    ax.text(
        0.99,
        0.01,
        "Positive values favor observation-aware discovery.",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
    )
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    paths = [
        output_dir / "fig_multiseason_observation_search_impact.pdf",
        output_dir / "fig_multiseason_observation_search_impact.png",
    ]
    for path in paths:
        fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return paths


def build_report(artifact_root: Path, report_path: Path, write_figures: bool) -> None:
    run_summary = json.loads((artifact_root / "run_summary.json").read_text(encoding="utf-8"))
    modes = _read_csv(artifact_root, "multiseason_recommendation_modes.csv")
    recommendations = _read_csv(artifact_root, "season_level_recommendations.csv")
    observation_maps = _read_csv(artifact_root, "observation_map_by_season.csv")
    impact = _read_csv(artifact_root, "observation_search_impact_by_season.csv")
    key_findings = _read_csv(artifact_root, "multiseason_key_findings.csv")

    figure_paths: list[Path] = []
    if write_figures:
        figure_dir = REPO_ROOT / "paper_draft" / "figures"
        figure_paths.extend(_write_recommendation_mode_figure(modes, figure_dir))
        figure_paths.extend(_write_observation_impact_figure(impact, figure_dir))

    pediatric = key_findings.loc[key_findings["age_group"] == "0-4 yr"]
    if pediatric.empty:
        headline = "The pediatric 0-4 yr series was not included in this run."
    else:
        interpretation = str(pediatric.iloc[0]["interpretation"])
        headline = f"For `0-4 yr`, the compact multi-season check reports: {interpretation}."

    lines = [
        "# Multi-Season Robustness Appendix",
        "",
        "This appendix is a compact robustness check for the frozen discovery-ablation paper package.",
        "It does not replace the main frozen benchmark and does not make a FluSight, SOTA, or transfer-forecasting claim.",
        "",
        "## Data Scope",
        "",
        "- Source dataset: CDC RESP-NET dataset `kvib-3txy`, filtered/transformed to FluSurv-NET hospitalization rates.",
        "- Attribution: Centers for Disease Control and Prevention, RESP-NET/FluSurv-NET.",
        f"- Completed seasons included: {', '.join(run_summary['seasons'])}.",
        "- Excluded seasons: `2020-21` because required age strata are incomplete; `2025-26` because it is preliminary.",
        f"- Age groups evaluated: {', '.join(run_summary['age_groups'])}.",
        "",
        "## Evaluation Design",
        "",
        "Each completed season is evaluated as its own within-season trajectory with chronological train/validation/test splits.",
        "This is not previous-season-to-future-season transfer forecasting. Structure selection uses train/validation evidence only;",
        "test and rolling-origin metrics are used for post-selection evaluation and appendix interpretation.",
        "",
        "## Model Set And Budget",
        "",
        f"- Models: {', '.join(run_summary['models'])}.",
        f"- Horizons: {', '.join(str(value) for value in run_summary['horizons'])}.",
        f"- Reduced fitting budget: n_restarts={run_summary['fitting']['n_restarts']}, "
        f"rolling_n_restarts={run_summary['fitting']['rolling_n_restarts']}, "
        f"maxiter={run_summary['fitting']['maxiter']}.",
        f"- Discovery budget: beam_width={run_summary['discovery']['beam_width']}, "
        f"max_rounds={run_summary['discovery']['max_rounds']}, "
        f"exhaustive_max_candidates={run_summary['discovery']['exhaustive_max_candidates']}, "
        f"allow_truncated_exhaustive={run_summary['discovery']['allow_truncated_exhaustive']}.",
        "",
        "## Key Finding",
        "",
        headline,
        "A positive constrained-vs-no-observation rolling delta means the observation-aware constrained discovery model",
        "had lower rolling mean absolute error than the no-observation-search ablation for that season/age stratum.",
        "",
        "## Recommendation Modes By Age Group",
        "",
        _markdown_table(
            modes,
            [
                "age_group",
                "num_seasons",
                "recommended_model_mode",
                "recommended_model_frequency",
                "constrained_discovery_recommended_count",
                "delayed_I_selected_count",
                "positive_observation_search_delta_count",
            ],
        ),
        "",
        "## Season-Level Recommendations",
        "",
        _markdown_table(
            recommendations,
            [
                "season",
                "age_group",
                "recommended_model",
                "decision_type",
                "best_test_model",
                "best_rolling_model",
            ],
        ),
        "",
        "## Observation Map Frequencies",
        "",
        _markdown_table(
            observation_maps,
            [
                "season",
                "age_group",
                "model_name",
                "structure_name",
                "observation_map",
                "delay_weeks",
                "score_policy",
            ],
        ),
        "",
        "## Observation-Search Impact By Season",
        "",
        _markdown_table(
            impact,
            [
                "season",
                "age_group",
                "delta_test_mae",
                "delta_rolling_mean_mae",
                "constrained_structure",
                "constrained_observation_map",
                "no_observation_structure",
                "no_observation_observation_map",
            ],
        ),
        "",
        "## Caveats",
        "",
        "- This appendix is reduced-budget robustness evidence, not a new main benchmark freeze.",
        "- It is within-season retrospective evaluation, not FluSight-style prospective forecasting.",
        "- The result should only strengthen the paper if the pediatric observation-aware signal is repeated across seasons;",
        "  otherwise it should be framed as season-dependent evidence.",
        "- Numerical instability flags, if present in compact summaries, should be retained for transparency and not used for positive claims.",
    ]

    if figure_paths:
        lines.extend(
            [
                "",
                "## Figures",
                "",
                *[f"- `{path.relative_to(REPO_ROOT).as_posix()}`" for path in figure_paths],
            ]
        )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the compact multi-season robustness appendix report.")
    parser.add_argument("--artifact-root", default="artifacts_multiseason_robustness_compact")
    parser.add_argument("--report-path", default=None)
    parser.add_argument("--write-figures", action="store_true", default=None)
    parser.add_argument("--no-figures", dest="write_figures", action="store_false")
    args = parser.parse_args()
    artifact_root = _artifact_path(args.artifact_root)
    report_path = (
        _artifact_path(args.report_path)
        if args.report_path is not None
        else REPO_ROOT / "reports" / "multiseason_robustness_appendix.md"
    )
    write_figures = bool(args.write_figures) if args.write_figures is not None else "smoke" not in artifact_root.name
    build_report(artifact_root, report_path, write_figures=write_figures)
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
