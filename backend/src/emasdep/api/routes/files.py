from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..db.base import get_db
from ..models.pipeline import PipelineRun
from ..pipeline_files import FileEntry, list_files, get_file_content, build_zip
from .pipeline import PipelineStatusResponse

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.get("/files/{correlation_id}")
def list_pipeline_files(correlation_id: str, db: Session = Depends(get_db)):
    run = db.query(PipelineRun).filter_by(correlation_id=correlation_id).first()
    if not run:
        raise HTTPException(404, "Pipeline run not found")
    return list_files(correlation_id, db)


@router.get("/files/{correlation_id}/content")
def get_pipeline_file_content(correlation_id: str, path: str, db: Session = Depends(get_db)):
    run = db.query(PipelineRun).filter_by(correlation_id=correlation_id).first()
    if not run:
        raise HTTPException(404, "Pipeline run not found")
    content = get_file_content(correlation_id, path, db)
    if content is None:
        raise HTTPException(404, f"File '{path}' not found")
    return {"path": path, "content": content}


@router.get("/download/{correlation_id}")
def download_pipeline_zip(correlation_id: str, db: Session = Depends(get_db)):
    run = db.query(PipelineRun).filter_by(correlation_id=correlation_id).first()
    if not run:
        raise HTTPException(404, "Pipeline run not found")
    data = build_zip(correlation_id, db)
    if data is None:
        raise HTTPException(404, "No artifacts available for this pipeline run")
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{correlation_id}.zip"'},
    )
