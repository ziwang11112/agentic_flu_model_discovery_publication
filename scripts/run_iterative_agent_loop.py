from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.selection.iterative_agent_loop import run_iterative_agent_loop  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run verifier-gated iterative agent loop replay evaluation.")
    parser.add_argument("--config", default="configs/iterative_agent_loop_smoke.yaml")
    args = parser.parse_args()
    config = yaml.safe_load((REPO_ROOT / args.config).read_text(encoding="utf-8"))
    status = run_iterative_agent_loop(config, REPO_ROOT)
    print(f"Wrote iterative agent loop artifacts to {status['artifact_root']}")
    print(f"external_api_used={status['external_api_used']}")
    print(f"safe_audit_passed={status['safe_audit_passed']}")
    print(f"claim_audit_passed={status['claim_audit_passed']}")


if __name__ == "__main__":
    main()
