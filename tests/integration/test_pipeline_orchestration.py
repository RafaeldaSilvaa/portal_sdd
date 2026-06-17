"""Integration tests for the EMASDEP pipeline orchestration."""

import pytest

from emasdep.core.types import PipelineContext, PipelineGateID, PipelineState
from emasdep.gates.gate_01_spec import SpecGate
from emasdep.gates.gate_02_probing import ProbingGate
from emasdep.gates.gate_03_arch import ArchitectureGate


class TestPipelineGatesIntegration:
    @pytest.fixture
    def ctx(self):
        return PipelineContext()

    @pytest.mark.asyncio
    async def test_spec_to_probing_transition(self, ctx):
        spec_gate = SpecGate()
        ctx = await spec_gate.process(ctx)
        assert ctx.current_gate == PipelineGateID.SPEC
        assert ctx.current_state == PipelineState.SPEC_V1

        probing_gate = ProbingGate()
        ctx_after = await probing_gate.process(ctx)
        assert ctx_after is not None

    @pytest.mark.asyncio
    async def test_pipeline_starts_in_init_state(self, ctx):
        assert ctx.current_state == PipelineState.INIT
        assert ctx.correlation_id.startswith("tx-")

    def test_pipeline_context_version_increments(self, ctx):
        v1 = ctx.version
        ctx.increment_version()
        assert ctx.version == v1 + 1

    @pytest.mark.asyncio
    async def test_architecture_gate_requires_spec(self, ctx):
        arch_gate = ArchitectureGate()
        ctx = await arch_gate.process(ctx)
        assert ctx.current_state == PipelineState.FAILED
        assert "No spec available" in (ctx.failure_reason or "")


class TestPipelineContext:
    def test_snapshots_are_append_only(self):
        from emasdep.core.types import CodePatchSnapshot

        ctx = PipelineContext()
        assert len(ctx.snapshots) == 0

        ctx.snapshots.append(
            CodePatchSnapshot.create(
                filepath="test.py", contents="code", crash_log=""
            )
        )
        assert len(ctx.snapshots) == 1

    def test_telemetry_trace_id_is_generated(self):
        ctx = PipelineContext()
        assert len(ctx.telemetry.trace_id) == 20

    def test_code_artifacts_can_be_stored(self):
        ctx = PipelineContext()
        ctx.code_artifacts["module_1.py"] = "def hello(): pass"
        assert ctx.code_artifacts["module_1.py"] == "def hello(): pass"
