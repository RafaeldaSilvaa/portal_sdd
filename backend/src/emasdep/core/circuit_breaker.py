"""Circuit Breaker: max 3 healing attempts, then rollback to parent node."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from .types import PipelineGateID


class CircuitState(Enum):
    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()


class RollbackTarget(Enum):
    PREVIOUS_GATE = auto()
    ARCHITECT = auto()
    PLANNER = auto()


@dataclass
class CircuitBreaker:
    gate_id: PipelineGateID
    max_attempts: int = 3
    _attempts: int = 0
    _state: CircuitState = CircuitState.CLOSED

    @property
    def is_tripped(self) -> bool:
        return self._state == CircuitState.OPEN

    @property
    def remaining_attempts(self) -> int:
        return max(0, self.max_attempts - self._attempts)

    def record_attempt(self) -> CircuitState:
        """record attempt.

Retorna:
    Descrição do valor retornado."""
        self._attempts += 1
        if self._attempts >= self.max_attempts:
            self._state = CircuitState.OPEN
        return self._state

    def get_rollback_target(self) -> RollbackTarget:
        """get rollback target.

Retorna:
    Descrição do valor retornado."""
        gate_map = {
            PipelineGateID.SPEC: RollbackTarget.PREVIOUS_GATE,
            PipelineGateID.PROBING: RollbackTarget.PREVIOUS_GATE,
            PipelineGateID.ARCHITECTURE: RollbackTarget.PREVIOUS_GATE,
            PipelineGateID.RISK_ANALYSIS: RollbackTarget.PREVIOUS_GATE,
            PipelineGateID.PLANNER: RollbackTarget.ARCHITECT,
            PipelineGateID.QA: RollbackTarget.PLANNER,
            PipelineGateID.ENGINEER: RollbackTarget.PLANNER,
            PipelineGateID.CONVERGENCE: RollbackTarget.PREVIOUS_GATE,
        }
        return gate_map.get(self.gate_id, RollbackTarget.PREVIOUS_GATE)

    def reset(self) -> None:
        """reset.

Retorna:
    Descrição do valor retornado."""
        self._attempts = 0
        self._state = CircuitState.CLOSED
