import pytest
from emasdep.gates.gate_02_probing import ProbingGate
from emasdep.core.types import SpecContract


class TestProbingGate:
    @pytest.fixture
    def gate(self):
        return ProbingGate()

    def test_clear_spec_proceeds_to_design(self, gate):
        spec: SpecContract = {
            "spec_version": "3.0.0",
            "security_clearance": "enterprise-restricted",
            "correlation_id": "tx-test",
            "domain_boundary": {"context_name": "Test", "aggregate_root": "Entity"},
            "contract_interface": {
                "strict_inputs": [
                    {
                        "name": "amount",
                        "type": "integer",
                        "format": None,
                        "minimum": 1,
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
                        "pattern": "^[A-Z]+$",
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
                "excluded_mutators": [],
            },
            "fail_safe_protocols": [
                {
                    "trigger_exception": "TimeoutException",
                    "reversal_action": "abort_and_retry",
                }
            ],
        }

        result = gate.evaluate_spec_clarity("test intent", spec)
        assert result["action"] == "PROCEED_TO_DESIGN"

    def test_vague_spec_blocks_with_questions(self, gate):
        spec: SpecContract = {
            "spec_version": "3.0.0",
            "security_clearance": "enterprise-restricted",
            "correlation_id": "tx-vague",
            "domain_boundary": {"context_name": "Test", "aggregate_root": "Entity"},
            "contract_interface": {
                "strict_inputs": [
                    {
                        "name": "data",
                        "type": "string",
                        "format": None,
                        "minimum": None,
                        "maximum": None,
                        "pattern": None,
                        "enum": None,
                        "required": True,
                    }
                ],
                "strict_outputs": [],
            },
            "architectural_invariants": {
                "concurrency_control": "pessimistic",
                "idempotency_strategy": "none",
                "allow_shared_memory": True,
            },
            "mutation_testing_criteria": {
                "minimum_mutation_score": 0.5,
                "target_test_framework": "unittest",
                "excluded_mutators": [],
            },
            "fail_safe_protocols": [],
        }

        result = gate.evaluate_spec_clarity("vague intent", spec)
        assert result["action"] == "BLOCK_AND_PROBE"
        assert len(result["questionnaire"]) > 0

    def test_ambiguity_score_exceeds_threshold_when_missing_fields(self, gate):
        spec: SpecContract = {
            "spec_version": "3.0.0",
            "security_clearance": "enterprise-restricted",
            "correlation_id": "tx-ambig",
            "domain_boundary": {"context_name": "X", "aggregate_root": "Y"},
            "contract_interface": {
                "strict_inputs": [
                    {
                        "name": "x",
                        "type": "string",
                        "format": None,
                        "minimum": None,
                        "maximum": None,
                        "pattern": None,
                        "enum": None,
                        "required": True,
                    }
                ],
                "strict_outputs": [],
            },
            "architectural_invariants": {
                "concurrency_control": "none",
                "idempotency_strategy": "none",
                "allow_shared_memory": True,
            },
            "mutation_testing_criteria": {
                "minimum_mutation_score": 0.5,
                "target_test_framework": "unittest",
                "excluded_mutators": [],
            },
            "fail_safe_protocols": [],
        }

        result = gate.evaluate_spec_clarity("test", spec)
        assert result["ambiguity_score"] > 0.15

    def test_questionnaire_includes_missing_validation_rules(self, gate):
        spec: SpecContract = {
            "spec_version": "3.0.0",
            "security_clearance": "enterprise-restricted",
            "correlation_id": "tx-q",
            "domain_boundary": {"context_name": "T", "aggregate_root": "E"},
            "contract_interface": {
                "strict_inputs": [
                    {
                        "name": "email",
                        "type": "string",
                        "format": None,
                        "minimum": None,
                        "maximum": None,
                        "pattern": None,
                        "enum": None,
                        "required": True,
                    }
                ],
                "strict_outputs": [],
            },
            "architectural_invariants": {
                "concurrency_control": "none",
                "idempotency_strategy": "none",
                "allow_shared_memory": False,
            },
            "mutation_testing_criteria": {
                "minimum_mutation_score": 0.85,
                "target_test_framework": "pytest",
                "excluded_mutators": [],
            },
            "fail_safe_protocols": [],
        }

        result = gate.evaluate_spec_clarity("test", spec)
        questions = result["questionnaire"]
        assert any("email" in q["context"] for q in questions)
