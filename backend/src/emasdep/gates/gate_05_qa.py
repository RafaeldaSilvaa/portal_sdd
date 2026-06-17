"""Gate 5: Detached Test Invariance Generation (QA Agent)."""

from __future__ import annotations

from ..agents.qa_agent import QAAgent
from ..core.types import PipelineContext, PipelineGateID, PipelineState
from .base import PipelineGate


class QAGate(PipelineGate):
    def __init__(self, agent: QAAgent | None = None):
        self._agent = agent or QAAgent()

    @property
    def gate_id(self) -> PipelineGateID:
        return PipelineGateID.QA

    @property
    def name(self) -> str:
        return "Test Invariance Generation"

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        spec_dict = ctx.spec or {}
        sdd = ctx.sdd or ""
        test_suite = await self._agent.generate_tests(spec_dict, sdd)
        ctx.test_suite = test_suite
        ctx.current_state = PipelineState.TESTING
        ctx.current_gate = self.gate_id
        ctx.telemetry.pipeline_gate = self.name
        return ctx
