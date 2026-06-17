"""Gate 7: Cryptographic Convergence (Output Stage)."""

from __future__ import annotations

import hashlib
import json

from ..core.types import PipelineContext, PipelineGateID, PipelineState
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
    ):
        self._ast = ast_validator or ASTValidator()
        self._coverage = coverage_tracker or CoverageTracker()
        self._mutation = mutation_validator or MutationValidator()

    @property
    def gate_id(self) -> PipelineGateID:
        return PipelineGateID.CONVERGENCE

    @property
    def name(self) -> str:
        return "Cryptographic Convergence"

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        ctx.current_gate = self.gate_id
        ctx.current_state = PipelineState.VALIDATION
        ctx.telemetry.pipeline_gate = self.name

        # Gate Tier 1: AST Integrity
        ast_clean = True
        for filename, content in ctx.code_artifacts.items():
            if not self._ast.validate(content):
                ast_clean = False
                break

        # Gate Tier 2: Coverage
        coverage_result = await self._coverage.measure(
            list(ctx.code_artifacts.values())
        )

        # Gate Tier 3: Mutation
        mutation_result = await self._mutation.validate(
            code_artifacts=ctx.code_artifacts,
            test_suite=ctx.test_suite or "",
        )

        passed_all = (
            ast_clean
            and coverage_result >= 0.95
            and mutation_result.passed_minimum
        )

        ctx.validation = type(
            "ValidationResult",
            (),
            {
                "ast_clean": ast_clean,
                "coverage_percent": coverage_result,
                "mutation": mutation_result,
                "passed_all_gates": passed_all,
            },
        )

        # SHA-256 checksums
        checksums = {}
        for filename, content in ctx.code_artifacts.items():
            checksums[filename] = hashlib.sha256(content.encode()).hexdigest()
        ctx.telemetry.state_checksums = checksums

        if passed_all:
            ctx.current_state = PipelineState.CONVERGED
        else:
            ctx.current_state = PipelineState.FAILED
            ctx.failure_reason = (
                f"Convergence failed: AST={ast_clean}, "
                f"Cov={coverage_result:.2%}, "
                f"Mut={mutation_result.mutation_score:.2%}"
            )

        return ctx
