"""Structured tracing for AgentOps auditability."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from datetime import timezone as tz
from pathlib import Path
from typing import Any

logger = logging.getLogger("emasdep.telemetry")


class PipelineTracer:
    def __init__(self, output_path: str = "./.emasdep_traces") -> None:
        """  init  .

Args:
    output_path: Descrição do parâmetro output_path.

Retorna:
    Descrição do valor retornado."""
        self._path = Path(output_path)
        self._path.mkdir(parents=True, exist_ok=True)

    def trace_event(
        self,
        trace_id: str,
        pipeline_gate: str,
        metrics: dict[str, Any] | None = None,
        inference: dict[str, Any] | None = None,
        mutation: dict[str, Any] | None = None,
        checksums: dict[str, str] | None = None,
    ) -> str:
        event_id = uuid.uuid4().hex[:12]
        event = {
            "trace_id": trace_id,
            "event_id": event_id,
            "pipeline_gate": pipeline_gate,
            "timestamp": datetime.now(tz.utc).isoformat(),
            "metrics": metrics or {},
            "inference_analytics": inference or {},
            "mutation_integrity": mutation or {},
            "state_checksums": checksums or {},
        }

        event_path = self._path / f"{trace_id}_{event_id}.json"
        event_path.write_text(json.dumps(event, indent=2, default=str), encoding="utf-8")

        logger.info(
            "Trace event | gate=%s | trace=%s | event=%s",
            pipeline_gate, trace_id, event_id,
        )

        return event_id

    def get_trace_events(self, trace_id: str) -> list[dict]:
        """get trace events.

Args:
    trace_id: Descrição do parâmetro trace_id.

Retorna:
    Descrição do valor retornado."""
        events: list[dict] = []
        for f in sorted(self._path.glob(f"{trace_id}_*.json")):
            events.append(json.loads(f.read_text(encoding="utf-8")))
        return events

    def get_all_trace_ids(self) -> list[str]:
        """get all trace ids.

Retorna:
    Descrição do valor retornado."""
        trace_ids: set[str] = set()
        for f in self._path.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                trace_ids.add(data.get("trace_id", f.stem.split("_")[0]))
            except Exception:
                continue
        return sorted(trace_ids)
