"""Metrics collection for pipeline execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from datetime import timezone as tz
from typing import Any


@dataclass
class MetricPoint:
    name: str
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz.utc))


class MetricsCollector:
    def __init__(self):
        self._points: list[MetricPoint] = []

    def record(self, name: str, value: float, labels: dict[str, str] | None = None):
        self._points.append(
            MetricPoint(name=name, value=value, labels=labels or {})
        )

    def get_pipeline_metrics(
        self,
        latency_ms: int,
        token_cost: float,
        mutation_score: float,
        coverage: float,
    ) -> dict[str, Any]:
        return {
            "latency_duration_ms": latency_ms,
            "financial_token_cost_usd": round(token_cost, 6),
            "mutation_score": round(mutation_score, 4),
            "coverage_percent": round(coverage, 4),
        }

    def summarize(self) -> dict[str, float]:
        summary: dict[str, float] = {}
        for point in self._points:
            if point.name not in summary:
                summary[point.name] = 0.0
            summary[point.name] += point.value
        return summary

    def clear(self):
        self._points.clear()
