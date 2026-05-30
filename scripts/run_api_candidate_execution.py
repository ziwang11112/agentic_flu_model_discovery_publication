from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.selection.api_execution import run_api_candidate_execution  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run verifier-gated API/mock candidate execution and replay evaluation.")
    parser.add_argument("--config", default="configs/api_candidate_execution_smoke.yaml")
    args = parser.parse_args()
    config_path = REPO_ROOT / args.config
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    status = run_api_candidate_execution(config, REPO_ROOT)
    print(f"Wrote API candidate execution artifacts to {status['artifact_root']}")
    print(f"External API used: {status['external_api_used']}")
    print(f"Synthetic rows: {status['synthetic_rows']}")
    print(f"Real-data replay rows: {status['realdata_rows']}")
    print(f"Prompt audit passed: {status['safe_prompt_passed']}")


if __name__ == "__main__":
    main()
