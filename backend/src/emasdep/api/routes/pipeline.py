import asyncio
import json
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...agents.base import LLMConfig
from ...agents.orchestrator_agent import OrchestratorAgent
from ...core.types import (
    AgentTraceEntry,
    PipelineContext,
    PipelineState,
    PipelineGateID,
)
from ...core.token_optimizer import TokenOptimizer
from ...gates.gate_01_spec import SpecGate
from ...gates.gate_02_probing import ProbingGate
from ...gates.gate_03_arch import ArchitectureGate
from ...gates.gate_45_risk import RiskAnalysisGate
from ...gates.gate_04_planner import PlannerGate
from ...gates.gate_05_qa import QAGate
from ...gates.gate_06_engineer import EngineerGate
from ...gates.gate_07_conv import ConvergenceGate
from ...agents.architect_agent import ArchitectAgent
from ...agents.planner_agent import PlannerAgent
from ...agents.qa_agent import QAAgent
from ...agents.engineer_agent import EngineerAgent
from ...validation.guardrails import Guardrails
from ...memory.rag_memory import get_memory
from ..db.base import get_db
from ..models.pipeline import PipelineRun, ProbingQuestion
from ..pipeline_logs import add_log, get_logs

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

_active_tasks: dict[str, asyncio.Task] = {}


class StartPipelineRequest(BaseModel):
    raw_intent: str
    project_name: str = "default"


class AnswerQuestionRequest(BaseModel):
    question_id: str
    answer: str


class InteractRequest(BaseModel):
    correlation_id: str
    response: str


class PipelineStatusResponse(BaseModel):
    correlation_id: str
    current_state: str
    current_gate: int
    spec: dict | None
    probing_questions: list[dict] | None
    sdd: str | None
    risk_analysis: dict | None
    task_count: int | None
    mutation_score: float | None
    coverage_percent: float | None
    failure_reason: str | None
    is_converged: bool
    is_cancelled: bool
    interaction_pending: str | None
    total_latency_ms: int | None
    total_tokens: int | None
    agent_trace: list[dict] | None


GATE_NAMES = {
    PipelineGateID.ARCHITECTURE: "Architecture",
    PipelineGateID.RISK_ANALYSIS: "RiskAnalysis",
    PipelineGateID.PLANNER: "Planner",
    PipelineGateID.QA: "QA",
    PipelineGateID.ENGINEER: "Engineer",
    PipelineGateID.CONVERGENCE: "Convergence",
}

ALL_GATES = [
    PipelineGateID.ARCHITECTURE,
    PipelineGateID.RISK_ANALYSIS,
    PipelineGateID.PLANNER,
    PipelineGateID.QA,
    PipelineGateID.ENGINEER,
    PipelineGateID.CONVERGENCE,
]

_token_optimizer = TokenOptimizer()


async def _run_full_pipeline(cid: str, raw_intent: str, db_url: str):
    """ run full pipeline.

Args:
    cid: Descrição do parâmetro cid.
    raw_intent: Descrição do parâmetro raw_intent.
    db_url: Descrição do parâmetro db_url.

Retorna:
    None"""
    import os
    from emasdep.agents.base import LLMConfig
    from emasdep.api.db.base import SessionLocal

    db = SessionLocal()
    memory = get_memory()
    try:
        add_log(cid, "Running SpecGate...", gate="SPEC", db=db)
        ctx = PipelineContext()
        ctx.correlation_id = cid
        llm_config = LLMConfig.from_env(os.environ)
        orchestrator = OrchestratorAgent(config=llm_config)

        spec_gate = SpecGate(llm_config=llm_config)
        ctx = await spec_gate.process(ctx, raw_intent=raw_intent)

        run = db.query(PipelineRun).filter_by(correlation_id=cid).first()
        if run:
            run.current_state = ctx.current_state.name
            run.current_gate = ctx.current_gate.value
            if ctx.spec:
                run.spec_json = json.dumps(ctx.spec)
            db.commit()

        if ctx.spec:
            add_log(cid, "Spec generated successfully", gate="SPEC", db=db)
            memory.store_semantic("spec", json.dumps(ctx.spec))
        else:
            add_log(cid, "Spec generation failed (using default)", level="warning", gate="SPEC", db=db)
        add_log(cid, f"SpecGate complete — state: {ctx.current_state.name}", gate="SPEC", db=db)
        add_log(cid, "Running ProbingGate...", gate="PROBING", db=db)

        probing_gate = ProbingGate(llm_config=llm_config)
        probe_result = await probing_gate.avaliar_clareza_especificacao(ctx.spec or {})

        guard = Guardrails()
        gr = guard.check_no_undefined_schema(ctx.spec)
        if not gr.passed:
            for v in gr.violations:
                add_log(cid, f"Guardrail: {v.rule} - {v.detail}", level="warning", gate="GUARDRAILS", db=db)

        if probe_result["action"] == "BLOCK_AND_PROBE":
            ctx.current_state = PipelineState.BLOCKED_PROBE
            if run:
                run.current_state = ctx.current_state.name
                for q in probe_result.get("questionnaire", []):
                    pq = ProbingQuestion(
                        run_id=run.id,
                        question_id=q["id"],
                        context=q["context"],
                        question_text=q["question"],
                    )
                    db.add(pq)
                db.commit()
            add_log(cid, f"Blocked — {len(probe_result.get('questionnaire', []))} probing questions", gate="PROBING", db=db)
        else:
            add_log(cid, "Spec clarity approved, running full pipeline...", gate="PROBING", db=db)
            await _run_remaining_gates(cid, ctx, db, llm_config, orchestrator)

        run = db.query(PipelineRun).filter_by(correlation_id=cid).first()
        if run and run.current_state not in ("FAILED", "CANCELLED"):
            final = "CONVERGED" if run.is_converged else run.current_state
            add_log(cid, f"Pipeline finished — state: {final}", level="success", db=db)

    except Exception as exc:
        add_log(cid, f"Pipeline error: {exc}", level="error", db=db)
        try:
            run = db.query(PipelineRun).filter_by(correlation_id=cid).first()
            if run:
                run.current_state = "FAILED"
                run.failure_reason = str(exc)
                db.commit()
        except Exception:
            pass
    finally:
        _active_tasks.pop(cid, None)
        db.close()


async def _run_remaining_gates(
    cid: str,
    ctx: PipelineContext | None = None,
    db: Session | None = None,
    llm_config: LLMConfig | None = None,
    orchestrator: OrchestratorAgent | None = None,
):
    """executa os gates restantes do pipeline."""
    import os
    from emasdep.agents.base import LLMConfig as _LLMConfig
    from emasdep.api.db.base import SessionLocal

    if llm_config is None:
        llm_config = _LLMConfig.from_env(os.environ)
    if orchestrator is None:
        orchestrator = OrchestratorAgent(config=llm_config)

    memory = get_memory()
    guard = Guardrails()
    close_db = db is None
    if db is None:
        db = SessionLocal()

    _log = lambda msg, level="info", gate="": add_log(cid, msg, level=level, gate=gate, db=db)

    try:
        run = db.query(PipelineRun).filter_by(correlation_id=cid).first()
        if not run:
            return

        if ctx is None:
            spec_contract = None
            if run.spec_json:
                try:
                    spec_contract = json.loads(run.spec_json)
                except json.JSONDecodeError:
                    pass

            ctx = PipelineContext()
            ctx.correlation_id = cid
            ctx.current_state = PipelineState.SPEC_V1
            ctx.current_gate = PipelineGateID.ARCHITECTURE
            ctx.spec = spec_contract

        gates = [
            (PipelineGateID.ARCHITECTURE, ArchitectureGate(ArchitectAgent(config=llm_config)), "ARCHITECTURE"),
            (PipelineGateID.RISK_ANALYSIS, RiskAnalysisGate(llm_config=llm_config), "RISK_ANALYSIS"),
            (PipelineGateID.PLANNER, PlannerGate(PlannerAgent(config=llm_config)), "PLANNER"),
            (PipelineGateID.QA, QAGate(QAAgent(config=llm_config)), "QA"),
            (PipelineGateID.ENGINEER, EngineerGate(EngineerAgent(config=llm_config)), "ENGINEER"),
            (PipelineGateID.CONVERGENCE, ConvergenceGate(llm_config=llm_config), "CONVERGENCE"),
        ]

        for gate_id, gate, gate_name in gates:
            run = db.query(PipelineRun).filter_by(correlation_id=cid).first()
            if not run or run.is_cancelled:
                _log(f"Skipping {gate_name} — pipeline cancelled", level="warning")
                break

            gr = guard.check_all(ctx)
            if not gr.passed:
                for v in gr.violations:
                    _log(f"Guardrail: {v.rule} ({v.severity}): {v.detail}", level="warning", gate=gate_name)

            _log(f"Running {gate_name}Gate...", gate=gate_name)
            run.current_gate = gate_id.value
            db.commit()

            try:
                start_ms = int(time.time() * 1000)

                if gate_id == PipelineGateID.ENGINEER and ctx.task_dag:
                    engineer_tasks = [
                        t for t in ctx.task_dag.tasks.values()
                        if t.agent_role.value == "engineer"
                    ]
                    _log(f"Generating {len(engineer_tasks)} code file(s)...", gate=gate_name)

                if ctx.sdd:
                    compressed = _token_optimizer.compress(ctx.sdd, preserve_sections=["domain_model"])
                    if compressed.compressed_length < compressed.original_length:
                        _log(f"SDD compressed: {compressed.original_length}→{compressed.compressed_length} chars", gate=gate_name)

                ctx = await gate.process(ctx)
                latency = int(time.time() * 1000) - start_ms
                run.current_state = ctx.current_state.name

                ctx.telemetry.agent_trace.append(AgentTraceEntry(
                    agent_role=gate_name.lower(),
                    gate=gate_name,
                    latency_ms=latency,
                    token_usage=len(str(ctx.spec or "")) + len(ctx.sdd or ""),
                    status="success" if ctx.current_state != PipelineState.FAILED else "error",
                ))
                ctx.telemetry.total_latency_ms += latency

                if gate_id == PipelineGateID.ENGINEER and ctx.code_artifacts:
                    for fname, code in ctx.code_artifacts.items():
                        _log(f"Generated src/{fname} ({len(code)} bytes)", gate=gate_name)
                    run.code_artifacts = json.dumps(ctx.code_artifacts)
                    memory.store_episodic(cid, f"Generated {len(ctx.code_artifacts)} files", failed=False)

                if gate_id in (PipelineGateID.ARCHITECTURE, PipelineGateID.QA, PipelineGateID.ENGINEER, PipelineGateID.CONVERGENCE):
                    db.commit()

                _log(f"{gate_name}Gate complete — state: {ctx.current_state.name} ({latency}ms)", gate=gate_name)
            except Exception as exc:
                run.current_state = "FAILED"
                run.failure_reason = str(exc)
                db.commit()
                _log(f"{gate_name}Gate failed: {exc}", level="error", gate=gate_name)
                memory.store_episodic(cid, f"Gate {gate_name} failed: {exc}", failed=True)

                recovery = await orchestrator.handle_failure(ctx, str(exc))
                if recovery.data.get("action") in ("retry_same", "simplify_context"):
                    _log(f"Orchestrator recommends {recovery.data.get('action')} — retrying", gate=gate_name)
                    continue
                elif recovery.data.get("action") == "fallback_model":
                    _log("Orchestrator recommends fallback model — aborting", gate=gate_name)
                break

            if gate_id == PipelineGateID.ARCHITECTURE and ctx.sdd:
                run.sdd_text = ctx.sdd
            elif gate_id == PipelineGateID.RISK_ANALYSIS and ctx.risk_analysis:
                run.sdd_text = (run.sdd_text or "") + "\n\n## Risk Analysis\n" + json.dumps({
                    "risks": [{"description": r.description, "impact": r.impact, "probability": r.probability} for r in ctx.risk_analysis.risks],
                    "trade_offs": [{"decision": t.decision, "recommended": t.recommended} for t in ctx.risk_analysis.trade_offs],
                    "overall_risk_score": ctx.risk_analysis.overall_risk_score,
                    "recommendations": ctx.risk_analysis.recommendations,
                }, indent=2)
            elif gate_id == PipelineGateID.QA and ctx.test_suite:
                run.test_suite = ctx.test_suite
            elif gate_id == PipelineGateID.CONVERGENCE:
                run.is_converged = ctx.current_state == PipelineState.CONVERGED
                run.mutation_score = ctx.validation.mutation.mutation_score if ctx.validation and ctx.validation.mutation else None
                run.coverage_percent = ctx.validation.coverage_percent if ctx.validation else None

            if gate_id in (PipelineGateID.ARCHITECTURE, PipelineGateID.QA, PipelineGateID.ENGINEER, PipelineGateID.CONVERGENCE):
                if gate_id == PipelineGateID.CONVERGENCE and ctx.failure_reason:
                    run.failure_reason = ctx.failure_reason
                    _log(f"Convergence details: {ctx.failure_reason}", level="warning", gate=gate_name)
                    memory.store_episodic(cid, f"Convergence: {ctx.failure_reason}", failed=True)
                db.commit()

            decision = await orchestrator.decide_next_action(ctx)
            if decision.data.get("action") in ("halt", "replan"):
                _log(f"Orchestrator halts pipeline: {decision.data.get('reason', 'unknown')}", level="warning")
                break

        run = db.query(PipelineRun).filter_by(correlation_id=cid).first()
        if run and run.current_state not in ("FAILED", "CANCELLED"):
            final = "CONVERGED" if run.is_converged else run.current_state
            _log(f"Pipeline finished — state: {final}", level="success")

    except Exception as exc:
        _log(f"Pipeline error: {exc}", level="error")
        try:
            run = db.query(PipelineRun).filter_by(correlation_id=cid).first()
            if run:
                run.current_state = "FAILED"
                run.failure_reason = str(exc)
                db.commit()
        except Exception:
            pass
    finally:
        _active_tasks.pop(cid, None)
        if close_db:
            db.close()


@router.post("/start")
async def start_pipeline(req: StartPipelineRequest, db: Session = Depends(get_db)):
    """inicia um pipeline executando SpecGate + ProbingGate de forma síncrona e retorna perguntas."""
    import os
    from emasdep.agents.base import LLMConfig
    from emasdep.memory.rag_memory import get_memory

    cid = f"tx-{__import__('uuid').uuid4().hex[:18]}"
    add_log(cid, f"Iniciando pipeline: {req.raw_intent[:80]}...", level="info", db=db)

    run = PipelineRun(
        correlation_id=cid,
        current_state="PENDING",
        current_gate=0,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    llm_config = LLMConfig.from_env(os.environ)
    memory = get_memory()
    ctx = PipelineContext()
    ctx.correlation_id = cid

    try:
        # SpecGate síncrono
        add_log(cid, "Executando SpecGate...", gate="SPEC", db=db)
        spec_gate = SpecGate(llm_config=llm_config)
        ctx = await spec_gate.process(ctx, raw_intent=req.raw_intent)

        run.current_state = ctx.current_state.name
        run.current_gate = ctx.current_gate.value
        if ctx.spec:
            run.spec_json = json.dumps(ctx.spec)
        db.commit()

        if ctx.spec:
            add_log(cid, "Spec gerado com sucesso", gate="SPEC", db=db)
            memory.store_semantic("spec", json.dumps(ctx.spec))

        # ProbingGate síncrono
        add_log(cid, "Executando ProbingGate...", gate="PROBING", db=db)
        probing_gate = ProbingGate(llm_config=llm_config)
        probe_result = await probing_gate.avaliar_clareza_especificacao(ctx.spec or {})

        questionario = probe_result.get("questionnaire", [])
        run.current_state = ctx.current_state.name
        run.current_gate = ctx.current_gate.value

        if probe_result["action"] == "BLOCK_AND_PROBE":
            ctx.current_state = PipelineState.BLOCKED_PROBE
            run.current_state = ctx.current_state.name
            db.commit()

            # Salva perguntas no banco com opções em JSON no campo context
            for q in questionario:
                pq = ProbingQuestion(
                    run_id=run.id,
                    question_id=q["id"],
                    context=q.get("context", ""),
                    question_text=q["question"],
                )
                db.add(pq)
            db.commit()

            add_log(cid, f"Pipeline bloqueado — {len(questionario)} perguntas de esclarecimento", gate="PROBING", db=db)
        else:
            add_log(cid, "Especificação aprovada — continuando pipeline em background...", gate="PROBING", db=db)
            run.current_state = "DESIGN"
            db.commit()
            # Continua o resto do pipeline em background (não passa db — cria próprio SessionLocal)
            task = asyncio.create_task(
                _run_remaining_gates(cid, ctx, llm_config=llm_config)
            )
            _active_tasks[cid] = task

    except Exception as exc:
        run.current_state = "FAILED"
        run.failure_reason = str(exc)
        db.commit()
        add_log(cid, f"Erro no pipeline: {exc}", level="error", db=db)
        return {"correlation_id": cid, "status": "FAILED", "error": str(exc)}

    return {
        "correlation_id": cid,
        "status": run.current_state,
        "probing": {
            "action": probe_result.get("action", "PROCEED_TO_DESIGN"),
            "ambiguity_score": probe_result.get("ambiguity_score", 0.0),
            "questionnaire": questionario,
        },
    }


@router.post("/answer")
async def answer_question(req: AnswerQuestionRequest, db: Session = Depends(get_db)):
    """responde a uma pergunta de sondagem e continua o pipeline se todas forem respondidas."""
    question = db.query(ProbingQuestion).filter_by(question_id=req.question_id).first()
    if not question:
        raise HTTPException(404, f"Question {req.question_id} not found")
    question.answer = req.answer
    question.answered_at = datetime.now(timezone.utc)
    db.commit()

    # Verifica se todas as perguntas deste run foram respondidas
    todas_perguntas = db.query(ProbingQuestion).filter_by(run_id=question.run_id).all()
    todas_respondidas = all(q.answer is not None for q in todas_perguntas)

    resultado: dict = {
        "status": "answered",
        "question_id": req.question_id,
        "all_answered": todas_respondidas,
    }

    if todas_respondidas:
        # Busca o correlation_id do run para continuar o pipeline
        run = db.query(PipelineRun).filter_by(id=question.run_id).first()
        if run and run.correlation_id:
            correlation_id = run.correlation_id
            resultado["correlation_id"] = correlation_id
            # Atualiza estado imediatamente para DESIGN p/ evitar que frontend veja BLOCKED_PROBE
            run.current_state = "DESIGN"
            db.commit()
            add_log(correlation_id, "Todas as perguntas respondidas — continuando pipeline...", level="success", db=db)

            # Continua o pipeline em background (cria próprio SessionLocal)
            task = asyncio.create_task(
                _run_remaining_gates(correlation_id)
            )
            _active_tasks[correlation_id] = task

    return resultado


@router.post("/cancel/{correlation_id}")
async def cancel_pipeline(correlation_id: str, db: Session = Depends(get_db)):
    """cancel pipeline.

Args:
    correlation_id: Descrição do parâmetro correlation_id.
    db: Descrição do parâmetro db.

Retorna:
    None"""
    run = db.query(PipelineRun).filter_by(correlation_id=correlation_id).first()
    if not run:
        raise HTTPException(404, "Pipeline run not found")
    run.is_cancelled = True
    run.current_state = "CANCELLED"
    db.commit()
    add_log(correlation_id, "Pipeline cancelled by user", level="warning", db=db)

    task = _active_tasks.pop(correlation_id, None)
    if task and not task.done():
        task.cancel()

    return {"status": "cancelled", "correlation_id": correlation_id}


@router.post("/interact/{correlation_id}")
async def interact_pipeline(correlation_id: str, req: InteractRequest, db: Session = Depends(get_db)):
    """interact pipeline.

Args:
    correlation_id: Descrição do parâmetro correlation_id.
    req: Descrição do parâmetro req.
    db: Descrição do parâmetro db.

Retorna:
    None"""
    run = db.query(PipelineRun).filter_by(correlation_id=correlation_id).first()
    if not run:
        raise HTTPException(404, "Pipeline run not found")
    run.interaction_pending = None
    db.commit()
    add_log(correlation_id, f"User interaction: {req.response}", level="info", db=db)
    return {"status": "acknowledged", "correlation_id": correlation_id}


@router.get("/logs/{correlation_id}")
async def get_pipeline_logs(correlation_id: str, since: str | None = None, db: Session = Depends(get_db)):
    return get_logs(correlation_id, since=since, db=db)


@router.get("/status/{correlation_id}")
async def get_pipeline_status(correlation_id: str, db: Session = Depends(get_db)):
    """get pipeline status.

Args:
    correlation_id: Descrição do parâmetro correlation_id.
    db: Descrição do parâmetro db.

Retorna:
    None"""
    run = db.query(PipelineRun).filter_by(correlation_id=correlation_id).first()
    if not run:
        raise HTTPException(404, "Pipeline run not found")

    questions = db.query(ProbingQuestion).filter_by(run_id=run.id).all()
    questions_data = [
        {
            "id": q.question_id,
            "context": q.context,
            "question": q.question_text,
            "options": None,
            "answer": q.answer,
            "answered": q.answer is not None,
        }
        for q in questions
    ]

    return PipelineStatusResponse(
        correlation_id=run.correlation_id,
        current_state=run.current_state,
        current_gate=run.current_gate,
        spec=None,
        probing_questions=questions_data if questions else None,
        sdd=run.sdd_text,
        risk_analysis=None,
        task_count=None,
        mutation_score=run.mutation_score,
        coverage_percent=run.coverage_percent,
        failure_reason=run.failure_reason,
        is_converged=run.is_converged,
        is_cancelled=run.is_cancelled,
        interaction_pending=run.interaction_pending,
        total_latency_ms=None,
        total_tokens=None,
        agent_trace=None,
    )


@router.get("/runs")
async def list_runs(db: Session = Depends(get_db)):
    """list runs.

Args:
    db: Descrição do parâmetro db.

Retorna:
    None"""
    runs = db.query(PipelineRun).order_by(PipelineRun.created_at.desc()).limit(50).all()
    return [
        {
            "correlation_id": r.correlation_id,
            "state": r.current_state,
            "gate": r.current_gate,
            "converged": r.is_converged,
            "cancelled": r.is_cancelled,
            "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]
