import asyncio
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from polling_app.utils.connection_manager import connection_manager

from .. import crud, schemas
from ..database import SessionLocal

router = APIRouter(prefix="/polls", tags=["polls"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


@router.delete("/{poll_id}")
async def delete_poll(poll_id: str, db: Session = Depends(get_db)):
    """Delete a poll."""
    success = crud.delete_poll(db, poll_id)
    if not success:
        raise HTTPException(status_code=404, detail="Poll not found")
    asyncio.create_task(connection_manager.cleanup_poll(poll_id))

    return {"status": "deleted"}
