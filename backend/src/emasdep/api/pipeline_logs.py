"""Pipeline event log store with optional DB persistence."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from .models.pipeline import PipelineLog


_logs: dict[str, list[dict[str, Any]]] = {}


def add_log(
    correlation_id: str,
    message: str,
    level: str = "info",
    gate: str = "",
    db: Session | None = None,
) -> None:
    """add log entry to memory and optionally to DB."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": message,
        "level": level,
        "gate": gate,
    }
    if correlation_id not in _logs:
        _logs[correlation_id] = []
    _logs[correlation_id].append(entry)

    if db is not None:
        try:
            db.add(PipelineLog(
                correlation_id=correlation_id,
                message=message,
                level=level,
                gate=gate,
            ))
            db.commit()
        except Exception:
            db.rollback()


def get_logs(
    correlation_id: str,
    since: str | None = None,
    db: Session | None = None,
) -> list[dict[str, Any]]:
    """get logs from memory, falling back to DB if memory is empty."""
    entries = _logs.get(correlation_id, [])

    if not entries and db is not None:
        query = db.query(PipelineLog).filter_by(correlation_id=correlation_id)
        if since:
            try:
                since_dt = datetime.fromisoformat(since)
                query = query.filter(PipelineLog.created_at > since_dt)
            except ValueError:
                pass
        rows = query.order_by(PipelineLog.id).all()
        entries = [
            {
                "timestamp": r.created_at.isoformat(),
                "message": r.message,
                "level": r.level,
                "gate": r.gate,
            }
            for r in rows
        ]
        _logs[correlation_id] = entries

    if since:
        entries = [e for e in entries if e["timestamp"] > since]
    return entries


def persist_logs_to_db(correlation_id: str, db: Session) -> None:
    """flush all in-memory logs for a correlation_id to DB."""
    entries = _logs.get(correlation_id, [])
    if not entries:
        return
    existing = set()
    for row in db.query(PipelineLog).filter_by(correlation_id=correlation_id).all():
        existing.add((row.message, row.level, row.gate))
    for e in entries:
        key = (e["message"], e["level"], e["gate"])
        if key not in existing:
            db.add(PipelineLog(
                correlation_id=correlation_id,
                message=e["message"],
                level=e["level"],
                gate=e["gate"],
            ))
            existing.add(key)
    try:
        db.commit()
    except Exception:
        db.rollback()


def clear_logs(correlation_id: str) -> None:
    _logs.pop(correlation_id, None)
