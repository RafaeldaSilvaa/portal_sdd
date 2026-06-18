"""Gate 7: Cryptographic Convergence with LLM-as-Judge scoring."""

from __future__ import annotations

import hashlib

from ..agents.base import LLMAgent, LLMConfig
from ..core.types import PipelineContext, PipelineGateID, PipelineState, ValidationResult
from ..validation.ast_validator import ASTValidator
from ..validation.coverage import CoverageTracker
from ..validation.mutation import MutationValidator
from .base import PipelineGate


class ConvergenceGate(PipelineGate):
    def __init__(
        self,
        ast_validator: ASTValidator | None = None,
        coverage_tracker: CoverageTracker | None = None,
        mutation_validator: MutationValidator | None = None,
        llm_config: LLMConfig | None = None,
    ) -> None:
        """inicializa o gate de convergência com validação e LLM-as-Judge."""
        self._ast = ast_validator or ASTValidator()
        self._coverage = coverage_tracker or CoverageTracker()
        self._mutation = mutation_validator or MutationValidator()
        self._llm_config = llm_config

    @property
    def gate_id(self) -> PipelineGateID:
        return PipelineGateID.CONVERGENCE

    @property
    def name(self) -> str:
        return "Cryptographic Convergence"

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        """process.

Args:
    ctx: Descrição do parâmetro ctx.

Retorna:
    Descrição do valor retornado."""
        ctx.current_gate = self.gate_id
        ctx.current_state = PipelineState.VALIDATION
        ctx.telemetry.pipeline_gate = self.name

        ast_clean = True
        for filename, content in ctx.code_artifacts.items():
            basic = self._ast.validate(content)
            ruff = self._ast.validate_with_ruff(content)
            mypy = self._ast.validate_with_mypy(content)
            if not (basic.is_valid and ruff.is_valid and mypy.is_valid):
                ast_clean = False
                break

        coverage_result = await self._coverage.measure(
            list(ctx.code_artifacts.values()),
            test_suite=ctx.test_suite or "",
        )

        mutation_result = await self._mutation.validate(
            code_artifacts=ctx.code_artifacts,
            test_suite=ctx.test_suite or "",
        )

        checksums = {}
        for filename, content in ctx.code_artifacts.items():
            checksums[filename] = hashlib.sha256(content.encode()).hexdigest()
        ctx.telemetry.state_checksums = checksums

        eval_score, eval_confidence, eval_issues, eval_action = 10.0, 1.0, [], "accept"
        if not ast_clean:
            eval_issues.append("AST integrity check failed")
            eval_action = "retry"
        if coverage_result < 0.95:
            eval_issues.append(f"Coverage {coverage_result:.1%} below 95% threshold")
            eval_action = "retry"
        if mutation_result and not mutation_result.passed_minimum:
            eval_issues.append(f"Mutation score {mutation_result.mutation_score:.1%} below minimum")
            eval_action = "replan"
        if eval_issues:
            eval_score = max(0.0, 10.0 - len(eval_issues) * 3.0)
            eval_confidence = max(0.0, 1.0 - len(eval_issues) * 0.2)

        if self._llm_config and self._llm_config.provider.name != "MOCK":
            try:
                llm_score = await self._llm_judge(ctx)
                if llm_score is not None:
                    eval_score = (eval_score + llm_score) / 2
            except Exception:
                pass

        passed_all = (
            ast_clean
            and coverage_result >= 0.95
            and mutation_result.passed_minimum
            and eval_action in ("accept",)
        )

        ctx.validation = ValidationResult(
            ast_clean=ast_clean,
            coverage_percent=coverage_result,
            mutation=mutation_result,
            passed_all_gates=passed_all,
            eval_score=eval_score,
            eval_confidence=eval_confidence,
            eval_issues=eval_issues,
            eval_action=eval_action,
        )

        if passed_all:
            ctx.current_state = PipelineState.CONVERGED
        else:
            ctx.current_state = PipelineState.FAILED
            ctx.failure_reason = (
                f"Convergence failed: AST={ast_clean}, "
                f"Cov={coverage_result:.2%}, "
                f"Mut={mutation_result.mutation_score:.2%}, "
                f"Judge={eval_action}({eval_score:.1f})"
            )

        return ctx

    async def _llm_judge(self, ctx: PipelineContext) -> float | None:
        """ llm judge.

Args:
    ctx: Descrição do parâmetro ctx.

Retorna:
    Descrição do valor retornado."""
        from ..agents.base import LLMResponse

        spec_str = str(ctx.spec)
        sample_code = ""
        if ctx.code_artifacts:
            sample_code = list(ctx.code_artifacts.values())[0][:1500]

        judge = _JudgeAgent(config=self._llm_config)
        response: LLMResponse = await judge.call(
            prompt=(
                f"Evaluate this generated code against its spec.\n\n"
                f"Spec excerpt:\n{spec_str[:1000]}\n\n"
                f"Code:\n{sample_code}\n\n"
                "Rate from 0-10: correctness, completeness, adherence to spec. "
                "Output ONLY a number."
            ),
            system_prompt="You are an LLM-as-Judge. Output ONLY a number 0-10.",
        )
        try:
            return float(response.content.strip())
        except (ValueError, TypeError):
            return None


class _JudgeAgent(LLMAgent):
    def build_system_prompt(self) -> str:
        return "You are an LLM-as-Judge. Output ONLY a number 0-10."
