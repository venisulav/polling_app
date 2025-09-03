import asyncio
import json
from typing import Any, List

from fastapi import (APIRouter, Depends, HTTPException, WebSocket,
                     WebSocketDisconnect)
from sqlalchemy.orm import Session

from polling_app import constants as C
from polling_app.utils.ws_helpers import send_error, send_success

from .. import crud, models, schemas
from ..database import SessionLocal

router = APIRouter(prefix="/polls", tags=["polls"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


connections: dict[str, List[WebSocket]] = {}


@router.post("/", response_model=schemas.PollOut)
def create_poll(
    poll: schemas.PollCreate, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Create a new poll with choices."""
    db_poll = crud.create_poll(db, poll)
    results = crud.get_poll_results(db, str(db_poll.id))
    return {
        "id": db_poll.id,
        "title": db_poll.title,
        "question": db_poll.question,
        "choices": results,
    }


@router.get("/", response_model=List[schemas.PollOut])
def list_polls(db: Session = Depends(get_db)):
    """List all polls with their results."""
    polls = crud.get_polls(db)
    out: list[dict[str, Any]] = []
    for p in polls:
        results = crud.get_poll_results(db, str(p.id))
        out.append(
            {"id": p.id, "title": p.title, "question": p.question, "choices": results}
        )
    return out


@router.get("/{poll_id}", response_model=schemas.PollOut)
def get_poll(poll_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Get a specific poll with its results."""
    poll = crud.get_poll(db, poll_id)
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    results = crud.get_poll_results(db, str(poll.id))
    return {
        "id": poll.id,
        "title": poll.title,
        "question": poll.question,
        "choices": results,
    }


@router.post("/{poll_id}/vote")
async def vote(poll_id: str, vote: schemas.VoteCreate, db: Session = Depends(get_db)):
    """Cast a vote for a choice in a poll. broadcasts update to subscribers."""
    poll = crud.get_poll(db, poll_id)
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    if not any(c.id == vote.choice_id for c in poll.choices):
        raise HTTPException(status_code=400, detail="Invalid choice")
    if crud.has_user_voted(db, poll_id, vote.username):
        raise HTTPException(
            status_code=400, detail="User has already voted in this poll"
        )
    crud.create_vote(db, vote)
    response_data: dict[str, Any] = {
        "poll_id": poll_id,
        "results": crud.get_poll_results(db, poll_id),
    }
    for ws in connections.get(poll_id, []):
        asyncio.create_task(send_success(ws, C.ACTION_UPDATE, response_data))
    return {"status": "ok"}


@router.delete("/{poll_id}")
async def delete_poll(poll_id: str, db: Session = Depends(get_db)):
    """Delete a poll and notify subscribers."""
    success = crud.delete_poll(db, poll_id)
    if not success:
        raise HTTPException(status_code=404, detail="Poll not found")
    sockets = connections.pop(poll_id, [])
    for socket in sockets:
        asyncio.create_task(
            send_error(socket, C.ERR_POLL_DELETED, f"Poll {poll_id} has been deleted")
        )
    return {"status": "deleted"}


def poll_exists(poll_id: str) -> bool:
    """Check if a poll exists in the database."""
    db: Session = SessionLocal()
    try:
        return (
            db.query(models.Poll).filter(models.Poll.id == poll_id).first() is not None
        )
    finally:
        db.close()


async def handle_subscribe(
    ws: WebSocket, db: Session, poll_id: str, subscribed_polls: set[str]
):
    """Handle subscription to a poll's live updates."""
    if not poll_exists(poll_id):
        await send_error(ws, C.ERR_POLL_NOT_FOUND, f"Poll {poll_id} does not exist")
        return

    if poll_id in subscribed_polls:
        await send_error(
            ws, C.ERR_ALREADY_SUBSCRIBED, f"Already subscribed to {poll_id}"
        )
        return

    if poll_id not in connections:
        connections[poll_id] = []
    connections[poll_id].append(ws)
    subscribed_polls.add(poll_id)

    results = crud.get_poll_results(db, poll_id)
    await send_success(ws, C.ACTION_SUBSCRIBE, {"poll_id": poll_id, "results": results})


async def handle_unsubscribe(ws: WebSocket, poll_id: str, subscribed_polls: set[str]):
    """Handle unsubscription from a poll's live updates."""
    if poll_id not in subscribed_polls:
        await send_error(ws, C.ERR_NOT_SUBSCRIBED, f"Not subscribed to {poll_id}")
        return

    if poll_id in connections and ws in connections[poll_id]:
        connections[poll_id].remove(ws)
    subscribed_polls.remove(poll_id)

    await send_success(ws, C.ACTION_UNSUBSCRIBE, {"poll_id": poll_id})


async def handle_disconnect(ws: WebSocket, subscribed_polls: set[str]):
    """Handle disconnection and cleanup all subscriptions."""
    for pid in subscribed_polls:
        if pid in connections and ws in connections[pid]:
            connections[pid].remove(ws)
    subscribed_polls.clear()
    await send_success(ws, C.ACTION_DISCONNECT)
    await ws.close()


@router.websocket("/ws")
async def websocket_subscribe_multi_poll(ws: WebSocket, db: Session = Depends(get_db)):
    """
    WebSocket endpoint to subscribe to multiple polls' live updates. Client can send JSON messages with actions:
    """
    await ws.accept()
    await send_success(ws, C.ACTION_CONNECT, {"message": "connected"})
    subscribed_polls: set[str] = set()

    try:
        while True:
            msg = await ws.receive_text()
            data = json.loads(msg)
            action = data.get("action")
            poll_id = data.get("poll_id")

            if action == C.ACTION_SUBSCRIBE and poll_id:
                await handle_subscribe(ws, db, poll_id, subscribed_polls)

            elif action == C.ACTION_UNSUBSCRIBE and poll_id:
                await handle_unsubscribe(ws, poll_id, subscribed_polls)

            elif action == C.ACTION_DISCONNECT:
                await handle_disconnect(ws, subscribed_polls)
                break

            else:
                await send_error(ws, C.ERR_UNKNOWN_ACTION, f"Unknown action {action}")

    except Exception as e:
        await send_error(ws, C.ERR_INTERNAL, str(e))
        await ws.close()


@router.websocket("/ws/{poll_id}")
async def websocket_endpoint_one_poll(
    ws: WebSocket, poll_id: str, db: Session = Depends(get_db)
):
    await ws.accept()
    await send_success(ws, C.ACTION_CONNECT, {"message": "connected"})
    if not poll_exists(poll_id):
        await send_error(ws, C.ERR_POLL_NOT_FOUND, f"Poll {poll_id} does not exist")
        return
    if poll_id not in connections:
        connections[poll_id] = []
    connections[poll_id].append(ws)
    await send_success(
        ws,
        C.ACTION_SUBSCRIBE,
        {"poll_id": poll_id, "results": crud.get_poll_results(db, poll_id)},
    )
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        # Cleanup subscription
        if poll_id in connections:
            connections[poll_id] = [c for c in connections[poll_id] if c != ws]
