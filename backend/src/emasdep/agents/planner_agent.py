"""Planner Agent: compiles SDD into an execution DAG."""

from __future__ import annotations

import json

from networkx import DiGraph, topological_sort

from .base import LLMAgent, LLMConfig, LLMResponse
from ..core.types import AgentRole, TaskDAG, TaskNode


class PlannerAgent(LLMAgent):
    def __init__(self, config: LLMConfig | None = None):
        super().__init__(config)

    def build_system_prompt(self) -> str:
        return (
            "You are a Graph Compiler. "
            "Decompose the SDD into a Directed Acyclic Graph (DAG) of "
            "independent, parallelizable tasks. Output ONLY a JSON array."
        )

    async def build_dag(self, sdd: str, spec: dict | None = None) -> TaskDAG:
        response: LLMResponse = await self.call(
            prompt=(
                f"SDD:\n{sdd[:3000]}\n\n"
                "Generate JSON array of tasks:\n"
                "- task_id: string\n"
                "- description: string\n"
                "- dependencies: list of task_ids\n"
                "- agent_role: 'engineer' | 'qa'\n"
                "- target_files: list\n"
                "- estimated_complexity: 1-5"
            ),
            system_prompt=self.build_system_prompt(),
        )

        try:
            tasks_data = json.loads(response.content)
        except json.JSONDecodeError:
            tasks_data = [self._default_task()]

        dag = TaskDAG()
        items = tasks_data if isinstance(tasks_data, list) else [tasks_data]
        for t in items:
            tid = t.get("task_id") or t.get("id") or f"task_{len(dag.tasks) + 1:03d}"
            dag.tasks[tid] = TaskNode(
                task_id=tid,
                description=t.get("description", ""),
                dependencies=t.get("dependencies", []),
                agent_role=AgentRole(t.get("agent_role", "engineer")),
                target_files=t.get("target_files", []),
                estimated_complexity=t.get("estimated_complexity", 1),
            )

        dag.topological_order = self._compute_order(dag)
        return dag

    def _compute_order(self, dag: TaskDAG) -> list[str]:
        graph = DiGraph()
        for task_id, node in dag.tasks.items():
            graph.add_node(task_id)
            for dep in node.dependencies:
                if dep in dag.tasks:
                    graph.add_edge(dep, task_id)
        try:
            return list(topological_sort(graph))
        except Exception:
            return list(dag.tasks.keys())

    def _default_task(self) -> dict:
        return {
            "task_id": "task_001",
            "description": "Implement core domain logic",
            "dependencies": [],
            "agent_role": "engineer",
            "target_files": ["domain.py"],
            "estimated_complexity": 3,
        }
