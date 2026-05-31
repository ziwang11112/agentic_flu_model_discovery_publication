from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.selection.provider_iterative_benchmark import run_provider_iterative_benchmark  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run cross-provider iterative proposer benchmark.")
    parser.add_argument("--config", default="configs/provider_iterative_benchmark_smoke.yaml")
    args = parser.parse_args()
    config = yaml.safe_load((REPO_ROOT / args.config).read_text(encoding="utf-8"))
    status = run_provider_iterative_benchmark(config, REPO_ROOT)
    print(f"Wrote provider benchmark artifacts to {status['artifact_root']}")
    print(f"real_provider_count={status['real_provider_count']}")
    print(f"sufficient_real_providers={status['sufficient_real_providers_for_cross_provider_evidence']}")
    print(f"safe_audit_passed={status['safe_audit_passed']}")


if __name__ == "__main__":
    main()
