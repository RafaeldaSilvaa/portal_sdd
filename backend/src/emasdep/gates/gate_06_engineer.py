"""Gate 6: Sandboxed Execution & Transactional Healing."""

from __future__ import annotations

from ..agents.engineer_agent import EngineerAgent
from ..core.circuit_breaker import CircuitBreaker, CircuitState
from ..core.types import PipelineContext, PipelineGateID, PipelineState, TaskNode
from ..healing.engine import HealingEngine
from .base import PipelineGate


class EngineerGate(PipelineGate):
    def __init__(
        self,
        agent: EngineerAgent | None = None,
        healing_engine: HealingEngine | None = None,
    ):
        self._agent = agent or EngineerAgent()
        self._healing = healing_engine or HealingEngine()

    @property
    def gate_id(self) -> PipelineGateID:
        return PipelineGateID.ENGINEER

    @property
    def name(self) -> str:
        return "Sandboxed Code Generation"

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        if not ctx.task_dag:
            ctx.failure_reason = "No task DAG available"
            ctx.current_state = PipelineState.FAILED
            return ctx

        engineer_tasks = [
            t for t in ctx.task_dag.tasks.values()
            if t.agent_role.value == "engineer"
        ]

        if not engineer_tasks:
            ctx.current_state = PipelineState.CODING
            ctx.current_gate = self.gate_id
            return ctx

        breaker = CircuitBreaker(self.gate_id)
        spec_dict = ctx.spec or {}
        test_suite = ctx.test_suite or ""

        for task in engineer_tasks:
            success = False
            while breaker.remaining_attempts > 0 and not success:
                code = await self._agent.generate_code(
                    task.description, test_suite, spec_dict
                )
                ctx.code_artifacts[task.task_id] = code

                filepath = task.target_files[0] if task.target_files else "output.py"
                heal_result = await self._healing.attempt_heal(
                    filepath=filepath,
                    code_content=code,
                    test_command=f"pytest -x tests/",
                )

                if heal_result.success:
                    success = True
                else:
                    breaker.record_attempt()
                    ctx.snapshots.append(heal_result.snapshot)

            if not success:
                ctx.current_state = PipelineState.HEALING_LOOP
                ctx.failure_reason = (
                    f"Task {task.task_id} failed after "
                    f"{breaker.max_attempts} healing attempts"
                )
                ctx.current_gate = self.gate_id
                return ctx

        ctx.current_state = PipelineState.CODING
        ctx.current_gate = self.gate_id
        ctx.telemetry.pipeline_gate = self.name
        return ctx
