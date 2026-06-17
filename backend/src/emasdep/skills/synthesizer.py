"""On-Demand Skill Synthesis: generates skills when no match found."""

from __future__ import annotations

import json

from ..agents.base import LLMAgent, LLMResponse
from ..core.types import AgentRole, ThinkingMode


class SkillSynthesizer(LLMAgent):
    def __init__(self, api_key: str = "", base_url: str = "", model: str = ""):
        super().__init__(
            role=AgentRole.ORCHESTRATOR,
            thinking_mode=ThinkingMode.ENABLED_MAX,
            api_key=api_key,
            base_url=base_url,
            model=model,
        )

    def build_system_prompt(self) -> str:
        return (
            "You are a Skill Synthesizer for EMASDEP. "
            "Generate a markdown skill guide with:\n"
            "1. Title and intent\n"
            "2. Typed code blueprints\n"
            "3. Known anti-patterns to block\n"
            "4. Testing patterns\n"
            "5. Interface contracts"
        )

    async def synthesize_skill(self, tech_stack: str, design_pattern: str) -> str:
        prompt = (
            f"{self.build_system_prompt()}\n\n"
            f"Tech Stack: {tech_stack}\n"
            f"Design Pattern: {design_pattern}\n\n"
            "Generate a complete skill guide."
        )

        response: LLMResponse = await self.call(prompt)
        return response.content
