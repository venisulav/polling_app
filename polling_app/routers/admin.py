from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from polling_app.utils.connection_manager import connection_manager

from .. import crud
from ..database import SessionLocal

router = APIRouter(prefix="/admin", tags=["admin"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.delete("/polls/{poll_id}")
async def delete_poll(poll_id: str, db: Session = Depends(get_db)):
    """Delete a poll and notify all subscribers."""
    success = crud.delete_poll(db, poll_id)
    if not success:
        raise HTTPException(status_code=404, detail="Poll not found")

    # Clean up WebSocket connections and notify subscribers
    await connection_manager.cleanup_poll(poll_id)

    return {"status": "deleted"}
