from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.selection.iterative_agent_loop import build_iterative_agent_loop_figures  # noqa: E402


def _repo_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _read_csv(root: Path, name: str) -> pd.DataFrame:
    path = root / name
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _markdown_table(frame: pd.DataFrame, max_rows: int = 28) -> str:
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
    summary = _read_csv(artifact_root, "iterative_agent_summary.csv")
    by_round = _read_csv(artifact_root, "iterative_agent_by_round.csv")
    replay = _read_csv(artifact_root, "iterative_agent_replay_by_round.csv")
    audit = _read_csv(artifact_root, "iterative_agent_prompt_audit.csv")
    claim = _read_csv(artifact_root, "iterative_agent_claim_audit.csv")

    figures: list[Path] = []
    if write_figures:
        figures = build_iterative_agent_loop_figures(artifact_root, REPO_ROOT / "paper_draft" / "figures")

    lines = [
        "# Verifier-Gated Iterative Agent Loop Evaluation",
        "",
        "This Stage 8 report evaluates a constrained multi-round structured proposer loop.",
        "It uses verifier feedback and non-final replay evidence between rounds. It supports",
        "proposal/refinement and candidate-budget-efficiency claims only, not forecasting SOTA,",
        "autonomous-science, real-world mechanism-recovery, or operational forecasting claims.",
        "",
        "## Scope",
        "",
        f"- Series: {status.get('series')}.",
        f"- Rounds: {status.get('rounds')}.",
        f"- Candidates per round: {status.get('candidates_per_round')}.",
        f"- Budgets: {status.get('budgets')}.",
        f"- Replay only: {status.get('replay_only')}.",
        f"- External API used: {status.get('external_api_used')}.",
        f"- API statuses: {status.get('api_statuses')}.",
        f"- Prompt/feedback/selection audit passed: {status.get('safe_audit_passed')}.",
        f"- Claim audit passed: {status.get('claim_audit_passed')}.",
        f"- Test metric usage: {status.get('test_metric_usage')}.",
        "",
        "## Final Summary",
        "",
        _markdown_table(summary),
        "",
        "## Round Progress",
        "",
        _markdown_table(by_round),
        "",
        "## Replay By Budget",
        "",
        _markdown_table(replay),
        "",
        "## No-Leakage Audit",
        "",
        _markdown_table(audit, max_rows=36),
        "",
        "## Claim Audit",
        "",
        _markdown_table(claim),
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
            "- The agent loop proposes structured candidates only.",
            "- API output, when enabled, is JSON-only, allowlisted, and verifier-checked.",
            "- The committed evaluation uses frozen replay by default and does not refit real-data models.",
            "- Final split metrics are post-selection descriptive only.",
            "- The result is evidence about proposal refinement and candidate-budget efficiency.",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return figures


def main() -> None:
    parser = argparse.ArgumentParser(description="Build iterative agent loop report.")
    parser.add_argument("--artifact-root", default="artifacts_iterative_agent_loop_compact")
    parser.add_argument("--report-path", default="reports/iterative_agent_loop_report.md")
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
