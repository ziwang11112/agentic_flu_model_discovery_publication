from __future__ import annotations

from pathlib import Path


def repo_relative_path(path: Path, repo_root: Path) -> str:
    """Return a repo-relative path when possible, preserving external paths."""
    resolved = Path(path).resolve()
    root = Path(repo_root).resolve()
    try:
        return str(resolved.relative_to(root))
    except ValueError:
        return str(path)
