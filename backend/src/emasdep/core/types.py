from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from datetime import timezone as tz
from enum import Enum, auto
from pathlib import Path
from typing import TypedDict


class PipelineGateID(Enum):
    SPEC = 1
    PROBING = 2
    ARCHITECTURE = 3
    PLANNER = 4
    QA = 5
    ENGINEER = 6
    CONVERGENCE = 7


class PipelineState(Enum):
    INIT = auto()
    SPEC_V1 = auto()
    BLOCKED_PROBE = auto()
    DESIGN = auto()
    PLANNING = auto()
    TESTING = auto()
    CODING = auto()
    HEALING_LOOP = auto()
    VALIDATION = auto()
    CONVERGED = auto()
    FAILED = auto()


class AgentRole(Enum):
    PM = "pm"
    ARCHITECT = "architect"
    PLANNER = "planner"
    ENGINEER = "engineer"
    QA = "qa"
    ORCHESTRATOR = "orchestrator"


class ThinkingMode(Enum):
    DISABLED = "disabled"
    ENABLED_HIGH = "enabled_high"
    ENABLED_MAX = "enabled_max"


# --- Spec Contract Types ---

class DomainBoundary(TypedDict):
    context_name: str
    aggregate_root: str


class InputProperty(TypedDict):
    name: str
    type: str
    format: str | None
    minimum: int | None
    maximum: int | None
    pattern: str | None
    enum: list[str] | None
    required: bool


class ContractInterface(TypedDict):
    strict_inputs: list[InputProperty]
    strict_outputs: list[InputProperty]


class ArchitecturalInvariants(TypedDict):
    concurrency_control: str
    idempotency_strategy: str
    allow_shared_memory: bool


class MutationCriteria(TypedDict):
    minimum_mutation_score: float
    target_test_framework: str
    excluded_mutators: list[str]


class FailSafeProtocol(TypedDict):
    trigger_exception: str
    reversal_action: str


class SpecContract(TypedDict):
    spec_version: str
    security_clearance: str
    correlation_id: str
    domain_boundary: DomainBoundary
    contract_interface: ContractInterface
    architectural_invariants: ArchitecturalInvariants
    mutation_testing_criteria: MutationCriteria
    fail_safe_protocols: list[FailSafeProtocol]


# --- Task / DAG Types ---

@dataclass
class TaskNode:
    task_id: str
    description: str
    dependencies: list[str]
    agent_role: AgentRole
    target_files: list[str] = field(default_factory=list)
    estimated_complexity: int = 1
    status: str = "pending"


@dataclass
class TaskDAG:
    tasks: dict[str, TaskNode] = field(default_factory=dict)
    topological_order: list[str] = field(default_factory=list)


# --- Snapshot Types ---

@dataclass
class CodePatchSnapshot:
    state_id: str
    target_filepath: Path
    original_contents: str
    crash_log: str
    created_at: datetime = field(default_factory=lambda: datetime.now(tz.utc))

    @classmethod
    def create(cls, filepath: Path, contents: str, crash_log: str = "") -> CodePatchSnapshot:
        return cls(
            state_id=f"snap_{uuid.uuid4().hex[:12]}",
            target_filepath=filepath,
            original_contents=contents,
            crash_log=crash_log,
        )


@dataclass
class TestSuiteResult:
    passed: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_message: str = ""


@dataclass
class MutationResult:
    mutation_score: float
    total_mutants: int
    killed_mutants: int
    survived_mutants: int
    passed_minimum: bool


@dataclass
class ValidationResult:
    ast_clean: bool
    coverage_percent: float
    mutation: MutationResult | None
    passed_all_gates: bool


# --- Telemetry Types ---

@dataclass
class InferenceAnalytics:
    engine_model_resolved: str
    prompt_tokens_total: int
    prompt_tokens_cache_hits: int
    completion_reasoning_tokens: int
    latency_duration_ms: int
    financial_token_cost_usd: float


@dataclass
class PipelineTelemetry:
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:20])
    pipeline_gate: str = ""
    metrics: dict = field(default_factory=dict)
    inference_analytics: InferenceAnalytics | None = None
    mutation_integrity: dict | None = None
    state_checksums: dict = field(default_factory=dict)


# --- Pipeline Context ---

@dataclass
class PipelineContext:
    correlation_id: str = field(default_factory=lambda: f"tx-{uuid.uuid4().hex[:18]}")
    current_state: PipelineState = PipelineState.INIT
    current_gate: PipelineGateID = PipelineGateID.SPEC

    spec: SpecContract | None = None
    sdd: str | None = None  # Architecture document (markdown)
    task_dag: TaskDAG | None = None
    test_suite: str | None = None  # Generated test code
    code_artifacts: dict[str, str] = field(default_factory=dict)
    snapshots: list[CodePatchSnapshot] = field(default_factory=list)
    telemetry: PipelineTelemetry = field(default_factory=PipelineTelemetry)
    validation: ValidationResult | None = None
    failure_reason: str = ""
    version: int = 0

    def increment_version(self) -> int:
        self.version += 1
        return self.version

    def __hash__(self) -> int:
        return hash(self.correlation_id)
