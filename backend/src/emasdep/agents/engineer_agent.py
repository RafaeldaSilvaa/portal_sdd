"""Engineer Agent: high-velocity production code generation."""

from __future__ import annotations

import json

from .base import LLMAgent, LLMConfig, LLMResponse


class EngineerAgent(LLMAgent):
    def __init__(self, config: LLMConfig | None = None) -> None:
        super().__init__(config)

    def build_system_prompt(self) -> str:
        """build system prompt.

Retorna:
    Descrição do valor retornado."""
        return (
            "You are a High-Velocity Constructor. "
            "Write production-ready Python 3.12 code that passes the provided tests. "
            "Strict typing, SOLID, clean architecture. Output ONLY the code."
        )

    async def generate_code(self, task_description: str, test_suite: str, spec: dict) -> str:
        """generate code.

Args:
    task_description: Descrição do parâmetro task_description.
    test_suite: Descrição do parâmetro test_suite.
    spec: Descrição do parâmetro spec.

Retorna:
    Descrição do valor retornado."""
        response: LLMResponse = await self.call(
            prompt=(
                f"Task: {task_description}\n"
                f"Tests:\n{test_suite[:2000]}\n"
                f"Spec:\n{json.dumps(spec, indent=2)[:2000]}\n\n"
                "Generate production code passing ALL tests. Output ONLY the code."
            ),
            system_prompt=self.build_system_prompt(),
        )
        return response.content

