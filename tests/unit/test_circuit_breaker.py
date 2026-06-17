import pytest
from emasdep.core.circuit_breaker import CircuitBreaker, CircuitState, RollbackTarget
from emasdep.core.types import PipelineGateID


class TestCircuitBreaker:
    def test_default_state_is_closed(self):
        breaker = CircuitBreaker(gate_id=PipelineGateID.ENGINEER)
        assert breaker._state == CircuitState.CLOSED

    def test_not_tripped_initially(self):
        breaker = CircuitBreaker(gate_id=PipelineGateID.ENGINEER)
        assert breaker.is_tripped is False

    def test_remaining_attempts_starts_at_max(self):
        breaker = CircuitBreaker(gate_id=PipelineGateID.ENGINEER, max_attempts=3)
        assert breaker.remaining_attempts == 3

    def test_record_attempt_decrements_remaining(self):
        breaker = CircuitBreaker(gate_id=PipelineGateID.ENGINEER, max_attempts=3)
        breaker.record_attempt()
        assert breaker.remaining_attempts == 2

    def test_record_attempt_returns_closed_before_limit(self):
        breaker = CircuitBreaker(gate_id=PipelineGateID.ENGINEER, max_attempts=3)
        state = breaker.record_attempt()
        assert state == CircuitState.CLOSED

    def test_circuit_opens_after_max_attempts(self):
        breaker = CircuitBreaker(gate_id=PipelineGateID.ENGINEER, max_attempts=2)
        breaker.record_attempt()
        state = breaker.record_attempt()
        assert state == CircuitState.OPEN
        assert breaker.is_tripped is True

    def test_remaining_attempts_zero_when_tripped(self):
        breaker = CircuitBreaker(gate_id=PipelineGateID.ENGINEER, max_attempts=1)
        breaker.record_attempt()
        assert breaker.remaining_attempts == 0

    def test_get_rollback_target_for_engineer_returns_planner(self):
        breaker = CircuitBreaker(gate_id=PipelineGateID.ENGINEER)
        assert breaker.get_rollback_target() == RollbackTarget.PLANNER

    def test_get_rollback_target_for_qa_returns_planner(self):
        breaker = CircuitBreaker(gate_id=PipelineGateID.QA)
        assert breaker.get_rollback_target() == RollbackTarget.PLANNER

    def test_get_rollback_target_for_spec_returns_previous(self):
        breaker = CircuitBreaker(gate_id=PipelineGateID.SPEC)
        assert breaker.get_rollback_target() == RollbackTarget.PREVIOUS_GATE

    def test_reset_restores_initial_state(self):
        breaker = CircuitBreaker(gate_id=PipelineGateID.ENGINEER, max_attempts=2)
        breaker.record_attempt()
        breaker.record_attempt()
        assert breaker.is_tripped is True
        breaker.reset()
        assert breaker.is_tripped is False
        assert breaker.remaining_attempts == 2
