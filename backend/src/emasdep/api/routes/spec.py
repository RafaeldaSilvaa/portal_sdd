from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.types import SpecContract
from ..db.base import get_db
from ..models.pipeline import PipelineRun

router = APIRouter(prefix="/api/spec", tags=["spec"])


class SpecUpdateRequest(BaseModel):
    spec_json: dict


@router.get("/{correlation_id}")
async def get_spec(correlation_id: str, db: Session = Depends(get_db)):
    run = db.query(PipelineRun).filter_by(correlation_id=correlation_id).first()
    if not run:
        raise HTTPException(404, "Pipeline run not found")
    return {"spec": run.spec_json}


@router.put("/{correlation_id}")
async def update_spec(correlation_id: str, req: SpecUpdateRequest, db: Session = Depends(get_db)):
    run = db.query(PipelineRun).filter_by(correlation_id=correlation_id).first()
    if not run:
        raise HTTPException(404, "Pipeline run not found")
    import json
    run.spec_json = json.dumps(req.spec_json)
    db.commit()
    return {"status": "updated"}
