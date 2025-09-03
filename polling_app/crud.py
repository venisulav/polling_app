from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models, schemas


def create_poll(db: Session, poll: schemas.PollCreate):
    db_poll = models.Poll(title=poll.title, question=poll.question)
    db.add(db_poll)
    db.commit()
    db.refresh(db_poll)
    for c in poll.choices:
        db_choice = models.Choice(text=c.text, poll_id=db_poll.id)
        db.add(db_choice)
    db.commit()
    return db_poll


def get_poll(db: Session, poll_id: str):
    return db.query(models.Poll).filter(models.Poll.id == poll_id).first()


def get_polls(db: Session):
    return db.query(models.Poll).all()


def has_user_voted(db: Session, poll_id: str, username: str) -> bool:
    # Returns True if the user has already voted for the poll
    subquery = (
        db.query(models.Vote.id)
        .join(models.Choice)
        .filter(models.Vote.username == username, models.Choice.poll_id == poll_id)
    )
    return db.query(subquery.exists()).scalar()


def create_vote(db: Session, vote: schemas.VoteCreate):
    db_vote = models.Vote(username=vote.username, choice_id=vote.choice_id)
    db.add(db_vote)
    db.commit()
    db.refresh(db_vote)
    return db_vote


def get_poll_results(db: Session, poll_id: str):
    choices = db.query(models.Choice).filter(models.Choice.poll_id == poll_id).all()
    results: list[dict[str, Any]] = []
    for c in choices:
        count = (
            db.query(func.count(models.Vote.id))
            .filter(models.Vote.choice_id == c.id)
            .scalar()
        )
        results.append({"id": c.id, "text": c.text, "votes": count})
    return results


def delete_poll(db: Session, poll_id: str):
    poll = db.query(models.Poll).filter(models.Poll.id == poll_id).first()
    if poll:
        db.delete(poll)
        db.commit()
        return True
    return False
