from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.ws_manager import manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/outages/live")
async def outage_live_feed(websocket: WebSocket) -> None:
    """Real-time outage event stream.

    Connect to receive live JSON events whenever an outage is reported or verified.
    Events shape: {"event": "new_report"|"verified", "h3_index": str, "id": str}
    """
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
