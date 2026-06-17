"""Gate 2: Proactive Probing & Clarification Loop."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config import EMASDEPConfig
from ..core.types import InputProperty, PipelineContext, PipelineGateID, PipelineState


@dataclass
class ProbingQuestionnaire:
    questions: list[dict] = field(default_factory=list)
    ambiguity_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "action": "BLOCK_AND_PROBE" if self.ambiguity_score > 0.15 else "PROCEED_TO_DESIGN",
            "ambiguity_score": self.ambiguity_score,
            "threshold_limit": 0.15,
            "reason": "Contrato de especificação abaixo da linha de corte de nitidez técnica."
            if self.ambiguity_score > 0.15
            else "Spec clarity approved.",
            "questionnaire": self.questions,
        }


class ProbingGate:
    def __init__(self, config: EMASDEPConfig | None = None):
        self.config = config or EMASDEPConfig()
        self.gate_id = PipelineGateID.PROBING

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        if not ctx.spec:
            return ctx

        result = self.evaluate_spec_clarity("", ctx.spec)
        if result["action"] == "BLOCK_AND_PROBE":
            ctx.current_state = PipelineState.BLOCKED_PROBE
        return ctx

    def evaluate_spec_clarity(self, raw_intent: str, spec: dict) -> dict:
        missing_fields: list[str] = []
        questionnaire = ProbingQuestionnaire()

        if not isinstance(spec, dict):
            return questionnaire.to_dict()

        meta = spec.get("project_metadata", {})
        if not isinstance(meta, dict):
            meta = {}

        if not meta.get("project_type"):
            questionnaire.questions.append({
                "id": "q_01_project_type",
                "context": "Tipo de projeto",
                "question": "Que tipo de projeto é este? (web_api, cli, library, pipeline, mobile_backend)",
            })
        if not meta.get("framework"):
            questionnaire.questions.append({
                "id": "q_02_framework",
                "context": "Framework",
                "question": "Qual framework ou biblioteca principal devo usar? (ex: FastAPI, Flask, Django, plain Python)",
            })
        if not meta.get("deployment_target"):
            questionnaire.questions.append({
                "id": "q_03_deployment",
                "context": "Deploy",
                "question": "Onde este projeto será executado? (docker, serverless, vm, edge)",
            })
        if not meta.get("structured_as"):
            questionnaire.questions.append({
                "id": "q_04_structure",
                "context": "Estrutura",
                "question": "Como o código deve ser estruturado? (modular com pacotes separados, monolítico, microserviços)",
            })

        inputs: list[InputProperty] = spec.get("contract_interface", {}).get("strict_inputs", [])
        for inp in inputs:
            if not isinstance(inp, dict):
                continue
            name = inp.get("name", "unknown")
            if not inp.get("pattern") and inp.get("type") == "string":
                missing_fields.append(f"Regra de validação (pattern) para input: {name}")
            if inp.get("minimum") is None and inp.get("type") in ("integer", "number"):
                missing_fields.append(f"Valor mínimo não definido para input: {name}")

        if not spec.get("fail_safe_protocols"):
            missing_fields.append("Mapeamento de cenários de falha e tratamento de exceções")

        questionnaire.ambiguity_score = (len(missing_fields) + len(questionnaire.questions)) / 10.0

        if questionnaire.ambiguity_score > self.config.ambiguity_threshold:
            for idx, mf in enumerate(missing_fields[:3]):
                questionnaire.questions.append({
                    "id": f"q_{idx+5:02d}_ambiguity",
                    "context": mf,
                    "question": f"Como o sistema deve se comportar diante de: {mf}? "
                    f"Defina a estratégia de validação e fallback.",
                })

        return questionnaire.to_dict()
