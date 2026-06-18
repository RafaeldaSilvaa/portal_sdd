"""Architect Agent: constructs the System Design Document (SDD)."""

from __future__ import annotations

import json

from .base import LLMAgent, LLMConfig, LLMResponse
from ..core.types import SpecContract


class ArchitectAgent(LLMAgent):
    def __init__(self, config: LLMConfig | None = None) -> None:
        super().__init__(config)

    def build_system_prompt(self) -> str:
        """build system prompt.

Retorna:
    Descrição do valor retornado."""
        return (
            "You are an Architectural Guard. "
            "Construct rigorous System Design Documents (SDD) enforcing "
            "Hexagonal Architecture boundaries, domain layers, and adapter ports."
        )

    async def generate_sdd(self, spec: SpecContract) -> str:
        """generate sdd.

Args:
    spec: Descrição do parâmetro spec.

Retorna:
    Descrição do valor retornado."""
        response: LLMResponse = await self.call(
            prompt=(
                f"Specification:\n{json.dumps(spec, indent=2)}\n\n"
                "Generate SDD in markdown:\n"
                "1. Domain Model & Aggregates\n"
                "2. Hexagonal Port/Adapter definitions\n"
                "3. Layer boundaries\n"
                "4. Command/Query separation\n"
                "5. Error handling boundaries"
            ),
            system_prompt=self.build_system_prompt(),
        )
        return response.content


