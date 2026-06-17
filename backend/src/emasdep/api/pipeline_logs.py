"""In-memory pipeline event log store."""

from datetime import datetime, timezone
from typing import Any


_logs: dict[str, list[dict[str, Any]]] = {}


def add_log(correlation_id: str, message: str, level: str = "info", gate: str = ""):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": message,
        "level": level,
        "gate": gate,
    }
    if correlation_id not in _logs:
        _logs[correlation_id] = []
    _logs[correlation_id].append(entry)


def get_logs(correlation_id: str, since: str | None = None) -> list[dict[str, Any]]:
    entries = _logs.get(correlation_id, [])
    if since:
        entries = [e for e in entries if e["timestamp"] > since]
    return entries


def clear_logs(correlation_id: str):
    _logs.pop(correlation_id, None)
