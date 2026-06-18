"""Gate 2: Proactive Probing & Clarification Loop with LLM-generated questions."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from ..agents.base import LLMAgent, LLMConfig, LLMResponse
from ..config import EMASDEPConfig
from ..core.types import PipelineContext, PipelineGateID, PipelineState


@dataclass
class ProbingQuestionnaire:
    questions: list[dict] = field(default_factory=list)
    ambiguity_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "action": "BLOCK_AND_PROBE" if self.ambiguity_score > 0.15 else "PROCEED_TO_DESIGN",
            "ambiguity_score": self.ambiguity_score,
            "threshold_limit": 0.15,
            "reason": "Especificação precisa de esclarecimentos adicionais."
            if self.ambiguity_score > 0.15
            else "Spec clarity approved.",
            "questionnaire": self.questions,
        }


class ProbingGate:
    def __init__(self, config: EMASDEPConfig | None = None, llm_config: LLMConfig | None = None):
        self.config = config or EMASDEPConfig()
        self.llm_config = llm_config
        self.gate_id = PipelineGateID.PROBING

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        if not ctx.spec:
            return ctx

        result = await self.evaluate_spec_clarity(ctx.spec)
        if result["action"] == "BLOCK_AND_PROBE":
            ctx.current_state = PipelineState.BLOCKED_PROBE
        return ctx

    async def evaluate_spec_clarity(self, spec: dict) -> dict:
        questionnaire = ProbingQuestionnaire()

        if not isinstance(spec, dict):
            return questionnaire.to_dict()

        if self.llm_config and self.llm_config.provider.name != "MOCK":
            questions = await self._llm_generate_questions(spec)
            if questions:
                questionnaire.questions = questions
                questionnaire.ambiguity_score = len(questions) / 5.0
                return questionnaire.to_dict()

        return questionnaire.to_dict()

    async def _llm_generate_questions(self, spec: dict) -> list[dict]:
        agent = _ProbingAgent(config=self.llm_config)
        prompt = (
            f"Analyze this software specification and generate probing questions "
            f"to clarify ambiguities. For each missing or unclear field, provide a "
            f"question with 4-5 concrete numbered options that make sense for this project.\n\n"
            f"Specification:\n{json.dumps(spec, indent=2, ensure_ascii=False)}\n\n"
            "Output a JSON array of objects. Each object:\n"
            "{\n"
            '  "id": "q_01_unique_id",\n'
            '  "context": "short context label",\n'
            '  "question": "clear question text",\n'
            '  "options": [{"label": "1. Option text", "value": "option_value"}, ...]\n'
            "}\n\n"
            "Rules:\n"
            "- Only ask about MISSING or UNCLEAR fields\n"
            "- Each question MUST have 4-5 numbered options that are relevant to the spec\n"
            "- Include a 'Custom' option (value: 'other') as the last option\n"
            "- Max 7 questions. Output ONLY valid JSON array."
        )
        try:
            response: LLMResponse = await agent.call(
                prompt=prompt,
                system_prompt=agent.build_system_prompt(),
            )
            data = json.loads(response.content)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "questions" in data:
                return data["questions"]
            return []
        except (json.JSONDecodeError, Exception):
            return []


class _ProbingAgent(LLMAgent):
    def build_system_prompt(self) -> str:
        return (
            "You are a Requirements Analyst. "
            "Analyze specifications for ambiguities and generate clarifying questions "
            "with relevant numbered options. Output ONLY valid JSON."
        )
