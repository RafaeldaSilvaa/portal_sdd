"""Abstract base class for all Pipeline Gates."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..core.types import PipelineContext, PipelineGateID


class PipelineGate(ABC):
    @abstractmethod
    async def process(self, ctx: PipelineContext) -> PipelineContext:
        ...

    @property
    @abstractmethod
    def gate_id(self) -> PipelineGateID:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...
