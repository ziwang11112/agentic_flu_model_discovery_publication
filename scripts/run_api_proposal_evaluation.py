from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.selection.api_runner import run_api_proposal_evaluation  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run optional API-assisted structured proposal evaluation.")
    parser.add_argument("--config", default="configs/api_proposal_smoke.yaml")
    args = parser.parse_args()
    config_path = REPO_ROOT / args.config
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    status = run_api_proposal_evaluation(config, REPO_ROOT)
    print(f"API proposal evaluation status: {status['api_run_status']}")
    if status.get("skip_reason"):
        print(f"Skip reason: {status['skip_reason']}")
    print(f"Artifact root: {status['artifact_root']}")


if __name__ == "__main__":
    main()
