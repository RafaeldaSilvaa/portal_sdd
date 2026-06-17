"""EMASDEP CLI entrypoint."""

from __future__ import annotations

import asyncio
import json

import click

from .api.main import app
from .config import EMASDEPConfig
from .orchestrator import PipelineOrchestrator


@click.group()
def cli():
    """EMASDEP v3.0 - Enterprise Multi-Agent Spec-Driven Engineering Platform."""


@cli.command()
@click.option("--host", default="0.0.0.0", help="Bind address")
@click.option("--port", default=8000, help="Port number", type=int)
@click.option("--reload", is_flag=True, help="Auto-reload on code changes")
def serve(host: str, port: int, reload: bool):
    """Start the EMASDEP Portal API server."""
    import uvicorn
    uvicorn.run(
        "emasdep.api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


@cli.command()
@click.argument("raw_intent")
@click.option("--config", "-c", default=None, help="Config file path")
def run(raw_intent: str, config: str | None):
    """Run the full EMASDEP pipeline with a raw intent string."""

    async def _run():
        orchestrator = PipelineOrchestrator()
        result = await orchestrator.run_full_pipeline(raw_intent)
        click.echo(json.dumps({
            "success": result.success,
            "correlation_id": result.correlation_id,
            "final_state": result.final_state,
            "gates": result.gates_executed,
            "error": result.error,
            "telemetry": result.telemetry_data,
        }, indent=2))

    asyncio.run(_run())


@cli.command()
def version():
    """Show EMASDEP version."""
    from . import __version__, __title__
    click.echo(f"{__title__} v{__version__}")


if __name__ == "__main__":
    cli()
