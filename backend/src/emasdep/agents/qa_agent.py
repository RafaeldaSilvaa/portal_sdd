"""QA Agent: adversarial test generation and mutation analysis."""

from __future__ import annotations

import json

from .base import LLMAgent, LLMConfig, LLMResponse


class QAAgent(LLMAgent):
    def __init__(self, config: LLMConfig | None = None):
        super().__init__(config)

    def build_system_prompt(self) -> str:
        return (
            "You are an Adversarial Mutator. "
            "Generate rigorous pytest tests using AAA (Arrange, Act, Assert). "
            "Cover edge cases, failure modes, and boundary conditions."
        )

    async def generate_tests(self, spec: dict, sdd: str) -> str:
        response: LLMResponse = await self.call(
            prompt=(
                f"Spec: {json.dumps(spec, indent=2)[:2000]}\nSDD: {sdd[:2000]}\n\n"
                "Generate a complete pytest test suite covering:\n"
                "- All input validation rules\n"
                "- Happy path\n"
                "- Edge cases (null, empty, boundary)\n"
                "- Failure scenarios\n"
                "- Idempotency verification"
            ),
            system_prompt=self.build_system_prompt(),
        )
        return response.content

