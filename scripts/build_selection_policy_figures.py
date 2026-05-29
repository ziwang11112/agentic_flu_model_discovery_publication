from __future__ import annotations

import argparse
import sys
from pathlib import Path

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


def _save(fig: plt.Figure, stem: str) -> None:
    out = REPO_ROOT / "paper_draft" / "figures"
    out.mkdir(parents=True, exist_ok=True)
    for suffix in ("pdf", "png"):
        fig.savefig(out / f"{stem}.{suffix}", dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_policy_audit_figure(artifact_root: Path) -> None:
    audit = pd.read_csv(artifact_root / "claim_audit_scores.csv")
    bool_rows = audit.loc[audit["value"].astype(str).isin(["True", "False"])].copy()
    bool_rows["score"] = bool_rows["value"].map({"True": 1, "False": 0})
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    y = range(len(bool_rows))
    colors = ["#0072B2" if value else "#D55E00" for value in bool_rows["score"]]
    ax.barh(y, bool_rows["score"], color=colors)
    ax.set_yticks(list(y), bool_rows["audit_label"].astype(str))
    ax.invert_yaxis()
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Audit label present")
    ax.set_title("Offline claim-boundary audit", weight="semibold")
    ax.spines[["top", "right"]].set_visible(False)
    _save(fig, "fig_selection_policy_audit")


def build_toy_recovery_figure(artifact_root: Path) -> None:
    toy = pd.read_csv(artifact_root / "toy_observation_recovery_summary.csv")
    rates = toy.groupby("scenario_name")["recovered"].mean().sort_index()
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.bar(range(len(rates)), rates.to_numpy(), color="#009E73", edgecolor="#222222", linewidth=0.6)
    ax.set_xticks(range(len(rates)), rates.index, rotation=15, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Recovery rate")
    ax.set_title("Toy observation-label recovery", weight="semibold")
    ax.spines[["top", "right"]].set_visible(False)
    _save(fig, "fig_toy_observation_recovery")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build selection-policy figures from compact artifacts.")
    parser.add_argument("--artifact-root", default="artifacts_selection_policy_eval_compact")
    args = parser.parse_args()
    artifact_root = _artifact_path(args.artifact_root)
    build_policy_audit_figure(artifact_root)
    build_toy_recovery_figure(artifact_root)
    print("Wrote selection-policy figures to paper_draft/figures")


if __name__ == "__main__":
    main()

