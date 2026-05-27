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


def _finalize_plot(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()


def _series_order(summary: pd.DataFrame) -> list[str]:
    series = summary["series_name"].drop_duplicates().tolist()
    ordered = [name for name in ["Overall", "0-4 yr", "5-17 yr", "18-49 yr", "50-64 yr", ">= 65 yr"] if name in series]
    return ordered + [name for name in series if name not in ordered]


def plot_metric_heatmap(
    summary: pd.DataFrame,
    metric_column: str,
    title: str,
    path: Path,
) -> None:
    """Plot a model-by-series heatmap for one summary metric."""
    ordered_series = _series_order(summary)
    pivot = (
        summary.pivot(index="series_name", columns="model_name", values=metric_column)
        .reindex(index=ordered_series, columns=MODEL_ORDER)
    )
    values = pivot.to_numpy(dtype=float)

    plt.figure(figsize=(10, max(3.5, 0.7 * len(ordered_series))))
    image = plt.imshow(values, aspect="auto", cmap="YlGnBu_r")
    plt.colorbar(image, label=metric_column)
    plt.xticks(np.arange(len(MODEL_ORDER)), MODEL_ORDER, rotation=20)
    plt.yticks(np.arange(len(ordered_series)), ordered_series)
    plt.title(title)

    for row_idx, series_name in enumerate(ordered_series):
        for col_idx, model_name in enumerate(MODEL_ORDER):
            value = pivot.loc[series_name, model_name]
            if pd.notna(value):
                plt.text(col_idx, row_idx, f"{value:.3f}", ha="center", va="center", color="black", fontsize=9)

    _finalize_plot(path)


def plot_metric_bars(
    summary: pd.DataFrame,
    metric_column: str,
    title: str,
    path: Path,
) -> None:
    """Plot grouped bars by series for one benchmark metric."""
    ordered_series = _series_order(summary)
    n_models = len(MODEL_ORDER)
    width = min(0.8 / max(n_models, 1), 0.18)
    x_positions = np.arange(len(ordered_series), dtype=float)
    colors = {
        "deterministic_seir": "#005f73",
        "probabilistic_seir": "#0a9396",
        "hospitalized_seihr": "#2a9d8f",
        "delayed_observation_seir": "#7f5539",
        "fractional_seir": "#94d2bd",
        "constrained_structure_discovery": "#ca6702",
    }

    plt.figure(figsize=(12, 5.5))
    for idx, model_name in enumerate(MODEL_ORDER):
        subset = summary.loc[summary["model_name"] == model_name].set_index("series_name")
        metric_map = subset[metric_column].to_dict()
        values = [metric_map.get(series_name, np.nan) for series_name in ordered_series]
        plt.bar(
            x_positions + (idx - (n_models - 1) / 2) * width,
            values,
            width=width,
            label=model_name,
            color=colors[model_name],
        )

    plt.xticks(x_positions, ordered_series, rotation=20)
    plt.ylabel(metric_column)
    plt.title(title)
    plt.legend()
    _finalize_plot(path)
