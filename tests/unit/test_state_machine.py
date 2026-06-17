import pytest
from emasdep.core.state_machine import StateMachine
from emasdep.core.types import PipelineState


class TestStateMachine:
    def test_initial_state_is_init(self):
        sm = StateMachine()
        assert sm.state == PipelineState.INIT

    def test_transition_from_init_to_spec_v1(self):
        sm = StateMachine()
        new_state = sm.transition(PipelineState.SPEC_V1)
        assert new_state == PipelineState.SPEC_V1
        assert sm.state == PipelineState.SPEC_V1

    def test_transition_with_condition_matches_correct_path(self):
        sm = StateMachine(PipelineState.SPEC_V1)
        new_state = sm.transition(PipelineState.DESIGN, condition="ambiguity <= threshold")
        assert new_state == PipelineState.DESIGN

    def test_invalid_transition_raises_error(self):
        sm = StateMachine(PipelineState.CONVERGED)
        with pytest.raises(ValueError, match="No valid transition"):
            sm.transition(PipelineState.INIT)

    def test_get_next_gate_returns_correct_gate(self):
        sm = StateMachine(PipelineState.PLANNING)
        from emasdep.core.types import PipelineGateID
        assert sm.get_next_gate() == PipelineGateID.PLANNER

    def test_get_next_gate_returns_none_when_no_mapping(self):
        sm = StateMachine(PipelineState.CONVERGED)
        assert sm.get_next_gate() is None

    def test_can_transition_returns_true_for_valid(self):
        sm = StateMachine(PipelineState.INIT)
        assert sm.can_transition(PipelineState.SPEC_V1) is True

    def test_can_transition_returns_false_for_invalid(self):
        sm = StateMachine(PipelineState.INIT)
        assert sm.can_transition(PipelineState.CONVERGED) is False

    def test_blocked_probe_transitions_back_to_spec_v1(self):
        sm = StateMachine(PipelineState.BLOCKED_PROBE)
        new_state = sm.transition(PipelineState.SPEC_V1, condition="human answered")
        assert new_state == PipelineState.SPEC_V1

    def test_multiple_transitions_through_pipeline(self):
        sm = StateMachine()
        sm.transition(PipelineState.SPEC_V1)
        sm.transition(PipelineState.DESIGN, condition="ambiguity <= threshold")
        sm.transition(PipelineState.PLANNING)
        sm.transition(PipelineState.TESTING)
        sm.transition(PipelineState.CODING)
        assert sm.state == PipelineState.CODING
