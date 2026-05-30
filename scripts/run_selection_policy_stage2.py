from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.selection.stage2 import run_selection_policy_stage2  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Stage 2 deterministic offline selection-policy validation.")
    parser.add_argument("--config", default="configs/selection_policy_smoke.yaml")
    args = parser.parse_args()
    config_path = REPO_ROOT / args.config
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    summary = run_selection_policy_stage2(config, REPO_ROOT)
    print(f"Wrote Stage 2 compact artifacts to {summary['artifact_root']}")
    print(f"Negative-set rejection rate: {summary['stage2_negative_rejection_rate']:.3f}")
    print(f"Budgeted replay rows: {summary['stage2_budgeted_replay_rows']}")
    print(f"Toy policy rows: {summary['stage2_toy_policy_rows']}")


if __name__ == "__main__":
    main()
