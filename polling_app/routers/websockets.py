import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from polling_app import constants as C
from polling_app.utils.connection_manager import connection_manager
from polling_app.utils.ws_helpers import send_error

from ..database import SessionLocal

router = APIRouter(prefix="/polls", tags=["websockets"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def cleanup_poll_connections(poll_id: str):
    """Clean up all WebSocket connections for a deleted poll."""
    await connection_manager.cleanup_poll(poll_id)


@router.websocket("/ws")
async def websocket_subscribe_multi_poll(ws: WebSocket, db: Session = Depends(get_db)):
    """
    WebSocket endpoint to subscribe to multiple polls' live updates.
    Client can send JSON messages with actions: subscribe, unsubscribe, disconnect.
    """
    await connection_manager.connect(ws)

    try:
        while True:
            msg = await ws.receive_text()
            data = json.loads(msg)
            action = data.get("action")
            poll_id = data.get("poll_id")

            if action == C.ACTION_SUBSCRIBE and poll_id:
                await connection_manager.subscribe_to_poll(ws, poll_id, db)

            elif action == C.ACTION_UNSUBSCRIBE and poll_id:
                await connection_manager.unsubscribe_from_poll(ws, poll_id)

            elif action == C.ACTION_DISCONNECT:
                await connection_manager.disconnect(ws)
                break

            else:
                await send_error(ws, C.ERR_UNKNOWN_ACTION, f"Unknown action {action}")

    except WebSocketDisconnect:
        await connection_manager.disconnect(ws)
    except Exception as e:
        await send_error(ws, C.ERR_INTERNAL, str(e))
        await connection_manager.disconnect(ws)


@router.websocket("/ws/{poll_id}")
async def websocket_subscribe_one_poll(
    ws: WebSocket, poll_id: str, db: Session = Depends(get_db)
):
    """WebSocket endpoint to subscribe to a single poll's live updates."""
    await connection_manager.connect(ws)

    # Automatically subscribe to the specified poll
    success = await connection_manager.subscribe_to_poll(ws, poll_id, db)
    if not success:
        await connection_manager.disconnect(ws)
        return

    try:
        while True:
            # Keep connection alive, ignore any messages
            await ws.receive_text()
    except WebSocketDisconnect:
        await connection_manager.disconnect(ws)


@router.get("/stats")
def get_websocket_stats():
    """Get WebSocket connection statistics."""
    return {
        "total_connections": connection_manager.get_total_connections(),
        "active_polls": len(connection_manager._connections),
    }


@router.get("/{poll_id}/stats")
def get_poll_stats(poll_id: str):
    """Get connection statistics for a specific poll."""
    return {
        "poll_id": poll_id,
        "connection_count": connection_manager.get_connection_count(poll_id),
    }
