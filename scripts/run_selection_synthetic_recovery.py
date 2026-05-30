from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.selection.structured_recovery import run_structured_recovery_from_config  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local synthetic structured recovery evaluation.")
    parser.add_argument("--config", default="configs/selection_synthetic_recovery_smoke.yaml")
    args = parser.parse_args()
    config_path = REPO_ROOT / args.config
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    summary = run_structured_recovery_from_config(config, REPO_ROOT)
    print(f"Wrote synthetic structured recovery artifacts to {summary['artifact_root']}")
    print(f"Rows: {summary['by_seed_rows']}")
    print(f"Valid proposal rate: {summary['valid_proposal_rate']:.3f}")
    print(f"Claim-safety violations: {summary['claim_safety_violation_count']}")


if __name__ == "__main__":
    main()
