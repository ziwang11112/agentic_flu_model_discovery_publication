from __future__ import annotations

import json
from pathlib import Path

from src.selection.schema import TraceEvent


class TraceWriter:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: TraceEvent) -> None:
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")


def read_trace(path: Path) -> list[TraceEvent]:
    events: list[TraceEvent] = []
    if not path.exists():
        return events
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            data = json.loads(line)
            events.append(TraceEvent(**data))
    return events
