"""PM Agent: transforms raw intent into a formal SpecContract."""

from __future__ import annotations

import json
import uuid
from typing import Any

from .base import LLMAgent, LLMConfig, LLMResponse
from ..core.types import SpecContract


class PMAgent(LLMAgent):
    def __init__(self, config: LLMConfig | None = None):
        super().__init__(config)

    def build_system_prompt(self) -> str:
        return (
            "You are a Formal Contract Engine. "
            "Translate raw business intent into a strictly typed SpecContract JSON. "
            "Output ONLY valid JSON matching the SpecContract schema."
        )

    async def generate_spec(self, raw_intent: str) -> SpecContract:
        response: LLMResponse = await self.call(
            prompt=(
                f"Raw intent: {raw_intent}\n\n"
                "Generate a SpecContract JSON with:\n"
                "- spec_version: '3.0.0'\n"
                "- security_clearance: 'enterprise-restricted'\n"
                "- correlation_id: tx- format\n"
                "- domain_boundary (context_name, aggregate_root)\n"
                "- project_metadata (project_type: web_api|cli|library|pipeline, framework, deployment_target, structured_as: modular|monolithic)\n"
                "- contract_interface (strict_inputs, strict_outputs with validation)\n"
                "- architectural_invariants\n"
                "- mutation_testing_criteria\n"
                "- fail_safe_protocols\n"
                "- context (domain, assumptions as list, dependencies as list)\n"
                "- constraints (list of {type: performance|cost|security, description})\n"
                "- acceptance_criteria (list of {id, description, measurable})\n"
                "- failure_modes (list of {type, cause, mitigation})\n"
                "- observability (logs as list, metrics as list, tracing as list)\n"
                "Output ONLY valid JSON."
            ),
            system_prompt=self.build_system_prompt(),
        )

        try:
            spec_data = json.loads(response.content)
        except json.JSONDecodeError:
            spec_data = self._build_default_spec(raw_intent)

        return self._normalize_spec(spec_data, raw_intent)

    def _normalize_spec(self, spec: Any, raw_intent: str) -> SpecContract:
        if not isinstance(spec, dict):
            return self._build_default_spec(raw_intent)

        if "contract_interface" not in spec or not isinstance(spec["contract_interface"], dict):
            spec["contract_interface"] = {}

        contract = spec["contract_interface"]
        for key in ("strict_inputs", "strict_outputs"):
            items = contract.get(key, [])
            if isinstance(items, list):
                contract[key] = [
                    {"name": item, "type": "string", "format": None, "minimum": None, "maximum": None, "pattern": None, "enum": None, "required": True}
                    if isinstance(item, str)
                    else item
                    for item in items
                ]

        return spec

    def _build_default_spec(self, raw_intent: str) -> SpecContract:
        return {
            "spec_version": "3.0.0",
            "security_clearance": "enterprise-restricted",
            "correlation_id": f"tx-{uuid.uuid4().hex[:18]}",
            "domain_boundary": {
                "context_name": raw_intent.split()[0] if raw_intent else "Unknown",
                "aggregate_root": "DefaultRoot",
            },
            "project_metadata": {
                "project_type": "web_api",
                "framework": "fastapi",
                "deployment_target": "docker",
                "structured_as": "modular",
            },
            "contract_interface": {
                "strict_inputs": [
                    {
                        "name": "input_data",
                        "type": "string",
                        "format": None,
                        "minimum": None,
                        "maximum": None,
                        "pattern": None,
                        "enum": None,
                        "required": True,
                    }
                ],
                "strict_outputs": [
                    {
                        "name": "result",
                        "type": "string",
                        "format": None,
                        "minimum": None,
                        "maximum": None,
                        "pattern": None,
                        "enum": None,
                        "required": True,
                    }
                ],
            },
            "architectural_invariants": {
                "concurrency_control": "optimistic_locking",
                "idempotency_strategy": "header_token_verification",
                "allow_shared_memory": False,
            },
            "mutation_testing_criteria": {
                "minimum_mutation_score": 0.85,
                "target_test_framework": "pytest-v8",
                "excluded_mutators": ["ODD_FLAVOR_MUTATION"],
            },
            "fail_safe_protocols": [
                {
                    "trigger_exception": "TimeoutException",
                    "reversal_action": "abort_and_emit_compensation",
                }
            ],
            "context": {
                "domain": "general",
                "assumptions": ["Standard operating environment"],
                "dependencies": ["Python 3.12+"],
            },
            "constraints": [
                {"type": "performance", "description": "Response under 500ms"},
                {"type": "security", "description": "Input validation required"},
            ],
            "acceptance_criteria": [
                {"id": "AC-01", "description": "All tests pass", "measurable": True},
            ],
            "failure_modes": [
                {"type": "input_error", "cause": "Invalid input", "mitigation": "Return 400"},
            ],
            "observability": {
                "logs": ["application"],
                "metrics": ["response_time", "error_rate"],
                "tracing": ["request_id"],
            },
        }
