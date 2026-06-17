"""Gate 1: Intent & Formal Specification Contract (PM Agent)."""

from __future__ import annotations

from ..core.types import PipelineContext, PipelineGateID, PipelineState, SpecContract
from .base import PipelineGate


class SpecGate(PipelineGate):
    @property
    def gate_id(self) -> PipelineGateID:
        return PipelineGateID.SPEC

    @property
    def name(self) -> str:
        return "Specification Contract"

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        ctx.current_gate = self.gate_id
        ctx.current_state = PipelineState.SPEC_V1
        ctx.telemetry.pipeline_gate = self.name
        return ctx

    def validate_spec(self, spec: SpecContract) -> list[str]:
        errors: list[str] = []
        required_fields = [
            "spec_version", "security_clearance", "correlation_id",
            "domain_boundary", "contract_interface",
            "architectural_invariants", "mutation_testing_criteria",
        ]
        for field in required_fields:
            if field not in spec:
                errors.append(f"Missing required field: {field}")

        if "context_name" not in spec.get("domain_boundary", {}):
            errors.append("domain_boundary.context_name is required")
        if "aggregate_root" not in spec.get("domain_boundary", {}):
            errors.append("domain_boundary.aggregate_root is required")

        contract = spec.get("contract_interface", {})
        if "strict_inputs" not in contract:
            errors.append("contract_interface.strict_inputs is required")
        if "strict_outputs" not in contract:
            errors.append("contract_interface.strict_outputs is required")

        return errors
