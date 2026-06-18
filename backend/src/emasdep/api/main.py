"""EMASDEP Portal - FastAPI Application Entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from .db.base import Base, ensure_engine, migrate_schema
from .routes.pipeline import router as pipeline_router
from .routes.spec import router as spec_router
from .routes.telemetry import router as telemetry_router
from .routes.config import router as config_router
from .routes.files import router as files_router
from .ws.pipeline_events import pipeline_ws_handler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("emasdep.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """lifespan.

Args:
    app: Descrição do parâmetro app.

Retorna:
    None"""
    logger.info("EMASDEP Portal v3.0 starting...")
    eng = ensure_engine()
    Base.metadata.create_all(bind=eng)
    migrate_schema()
    logger.info("Database tables created/verified.")
    yield
    logger.info("EMASDEP Portal shutting down.")


app = FastAPI(
    title="EMASDEP Portal",
    description="Enterprise Multi-Agent Spec-Driven Engineering Platform",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pipeline_router)
app.include_router(spec_router)
app.include_router(telemetry_router)
app.include_router(config_router)
app.include_router(files_router)


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "3.0.0", "platform": "EMASDEP"}


@app.websocket("/ws/pipeline")
async def websocket_endpoint(websocket: WebSocket):
    await pipeline_ws_handler(websocket)
