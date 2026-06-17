"""Gate 4: Deterministic Decomposition (Planner Agent)."""

from __future__ import annotations

from ..agents.planner_agent import PlannerAgent
from ..core.types import PipelineContext, PipelineGateID, PipelineState
from .base import PipelineGate


class PlannerGate(PipelineGate):
    def __init__(self, agent: PlannerAgent | None = None):
        self._agent = agent or PlannerAgent()

    @property
    def gate_id(self) -> PipelineGateID:
        return PipelineGateID.PLANNER

    @property
    def name(self) -> str:
        return "Deterministic Decomposition"

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        sdd = ctx.sdd or ""
        dag = await self._agent.build_dag(sdd, ctx.spec)
        ctx.task_dag = dag
        ctx.current_state = PipelineState.PLANNING
        ctx.current_gate = self.gate_id
        ctx.telemetry.pipeline_gate = self.name
        return ctx
