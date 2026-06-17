"""WebSocket handler for real-time pipeline status streaming."""

import asyncio
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class PipelineEventManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, event_type: str, data: dict):
        payload = json.dumps({"type": event_type, "data": data})
        stale = set()
        for ws in self.active_connections:
            try:
                await ws.send_text(payload)
            except Exception:
                stale.add(ws)
        self.active_connections -= stale


manager = PipelineEventManager()


async def pipeline_ws_handler(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            msg = await websocket.receive_text()
            data = json.loads(msg)
            if data.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WS error: {e}")
        manager.disconnect(websocket)
