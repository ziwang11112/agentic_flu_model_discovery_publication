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


def _markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 20) -> str:
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
            if isinstance(value, float):
                values.append(f"{value:.4f}")
            else:
                values.append("" if pd.isna(value) else str(value))
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


def _build_recovery_figure(summary: pd.DataFrame, output_dir: Path) -> list[Path]:
    policies = [
        "pareto_epsilon",
        "weighted_score",
        "hard_veto_decision_tree",
        "random_label_baseline",
        "no_observation_label_baseline",
        "deterministic_seed_proposer",
    ]
    plot = summary.set_index("policy_name").reindex([policy for policy in policies if policy in set(summary["policy_name"])])
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    colors = ["#1b9e77", "#7570b3", "#d95f02"]
    x = range(len(plot))
    width = 0.25
    ax.bar([i - width for i in x], plot["observation_label_recovery_rate"], width=width, label="Observation label", color=colors[0])
    ax.bar(list(x), plot["delay_label_recovery_rate"], width=width, label="Delay label", color=colors[1])
    ax.bar([i + width for i in x], plot["candidate_family_recovery_rate"], width=width, label="Family label", color=colors[2])
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Recovery rate")
    ax.set_title("Synthetic structured recovery", weight="semibold")
    ax.set_xticks(list(x))
    ax.set_xticklabels([label.replace("_", "\n") for label in plot.index], fontsize=8)
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.14))
    ax.grid(axis="y", alpha=0.25)
    return _save_figure(fig, output_dir, "fig_synthetic_structured_recovery")


def _build_budget_figure(curve: pd.DataFrame, output_dir: Path) -> list[Path]:
    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    palette = {
        "pareto_epsilon": "#1b9e77",
        "weighted_score": "#7570b3",
        "hard_veto_decision_tree": "#d95f02",
        "random_label_baseline": "#666666",
        "no_observation_label_baseline": "#e7298a",
        "deterministic_seed_proposer": "#66a61e",
    }
    for policy_name, subset in curve.groupby("policy_name", sort=True):
        ax.plot(
            subset["budget"],
            subset["observation_label_recovery_rate"],
            marker="o",
            linewidth=2,
            label=policy_name,
            color=palette.get(str(policy_name), None),
        )
    ax.set_ylim(0, 1.08)
    ax.set_xlabel("Candidate budget")
    ax.set_ylabel("Observation-label recovery rate")
    ax.set_title("Budgeted synthetic recovery", weight="semibold")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, fontsize=8, ncol=2)
    return _save_figure(fig, output_dir, "fig_synthetic_budget_curve")


def _build_full_policy_figure(summary: pd.DataFrame, output_dir: Path) -> list[Path]:
    plot = summary.sort_values("observation_label_recovery_rate", ascending=False)
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    x = range(len(plot))
    width = 0.24
    ax.bar([i - width for i in x], plot["observation_label_recovery_rate"], width=width, label="Observation", color="#1b9e77")
    ax.bar(list(x), plot["delay_label_recovery_rate"], width=width, label="Delay", color="#7570b3")
    ax.bar([i + width for i in x], plot["top_epsilon_hit_rate"], width=width, label="Top-epsilon", color="#d95f02")
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Rate")
    ax.set_title("Expanded synthetic structured recovery", weight="semibold")
    ax.set_xticks(list(x))
    ax.set_xticklabels([label.replace("_", "\n") for label in plot["policy_name"]], fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.14))
    return _save_figure(fig, output_dir, "fig_synthetic_recovery_full_policy_comparison")


def _build_full_noise_budget_figure(noise_curve: pd.DataFrame, budget_curve: pd.DataFrame, output_dir: Path) -> list[Path]:
    policies = ["pareto_epsilon", "weighted_score", "deterministic_seed_proposer", "random_label_baseline", "no_observation_label_baseline"]
    palette = {
        "pareto_epsilon": "#1b9e77",
        "weighted_score": "#7570b3",
        "hard_veto_decision_tree": "#d95f02",
        "random_label_baseline": "#666666",
        "no_observation_label_baseline": "#e7298a",
        "deterministic_seed_proposer": "#66a61e",
    }
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), sharey=True)
    for policy in policies:
        subset = noise_curve.loc[noise_curve["policy_name"] == policy].sort_values("noise_level")
        if not subset.empty:
            axes[0].plot(subset["noise_level"], subset["observation_label_recovery_rate"], marker="o", linewidth=2, label=policy, color=palette.get(policy))
        bsubset = budget_curve.loc[budget_curve["policy_name"] == policy].sort_values("budget")
        if not bsubset.empty:
            axes[1].plot(bsubset["budget"], bsubset["observation_label_recovery_rate"], marker="o", linewidth=2, label=policy, color=palette.get(policy))
    axes[0].set_title("Noise sensitivity", weight="semibold")
    axes[0].set_xlabel("Noise level")
    axes[0].set_ylabel("Observation-label recovery rate")
    axes[1].set_title("Budget sensitivity", weight="semibold")
    axes[1].set_xlabel("Candidate budget")
    for ax in axes:
        ax.set_ylim(0, 1.08)
        ax.grid(alpha=0.25)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=8, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.02))
    fig.subplots_adjust(bottom=0.22, wspace=0.20)
    return _save_figure(fig, output_dir, "fig_synthetic_recovery_full_noise_budget")


def build_report(
    artifact_root: Path,
    report_path: Path,
    write_figures: bool = True,
    full: bool = False,
    full_prefix: str = "synthetic_structured_recovery_full",
) -> list[Path]:
    if full:
        return build_full_report(artifact_root, report_path, write_figures=write_figures, prefix=full_prefix)

    run_summary = json.loads((artifact_root / "synthetic_structured_recovery_run_summary.json").read_text(encoding="utf-8"))
    summary = _read_csv(artifact_root, "synthetic_structured_recovery_summary.csv")
    by_seed = _read_csv(artifact_root, "synthetic_structured_recovery_by_seed.csv")
    curve = _read_csv(artifact_root, "synthetic_structured_recovery_budget_curve.csv")

    policy_summary = summary.sort_values("policy_name")
    per_task = (
        by_seed.groupby(["task_name", "policy_name"], as_index=False)
        .agg(
            observation_label_recovery_rate=("observation_label_recovered", "mean"),
            delay_label_recovery_rate=("delay_label_recovered", "mean"),
            mean_rolling_error=("rolling_error", "mean"),
        )
        .sort_values(["task_name", "policy_name"])
    )

    lines = [
        "# Synthetic Structured Recovery Evaluation",
        "",
        "This is a local deterministic software evaluation over generic structured time-series toy tasks.",
        "It does not call external APIs, does not run new forecasting experiments, and does not provide",
        "biological, medical, operational, or intervention guidance.",
        "",
        "## Scope",
        "",
        f"- Tasks: {', '.join(run_summary['tasks'])}.",
        f"- Seeds: {run_summary['seeds']}.",
        f"- Noise levels: {run_summary['noise_levels']}.",
        f"- Candidate budgets: {run_summary['budgets']}.",
        f"- Policies/baselines: {', '.join(run_summary['policies'])}.",
        "- API path: disabled by default.",
        "",
        "The tasks are generic structured state-space analogues for direct, lagged, mixture, and proxy",
        "observation labels. They are not mechanism-discovery evidence for the real FluSurv-NET benchmark.",
        "",
        "## Policy-Level Recovery",
        "",
        _markdown_table(
            policy_summary,
            [
                "policy_name",
                "observation_label_recovery_rate",
                "delay_label_recovery_rate",
                "candidate_family_recovery_rate",
                "mean_rolling_error",
                "budget_to_recover_true_label",
                "valid_proposal_rate",
                "duplicate_proposal_rate",
                "top_epsilon_hit_rate",
            ],
            max_rows=20,
        ),
        "",
        "## Per-Task Recovery",
        "",
        _markdown_table(
            per_task,
            ["task_name", "policy_name", "observation_label_recovery_rate", "delay_label_recovery_rate", "mean_rolling_error"],
            max_rows=36,
        ),
        "",
        "## Budget Curve",
        "",
        _markdown_table(
            curve,
            ["policy_name", "budget", "observation_label_recovery_rate", "delay_label_recovery_rate", "top_epsilon_hit_rate"],
            max_rows=36,
        ),
        "",
        "## Caveats",
        "",
        "- This is a local synthetic recovery check, not a real-data forecasting-performance result.",
        "- The toy tasks are deliberately small and deterministic so they can be tested quickly.",
        "- API-assisted proposal is not used unless explicitly enabled in a future config.",
        "- The result should be read as software validation for observation-label and delay-label selection logic.",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")

    outputs: list[Path] = []
    if write_figures:
        figure_dir = REPO_ROOT / "paper_draft" / "figures"
        outputs.extend(_build_recovery_figure(summary, figure_dir))
        outputs.extend(_build_budget_figure(curve, figure_dir))
    return outputs


def build_full_report(
    artifact_root: Path,
    report_path: Path,
    write_figures: bool = True,
    prefix: str = "synthetic_structured_recovery_full",
) -> list[Path]:
    run_summary = json.loads((artifact_root / f"{prefix}_run_summary.json").read_text(encoding="utf-8"))
    summary = _read_csv(artifact_root, f"{prefix}_summary.csv")
    by_condition = _read_csv(artifact_root, f"{prefix}_by_condition.csv")
    budget_curve = _read_csv(artifact_root, f"{prefix}_budget_curve.csv")
    noise_curve = _read_csv(artifact_root, f"{prefix}_noise_curve.csv")

    per_task = (
        by_condition.groupby(["task_name", "policy_name"], as_index=False)
        .agg(
            observation_label_recovery_rate=("observation_label_recovery_rate", "mean"),
            delay_label_recovery_rate=("delay_label_recovery_rate", "mean"),
            mean_rolling_error=("mean_rolling_error", "mean"),
            top_epsilon_hit_rate=("top_epsilon_hit_rate", "mean"),
        )
        .sort_values(["task_name", "policy_name"])
    )
    stage4_comparison = pd.DataFrame()
    stage4_path = artifact_root / "synthetic_structured_recovery_summary.csv"
    if stage4_path.exists():
        stage4 = pd.read_csv(stage4_path)
        stage4_comparison = summary.merge(stage4, on="policy_name", suffixes=("_stage5", "_stage4"))
        keep = [
            "policy_name",
            "observation_label_recovery_rate_stage4",
            "observation_label_recovery_rate_stage5",
            "delay_label_recovery_rate_stage4",
            "delay_label_recovery_rate_stage5",
            "top_epsilon_hit_rate_stage4",
            "top_epsilon_hit_rate_stage5",
        ]
        stage4_comparison = stage4_comparison.loc[:, [column for column in keep if column in stage4_comparison.columns]]

    policy_rates = summary.set_index("policy_name")
    pareto_obs = float(policy_rates.loc["pareto_epsilon", "observation_label_recovery_rate"]) if "pareto_epsilon" in policy_rates.index else float("nan")
    random_obs = float(policy_rates.loc["random_label_baseline", "observation_label_recovery_rate"]) if "random_label_baseline" in policy_rates.index else float("nan")
    no_obs = float(policy_rates.loc["no_observation_label_baseline", "observation_label_recovery_rate"]) if "no_observation_label_baseline" in policy_rates.index else float("nan")
    seed_obs = float(policy_rates.loc["deterministic_seed_proposer", "observation_label_recovery_rate"]) if "deterministic_seed_proposer" in policy_rates.index else float("nan")
    noise_010 = noise_curve.loc[(noise_curve["policy_name"] == "pareto_epsilon") & (noise_curve["noise_level"].round(3) == 0.100)]
    pareto_noise_010 = float(noise_010["observation_label_recovery_rate"].iloc[0]) if not noise_010.empty else float("nan")

    lines = [
        "# Expanded Synthetic Structured Recovery Sweep",
        "",
        "This is a generic structured time-series software validation sweep. It uses no real FluSurv-NET",
        "data, runs no real-data forecasting experiments, calls no external API, and does not provide",
        "real-world mechanism-recovery evidence.",
        "",
        "## Scope",
        "",
        f"- Sweep label: {run_summary.get('config_scope', 'unknown')}.",
        f"- Tasks: {', '.join(run_summary['tasks'])}.",
        f"- Seeds: {run_summary['seeds'][0]}..{run_summary['seeds'][-1]} ({len(run_summary['seeds'])} seeds).",
        f"- Noise levels: {run_summary['noise_levels']}.",
        f"- Candidate budgets: {run_summary['budgets']}.",
        f"- Policies/baselines: {', '.join(run_summary['policies'])}.",
        "- API path: disabled.",
        "",
        "## Overall Policy Comparison",
        "",
        _markdown_table(
            summary.sort_values("observation_label_recovery_rate", ascending=False),
            [
                "policy_name",
                "observation_label_recovery_rate",
                "delay_label_recovery_rate",
                "candidate_family_recovery_rate",
                "mean_rolling_error",
                "budget_to_recover_true_label",
                "valid_proposal_rate",
                "duplicate_proposal_rate",
                "top_epsilon_hit_rate",
            ],
            max_rows=20,
        ),
        "",
        "## Noise-Stratified Recovery",
        "",
        _markdown_table(
            noise_curve,
            ["policy_name", "noise_level", "observation_label_recovery_rate", "delay_label_recovery_rate", "top_epsilon_hit_rate"],
            max_rows=40,
        ),
        "",
        "## Budget-Stratified Recovery",
        "",
        _markdown_table(
            budget_curve,
            ["policy_name", "budget", "observation_label_recovery_rate", "delay_label_recovery_rate", "top_epsilon_hit_rate"],
            max_rows=40,
        ),
        "",
        "## Per-Task Recovery",
        "",
        _markdown_table(
            per_task,
            ["task_name", "policy_name", "observation_label_recovery_rate", "delay_label_recovery_rate", "mean_rolling_error", "top_epsilon_hit_rate"],
            max_rows=40,
        ),
        "",
        "## Comparison To Stage 4 Local Sweep",
        "",
        _markdown_table(stage4_comparison, list(stage4_comparison.columns), max_rows=20) if not stage4_comparison.empty else "_Stage 4 summary not found._",
        "",
        "## Go/No-Go Interpretation",
        "",
        f"- Pareto-epsilon observation recovery is {pareto_obs:.4f}, compared with random-label baseline {random_obs:.4f} and no-observation-label baseline {no_obs:.4f}.",
        f"- At noise level 0.10, pareto-epsilon observation recovery is {pareto_noise_010:.4f}.",
        f"- Deterministic seed proposer observation recovery is {seed_obs:.4f}; when it is stronger or comparable, we do not claim pareto-epsilon is universally best.",
        "- Mixture and proxy tasks remain the hardest conditions and should be described as controlled failure modes, not as real-data mechanism evidence.",
        "",
        "## Caveats",
        "",
        "- This expanded sweep is synthetic software validation only.",
        "- It does not use real FluSurv-NET data and does not alter the frozen discovery-ablation artifacts.",
        "- It does not evaluate real-world forecasting performance or mechanism recovery.",
        "- API-assisted proposal is disabled.",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")

    outputs: list[Path] = []
    if write_figures:
        figure_dir = REPO_ROOT / "paper_draft" / "figures"
        outputs.extend(_build_full_policy_figure(summary, figure_dir))
        outputs.extend(_build_full_noise_budget_figure(noise_curve, budget_curve, figure_dir))
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Build synthetic structured recovery report.")
    parser.add_argument("--artifact-root", default="artifacts_selection_policy_eval_compact")
    parser.add_argument("--report-path", default="reports/selection_synthetic_recovery_report.md")
    parser.add_argument("--no-figures", action="store_true")
    parser.add_argument("--full", action="store_true", help="Build the expanded Stage 5 synthetic recovery report.")
    parser.add_argument("--full-prefix", default="synthetic_structured_recovery_full", help="Artifact filename prefix for --full reports.")
    args = parser.parse_args()
    artifact_root = _artifact_path(args.artifact_root)
    default_full_report = args.report_path == "reports/selection_synthetic_recovery_report.md"
    report_path = _artifact_path("reports/selection_synthetic_recovery_full_report.md" if args.full and default_full_report else args.report_path)
    figures = build_report(
        artifact_root,
        report_path,
        write_figures=not args.no_figures,
        full=args.full,
        full_prefix=args.full_prefix,
    )
    print(f"Wrote {report_path}")
    for figure in figures:
        print(f"Wrote {figure}")


if __name__ == "__main__":
    main()
