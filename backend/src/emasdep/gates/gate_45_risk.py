"""Gate 4.5: Risk & Trade-off Analysis between SDD and Planner."""

from __future__ import annotations

import json

from ..agents.base import LLMAgent, LLMConfig, LLMResponse
from ..core.types import (
    PipelineContext,
    PipelineGateID,
    PipelineState,
    RiskAnalysis,
    RiskItem,
    TradeOff,
)
from .base import PipelineGate


class RiskAnalysisGate(PipelineGate):
    def __init__(self, llm_config: LLMConfig | None = None):
        self._agent = _RiskAgent(config=llm_config)

    @property
    def gate_id(self) -> PipelineGateID:
        return PipelineGateID.RISK_ANALYSIS

    @property
    def name(self) -> str:
        return "Risk & Trade-off Analysis"

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        if not ctx.sdd:
            ctx.failure_reason = "No SDD available for risk analysis"
            ctx.current_state = PipelineState.FAILED
            return ctx

        risk = await self._agent.analyze(ctx.sdd, ctx.spec)
        ctx.risk_analysis = risk
        ctx.current_state = PipelineState.RISK_ANALYSIS
        ctx.current_gate = self.gate_id
        ctx.telemetry.pipeline_gate = self.name
        return ctx


class _RiskAgent(LLMAgent):
    def __init__(self, config: LLMConfig | None = None):
        super().__init__(config)

    def build_system_prompt(self) -> str:
        return (
            "You are a Risk & Trade-off Analyst. "
            "Analyze system design documents for risks, failure scenarios, "
            "cost-vs-performance trade-offs, and resilience gaps. "
            "Output ONLY valid JSON."
        )

    async def analyze(self, sdd: str, spec: dict | None) -> RiskAnalysis:
        prompt = (
            f"SDD:\n{sdd[:3000]}\n\n"
            f"Spec:\n{json.dumps(spec, indent=2)[:2000] if spec else 'N/A'}\n\n"
            "Generate a RiskAnalysis JSON with:\n"
            "- risks: list of {description, probability (0-1), impact (low|medium|high|critical), mitigation}\n"
            "- trade_offs: list of {decision, pros, cons, recommended}\n"
            "- overall_risk_score: 0-1\n"
            "- recommendations: list of strings\n"
            "Output ONLY valid JSON."
        )
        response: LLMResponse = await self.call(
            prompt=prompt,
            system_prompt=self.build_system_prompt(),
        )
        try:
            data = json.loads(response.content)
        except json.JSONDecodeError:
            return self._default_risk(sdd)

        risks = [
            RiskItem(
                description=r.get("description", ""),
                probability=float(r.get("probability", 0.5)),
                impact=r.get("impact", "medium"),
                mitigation=r.get("mitigation", ""),
            )
            for r in data.get("risks", [])
        ]
        trade_offs = [
            TradeOff(
                decision=t.get("decision", ""),
                pros=t.get("pros", []),
                cons=t.get("cons", []),
                recommended=t.get("recommended", False),
            )
            for t in data.get("trade_offs", [])
        ]
        return RiskAnalysis(
            risks=risks,
            trade_offs=trade_offs,
            overall_risk_score=float(data.get("overall_risk_score", 0.5)),
            recommendations=data.get("recommendations", []),
        )

    def _default_risk(self, sdd: str) -> RiskAnalysis:
        return RiskAnalysis(
            risks=[RiskItem("Unspecified risk", 0.5, "medium", "Review SDD for hidden assumptions")],
            trade_offs=[],
            overall_risk_score=0.5,
            recommendations=["Review edge cases and failure scenarios before proceeding"],
        )
