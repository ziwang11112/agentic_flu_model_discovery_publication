from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.selection.orchestrator import run_offline_selection_evaluation  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deterministic offline selection-policy evaluation.")
    parser.add_argument("--config", default="configs/selection_policy_smoke.yaml")
    args = parser.parse_args()
    config_path = REPO_ROOT / args.config
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    summary = run_offline_selection_evaluation(config, REPO_ROOT)
    print(f"Wrote compact selection-policy artifacts to {summary['artifact_root']}")
    print(f"Verified candidates: {summary['verified_candidate_count']} / {summary['candidate_count']}")
    print(f"Toy observation recovery rate: {summary['toy_recovery_rate']:.3f}")


if __name__ == "__main__":
    main()

