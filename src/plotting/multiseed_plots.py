from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


MODEL_ORDER = [
    "deterministic_seir",
    "probabilistic_seir",
    "hospitalized_seihr",
    "delayed_observation_seir",
    "fractional_seir",
    "constrained_structure_discovery",
]

SERIES_ORDER = ["Overall", "0-4 yr", "5-17 yr", "18-49 yr", "50-64 yr", ">= 65 yr"]

MODEL_COLORS = {
    "deterministic_seir": "#005f73",
    "probabilistic_seir": "#0a9396",
    "hospitalized_seihr": "#2a9d8f",
    "delayed_observation_seir": "#7f5539",
    "fractional_seir": "#94d2bd",
    "constrained_structure_discovery": "#ca6702",
}


def _finalize_plot(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()


def _series_order(summary: pd.DataFrame) -> list[str]:
    observed = summary["series_name"].drop_duplicates().tolist()
    ordered = [name for name in SERIES_ORDER if name in observed]
    return ordered + [name for name in observed if name not in ordered]


def plot_multiseed_errorbars(
    summary: pd.DataFrame,
    mean_column: str,
    std_column: str,
    title: str,
    ylabel: str,
    path: Path,
) -> None:
    """Plot grouped error bars for multi-seed metric summaries."""
    ordered_series = _series_order(summary)
    ordered_models = [model for model in MODEL_ORDER if model in summary["model_name"].unique()]
    n_models = len(ordered_models)
    width = min(0.8 / max(n_models, 1), 0.16)
    x_positions = np.arange(len(ordered_series), dtype=float)

    plt.figure(figsize=(13, 6))
    for idx, model_name in enumerate(ordered_models):
        subset = summary.loc[summary["model_name"] == model_name].set_index("series_name")
        means = [float(subset.loc[series_name, mean_column]) for series_name in ordered_series]
        stds = [float(subset.loc[series_name, std_column]) for series_name in ordered_series]
        plt.bar(
            x_positions + (idx - (n_models - 1) / 2) * width,
            means,
            width=width,
            yerr=stds,
            capsize=3,
            label=model_name,
            color=MODEL_COLORS.get(model_name, "#666666"),
            alpha=0.9,
        )

    plt.xticks(x_positions, ordered_series, rotation=20)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend(ncols=2)
    _finalize_plot(path)
