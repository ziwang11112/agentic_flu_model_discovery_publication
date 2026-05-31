from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.selection.provider_iterative_benchmark import build_provider_iterative_figures  # noqa: E402


def _repo_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _read_csv(root: Path, name: str) -> pd.DataFrame:
    path = root / name
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _markdown_table(frame: pd.DataFrame, max_rows: int = 30) -> str:
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
    provider_status = _read_csv(artifact_root, "provider_status.csv")
    validity = _read_csv(artifact_root, "provider_proposal_validity.csv")
    replay = _read_csv(artifact_root, "provider_replay_by_budget.csv")
    stability = _read_csv(artifact_root, "provider_stability_by_repeat.csv")
    audit = _read_csv(artifact_root, "provider_prompt_audit.csv")
    latency = _read_csv(artifact_root, "provider_cost_latency.csv")
    union_summary = _read_csv(artifact_root, "provider_union_execution_summary.csv")

    figures: list[Path] = []
    if write_figures:
        figures = build_provider_iterative_figures(artifact_root, REPO_ROOT / "paper_draft" / "figures")

    sufficient = bool(status.get("sufficient_real_providers_for_cross_provider_evidence"))
    lines = [
        "# Cross-Provider Iterative Proposer Benchmark",
        "",
        "This Stage 9 report evaluates provider backends only as constrained structured candidate proposers.",
        "All provider outputs are JSON/schema parsed, allowlisted, verifier-checked, and audited before replay.",
        "The benchmark is not a forecasting-performance benchmark, FluSight leaderboard, clinical benchmark,",
        "autonomous-science claim, or real-world mechanism-discovery claim.",
        "",
        "## Scope",
        "",
        f"- Series: {status.get('series')}.",
        f"- Repeats: {status.get('repeats')}.",
        f"- Rounds: {status.get('rounds')}.",
        f"- Candidates per round: {status.get('candidates_per_round')}.",
        f"- Budgets: {status.get('budgets')}.",
        f"- Real providers run: {status.get('real_provider_count')}.",
        f"- Required providers for cross-provider evidence: {status.get('require_min_real_providers')}.",
        f"- Sufficient for cross-provider comparison: {sufficient}.",
        f"- Prompt/no-leakage audit passed: {status.get('safe_audit_passed')}.",
        f"- Claim audit passed: {status.get('claim_audit_passed')}.",
        f"- Bounded union execution run: {status.get('bounded_execution_run')}.",
        "",
    ]
    if not sufficient:
        lines.extend(
            [
                "**Insufficient real provider availability for cross-provider evidence.**",
                "",
                "The generated artifacts should be treated as infrastructure/status outputs only, not as a",
                "cross-provider comparison result. Configure at least the required provider key/model env vars",
                "and rerun before using this report as evidence.",
                "",
            ]
        )
    lines.extend(
        [
            "## Provider Status",
            "",
            _markdown_table(provider_status),
            "",
            "## Proposal Validity And Diversity",
            "",
            _markdown_table(validity),
            "",
            "## Frozen Replay By Budget",
            "",
            _markdown_table(replay, max_rows=36),
            "",
            "## Stability By Repeat",
            "",
            _markdown_table(stability),
            "",
            "## Cost And Latency",
            "",
            _markdown_table(latency),
            "",
            "## No-Leakage Audit",
            "",
            _markdown_table(audit, max_rows=36),
            "",
            "## Provider-Union Bounded Execution",
            "",
            _markdown_table(union_summary),
            "",
            "## Figures",
            "",
        ]
    )
    if figures:
        lines.extend([f"- `{path.relative_to(REPO_ROOT)}`" for path in figures])
    else:
        lines.append("- No figures written.")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "- Providers are interchangeable structured proposer backends.",
            "- No provider output generates or executes model code.",
            "- Held-out test metrics are excluded from prompts and selection evidence.",
            "- Frozen replay supports proposal ordering and budget-efficiency evidence only.",
            "- Provider-union bounded execution, when enabled, remains bounded and does not imply SOTA.",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(line.rstrip() for line in lines) + "\n")
    return figures


def main() -> None:
    parser = argparse.ArgumentParser(description="Build cross-provider iterative proposer benchmark report.")
    parser.add_argument("--artifact-root", default="artifacts_provider_iterative_benchmark_compact")
    parser.add_argument("--report-path", default="reports/provider_iterative_benchmark_report.md")
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args()
    figures = build_report(_repo_path(args.artifact_root), _repo_path(args.report_path), write_figures=not args.no_figures)
    print(f"Wrote {_repo_path(args.report_path)}")
    for figure in figures:
        print(f"Wrote {figure}")


if __name__ == "__main__":
    main()
