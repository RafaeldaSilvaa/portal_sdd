"""Programmatic Guardrails — no undefined schema, no skip validation, no hallucinated APIs."""

from __future__ import annotations

from ..core.types import (
    GuardrailResult,
    GuardrailViolation,
    PipelineContext,
    PipelineState,
)


class Guardrails:
    @staticmethod
    def check_no_exec_without_spec(ctx: PipelineContext) -> GuardrailResult:
        violations: list[GuardrailViolation] = []
        if ctx.current_state.value >= PipelineState.CODING.value and not ctx.spec:
            violations.append(GuardrailViolation(
                rule="no_exec_without_spec",
                severity="error",
                detail="Implementation requested but no SpecContract exists",
            ))
        return GuardrailResult(passed=len(violations) == 0, violations=violations)

    @staticmethod
    def check_no_undefined_schema(spec: dict | None) -> GuardrailResult:
        violations: list[GuardrailViolation] = []
        if not spec:
            return GuardrailResult(passed=False, violations=[
                GuardrailViolation("no_undefined_schema", "error", "Spec is None")
            ])

        contract = spec.get("contract_interface", {})
        for inp in contract.get("strict_inputs", []):
            if isinstance(inp, dict) and not inp.get("type"):
                violations.append(GuardrailViolation(
                    rule="no_undefined_schema",
                    severity="error",
                    detail=f"Input '{inp.get('name', 'unknown')}' has no type defined",
                ))
        return GuardrailResult(passed=len(violations) == 0, violations=violations)

    @staticmethod
    def check_no_hallucinated_apis(ctx: PipelineContext) -> GuardrailResult:
        violations: list[GuardrailViolation] = []
        for task_id, code in ctx.code_artifacts.items():
            if "import" not in code:
                continue
            for line in code.splitlines():
                line = line.strip()
                if not line.startswith("import ") and not line.startswith("from "):
                    continue
                if "unknown_library" in line.lower():
                    violations.append(GuardrailViolation(
                        rule="no_hallucinated_APIs",
                        severity="warning",
                        detail=f"Task {task_id}: possible hallucinated import '{line}'",
                    ))
        return GuardrailResult(passed=len(violations) == 0, violations=violations)

    @staticmethod
    def check_no_large_context_dumps(ctx: PipelineContext, max_chars: int = 30000) -> GuardrailResult:
        violations: list[GuardrailViolation] = []
        total = 0
        if ctx.sdd:
            total += len(ctx.sdd)
        if ctx.test_suite:
            total += len(ctx.test_suite)
        if ctx.code_artifacts:
            total += sum(len(c) for c in ctx.code_artifacts.values())
        if total > max_chars:
            violations.append(GuardrailViolation(
                rule="no_large_context_dumps",
                severity="warning",
                detail=f"Total context size {total} chars exceeds {max_chars} limit",
            ))
        return GuardrailResult(passed=len(violations) == 0, violations=violations)

    @staticmethod
    def check_all(ctx: PipelineContext) -> GuardrailResult:
        all_violations: list[GuardrailViolation] = []
        for check in [
            Guardrails.check_no_exec_without_spec,
            Guardrails.check_no_undefined_schema,
            Guardrails.check_no_hallucinated_apis,
            Guardrails.check_no_large_context_dumps,
        ]:
            result = check(ctx)
            all_violations.extend(result.violations)
        return GuardrailResult(passed=len(all_violations) == 0, violations=all_violations)

    @staticmethod
    def check_no_skip_validation(ctx: PipelineContext, current_gate_value: int) -> GuardrailResult:
        violations: list[GuardrailViolation] = []
        order = [
            "SPEC",
            "PROBING",
            "ARCHITECTURE",
            "RISK_ANALYSIS",
            "PLANNER",
            "QA",
            "ENGINEER",
            "CONVERGENCE",
        ]
        complete = ctx.spec and ctx.sdd and ctx.task_dag and ctx.test_suite
        if current_gate_value >= 6 and not complete:
            violations.append(GuardrailViolation(
                rule="no_skip_validation",
                severity="error",
                detail="Reached ENGINEER gate but one or more prior artifacts are missing",
            ))
        return GuardrailResult(passed=len(violations) == 0, violations=violations)
