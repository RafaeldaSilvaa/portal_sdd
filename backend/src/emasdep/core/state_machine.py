"""State Machine: hierarchical DAG with rollback support."""

from __future__ import annotations

from dataclasses import dataclass, field

from .types import PipelineContext, PipelineGateID, PipelineState


@dataclass
class StateTransition:
    from_state: PipelineState
    to_state: PipelineState
    gate: PipelineGateID | None
    condition: str = ""


STATE_GRAPH: list[StateTransition] = [
    StateTransition(PipelineState.INIT, PipelineState.SPEC_V1, PipelineGateID.SPEC),
    StateTransition(PipelineState.SPEC_V1, PipelineState.BLOCKED_PROBE, PipelineGateID.PROBING, "ambiguity > threshold"),
    StateTransition(PipelineState.SPEC_V1, PipelineState.DESIGN, PipelineGateID.PROBING, "ambiguity <= threshold"),
    StateTransition(PipelineState.BLOCKED_PROBE, PipelineState.SPEC_V1, PipelineGateID.SPEC, "human answered"),
    StateTransition(PipelineState.DESIGN, PipelineState.RISK_ANALYSIS, PipelineGateID.RISK_ANALYSIS),
    StateTransition(PipelineState.RISK_ANALYSIS, PipelineState.PLANNING, PipelineGateID.PLANNER),
    StateTransition(PipelineState.PLANNING, PipelineState.TESTING, PipelineGateID.QA),
    StateTransition(PipelineState.TESTING, PipelineState.CODING, PipelineGateID.ENGINEER),
    StateTransition(PipelineState.CODING, PipelineState.HEALING_LOOP, None, "test failure"),
    StateTransition(PipelineState.HEALING_LOOP, PipelineState.CODING, PipelineGateID.ENGINEER, "retry"),
    StateTransition(PipelineState.HEALING_LOOP, PipelineState.PLANNING, PipelineGateID.PLANNER, "circuit open"),
    StateTransition(PipelineState.CODING, PipelineState.VALIDATION, PipelineGateID.CONVERGENCE),
    StateTransition(PipelineState.VALIDATION, PipelineState.CONVERGED, None, "all gates passed"),
    StateTransition(PipelineState.VALIDATION, PipelineState.CODING, PipelineGateID.ENGINEER, "validation failed"),

]


class StateMachine:
    def __init__(self, initial_state: PipelineState = PipelineState.INIT):
        self._state = initial_state

    @property
    def state(self) -> PipelineState:
        return self._state

    def can_transition(self, target: PipelineState) -> bool:
        return any(
            t.from_state == self._state and t.to_state == target
            for t in STATE_GRAPH
        )

    def transition(self, target: PipelineState, condition: str = "") -> PipelineState:
        valid = [
            t
            for t in STATE_GRAPH
            if t.from_state == self._state and t.to_state == target
        ]
        if not valid:
            raise ValueError(
                f"No valid transition from {self._state.name} to {target.name}"
            )
        if condition:
            matching = [t for t in valid if t.condition == condition]
            if matching:
                valid = matching
        self._state = valid[0].to_state
        return self._state

    def get_next_gate(self) -> PipelineGateID | None:
        gate_map = {
            PipelineState.INIT: PipelineGateID.SPEC,
            PipelineState.SPEC_V1: PipelineGateID.PROBING,
            PipelineState.BLOCKED_PROBE: PipelineGateID.SPEC,
            PipelineState.DESIGN: PipelineGateID.ARCHITECTURE,
            PipelineState.RISK_ANALYSIS: PipelineGateID.RISK_ANALYSIS,
            PipelineState.PLANNING: PipelineGateID.PLANNER,
            PipelineState.TESTING: PipelineGateID.QA,
            PipelineState.CODING: PipelineGateID.ENGINEER,
            PipelineState.VALIDATION: PipelineGateID.CONVERGENCE,
        }
        return gate_map.get(self._state)
