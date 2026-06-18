"""Orchestrator Agent: adaptive routing, lifecycle management, agent coordination."""

from __future__ import annotations

import json

from .base import LLMAgent, LLMConfig, LLMResponse
from ..core.types import (
    AgentOutput,
    PipelineContext,
    PipelineGateID,
    PipelineState,
)


class OrchestratorAgent(LLMAgent):
    def __init__(self, config: LLMConfig | None = None):
        super().__init__(config)

    def build_system_prompt(self) -> str:
        return (
            "You are an Orchestrator Agent. "
            "You coordinate all sub-agents, manage lifecycle, enforce pipeline rules, "
            "and trigger self-healing when needed. "
            "Output ONLY valid JSON."
        )

    async def decide_next_action(self, ctx: PipelineContext) -> AgentOutput:
        prompt = (
            f"Current state: {ctx.current_state.name}\n"
            f"Current gate: {ctx.current_gate.name}\n"
            f"Spec present: {ctx.spec is not None}\n"
            f"SDD present: {ctx.sdd is not None}\n"
            f"Risk analysis present: {ctx.risk_analysis is not None}\n"
            f"Task DAG present: {ctx.task_dag is not None}\n"
            f"Test suite present: {ctx.test_suite is not None}\n"
            f"Code artifacts count: {len(ctx.code_artifacts)}\n"
            f"Failure reason: {ctx.failure_reason or 'none'}\n\n"
            "Decide next action. Output JSON:\n"
            "{\n"
            '  "next_gate": "SPEC|PROBING|ARCHITECTURE|RISK_ANALYSIS|PLANNER|QA|ENGINEER|CONVERGENCE",\n'
            '  "action": "proceed|retry|replan|halt",\n'
            '  "reason": "string"\n'
            "}\n"
            "Output ONLY valid JSON."
        )
        response: LLMResponse = await self.call(
            prompt=prompt,
            system_prompt=self.build_system_prompt(),
        )
        try:
            data = json.loads(response.content)
            return AgentOutput.ok(data)
        except json.JSONDecodeError:
            return AgentOutput.fail("Failed to parse orchestrator decision")

    async def handle_failure(self, ctx: PipelineContext, failure: str) -> AgentOutput:
        prompt = (
            f"Pipeline failure detected:\n"
            f"State: {ctx.current_state.name}\n"
            f"Gate: {ctx.current_gate.name}\n"
            f"Failure: {failure}\n\n"
            "Recommend recovery action. Output JSON:\n"
            "{\n"
            '  "action": "retry_same|simplify_context|replan|fallback_model|abort",\n'
            '  "next_gate": "same|PREVIOUS|PREVIOUS_TWO",\n'
            '  "reason": "string"\n'
            "}\n"
            "Output ONLY valid JSON."
        )
        response: LLMResponse = await self.call(
            prompt=prompt,
            system_prompt=self.build_system_prompt(),
        )
        try:
            data = json.loads(response.content)
            return AgentOutput.ok(data)
        except json.JSONDecodeError:
            return AgentOutput.fail("Failed to parse failure recovery decision")
