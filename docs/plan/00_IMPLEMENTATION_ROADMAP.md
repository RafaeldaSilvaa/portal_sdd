# EMASDEP v3.0 - Plano de Implementação Completo

## 1. VISÃO GERAL DA ARQUITETURA

EMASDEP (Enterprise Multi-Agent Spec-Driven Engineering Platform) é um
ecossistema determinístico de agentes autônomos que transforma intenção de
negócio em artefatos de software testados e prontos para produção.

### Stack Tecnológica
- **Runtime:** Python 3.12+ (strict typing, protocolos, dataclasses)
- **Inferência:** DeepSeek V4 Flash (via API REST)
- **Testes:** pytest 8 + mutmut (mutação)
- **Validação:** ruff + mypy --strict
- **Estado:** SQLite/RocksDB (transacional ponto-no-tempo)
- **Container:** Docker + gVisor (sandbox isolado)

### Mapa de Módulos

```
src/emasdep/
├── __init__.py              # Versão, metadata
├── main.py                  # Entrypoint CLI
├── config.py                # Config central (pydantic-settings)
│
├── core/                    # Núcleo determinístico
│   ├── types.py             # Tipos compartilhados (Spec, Task, Snapshot)
│   ├── state_machine.py     # Máquina de estados hierárquica (DAG)
│   └── circuit_breaker.py   # Circuit Breaker (3 tentativas máx)
│
├── gates/                   # Pipeline Gates (1-7)
│   ├── gate_01_spec.py      # PM Agent: Contrato de Spec
│   ├── gate_02_probing.py   # Proactive Probing
│   ├── gate_03_arch.py      # Architect Agent: SDD
│   ├── gate_04_planner.py   # Planner Agent: DAG de tarefas
│   ├── gate_05_qa.py        # QA Agent: Testes + mutação
│   ├── gate_06_engineer.py  # Engineer Agent: Código sandbox
│   └── gate_07_conv.py      # Convergência criptográfica
│
├── agents/                  # Wrappers de inferência
│   ├── base.py              # Classe base LLM Client
│   ├── pm_agent.py          # Formal Contract Engine
│   ├── architect_agent.py   # Architectural Guard
│   ├── planner_agent.py     # Graph Compiler
│   ├── engineer_agent.py    # High-Velocity Constructor
│   └── qa_agent.py          # Adversarial Mutator
│
├── skills/                  # SkillOps Engine (§7)
│   ├── registry.py          # Skill Registry
│   └── synthesizer.py       # On-Demand Synthesis
│
├── healing/                 # Self-Healing Engine (§9)
│   ├── engine.py            # Transactional Healing
│   └── snapshot.py          # State Snapshot
│
├── telemetry/               # AgentOps (§12)
│   ├── tracer.py            # Tracing estruturado
│   └── metrics.py           # Métricas de execução
│
├── sandbox/                 # Sandbox Isolado (§13)
│   ├── executor.py          # Executor containerizado
│   └── isolation.py         # Políticas de isolamento
│
└── validation/              # Gates de qualidade (§11)
    ├── mutation.py          # Mutation Testing Gate
    ├── coverage.py          # Code Coverage Tracker
    └── ast_validator.py     # Syntactic AST Integrity
```

---

## 2. FASES DE IMPLEMENTAÇÃO

### FASE 1: Fundação (Core + Config)
**Objetivo:** Base determinística do sistema

| # | Tarefa | Arquivos | Dependências |
|---|--------|----------|--------------|
| 1.1 | Tipos compartilhados | `core/types.py` | - |
| 1.2 | Máquina de estados | `core/state_machine.py` | 1.1 |
| 1.3 | Circuit Breaker | `core/circuit_breaker.py` | 1.1 |
| 1.4 | Config central | `config.py` | - |
| 1.5 | CLI entrypoint | `main.py` | 1.1-1.4 |

### FASE 2: Pipeline Gates Core
**Objetivo:** Implementar os 7 gates como classes independentes

| # | Tarefa | Arquivos | Dependências |
|---|--------|----------|--------------|
| 2.1 | Gate 1 - Contrato Spec | `gates/gate_01_spec.py` | Fase 1 |
| 2.2 | Gate 2 - Probing | `gates/gate_02_probing.py` | 2.1 |
| 2.3 | Gate 3 - Arquitetura | `gates/gate_03_arch.py` | 2.2 |
| 2.4 | Gate 4 - Planner DAG | `gates/gate_04_planner.py` | 2.3 |
| 2.5 | Gate 5 - QA/Mutação | `gates/gate_05_qa.py` | 2.4 |
| 2.6 | Gate 6 - Engineer | `gates/gate_06_engineer.py` | 2.5 |
| 2.7 | Gate 7 - Convergência | `gates/gate_07_conv.py` | 2.6 |

### FASE 3: Agentes de Inferência
**Objetivo:** Conectar gates ao DeepSeek V4

| # | Tarefa | Arquivos | Dependências |
|---|--------|----------|--------------|
| 3.1 | Base Agent (LLM Client) | `agents/base.py` | Fase 1 |
| 3.2 | PM Agent | `agents/pm_agent.py` | 3.1 |
| 3.3 | Architect Agent | `agents/architect_agent.py` | 3.1 |
| 3.4 | Planner Agent | `agents/planner_agent.py` | 3.1 |
| 3.5 | QA Agent | `agents/qa_agent.py` | 3.1 |
| 3.6 | Engineer Agent | `agents/engineer_agent.py` | 3.1 |

### FASE 4: Infraestrutura Avançada
**Objetivo:** Sistemas de suporte (healing, sandbox, telemetria)

| # | Tarefa | Arquivos | Dependências |
|---|--------|----------|--------------|
| 4.1 | SkillOps Registry | `skills/registry.py` | Fase 1 |
| 4.2 | SkillOps Synthesizer | `skills/synthesizer.py` | 4.1 |
| 4.3 | Healing Engine | `healing/engine.py` | Fase 1 |
| 4.4 | Snapshot Manager | `healing/snapshot.py` | 4.3 |
| 4.5 | Sandbox Executor | `sandbox/executor.py` | Fase 1 |
| 4.6 | Isolation Policies | `sandbox/isolation.py` | 4.5 |
| 4.7 | Tracer | `telemetry/tracer.py` | Fase 1 |
| 4.8 | Metrics Collector | `telemetry/metrics.py` | 4.7 |

### FASE 5: Validation Gates
**Objetivo:** Qualidade e segurança

| # | Tarefa | Arquivos | Dependências |
|---|--------|----------|--------------|
| 5.1 | Mutation Testing | `validation/mutation.py` | Fase 1 |
| 5.2 | Coverage Tracker | `validation/coverage.py` | 5.1 |
| 5.3 | AST Validator | `validation/ast_validator.py` | - |

### FASE 6: Skills Library
**Objetivo:** Base de conhecimento reutilizável

| # | Tarefa | Arquivos | Dependências |
|---|--------|----------|--------------|
| 6.1 | Skill: Python Protocols | `skills/python-protocols.md` | - |
| 6.2 | Skill: Hexagonal Arch | `skills/hexagonal-architecture.md` | - |
| 6.3 | Skill: Mutation Testing | `skills/mutation-testing.md` | - |
| 6.4 | Skill: DeepSeek Prompts | `skills/deepseek-prompt-optimization.md` | - |

### FASE 7: Testes
**Objetivo:** Cobertura >95% + Mutation Score >85%

| # | Tarefa | Arquivos | Dependências |
|---|--------|----------|--------------|
| 7.1 | Testes Core | `tests/unit/test_core*.py` | Fase 1 |
| 7.2 | Testes Gates | `tests/unit/test_gate*.py` | Fase 2 |
| 7.3 | Testes Agents | `tests/unit/test_agent*.py` | Fase 3 |
| 7.4 | Testes Healing | `tests/unit/test_healing*.py` | Fase 4 |
| 7.5 | Testes Sandbox | `tests/unit/test_sandbox*.py` | Fase 4 |
| 7.6 | Testes Telemetry | `tests/unit/test_telemetry*.py` | Fase 4 |
| 7.7 | Testes Integração | `tests/integration/` | Todas |

---

## 3. CONTRATOS DE INTERFACE (PORTAS HEXAGONAIS)

### 3.1 Core Types
```python
class SpecContract(TypedDict):
    spec_version: str
    security_clearance: str
    correlation_id: str
    domain_boundary: DomainBoundary
    contract_interface: ContractInterface
    architectural_invariants: ArchitecturalInvariants
    mutation_testing_criteria: MutationCriteria
    fail_safe_protocols: list[FailSafeProtocol]

class PipelineContext:
    spec: SpecContract
    sdd: ArchitectureDocument | None
    task_dag: TaskDAG | None
    test_suite: TestSuite | None
    code_artifacts: dict[str, str]
    snapshots: list[CodePatchSnapshot]
    telemetry: ExecutionTelemetry
```

### 3.2 Gate Interface
```python
class PipelineGate(ABC):
    @abstractmethod
    async def process(self, ctx: PipelineContext) -> PipelineContext: ...
    @property
    @abstractmethod
    def gate_id(self) -> int: ...
    @property
    @abstractmethod
    def name(self) -> str: ...
```

### 3.3 Agent Interface
```python
class LLMAgent(ABC):
    @abstractmethod
    async def call(self, prompt: str, thinking_mode: bool = False) -> str: ...
```

---

## 4. MÁQUINA DE ESTADOS (STATE MACHINE)

```
┌─────────────┐
│  INIT       │
└──────┬──────┘
       ↓
┌─────────────┐     ┌──────────────────┐
│  SPEC_V1    │────→│ BLOCKED_PROBE    │←── Human Feedback
└──────┬──────┘     └──────────────────┘
       ↓
┌─────────────┐
│  DESIGN     │
└──────┬──────┘
       ↓
┌─────────────┐
│  PLANNING   │
└──────┬──────┘
       ↓
┌─────────────┐
│  TESTING    │
└──────┬──────┘
       ↓
┌─────────────┐     ┌──────────────────┐
│  CODING     │────→│  HEALING_LOOP    │←── Rollback
└──────┬──────┘     └──────────────────┘
       ↓
┌─────────────┐
│ VALIDATION  │
└──────┬──────┘
       ↓
┌─────────────┐
│ CONVERGED   │
└─────────────┘
```

Transições de rollback:
- CODING → HEALING_LOOP (até 3x)
- HEALING_LOOP → PLANNING (se exceder tentativas)
- TESTING → DESIGN (se mutation score < 85%)

---

## 5. PLANO DE EXECUÇÃO (SEQUENCIAL)

### Sprint 1: Core + Config + Tipos
- `src/emasdep/__init__.py`
- `src/emasdep/config.py`
- `src/emasdep/core/types.py`
- `src/emasdep/core/state_machine.py`
- `src/emasdep/core/circuit_breaker.py`
- `pyproject.toml`, `requirements.txt`

### Sprint 2: Pipeline Gates (1-4)
- `src/emasdep/gates/gate_01_spec.py`
- `src/emasdep/gates/gate_02_probing.py`
- `src/emasdep/gates/gate_03_arch.py`
- `src/emasdep/gates/gate_04_planner.py`

### Sprint 3: Pipeline Gates (5-7) + Agents Base
- `src/emasdep/gates/gate_05_qa.py`
- `src/emasdep/gates/gate_06_engineer.py`
- `src/emasdep/gates/gate_07_conv.py`
- `src/emasdep/agents/base.py`

### Sprint 4: Agents de Inferência
- `src/emasdep/agents/pm_agent.py`
- `src/emasdep/agents/architect_agent.py`
- `src/emasdep/agents/planner_agent.py`
- `src/emasdep/agents/engineer_agent.py`
- `src/emasdep/agents/qa_agent.py`

### Sprint 5: SkillOps + Healing + Sandbox
- `src/emasdep/skills/registry.py`
- `src/emasdep/skills/synthesizer.py`
- `src/emasdep/healing/engine.py`
- `src/emasdep/healing/snapshot.py`
- `src/emasdep/sandbox/executor.py`
- `src/emasdep/sandbox/isolation.py`

### Sprint 6: Validation + Telemetry + Skills Library
- `src/emasdep/validation/mutation.py`
- `src/emasdep/validation/coverage.py`
- `src/emasdep/validation/ast_validator.py`
- `src/emasdep/telemetry/tracer.py`
- `src/emasdep/telemetry/metrics.py`
- `skills/*.md`

### Sprint 7: Main CLI + Testes
- `src/emasdep/main.py`
- `tests/unit/*.py`
- `tests/integration/*.py`
- `tests/fixtures/*.py`

---

## 6. CRITÉRIOS DE ACEITAÇÃO

1. **Pipeline completo**: spec → probing → design → plan → tests → code → converge
2. **Mutation Score ≥ 85%**: validação automática em cada ciclo
3. **Circuit Breaker**: rollback hierárquico funcional
4. **Snapshots**: cada mutação de estado gera ponto de restauração
5. **SkillOps**: skills injetadas no cache de prompt
6. **Sandbox**: execução isolada sem acesso à rede host
7. **Telemetria**: logs estruturados em formato JSON
8. **AST Integrity**: ruff + mypy com zero warnings
