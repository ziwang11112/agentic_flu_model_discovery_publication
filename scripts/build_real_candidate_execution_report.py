from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.selection.real_candidate_execution import build_real_candidate_execution_figures  # noqa: E402


def _repo_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _read_csv(root: Path, name: str) -> pd.DataFrame:
    path = root / name
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _markdown_table(frame: pd.DataFrame, max_rows: int = 24) -> str:
    if frame.empty:
        return "_No rows._"
    shown = frame.head(max_rows).copy()
    for column in shown.select_dtypes(include=["float"]).columns:
        shown[column] = shown[column].map(lambda value: "" if pd.isna(value) else f"{float(value):.4f}")
    columns = [str(column) for column in shown.columns]
    rows = []
    for _, row in shown.iterrows():
        rows.append(["" if pd.isna(value) else str(value) for value in row.tolist()])
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = ["| " + " | ".join(value.replace("\n", " ") for value in row) + " |" for row in rows]
    text = "\n".join([header, separator, *body])
    if len(frame) > max_rows:
        text += f"\n\n_Showing {max_rows} of {len(frame)} rows._"
    return text


def build_report(artifact_root: Path, report_path: Path, write_figures: bool = True) -> list[Path]:
    status = json.loads((artifact_root / "run_summary.json").read_text(encoding="utf-8"))
    replay_summary = _read_csv(artifact_root, "real_api_replay_repeated_summary.csv")
    replay_by_run = _read_csv(artifact_root, "real_api_replay_repeated_by_run.csv")
    bounded_summary = _read_csv(artifact_root, "bounded_real_execution_summary.csv")
    bounded = _read_csv(artifact_root, "bounded_real_execution_by_series_budget.csv")
    selected = _read_csv(artifact_root, "selected_models_by_proposer_budget.csv")
    audit = _read_csv(artifact_root, "no_leakage_audit.csv")

    figures: list[Path] = []
    if write_figures:
        figures = build_real_candidate_execution_figures(artifact_root, REPO_ROOT / "paper_draft" / "figures")

    safe_prompt = bool(audit["safe_prompt_passed"].all()) if not audit.empty else True
    safe_selection = bool(audit["safe_selection_passed"].all()) if not audit.empty else True
    lines = [
        "# Bounded Real Candidate Execution Evaluation",
        "",
        "This Stage 7 report summarizes verifier-gated proposal ordering and bounded candidate execution.",
        "It supports candidate-budget-efficiency claims only. It is not a FluSight leaderboard, SOTA,",
        "autonomous-science, mechanism-discovery, or operational forecasting-performance result.",
        "",
        "## Scope",
        "",
        f"- External API used: {status.get('external_api_used')}.",
        f"- API statuses: {status.get('api_statuses')}.",
        f"- Unique real-data model executions: {status.get('unique_model_executions')}.",
        f"- Frozen replay rows: {status.get('replay_rows')}.",
        f"- Bounded execution rows: {status.get('bounded_execution_rows')}.",
        f"- No-leakage audit rows: {status.get('audit_rows')}.",
        f"- Prompt audit passed: {safe_prompt}.",
        f"- Selection audit passed: {safe_selection}.",
        f"- Temporary artifacts removed: {status.get('temp_artifacts_removed')}.",
        f"- Test metric usage: {status.get('test_metric_usage')}.",
        "",
        "## Real API Repeated Frozen Replay",
        "",
        _markdown_table(replay_summary),
        "",
        "## Bounded Real-Data Execution",
        "",
        _markdown_table(bounded_summary),
        "",
        "## Selected Models By Proposer/Budget",
        "",
        _markdown_table(selected, max_rows=36),
        "",
        "## Replay By Run",
        "",
        _markdown_table(replay_by_run, max_rows=36),
        "",
        "## No-Leakage Audit",
        "",
        _markdown_table(audit, max_rows=36),
        "",
        "## Figures",
        "",
    ]
    if figures:
        lines.extend([f"- `{path.relative_to(REPO_ROOT)}`" for path in figures])
    else:
        lines.append("- No figures written.")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "- API output, when enabled, is JSON-only, allowlisted, and verifier-gated.",
            "- The real-data layer executes only deterministic repository code.",
            "- Held-out test MAE is post-selection descriptive only.",
            "- Frozen discovery-ablation artifacts are read-only inputs and are not modified.",
            "- Per-model temporary artifacts are removed before committing compact outputs.",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return figures


def main() -> None:
    parser = argparse.ArgumentParser(description="Build bounded real candidate execution report.")
    parser.add_argument("--artifact-root", default="artifacts_real_candidate_execution_compact")
    parser.add_argument("--report-path", default="reports/bounded_real_candidate_execution_report.md")
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args()
    artifact_root = _repo_path(args.artifact_root)
    report_path = _repo_path(args.report_path)
    figures = build_report(artifact_root, report_path, write_figures=not args.no_figures)
    print(f"Wrote {report_path}")
    for figure in figures:
        print(f"Wrote {figure}")


if __name__ == "__main__":
    main()
