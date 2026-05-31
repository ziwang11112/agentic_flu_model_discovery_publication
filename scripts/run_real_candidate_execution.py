from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.selection.real_candidate_execution import run_real_candidate_execution  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run bounded real candidate execution evaluation.")
    parser.add_argument("--config", default="configs/real_candidate_execution_smoke.yaml")
    args = parser.parse_args()
    with (REPO_ROOT / args.config).open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    status = run_real_candidate_execution(config, REPO_ROOT)
    print(f"Wrote bounded real candidate execution artifacts to {status['artifact_root']}")
    print(f"external_api_used={status['external_api_used']}")
    print(f"safe_audit_passed={status['safe_audit_passed']}")
    print(f"unique_model_executions={status['unique_model_executions']}")


if __name__ == "__main__":
    main()
