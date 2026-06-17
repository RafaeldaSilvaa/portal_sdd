import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...agents.base import LLMConfig
from ...core.types import (
    PipelineContext,
    PipelineState,
    PipelineGateID,
)
from ...gates.gate_01_spec import SpecGate
from ...gates.gate_02_probing import ProbingGate
from ...gates.gate_03_arch import ArchitectureGate
from ...gates.gate_04_planner import PlannerGate
from ...gates.gate_05_qa import QAGate
from ...gates.gate_06_engineer import EngineerGate
from ...gates.gate_07_conv import ConvergenceGate
from ...agents.architect_agent import ArchitectAgent
from ...agents.planner_agent import PlannerAgent
from ...agents.qa_agent import QAAgent
from ...agents.engineer_agent import EngineerAgent
from ...agents.pm_agent import PMAgent
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
    task_count: int | None
    mutation_score: float | None
    coverage_percent: float | None
    failure_reason: str | None
    is_converged: bool
    is_cancelled: bool
    interaction_pending: str | None


GATE_NAMES = {
    PipelineGateID.ARCHITECTURE: "Architecture",
    PipelineGateID.PLANNER: "Planner",
    PipelineGateID.QA: "QA",
    PipelineGateID.ENGINEER: "Engineer",
    PipelineGateID.CONVERGENCE: "Convergence",
}


async def _run_full_pipeline(cid: str, raw_intent: str, db_url: str):
    import os
    from emasdep.agents.base import LLMConfig
    from emasdep.api.db.base import SessionLocal

    db = SessionLocal()
    try:
        add_log(cid, "Running SpecGate...", gate="SPEC")
        ctx = PipelineContext()
        ctx.correlation_id = cid
        spec_gate = SpecGate()
        ctx = await spec_gate.process(ctx)

        run = db.query(PipelineRun).filter_by(correlation_id=cid).first()
        if run:
            run.current_state = ctx.current_state.name
            run.current_gate = ctx.current_gate.value
            db.commit()

        add_log(cid, f"SpecGate complete — state: {ctx.current_state.name}", gate="SPEC")
        add_log(cid, "Generating spec via PM Agent...", gate="SPEC")

        llm_config = LLMConfig.from_env(os.environ)
        pm_agent = PMAgent(config=llm_config)
        try:
            spec = await pm_agent.generate_spec(raw_intent)
            ctx.spec = spec
            if run:
                run.spec_json = json.dumps(spec) if spec else None
                db.commit()
            add_log(cid, "Spec generated successfully", gate="SPEC")
        except Exception as exc:
            add_log(cid, f"Spec generation failed (using default): {exc}", level="warning", gate="SPEC")

        add_log(cid, "Running ProbingGate...", gate="PROBING")
        probing_gate = ProbingGate()
        probe_result = probing_gate.evaluate_spec_clarity(raw_intent, ctx.spec or {})

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
            add_log(cid, f"Blocked — {len(probe_result.get('questionnaire', []))} probing questions", gate="PROBING")
        else:
            add_log(cid, "Spec clarity approved, running full pipeline...", gate="PROBING")
            await _run_remaining_gates(cid, ctx, db)

        run = db.query(PipelineRun).filter_by(correlation_id=cid).first()
        if run and run.current_state not in ("FAILED", "CANCELLED"):
            final = "CONVERGED" if run.is_converged else run.current_state
            add_log(cid, f"Pipeline finished — state: {final}", level="success")

    except Exception as exc:
        add_log(cid, f"Pipeline error: {exc}", level="error")
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


async def _run_remaining_gates(cid: str, ctx: PipelineContext | None = None, db: Session | None = None):
    import os
    from emasdep.agents.base import LLMConfig
    from emasdep.api.db.base import SessionLocal

    llm_config = LLMConfig.from_env(os.environ)
    close_db = db is None
    if db is None:
        db = SessionLocal()
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
            (PipelineGateID.PLANNER, PlannerGate(PlannerAgent(config=llm_config)), "PLANNER"),
            (PipelineGateID.QA, QAGate(QAAgent(config=llm_config)), "QA"),
            (PipelineGateID.ENGINEER, EngineerGate(EngineerAgent(config=llm_config)), "ENGINEER"),
            (PipelineGateID.CONVERGENCE, ConvergenceGate(), "CONVERGENCE"),
        ]

        for gate_id, gate, gate_name in gates:
            run = db.query(PipelineRun).filter_by(correlation_id=cid).first()
            if not run or run.is_cancelled:
                add_log(cid, f"Skipping {gate_name} — pipeline cancelled", level="warning")
                break

            add_log(cid, f"Running {gate_name}Gate...", gate=gate_name)
            run.current_gate = gate_id.value
            db.commit()

            try:
                if gate_id == PipelineGateID.ENGINEER and ctx.task_dag:
                    engineer_tasks = [
                        t for t in ctx.task_dag.tasks.values()
                        if t.agent_role.value == "engineer"
                    ]
                    add_log(cid, f"Generating {len(engineer_tasks)} code file(s)...", gate=gate_name)

                ctx = await gate.process(ctx)
                run.current_state = ctx.current_state.name

                if gate_id == PipelineGateID.ENGINEER and ctx.code_artifacts:
                    for task_id, code in ctx.code_artifacts.items():
                        fname = f"src/{task_id}.py"
                        add_log(cid, f"Generated {fname} ({len(code)} bytes)", gate=gate_name)
                    run.code_artifacts = json.dumps(ctx.code_artifacts)

                if gate_id in (PipelineGateID.ARCHITECTURE, PipelineGateID.QA, PipelineGateID.ENGINEER, PipelineGateID.CONVERGENCE):
                    db.commit()

                add_log(cid, f"{gate_name}Gate complete — state: {ctx.current_state.name}", gate=gate_name)
            except Exception as exc:
                run.current_state = "FAILED"
                run.failure_reason = str(exc)
                db.commit()
                add_log(cid, f"{gate_name}Gate failed: {exc}", level="error", gate=gate_name)
                break

            if gate_id == PipelineGateID.ARCHITECTURE and ctx.sdd:
                run.sdd_text = ctx.sdd
            elif gate_id == PipelineGateID.QA and ctx.test_suite:
                run.test_suite = ctx.test_suite
            elif gate_id == PipelineGateID.CONVERGENCE:
                run.is_converged = ctx.current_state == PipelineState.CONVERGED
                run.mutation_score = ctx.validation.mutation.mutation_score if ctx.validation and ctx.validation.mutation else None
                run.coverage_percent = ctx.validation.coverage_percent if ctx.validation else None

            if gate_id in (PipelineGateID.ARCHITECTURE, PipelineGateID.QA, PipelineGateID.ENGINEER, PipelineGateID.CONVERGENCE):
                if gate_id == PipelineGateID.CONVERGENCE and ctx.failure_reason:
                    run.failure_reason = ctx.failure_reason
                    add_log(cid, f"Convergence details: {ctx.failure_reason}", level="warning", gate=gate_name)
                db.commit()

        run = db.query(PipelineRun).filter_by(correlation_id=cid).first()
        if run and run.current_state not in ("FAILED", "CANCELLED"):
            final = "CONVERGED" if run.is_converged else run.current_state
            add_log(cid, f"Pipeline finished — state: {final}", level="success")

    except Exception as exc:
        add_log(cid, f"Pipeline error: {exc}", level="error")
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
    cid = f"tx-{__import__('uuid').uuid4().hex[:18]}"
    add_log(cid, f"Starting pipeline with intent: {req.raw_intent}", level="info")

    run = PipelineRun(
        correlation_id=cid,
        current_state="PENDING",
        current_gate=0,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    task = asyncio.create_task(
        _run_full_pipeline(cid, req.raw_intent, str(db.get_bind().url))
    )
    _active_tasks[cid] = task

    return {"correlation_id": cid, "status": "PENDING"}


@router.post("/answer")
async def answer_question(req: AnswerQuestionRequest, db: Session = Depends(get_db)):
    question = db.query(ProbingQuestion).filter_by(question_id=req.question_id).first()
    if not question:
        raise HTTPException(404, f"Question {req.question_id} not found")
    question.answer = req.answer
    db.commit()
    add_log(f"run-{question.run_id}", f"Answered probing: {req.question_id}", level="info")
    return {"status": "answered", "question_id": req.question_id}


@router.post("/cancel/{correlation_id}")
async def cancel_pipeline(correlation_id: str, db: Session = Depends(get_db)):
    run = db.query(PipelineRun).filter_by(correlation_id=correlation_id).first()
    if not run:
        raise HTTPException(404, "Pipeline run not found")
    run.is_cancelled = True
    run.current_state = "CANCELLED"
    db.commit()
    add_log(correlation_id, "Pipeline cancelled by user", level="warning")

    task = _active_tasks.pop(correlation_id, None)
    if task and not task.done():
        task.cancel()

    return {"status": "cancelled", "correlation_id": correlation_id}


@router.post("/interact/{correlation_id}")
async def interact_pipeline(correlation_id: str, req: InteractRequest, db: Session = Depends(get_db)):
    run = db.query(PipelineRun).filter_by(correlation_id=correlation_id).first()
    if not run:
        raise HTTPException(404, "Pipeline run not found")
    run.interaction_pending = None
    db.commit()
    add_log(correlation_id, f"User interaction: {req.response}", level="info")
    return {"status": "acknowledged", "correlation_id": correlation_id}


@router.get("/logs/{correlation_id}")
async def get_pipeline_logs(correlation_id: str, since: str | None = None):
    return get_logs(correlation_id, since=since)


@router.get("/status/{correlation_id}")
async def get_pipeline_status(correlation_id: str, db: Session = Depends(get_db)):
    run = db.query(PipelineRun).filter_by(correlation_id=correlation_id).first()
    if not run:
        raise HTTPException(404, "Pipeline run not found")

    questions = db.query(ProbingQuestion).filter_by(run_id=run.id).all()
    questions_data = [
        {
            "id": q.question_id,
            "context": q.context,
            "question": q.question_text,
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
        task_count=None,
        mutation_score=run.mutation_score,
        coverage_percent=run.coverage_percent,
        failure_reason=run.failure_reason,
        is_converged=run.is_converged,
        is_cancelled=run.is_cancelled,
        interaction_pending=run.interaction_pending,
    )


@router.get("/runs")
async def list_runs(db: Session = Depends(get_db)):
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
