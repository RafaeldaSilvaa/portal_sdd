import pytest
from emasdep.gates.gate_01_spec import SpecGate
from emasdep.core.types import SpecContract


class TestSpecGate:
    @pytest.fixture
    def gate(self):
        return SpecGate()

    def test_gate_id_is_spec(self, gate):
        from emasdep.core.types import PipelineGateID
        assert gate.gate_id == PipelineGateID.SPEC

    def test_gate_name(self, gate):
        assert gate.name == "Specification Contract"

    def test_validate_complete_spec_returns_no_errors(self, gate):
        spec: SpecContract = {
            "spec_version": "3.0.0",
            "security_clearance": "enterprise-restricted",
            "correlation_id": "tx-test",
            "domain_boundary": {"context_name": "Test", "aggregate_root": "Entity"},
            "contract_interface": {
                "strict_inputs": [],
                "strict_outputs": [],
            },
            "architectural_invariants": {
                "concurrency_control": "optimistic_locking",
                "idempotency_strategy": "header",
                "allow_shared_memory": False,
            },
            "mutation_testing_criteria": {
                "minimum_mutation_score": 0.85,
                "target_test_framework": "pytest",
                "excluded_mutators": [],
            },
            "fail_safe_protocols": [],
        }
        errors = gate.validate_spec(spec)
        assert len(errors) == 0

    def test_validate_missing_domain_boundary(self, gate):
        spec: SpecContract = {
            "spec_version": "3.0.0",
            "security_clearance": "enterprise-restricted",
            "correlation_id": "tx-test",
            "domain_boundary": {},
            "contract_interface": {"strict_inputs": [], "strict_outputs": []},
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
        errors = gate.validate_spec(spec)
        assert any("context_name" in e for e in errors)

    def test_validate_missing_required_fields(self, gate):
        spec: SpecContract = {}
        errors = gate.validate_spec(spec)
        assert len(errors) >= 6

    def test_validate_missing_contract_interface(self, gate):
        spec: SpecContract = {
            "spec_version": "3.0.0",
            "security_clearance": "enterprise-restricted",
            "correlation_id": "tx-test",
            "domain_boundary": {"context_name": "X", "aggregate_root": "Y"},
        }
        errors = gate.validate_spec(spec)
        assert any("contract_interface" in e for e in errors)
