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
    ) -> None:
        """inicializa o gate de engenharia."""
        self._agent = agent or EngineerAgent()
        self._healing = healing_engine or HealingEngine()

    @property
    def gate_id(self) -> PipelineGateID:
        return PipelineGateID.ENGINEER

    @property
    def name(self) -> str:
        return "Sandboxed Code Generation"

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        """process.

Args:
    ctx: Descrição do parâmetro ctx.

Retorna:
    Descrição do valor retornado."""
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
                elif result is not None:
                    fkey, code = result
                    ctx.code_artifacts[fkey] = code

        for task in dependent:
            result = await self._execute_task(task, spec_dict, test_suite, ctx)
            if result is not None:
                fkey, code = result
                ctx.code_artifacts[fkey] = code

        ctx.current_state = PipelineState.CODING
        ctx.current_gate = self.gate_id
        ctx.telemetry.pipeline_gate = self.name
        return ctx

    def _file_key(self, task) -> str:
        return task.target_files[0] if task.target_files else f"{task.task_id}.py"

    async def _execute_task(self, task, spec_dict: dict, test_suite: str, ctx: PipelineContext) -> tuple[str, str] | None:
        import time
        breaker = CircuitBreaker(self.gate_id)
        start_ms = int(time.time() * 1000)

        code = await self._agent.generate_code(
            task.description, test_suite, spec_dict
        )
        fkey = self._file_key(task)

        latency = int(time.time() * 1000) - start_ms
        ctx.telemetry.agent_trace.append(AgentTraceEntry(
            agent_role="engineer",
            gate=self.name,
            latency_ms=latency,
            token_usage=len(code),
            status="success",
        ))
        ctx.telemetry.total_latency_ms += latency
        ctx.telemetry.total_tokens += len(code)

        return fkey, code
