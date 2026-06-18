from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from datetime import timezone as tz
from enum import Enum, auto
from pathlib import Path
from typing import Any, TypedDict


class PipelineGateID(Enum):
    SPEC = 1
    PROBING = 2
    ARCHITECTURE = 3
    RISK_ANALYSIS = 4
    PLANNER = 5
    QA = 6
    ENGINEER = 7
    CONVERGENCE = 8


class PipelineState(Enum):
    INIT = auto()
    SPEC_V1 = auto()
    BLOCKED_PROBE = auto()
    DESIGN = auto()
    RISK_ANALYSIS = auto()
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


# --- Standardized Agent Output ---

@dataclass
class AgentOutput:
    status: str  # "success" | "error"
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @classmethod
    def ok(cls, data: dict[str, Any] | None = None) -> AgentOutput:
        return cls(status="success", data=data or {})

    @classmethod
    def fail(cls, error: str) -> AgentOutput:
        return cls(status="error", errors=[error])


# --- Spec Contract Types (expanded) ---

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


class SpecContext(TypedDict):
    domain: str
    assumptions: list[str]
    dependencies: list[str]


class SpecConstraint(TypedDict):
    type: str  # performance | cost | security
    description: str


class AcceptanceCriterion(TypedDict):
    id: str
    description: str
    measurable: bool


class FailureMode(TypedDict):
    type: str
    cause: str
    mitigation: str


class ObservabilitySpec(TypedDict):
    logs: list[str]
    metrics: list[str]
    tracing: list[str]


class SpecContract(TypedDict):
    spec_version: str
    security_clearance: str
    correlation_id: str
    domain_boundary: DomainBoundary
    contract_interface: ContractInterface
    architectural_invariants: ArchitecturalInvariants
    mutation_testing_criteria: MutationCriteria
    fail_safe_protocols: list[FailSafeProtocol]
    context: SpecContext | None
    constraints: list[SpecConstraint] | None
    acceptance_criteria: list[AcceptanceCriterion] | None
    failure_modes: list[FailureMode] | None
    observability: ObservabilitySpec | None


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


# --- Failure Classification ---

class FailureCategory(Enum):
    HALLUCINATION = "hallucination"
    SCHEMA_VIOLATION = "schema_violation"
    TIMEOUT = "timeout"
    LOGIC_ERROR = "logic_error"
    DEPENDENCY_FAILURE = "dependency_failure"
    UNKNOWN = "unknown"


# --- Snapshot Types ---

@dataclass
class CodePatchSnapshot:
    state_id: str
    target_filepath: Path
    original_contents: str
    crash_log: str
    failure_category: FailureCategory = FailureCategory.UNKNOWN
    created_at: datetime = field(default_factory=lambda: datetime.now(tz.utc))

    @classmethod
    def create(cls, filepath: Path, contents: str, crash_log: str = "", failure_category: FailureCategory = FailureCategory.UNKNOWN) -> CodePatchSnapshot:
        return cls(
            state_id=f"snap_{uuid.uuid4().hex[:12]}",
            target_filepath=filepath,
            original_contents=contents,
            crash_log=crash_log,
            failure_category=failure_category,
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
    eval_score: float = 0.0        # LLM-as-Judge score (0-10)
    eval_confidence: float = 0.0   # 0-1
    eval_issues: list[str] = field(default_factory=list)
    eval_action: str = "accept"    # accept | retry | replan


# --- Risk Analysis Types ---

@dataclass
class RiskItem:
    description: str
    probability: float  # 0-1
    impact: str  # low | medium | high | critical
    mitigation: str


@dataclass
class TradeOff:
    decision: str
    pros: list[str]
    cons: list[str]
    recommended: bool


@dataclass
class RiskAnalysis:
    risks: list[RiskItem] = field(default_factory=list)
    trade_offs: list[TradeOff] = field(default_factory=list)
    overall_risk_score: float = 0.0
    recommendations: list[str] = field(default_factory=list)


# --- Guardrails ---

@dataclass
class GuardrailViolation:
    rule: str
    severity: str  # error | warning
    detail: str


@dataclass
class GuardrailResult:
    passed: bool
    violations: list[GuardrailViolation] = field(default_factory=list)


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
class AgentTraceEntry:
    agent_role: str
    gate: str
    latency_ms: int
    token_usage: int
    status: str  # success | error | retry


@dataclass
class PipelineTelemetry:
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:20])
    pipeline_gate: str = ""
    metrics: dict = field(default_factory=dict)
    inference_analytics: InferenceAnalytics | None = None
    mutation_integrity: dict | None = None
    state_checksums: dict = field(default_factory=dict)
    agent_trace: list[AgentTraceEntry] = field(default_factory=list)
    total_latency_ms: int = 0
    total_tokens: int = 0


# --- Memory / RAG Types ---

@dataclass
class MemoryEntry:
    id: str
    entry_type: str  # episodic | semantic | architectural
    content: str
    metadata: dict = field(default_factory=dict)
    embedding: list[float] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(tz.utc))

    @classmethod
    def create(cls, entry_type: str, content: str, metadata: dict | None = None) -> MemoryEntry:
        return cls(
            id=f"mem_{uuid.uuid4().hex[:12]}",
            entry_type=entry_type,
            content=content,
            metadata=metadata or {},
        )


@dataclass
class MemoryResult:
    entries: list[MemoryEntry] = field(default_factory=list)
    scores: list[float] = field(default_factory=list)


# --- Token Optimization Types ---

@dataclass
class CompressedContext:
    original_length: int
    compressed_length: int
    content: str
    removed_sections: list[str] = field(default_factory=list)


# --- Pipeline Context ---

@dataclass
class PipelineContext:
    correlation_id: str = field(default_factory=lambda: f"tx-{uuid.uuid4().hex[:18]}")
    current_state: PipelineState = PipelineState.INIT
    current_gate: PipelineGateID = PipelineGateID.SPEC

    spec: SpecContract | None = None
    sdd: str | None = None
    risk_analysis: RiskAnalysis | None = None
    task_dag: TaskDAG | None = None
    test_suite: str | None = None
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
