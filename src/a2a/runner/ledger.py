"""JSONL ledger: append-only, one line per dyad."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from a2a.runner.models import DyadRecord

log = structlog.get_logger(__name__)


class Ledger:
    """Append-only JSONL ledger for dyad records.

    Each line is a complete DyadRecord serialised as JSON.
    The ledger is flushed after every write so it survives interruptions.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        log.info("ledger_opened", path=str(path))

    def append(self, record: DyadRecord) -> None:
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.as_ledger_line(), default=_json_default) + "\n")
        log.debug("ledger_append", dyad_id=record.dyad_id, outcome=record.outcome)

    def read_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        records = []
        with self._path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        log.warning("ledger_corrupt_line", line=line[:80])
        return records

    def count(self) -> int:
        if not self._path.exists():
            return 0
        with self._path.open(encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())


def _json_default(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serialisable")
