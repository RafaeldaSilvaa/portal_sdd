from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..db.base import get_db
from ..models.pipeline import PipelineRun, TelemetryRecord

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])


@router.get("/stats")
async def get_telemetry_stats(db: Session = Depends(get_db)):
    total_runs = db.query(func.count(PipelineRun.id)).scalar() or 0
    converged = db.query(func.count(PipelineRun.id)).filter_by(is_converged=True).scalar() or 0
    failed = (
        db.query(func.count(PipelineRun.id))
        .filter(PipelineRun.failure_reason.isnot(None))
        .scalar()
        or 0
    )

    avg_mutation = (
        db.query(func.avg(PipelineRun.mutation_score)).filter(PipelineRun.mutation_score.isnot(None)).scalar()
        or 0.0
    )
    avg_coverage = (
        db.query(func.avg(PipelineRun.coverage_percent)).filter(PipelineRun.coverage_percent.isnot(None)).scalar()
        or 0.0
    )

    return {
        "total_runs": total_runs,
        "converged_runs": converged,
        "failed_runs": failed,
        "avg_mutation_score": round(float(avg_mutation), 4),
        "avg_coverage": round(float(avg_coverage), 4),
    }
