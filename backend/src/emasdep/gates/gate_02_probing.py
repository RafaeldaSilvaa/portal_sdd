"""Gate 2: Sondagem Proativa e Loop de Esclarecimento com perguntas geradas por LLM."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from ..agents.base import LLMAgent, LLMConfig, LLMResponse
from ..config import EMASDEPConfig
from ..core.types import PipelineContext, PipelineGateID, PipelineState
from .base import PipelineGate


@dataclass
class QuestionarioSondagem:
    """Questionário de perguntas de esclarecimento geradas pelo ProbingGate."""
    perguntas: list[dict] = field(default_factory=list)
    pontuacao_ambiguidade: float = 0.0

    def para_dicionario(self) -> dict:
        """Converte o questionário para dicionário para resposta da API."""
        return {
            "action": "BLOCK_AND_PROBE" if self.pontuacao_ambiguidade > 0.15 else "PROCEED_TO_DESIGN",
            "ambiguity_score": self.pontuacao_ambiguidade,
            "threshold_limit": 0.15,
            "reason": "Especificação precisa de esclarecimentos adicionais."
            if self.pontuacao_ambiguidade > 0.15
            else "Especificação clara o suficiente.",
            "questionnaire": self.perguntas,
        }


class ProbingGate(PipelineGate):
    """Gate de sondagem que avalia a clareza da especificação e gera perguntas em português."""

    def __init__(self, config: EMASDEPConfig | None = None, llm_config: LLMConfig | None = None) -> None:
        """Inicializa o ProbingGate com configuração e agente LLM."""
        super().__init__()
        self.config = config or EMASDEPConfig()
        self.llm_config = llm_config

    @property
    def gate_id(self) -> PipelineGateID:
        return PipelineGateID.PROBING

    @property
    def name(self) -> str:
        return "Sondagem Proativa e Esclarecimento"

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        """Processa o contexto executando a avaliação de clareza da especificação."""
        if not ctx.spec:
            return ctx

        ctx.current_gate = self.gate_id
        ctx.telemetry.pipeline_gate = self.name
        resultado = await self.avaliar_clareza_especificacao(ctx.spec)
        if resultado["action"] == "BLOCK_AND_PROBE":
            ctx.current_state = PipelineState.BLOCKED_PROBE
        return ctx

    async def avaliar_clareza_especificacao(self, spec: dict) -> dict:
        """Avalia a clareza da especificação e retorna perguntas de esclarecimento em português."""
        questionario = QuestionarioSondagem()

        if not isinstance(spec, dict):
            return questionario.para_dicionario()

        if self.llm_config and self.llm_config.provider.name != "MOCK":
            perguntas = await self._gerar_perguntas_llm(spec)
            if perguntas:
                perguntas_validas = await self._validar_coerencia(perguntas, spec)
                if perguntas_validas:
                    questionario.perguntas = perguntas_validas
                    questionario.pontuacao_ambiguidade = len(perguntas_validas) / 5.0
                    return questionario.para_dicionario()

        return questionario.para_dicionario()

    async def _validar_coerencia(self, perguntas: list[dict], spec: dict) -> list[dict]:
        """Valida se cada pergunta gerada é coerente com a especificação usando o próprio LLM."""
        if not perguntas:
            return []

        try:
            validador = _ProbingAgent(config=self.llm_config)
            prompt_validacao = (
                f"Você é um analista de requisitos. Analise as perguntas de esclarecimento "
                f"geradas para a seguinte especificação e REMOVA qualquer pergunta que:\n"
                f"- JÁ seja respondida claramente pela especificação\n"
                f"- Seja irrelevante para o domínio do problema\n"
                f"- Esteja duplicada ou muito similar a outra pergunta\n"
                f"- Use linguagem muito técnica incompatível com o contexto\n\n"
                f"Especificação:\n{json.dumps(spec, indent=2, ensure_ascii=False)[:3000]}\n\n"
                f"Perguntas geradas:\n{json.dumps(perguntas, indent=2, ensure_ascii=False)}\n\n"
                "Retorne APENAS um array JSON válido com as perguntas que passaram na validação. "
                "Se nenhuma passar, retorne []."
            )
            resposta: LLMResponse = await validador.call(
                prompt=prompt_validacao,
                system_prompt="Você é um validador de perguntas de esclarecimento. Retorne APENAS JSON válido.",
            )
            dados = json.loads(resposta.content)
            if isinstance(dados, list):
                return dados
            return perguntas
        except (json.JSONDecodeError, Exception):
            return perguntas

    async def _gerar_perguntas_llm(self, spec: dict) -> list[dict]:
        """Gera perguntas de esclarecimento em português usando o LLM."""
        agente = _ProbingAgent(config=self.llm_config)
        examples_good = (
            '- Qual o porte esperado do sistema (quantas entidades/features)?\n'
            '- O sistema precisa de autenticacao e controle de acesso?\n'
            '- Ha requisitos de escalabilidade ou desempenho esperados?\n'
            '- O sistema sera integrado com outros sistemas existentes?\n'
        )
        examples_bad = (
            '- O campo X deve ser obrigatorio?\n'
            '- Qual o tipo de dado do atributo Y?\n'
            '- A interface Z deve ter paginacao?\n'
        )
        prompt = (
            "Analise a seguinte especificacao de software em portugues e gere "
            "perguntas MACRO de esclarecimento. Pergunte sobre decisoes "
            "arquiteturais de alto nivel, escopo do projeto, restricoes gerais "
            "e objetivos de negocio. Nao pergunte sobre campos especificos, "
            "detalhes de implementacao ou interfaces tecnicas.\n\n"
            "Exemplos de perguntas macro adequadas:\n"
            f"{examples_good}\n"
            "Exemplos de perguntas EVITAR (muito detalhadas):\n"
            f"{examples_bad}\n"
            f"Especificacao:\n{json.dumps(spec, indent=2, ensure_ascii=False)}\n\n"
            "Retorne um array JSON de objetos. Cada objeto:\n"
            "{\n"
            '  "id": "q_01_id_unico",\n'
            '  "context": "rotulo curto (ex: Escopo, Arquitetura, Seguranca)",\n'
            '  "question": "pergunta macro em portugues",\n'
            '  "options": [{"label": "1. Opcao concisa", "value": "valor_opcao"}, ...]\n'
            "}\n\n"
            "Regras:\n"
            "- APENAS perguntas MACRO sobre visao geral, escopo, restricoes\n"
            "- Cada pergunta DEVE ter 3-4 opcoes concisas\n"
            "- Gere a quantidade necessaria de perguntas (sem maximo fixo)\n"
            "- Use portugues claro e direto\n"
            "- Retorne APENAS o array JSON valido, sem texto adicional"
        )
        try:
            resposta: LLMResponse = await agente.call(
                prompt=prompt,
                system_prompt=agente.construir_prompt_sistema(),
            )
            dados = json.loads(resposta.content)
            if isinstance(dados, list):
                return dados
            if isinstance(dados, dict) and "questions" in dados:
                return dados["questions"]
            return []
        except (json.JSONDecodeError, Exception):
            return []


class _ProbingAgent(LLMAgent):
    """Agente LLM especializado em gerar perguntas de esclarecimento em português."""

    def construir_prompt_sistema(self) -> str:
        """Constrói o prompt de sistema para o agente de sondagem."""
        return (
            "Você é um Analista de Requisitos sênior especializado em esclarecer "
            "especificações de software. Gere perguntas objetivas em português com "
            "opções relevantes para resolver ambiguidades. Retorne APENAS JSON válido."
        )

    def build_system_prompt(self) -> str:
        """Mantido para compatibilidade com a interface LLMAgent."""
        return self.construir_prompt_sistema()
