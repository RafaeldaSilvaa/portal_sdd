import uuid
from datetime import datetime
from datetime import timezone as tz

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped

from ..db.base import Base


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    correlation_id: Mapped[str] = Column(
        String(64), unique=True, nullable=False, default=lambda: f"tx-{uuid.uuid4().hex[:18]}"
    )
    current_state: Mapped[str] = Column(String(32), default="INIT")
    current_gate: Mapped[int] = Column(Integer, default=1)
    spec_json: Mapped[str | None] = Column(Text, nullable=True)
    sdd_text: Mapped[str | None] = Column(Text, nullable=True)
    test_suite: Mapped[str | None] = Column(Text, nullable=True)
    code_artifacts: Mapped[str | None] = Column(Text, nullable=True)
    failure_reason: Mapped[str | None] = Column(Text, nullable=True)
    mutation_score: Mapped[float | None] = Column(Float, nullable=True)
    coverage_percent: Mapped[float | None] = Column(Float, nullable=True)
    is_converged: Mapped[bool] = Column(Boolean, default=False)
    is_cancelled: Mapped[bool] = Column(Boolean, default=False)
    interaction_pending: Mapped[str | None] = Column(Text, nullable=True)
    created_at: Mapped[datetime] = Column(DateTime, default=lambda: datetime.now(tz.utc))
    updated_at: Mapped[datetime] = Column(DateTime, default=lambda: datetime.now(tz.utc), onupdate=lambda: datetime.now(tz.utc))


class PipelineLog(Base):
    __tablename__ = "pipeline_logs"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    correlation_id: Mapped[str] = Column(String(64), nullable=False, index=True)
    message: Mapped[str] = Column(Text, nullable=False)
    level: Mapped[str] = Column(String(16), default="info")
    gate: Mapped[str] = Column(String(32), default="")
    created_at: Mapped[datetime] = Column(DateTime, default=lambda: datetime.now(tz.utc))


class ProbingQuestion(Base):
    __tablename__ = "probing_questions"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = Column(Integer, nullable=False)
    question_id: Mapped[str] = Column(String(32), nullable=False)
    context: Mapped[str] = Column(Text, nullable=False)
    question_text: Mapped[str] = Column(Text, nullable=False)
    answer: Mapped[str | None] = Column(Text, nullable=True)
    created_at: Mapped[datetime] = Column(DateTime, default=lambda: datetime.now(tz.utc))
    answered_at: Mapped[datetime | None] = Column(DateTime, nullable=True)


class TelemetryRecord(Base):
    __tablename__ = "telemetry_records"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = Column(Integer, nullable=False)
    trace_id: Mapped[str] = Column(String(64), nullable=False)
    pipeline_gate: Mapped[str] = Column(String(32), nullable=False)
    metrics_json: Mapped[str] = Column(Text, nullable=True)
    inference_json: Mapped[str | None] = Column(Text, nullable=True)
    mutation_json: Mapped[str | None] = Column(Text, nullable=True)
    created_at: Mapped[datetime] = Column(DateTime, default=lambda: datetime.now(tz.utc))
