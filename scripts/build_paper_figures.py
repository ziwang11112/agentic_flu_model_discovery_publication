"""Build paper-ready figures from frozen discovery-ablation artifacts.

This script is intentionally read-only with respect to benchmark artifacts: it
loads frozen CSV summaries from artifacts_discovery_ablation and writes figure
PDF/PNG files plus a lightweight figure index.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import wrap

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import patches


REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = REPO_ROOT / "artifacts_discovery_ablation"
FIGURE_DIR = REPO_ROOT / "paper_draft" / "figures"
FIGURE_INDEX = REPO_ROOT / "reports" / "paper_figure_index.md"

SERIES_ORDER = ["Overall", "0-4 yr", "5-17 yr", "18-49 yr", "50-64 yr", ">= 65 yr"]
DISCOVERY_MODEL_ORDER = [
    "constrained_structure_discovery",
    "random_structure_discovery",
    "exhaustive_structure_discovery",
    "validation_only_structure_selection",
    "no_observation_search_discovery",
    "no_stability_discovery",
]
FOREST_CHALLENGER_ORDER = [
    "deterministic_seir",
    "delayed_observation_seir",
    "arima_auto_small",
    "no_observation_search_discovery",
    "validation_only_structure_selection",
    "random_structure_discovery",
]

MODEL_LABELS = {
    "arima_auto_small": "ARIMA",
    "constrained_structure_discovery": "Constrained",
    "delayed_observation_seir": "Delayed SEIR",
    "deterministic_seir": "Det. SEIR",
    "equal_weight_point_ensemble": "Ensemble",
    "exhaustive_structure_discovery": "Exhaustive",
    "fractional_seir": "Fractional SEIR",
    "hospitalized_seihr": "Hosp. SEIHR",
    "lagged_gradient_boosting": "GBR",
    "lagged_ridge": "Ridge",
    "last_observed": "Last obs.",
    "no_observation_search_discovery": "No obs-search",
    "no_stability_discovery": "No stability",
    "probabilistic_seir": "Prob. SEIR",
    "random_structure_discovery": "Random",
    "rolling_mean_2wk": "Roll mean 2wk",
    "rolling_mean_4wk": "Roll mean 4wk",
    "validation_only_structure_selection": "Val-only",
}

MODEL_FAMILIES = {
    "arima_auto_small": "Forecasting baseline",
    "lagged_gradient_boosting": "Forecasting baseline",
    "lagged_ridge": "Forecasting baseline",
    "last_observed": "Forecasting baseline",
    "rolling_mean_2wk": "Forecasting baseline",
    "rolling_mean_4wk": "Forecasting baseline",
    "delayed_observation_seir": "Manual epidemic baseline",
    "deterministic_seir": "Manual epidemic baseline",
    "fractional_seir": "Manual epidemic baseline",
    "hospitalized_seihr": "Manual epidemic baseline",
    "probabilistic_seir": "Manual epidemic baseline",
    "constrained_structure_discovery": "Constrained discovery",
    "exhaustive_structure_discovery": "Discovery ablation",
    "no_observation_search_discovery": "Discovery ablation",
    "no_stability_discovery": "Discovery ablation",
    "random_structure_discovery": "Discovery ablation",
    "validation_only_structure_selection": "Discovery ablation",
    "equal_weight_point_ensemble": "Ensemble",
}

FAMILY_COLORS = {
    "Forecasting baseline": "#2F6F9F",
    "Manual epidemic baseline": "#B36B00",
    "Constrained discovery": "#007A5E",
    "Discovery ablation": "#9A4D7A",
    "Ensemble": "#6F6F6F",
}

FAMILY_FACE_COLORS = {
    "Forecasting baseline": "#E8F2F8",
    "Manual epidemic baseline": "#F8EAD1",
    "Constrained discovery": "#DFF1EA",
    "Discovery ablation": "#F3E2ED",
    "Ensemble": "#ECECEC",
}

FIGURE_CAPTIONS = {
    "fig1_recommendation_map": (
        "Age- and objective-aware model recommendations",
        "Different age strata favor different model families and objectives; this supports "
        "objective-aware recommendation rather than a single global winner.",
    ),
    "fig2_observation_search_impact": (
        "Impact of observation-map search",
        "Positive values favor observation-aware discovery. Pediatric strata show the clearest "
        "rolling-origin benefit from allowing delayed observation maps.",
    ),
    "fig3_discovery_ablation_matrix": (
        "Discovery ablations across age strata",
        "Rolling-origin MAE is ranked within each age stratum across same-grammar discovery "
        "variants; darker cells indicate better within-stratum ranks.",
    ),
    "fig4_paired_rolling_forest": (
        "Paired rolling-origin comparisons against constrained discovery",
        "Mean paired rolling absolute-error differences are challenger minus constrained "
        "discovery; positive values mean constrained discovery has lower rolling error.",
    ),
    "fig5_numerical_failure_audit": (
        "Numerical failure flags by model family",
        "Flagged rows are retained for transparency but not used to support positive claims.",
    ),
}


def _read_csv(name: str) -> pd.DataFrame:
    path = ARTIFACT_ROOT / name
    if not path.exists():
        raise FileNotFoundError(f"Missing frozen artifact CSV: {path}")
    return pd.read_csv(path)


def _set_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 120,
            "savefig.dpi": 220,
            "font.family": "DejaVu Sans",
            "font.size": 9.5,
            "axes.titlesize": 13,
            "axes.labelsize": 11,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "axes.edgecolor": "#333333",
            "axes.linewidth": 0.8,
            "grid.color": "#CFCFCF",
            "grid.linewidth": 0.7,
            "grid.alpha": 0.28,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def _short_model(model_name: str) -> str:
    return MODEL_LABELS.get(str(model_name), str(model_name).replace("_", " "))


def _family_for_model(model_name: str) -> str:
    return MODEL_FAMILIES.get(str(model_name), "Forecasting baseline")


def _save_figure(fig: plt.Figure, stem: str) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE_DIR / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(FIGURE_DIR / f"{stem}.png", bbox_inches="tight")
    plt.close(fig)


def _ordered_series(df: pd.DataFrame) -> pd.DataFrame:
    ordered = df.copy()
    ordered["series_name"] = pd.Categorical(ordered["series_name"], SERIES_ORDER, ordered=True)
    return ordered.sort_values("series_name").reset_index(drop=True)


def build_recommendation_map() -> None:
    df = _ordered_series(_read_csv("paper_recommendation_table.csv"))
    columns = [
        ("recommended_model", "Recommended"),
        ("best_test_model", "Best test"),
        ("best_rolling_model", "Best rolling"),
    ]

    fig, ax = plt.subplots(figsize=(10.4, 5.35))
    ax.set_xlim(-1.25, len(columns))
    ax.set_ylim(-0.8, len(df) + 0.4)
    ax.axis("off")
    ax.set_title("Age- and objective-aware model recommendations", pad=18, weight="semibold")
    ax.text(
        0.5,
        1.005,
        "Frozen discovery-ablation run; colors identify model families",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=9,
        color="#555555",
    )

    for col_idx, (_, label) in enumerate(columns):
        ax.text(col_idx + 0.5, len(df) - 0.08, label, ha="center", va="bottom", weight="semibold")

    for row_idx, row in df.iterrows():
        y = len(df) - row_idx - 1
        ax.text(-0.16, y + 0.5, str(row["series_name"]), ha="right", va="center", weight="semibold")
        for col_idx, (col_name, _) in enumerate(columns):
            model = str(row[col_name])
            family = _family_for_model(model)
            color = FAMILY_COLORS[family]
            face_color = FAMILY_FACE_COLORS[family]
            rect = patches.FancyBboxPatch(
                (col_idx + 0.03, y + 0.1),
                0.96,
                0.8,
                boxstyle="round,pad=0.012,rounding_size=0.035",
                facecolor=face_color,
                edgecolor=color,
                linewidth=1.15,
            )
            ax.add_patch(rect)
            stripe = patches.Rectangle(
                (col_idx + 0.03, y + 0.1),
                0.045,
                0.8,
                facecolor=color,
                edgecolor=color,
                linewidth=0,
            )
            ax.add_patch(stripe)
            label = "\n".join(wrap(_short_model(model), width=13))
            ax.text(col_idx + 0.52, y + 0.5, label, ha="center", va="center", color="#222222", weight="semibold")

    legend_handles = [
        patches.Patch(facecolor=FAMILY_FACE_COLORS[family], edgecolor=color, linewidth=1.2, label=family)
        for family, color in FAMILY_COLORS.items()
    ]
    ax.legend(handles=legend_handles, loc="lower center", bbox_to_anchor=(0.5, -0.12), ncol=3, frameon=False)
    _save_figure(fig, "fig1_recommendation_map")


def build_observation_search_impact() -> None:
    df = _ordered_series(_read_csv("observation_search_impact_table.csv"))
    rolling_col = "delta_rolling_mean_mae_no_observation_minus_constrained"
    test_col = "delta_test_mae_no_observation_minus_constrained"
    y = np.arange(len(df))
    rolling = df[rolling_col].astype(float).to_numpy()
    test = df[test_col].astype(float).to_numpy()

    fig, ax = plt.subplots(figsize=(9.4, 5.35))
    colors = np.where(rolling >= 0, "#4E9F8F", "#C58A32")
    ax.barh(y, rolling, color=colors, alpha=0.88, label="Rolling mean MAE")
    ax.scatter(test, y, marker="D", color="#2F5D8C", edgecolor="white", linewidth=0.6, s=52, label="Test MAE")
    ax.axvline(0, color="#222222", linewidth=1)
    ax.set_yticks(y, df["series_name"].astype(str).tolist())
    ax.invert_yaxis()
    ax.set_xlabel(r"$\Delta$ error: no-observation-search minus constrained discovery")
    ax.set_title("Impact of observation-map search", weight="semibold")
    ax.grid(axis="x")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    max_val = max(np.nanmax(np.abs(rolling)), np.nanmax(np.abs(test)), 0.01)
    ax.set_xlim(-0.015, max_val * 1.28)
    for label in ["0-4 yr", "5-17 yr"]:
        match = df.index[df["series_name"].astype(str) == label]
        if len(match) == 0:
            continue
        idx = int(match[0])
        ax.text(
            rolling[idx] + max_val * 0.03,
            idx,
            f"{label}: +{rolling[idx]:.3f}",
            va="center",
            ha="left",
            fontsize=9,
            weight="semibold",
            color="#222222",
        )
    ax.legend(loc="upper right", frameon=False)
    fig.subplots_adjust(bottom=0.2)
    fig.text(
        0.5,
        0.035,
        "Positive values favor observation-aware discovery.",
        ha="center",
        va="bottom",
        fontsize=9,
    )
    _save_figure(fig, "fig2_observation_search_impact")


def build_discovery_ablation_matrix() -> None:
    df = _read_csv("discovery_ablation_compact_table.csv")
    matrix = (
        df.pivot(index="model_name", columns="series_name", values="rolling_mean_mae")
        .reindex(index=DISCOVERY_MODEL_ORDER, columns=SERIES_ORDER)
    )
    flags = (
        df.pivot(index="model_name", columns="series_name", values="numerical_failure_flag")
        .reindex(index=DISCOVERY_MODEL_ORDER, columns=SERIES_ORDER)
        .fillna(False)
    )
    ranks = matrix.rank(axis=0, method="min", ascending=True)
    denom = max(len(DISCOVERY_MODEL_ORDER) - 1, 1)
    normalized = (ranks - 1) / denom

    fig, ax = plt.subplots(figsize=(10.8, 6.0))
    im = ax.imshow(normalized.to_numpy(dtype=float), cmap="cividis", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(np.arange(len(SERIES_ORDER)), SERIES_ORDER, rotation=35, ha="right")
    ax.set_yticks(np.arange(len(DISCOVERY_MODEL_ORDER)), [_short_model(m) for m in DISCOVERY_MODEL_ORDER])
    ax.set_title("Discovery ablations across age strata", weight="semibold", pad=14)

    for row_idx, model_name in enumerate(DISCOVERY_MODEL_ORDER):
        for col_idx, series_name in enumerate(SERIES_ORDER):
            value = matrix.loc[model_name, series_name]
            flag = bool(flags.loc[model_name, series_name])
            text = "" if pd.isna(value) else f"{value:.3f}{'*' if flag else ''}"
            color = "white" if normalized.loc[model_name, series_name] < 0.45 else "black"
            ax.text(col_idx, row_idx, text, ha="center", va="center", fontsize=8.4, color=color, weight="semibold")

    ax.set_xticks(np.arange(-0.5, len(SERIES_ORDER), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(DISCOVERY_MODEL_ORDER), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.5)
    ax.tick_params(which="minor", bottom=False, left=False)
    cbar = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.03)
    cbar.set_label("Within-series rank color (dark = lower rolling MAE)")
    ax.text(
        0,
        -0.16,
        "Cell text is rolling mean MAE; * marks a numerical-failure flag retained for transparency.",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
    )
    _save_figure(fig, "fig3_discovery_ablation_matrix")


def build_paired_rolling_forest() -> None:
    df = _read_csv("paired_rolling_key_comparisons.csv")
    df = df[df["challenger_model"].isin(FOREST_CHALLENGER_ORDER)].copy()
    df["series_name"] = pd.Categorical(df["series_name"], SERIES_ORDER, ordered=True)
    df["challenger_model"] = pd.Categorical(df["challenger_model"], FOREST_CHALLENGER_ORDER, ordered=True)
    df = df.sort_values(["series_name", "challenger_model"]).reset_index(drop=True)

    y = np.arange(len(df))
    mean = df["mean_diff_challenger_minus_reference"].astype(float).to_numpy()
    low = df["ci95_low"].astype(float).to_numpy()
    high = df["ci95_high"].astype(float).to_numpy()
    xerr = np.vstack([mean - low, high - mean])
    point_colors = np.where(mean >= 0, "#007A5E", "#B36B00")
    labels = [f"{row.series_name}: {_short_model(row.challenger_model)}" for row in df.itertuples()]

    fig, ax = plt.subplots(figsize=(10.5, 10.8))
    group_size = len(FOREST_CHALLENGER_ORDER)
    for start in range(0, len(df), group_size * 2):
        ax.axhspan(start - 0.5, min(start + group_size - 0.5, len(df) - 0.5), color="#F6F6F6", zorder=0)
    ax.errorbar(mean, y, xerr=xerr, fmt="none", ecolor="#4D4D4D", elinewidth=1.2, capsize=2.5, zorder=1)
    ax.scatter(mean, y, c=point_colors, s=35, zorder=2, edgecolor="white", linewidth=0.4)
    ax.axvline(0, color="black", linewidth=1)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("Mean rolling absolute-error difference: challenger minus constrained discovery")
    ax.set_title("Paired rolling-origin comparisons against constrained discovery", weight="semibold", pad=14)
    ax.grid(axis="x")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for boundary in range(group_size - 0, len(df), group_size):
        ax.axhline(boundary - 0.5, color="#D0D0D0", linewidth=0.8)
    ax.text(
        0.99,
        0.01,
        "Positive values favor constrained discovery; negative values favor the challenger.",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
    )
    _save_figure(fig, "fig4_paired_rolling_forest")


def build_numerical_failure_audit() -> None:
    df = _read_csv("numerical_failure_summary.csv")
    flagged = df[df["numerical_failure_flag"].astype(bool)]
    counts = flagged.groupby("model_name").size().sort_values(ascending=False)

    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    if counts.empty:
        ax.text(0.5, 0.5, "No numerical failure flags", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
    else:
        labels = [_short_model(model) for model in counts.index]
        y = np.arange(len(counts))
        ax.barh(y, counts.to_numpy(), color="#8C8C8C")
        ax.set_yticks(y, labels)
        ax.invert_yaxis()
        ax.set_xlabel("Flagged rows")
        ax.set_title("Numerical failure flags by model family", weight="semibold", pad=14)
        ax.grid(axis="x")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        for idx, count in enumerate(counts.to_numpy()):
            ax.text(count + 0.08, idx, str(int(count)), ha="left", va="center", weight="semibold")
        ax.set_xlim(0, counts.max() + 1.1)
    _save_figure(fig, "fig5_numerical_failure_audit")


def write_figure_index() -> None:
    lines = [
        "# Paper Figure Index",
        "",
        "These figures are generated from frozen CSV artifacts under "
        "`artifacts_discovery_ablation/` by running:",
        "",
        "```bash",
        "python scripts/build_paper_figures.py",
        "```",
        "",
        "No new experiments are run, and frozen result CSVs are not modified.",
        "",
    ]
    for idx, (stem, (title, caption)) in enumerate(FIGURE_CAPTIONS.items(), start=1):
        lines.extend(
            [
                f"## Figure {idx}: {title}",
                "",
                caption,
                "",
                f"- PDF: `paper_draft/figures/{stem}.pdf`",
                f"- PNG: `paper_draft/figures/{stem}.png`",
                "",
            ]
        )
    FIGURE_INDEX.parent.mkdir(parents=True, exist_ok=True)
    FIGURE_INDEX.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    _set_style()
    build_recommendation_map()
    build_observation_search_impact()
    build_discovery_ablation_matrix()
    build_paired_rolling_forest()
    build_numerical_failure_audit()
    write_figure_index()
    print(f"Wrote figures to {FIGURE_DIR.relative_to(REPO_ROOT)}")
    print(f"Wrote figure index to {FIGURE_INDEX.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
