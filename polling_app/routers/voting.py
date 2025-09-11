from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from polling_app import constants as C
from polling_app.utils.connection_manager import connection_manager

from .. import crud, schemas
from ..database import SessionLocal

router = APIRouter(prefix="/polls", tags=["voting"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/{poll_id}/vote")
async def vote(poll_id: str, vote: schemas.VoteCreate, db: Session = Depends(get_db)):
    """Cast a vote for a choice in a poll. Broadcasts update to subscribers."""
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

    # Broadcast update to WebSocket subscribers
    response_data: dict[str, Any] = {
        "poll_id": poll_id,
        "results": crud.get_poll_results(db, poll_id),
    }
    await connection_manager.broadcast_to_poll(poll_id, C.ACTION_UPDATE, response_data)

    return {"status": "ok"}
