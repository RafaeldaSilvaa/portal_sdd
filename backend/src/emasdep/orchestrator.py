"""Pipeline Orchestrator: state-machine hypervisor driving all 7 gates."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .core.state_machine import StateMachine
from .core.types import (
    PipelineContext,
    PipelineGateID,
    PipelineState,
)
from .gates.gate_01_spec import SpecGate
from .gates.gate_02_probing import ProbingGate
from .gates.gate_03_arch import ArchitectureGate
from .gates.gate_45_risk import RiskAnalysisGate
from .gates.gate_04_planner import PlannerGate
from .gates.gate_05_qa import QAGate
from .gates.gate_06_engineer import EngineerGate
from .gates.gate_07_conv import ConvergenceGate
from .telemetry.tracer import PipelineTracer
from .telemetry.metrics import MetricsCollector

logger = logging.getLogger("emasdep.orchestrator")


@dataclass
class OrchestrationResult:
    success: bool
    correlation_id: str
    final_state: str
    gates_executed: list[str] = field(default_factory=list)
    telemetry_data: dict | None = None
    error: str = ""


class PipelineOrchestrator:
    def __init__(self, config: dict | None = None) -> None:
        """  init  .

Args:
    config: Descrição do parâmetro config.

Retorna:
    Descrição do valor retornado."""
        self._state = StateMachine()
        self._config = config or {}
        self._tracer = PipelineTracer()
        self._metrics = MetricsCollector()

        self._gates = {
            PipelineGateID.SPEC: SpecGate(),
            PipelineGateID.PROBING: ProbingGate(),
            PipelineGateID.ARCHITECTURE: ArchitectureGate(),
            PipelineGateID.RISK_ANALYSIS: RiskAnalysisGate(),
            PipelineGateID.PLANNER: PlannerGate(),
            PipelineGateID.QA: QAGate(),
            PipelineGateID.ENGINEER: EngineerGate(),
            PipelineGateID.CONVERGENCE: ConvergenceGate(),
        }

    async def run_full_pipeline(self, raw_intent: str) -> OrchestrationResult:
        """run full pipeline.

Args:
    raw_intent: Descrição do parâmetro raw_intent.

Retorna:
    Descrição do valor retornado."""
        ctx = PipelineContext()

        try:
            ctx = await self._gates[PipelineGateID.SPEC].process(ctx)
            ctx = await self._gates[PipelineGateID.PROBING].process(ctx)

            if ctx.current_state == PipelineState.BLOCKED_PROBE:
                return OrchestrationResult(
                    success=False,
                    correlation_id=ctx.correlation_id,
                    final_state=ctx.current_state.name,
                    gates_executed=["SPEC", "PROBING"],
                    error="Pipeline blocked: awaiting human clarification",
                )

            ctx = await self._gates[PipelineGateID.ARCHITECTURE].process(ctx)
            ctx = await self._gates[PipelineGateID.RISK_ANALYSIS].process(ctx)
            ctx = await self._gates[PipelineGateID.PLANNER].process(ctx)
            ctx = await self._gates[PipelineGateID.QA].process(ctx)
            ctx = await self._gates[PipelineGateID.ENGINEER].process(ctx)
            ctx = await self._gates[PipelineGateID.CONVERGENCE].process(ctx)

            success = ctx.current_state == PipelineState.CONVERGED

            self._tracer.trace_event(
                trace_id=ctx.telemetry.trace_id,
                pipeline_gate="FULL_PIPELINE",
                metrics={"converged": success, "version": ctx.version},
            )

            return OrchestrationResult(
                success=success,
                correlation_id=ctx.correlation_id,
                final_state=ctx.current_state.name,
                gates_executed=[
                    "SPEC", "PROBING", "ARCHITECTURE",
                    "PLANNER", "QA", "ENGINEER", "CONVERGENCE",
                ],
                telemetry_data={
                    "trace_id": ctx.telemetry.trace_id,
                    "mutation_score": (
                        ctx.validation.mutation.mutation_score
                        if ctx.validation and ctx.validation.mutation
                        else None
                    ),
                    "coverage": (
                        ctx.validation.coverage_percent
                        if ctx.validation
                        else None
                    ),
                },
                error=ctx.failure_reason if not success else "",
            )

        except Exception as exc:
            logger.exception("Pipeline orchestration failed")
            return OrchestrationResult(
                success=False,
                correlation_id=ctx.correlation_id,
                final_state="FAILED",
                error=str(exc),
            )

    async def run_gate(
        self, ctx: PipelineContext, gate_id: PipelineGateID
    ) -> PipelineContext:
        """executa um gate específico no pipeline."""
        gate = self._gates.get(gate_id)
        if not gate:
            logger.error("Unknown gate: %s", gate_id)
            return ctx

        logger.info("Executing gate %d: %s", gate_id.value, gate.name)
        ctx = await gate.process(ctx)

        self._tracer.trace_event(
            trace_id=ctx.telemetry.trace_id,
            pipeline_gate=gate.name,
            metrics={"state": ctx.current_state.name, "version": ctx.version},
        )

        return ctx
