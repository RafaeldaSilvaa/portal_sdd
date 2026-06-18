"""Gate 6: Sandboxed Execution & Transactional Healing with parallelism."""

from __future__ import annotations

import asyncio
from pathlib import Path

from ..agents.engineer_agent import EngineerAgent
from ..core.circuit_breaker import CircuitBreaker
from ..core.types import (
    AgentTraceEntry,
    CodePatchSnapshot,
    PipelineContext,
    PipelineGateID,
    PipelineState,
)
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

        order = ctx.task_dag.topological_order
        all_tasks = ctx.task_dag.tasks
        engineer_tasks = [
            all_tasks[tid] for tid in order
            if tid in all_tasks and all_tasks[tid].agent_role.value == "engineer"
        ]

        if not engineer_tasks:
            ctx.current_state = PipelineState.CODING
            ctx.current_gate = self.gate_id
            return ctx

        spec_dict = ctx.spec or {}
        test_suite = ctx.test_suite or ""

        independent = [t for t in engineer_tasks if not t.dependencies]
        dependent = [t for t in engineer_tasks if t.dependencies]

        if independent:
            results = await asyncio.gather(
                *[self._execute_task(t, spec_dict, test_suite, ctx) for t in independent],
                return_exceptions=True,
            )
            for task, result in zip(independent, results):
                if isinstance(result, Exception):
                    ctx.failure_reason = f"Task {task.task_id} failed: {result}"
                    ctx.current_state = PipelineState.HEALING_LOOP
                    ctx.current_gate = self.gate_id
                    return ctx
                if result is not None:
                    ctx.code_artifacts[task.task_id] = result

        for task in dependent:
            code = await self._execute_task(task, spec_dict, test_suite, ctx)
            if code is None:
                ctx.failure_reason = f"Task {task.task_id} failed after healing attempts"
                ctx.current_state = PipelineState.HEALING_LOOP
                ctx.current_gate = self.gate_id
                return ctx
            ctx.code_artifacts[task.task_id] = code

        ctx.current_state = PipelineState.CODING
        ctx.current_gate = self.gate_id
        ctx.telemetry.pipeline_gate = self.name
        return ctx

    async def _execute_task(self, task, spec_dict: dict, test_suite: str, ctx: PipelineContext) -> str | None:
        import time
        breaker = CircuitBreaker(self.gate_id)
        start_ms = int(time.time() * 1000)

        while breaker.remaining_attempts > 0:
            code = await self._agent.generate_code(
                task.description, test_suite, spec_dict
            )
            filepath = task.target_files[0] if task.target_files else "output.py"
            heal_result = await self._healing.attempt_heal(
                filepath=filepath,
                code_content=code,
                test_command=f"pytest -x tests/",
                test_content=test_suite,
            )

            latency = int(time.time() * 1000) - start_ms
            ctx.telemetry.agent_trace.append(AgentTraceEntry(
                agent_role="engineer",
                gate=self.name,
                latency_ms=latency,
                token_usage=len(code),
                status="success" if heal_result.success else "error",
            ))
            ctx.telemetry.total_latency_ms += latency
            ctx.telemetry.total_tokens += len(code)

            if heal_result.success:
                return code
            else:
                breaker.record_attempt()
                ctx.snapshots.append(heal_result.snapshot)

                if heal_result.failure_category.value in ("dependency_failure", "hallucination"):
                    strategy = self._healing.select_healing_strategy(heal_result.failure_category, breaker.remaining_attempts)
                    if strategy == "replan":
                        break

        old_code = ctx.code_artifacts.pop(task.task_id, None)
        if old_code is not None:
            snap = CodePatchSnapshot.create(filepath=Path(filepath), contents=old_code)
            self._healing.rollback(snap)
        return None
