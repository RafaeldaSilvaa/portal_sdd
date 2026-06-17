"""Gate 3: Structural Architecture Blueprint (Architect Agent)."""

from __future__ import annotations

from ..agents.architect_agent import ArchitectAgent
from ..core.types import PipelineContext, PipelineGateID, PipelineState
from .base import PipelineGate


class ArchitectureGate(PipelineGate):
    def __init__(self, agent: ArchitectAgent | None = None):
        self._agent = agent or ArchitectAgent()

    @property
    def gate_id(self) -> PipelineGateID:
        return PipelineGateID.ARCHITECTURE

    @property
    def name(self) -> str:
        return "Structural Architecture Blueprint"

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        if not ctx.spec:
            ctx.failure_reason = "No spec available for architecture generation"
            ctx.current_state = PipelineState.FAILED
            return ctx

        sdd = await self._agent.generate_sdd(ctx.spec)
        ctx.sdd = sdd
        ctx.current_state = PipelineState.DESIGN
        ctx.current_gate = self.gate_id
        ctx.telemetry.pipeline_gate = self.name
        return ctx
