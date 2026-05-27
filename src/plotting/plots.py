from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.data.split import ChronologicalSplit
from src.discovery.rules import StructureSpec, structure_template


def _finalize_plot(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()


def plot_full_series_fit(
    t: np.ndarray,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    split: ChronologicalSplit,
    title: str,
    path: Path,
) -> None:
    plt.figure(figsize=(12, 5))
    plt.plot(t, y_true, label="Observed", color="#1b4965", linewidth=2.0)
    plt.plot(t, y_pred, label="Fitted", color="#ca6702", linewidth=2.0)
    plt.axvline(split.train_end - 0.5, color="#6c757d", linestyle="--", linewidth=1.0)
    plt.axvline(split.val_end - 0.5, color="#6c757d", linestyle="--", linewidth=1.0)
    plt.title(title)
    plt.xlabel("Week index t")
    plt.ylabel("Weekly hospitalization rate")
    plt.legend()
    _finalize_plot(path)


def plot_residuals(
    t: np.ndarray,
    residuals: np.ndarray,
    title: str,
    path: Path,
) -> None:
    plt.figure(figsize=(12, 4))
    plt.axhline(0.0, color="#6c757d", linestyle="--", linewidth=1.0)
    plt.plot(t, residuals, color="#ae2012", linewidth=1.8)
    plt.title(title)
    plt.xlabel("Week index t")
    plt.ylabel("Residual")
    _finalize_plot(path)


def plot_rolling_forecasts(
    rolling_frame: pd.DataFrame,
    title: str,
    path: Path,
) -> None:
    horizons = sorted(rolling_frame["horizon"].unique())
    figure, axes = plt.subplots(len(horizons), 1, figsize=(12, 3.6 * len(horizons)), sharex=False)
    if len(horizons) == 1:
        axes = [axes]

    for axis, horizon in zip(axes, horizons):
        subset = rolling_frame.loc[rolling_frame["horizon"] == horizon].copy()
        axis.plot(subset["target_t"], subset["actual"], label="Observed", color="#1b4965", linewidth=2.0)
        axis.plot(subset["target_t"], subset["prediction"], label="Forecast", color="#ee9b00", linewidth=2.0)
        axis.set_title(f"{title} | horizon={horizon}")
        axis.set_xlabel("Forecast target week")
        axis.set_ylabel("Rate")
        axis.legend()

    _finalize_plot(path)


def plot_leaderboard(leaderboard: pd.DataFrame, path: Path) -> None:
    board = leaderboard.sort_values("score", ascending=True).copy()
    plt.figure(figsize=(12, max(4, 0.4 * len(board))))
    plt.barh(board["spec_key"], board["score"], color="#0a9396")
    plt.xlabel("Validation score")
    plt.ylabel("Candidate")
    plt.title("Discovery Leaderboard")
    _finalize_plot(path)


def plot_model_comparison(summary: pd.DataFrame, path: Path) -> None:
    figure = plt.figure(figsize=(10, 5))
    color_map = {
        "deterministic_seir": "#005f73",
        "probabilistic_seir": "#0a9396",
        "hospitalized_seihr": "#2a9d8f",
        "delayed_observation_seir": "#7f5539",
        "fractional_seir": "#94d2bd",
        "constrained_structure_discovery": "#ca6702",
    }
    colors = [color_map.get(model_name, "#6c757d") for model_name in summary["model_name"]]
    plt.bar(summary["model_name"], summary["test_mae"], color=colors)
    plt.ylabel("Test MAE")
    plt.title("Manual Baselines vs. Discovered Model")
    plt.xticks(rotation=15)
    _finalize_plot(path)


def plot_structure_diagram(spec: StructureSpec, path: Path) -> None:
    template = structure_template(spec)
    positions: dict[str, tuple[float, float]]
    if spec.structure_name == "SEIAR":
        positions = {"S": (0, 0), "E": (1, 0), "I": (2, 0.7), "A": (2, -0.7), "R": (3.2, 0)}
    elif spec.structure_name == "SEIHR":
        positions = {"S": (0, 0), "E": (1, 0), "I": (2, 0), "H": (3, 0), "R": (4, 0)}
    else:
        positions = {name: (idx, 0.0) for idx, name in enumerate(template["compartments"])}

    plt.figure(figsize=(9, 3.5))
    for node, (x_coord, y_coord) in positions.items():
        circle = plt.Circle((x_coord, y_coord), 0.18, color="#ee9b00", alpha=0.9)
        plt.gca().add_patch(circle)
        plt.text(x_coord, y_coord, node, ha="center", va="center", fontsize=12, color="black")

    for source, target in template["edges"]:
        x0, y0 = positions[source]
        x1, y1 = positions[target]
        plt.annotate(
            "",
            xy=(x1, y1),
            xytext=(x0, y0),
            arrowprops={"arrowstyle": "->", "color": "#005f73", "linewidth": 2.0},
        )

    plt.axis("off")
    plt.title(
        f"Best discovered structure: {spec.structure_name} | "
        f"fractional={spec.fractional} | observation={spec.observation_map}"
        + (f" | delay={spec.delay_weeks}" if spec.observation_map == "delayed_I" else "")
    )
    _finalize_plot(path)


def plot_probabilistic_calibration(
    calibration_summary: dict[str, dict[str, float]],
    title: str,
    path: Path,
    raw_summary: dict[str, dict[str, float]] | None = None,
) -> None:
    if not calibration_summary:
        return

    levels = sorted(calibration_summary.keys(), key=int)
    nominal = [calibration_summary[level]["nominal_coverage"] for level in levels]
    empirical = [calibration_summary[level]["empirical_coverage"] for level in levels]
    widths = [calibration_summary[level]["average_interval_width"] for level in levels]
    x_positions = np.arange(len(levels))

    figure, axes = plt.subplots(1, 2, figsize=(11, 4))
    if raw_summary is None:
        width = 0.34
        axes[0].bar(x_positions - width / 2.0, nominal, width=width, color="#94d2bd", label="Nominal")
        axes[0].bar(x_positions + width / 2.0, empirical, width=width, color="#005f73", label="Empirical")
        axes[1].bar(x_positions, widths, color="#ee9b00")
    else:
        raw_empirical = [raw_summary[level]["empirical_coverage"] for level in levels]
        raw_widths = [raw_summary[level]["average_interval_width"] for level in levels]
        width = 0.24
        axes[0].bar(x_positions - width, nominal, width=width, color="#94d2bd", label="Nominal")
        axes[0].bar(x_positions, raw_empirical, width=width, color="#bb3e03", label="Raw")
        axes[0].bar(x_positions + width, empirical, width=width, color="#005f73", label="Calibrated")
        axes[1].bar(x_positions - width / 2.0, raw_widths, width=width, color="#ca6702", label="Raw")
        axes[1].bar(x_positions + width / 2.0, widths, width=width, color="#0a9396", label="Calibrated")

    axes[0].set_xticks(x_positions)
    axes[0].set_xticklabels([f"{level}%" for level in levels])
    axes[0].set_ylim(0.0, 1.05)
    axes[0].set_ylabel("Coverage")
    axes[0].set_title("Interval Coverage")
    axes[0].legend()

    axes[1].set_xticks(x_positions)
    axes[1].set_xticklabels([f"{level}%" for level in levels])
    axes[1].set_ylabel("Average interval width")
    axes[1].set_title("Interval Width")
    if raw_summary is not None:
        axes[1].legend()

    figure.suptitle(title)
    _finalize_plot(path)
