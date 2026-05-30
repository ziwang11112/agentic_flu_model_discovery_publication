from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _artifact_path(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def _markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int = 20) -> str:
    if frame.empty:
        return "_None._"
    shown = frame.loc[:, [column for column in columns if column in frame.columns]].head(max_rows)
    lines = [
        "| " + " | ".join(shown.columns.astype(str)) + " |",
        "| " + " | ".join(["---"] * len(shown.columns)) + " |",
    ]
    for _, row in shown.iterrows():
        values = []
        for value in row.tolist():
            if isinstance(value, float):
                values.append(f"{value:.4f}")
            else:
                values.append("" if pd.isna(value) else str(value))
        lines.append("| " + " | ".join(values) + " |")
    if len(frame) > max_rows:
        lines.append(f"\n_Showing {max_rows} of {len(frame)} rows._")
    return "\n".join(lines)


def build_report(artifact_root: Path, report_path: Path) -> None:
    status_path = artifact_root / "api_proposal_status.json"
    status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {"api_run_status": "missing"}
    metrics = pd.read_csv(artifact_root / "api_proposal_evaluation.csv") if (artifact_root / "api_proposal_evaluation.csv").exists() else pd.DataFrame()
    candidates = pd.read_csv(artifact_root / "api_proposal_candidates.csv") if (artifact_root / "api_proposal_candidates.csv").exists() else pd.DataFrame()
    lines = [
        "# API-Assisted Structured Proposal Evaluation",
        "",
        "This report summarizes an optional API-assisted structured candidate proposal check.",
        "The API layer is disabled or skipped when credentials are absent. API output is accepted only as JSON,",
        "restricted to an explicit allowlist, and passed through the same verifier before any use.",
        "It cannot create model code and does not run new forecasting experiments.",
        "",
        "## Status",
        "",
        f"- Status: `{status.get('api_run_status', 'missing')}`.",
        f"- External API used: `{status.get('external_api_used', False)}`.",
        f"- Skip reason: `{status.get('skip_reason', '')}`.",
        "",
        "## Metrics",
        "",
        _markdown_table(
            metrics,
            [
                "api_run_status",
                "proposal_count",
                "valid_proposal_count",
                "valid_proposal_rate",
                "duplicate_rate",
                "family_diversity",
                "observation_label_diversity",
                "top_epsilon_useful_rate",
            ],
        ),
        "",
        "## Verified Candidate Records",
        "",
        _markdown_table(
            candidates,
            [
                "candidate_id",
                "family",
                "model_name",
                "observation_label",
                "delay_label",
                "valid",
                "reasons",
                "top_epsilon_any_series",
            ],
            max_rows=24,
        ),
        "",
        "## Caveats",
        "",
        "- This is proposal-quality evaluation over frozen compact summaries, not a model performance experiment.",
        "- Tests use deterministic mock responses and do not require API credentials.",
        "- Any real API output is constrained by JSON parsing, allowlists, and verifier checks.",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build optional API proposal evaluation report.")
    parser.add_argument("--artifact-root", default="artifacts_selection_policy_eval_compact")
    parser.add_argument("--report-path", default="reports/api_proposal_evaluation.md")
    args = parser.parse_args()
    artifact_root = _artifact_path(args.artifact_root)
    report_path = _artifact_path(args.report_path)
    build_report(artifact_root, report_path)
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
