import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from .database import Base


def gen_id():
    return str(uuid.uuid4())


class Poll(Base):
    __tablename__ = "polls"
    id = Column(String, primary_key=True, default=gen_id)
    title = Column(String, nullable=False)
    question = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    choices = relationship("Choice", back_populates="poll", cascade="all, delete")


class Choice(Base):
    __tablename__ = "choices"
    id = Column(String, primary_key=True, default=gen_id)
    text = Column(String, nullable=False)
    poll_id = Column(String, ForeignKey("polls.id"))
    poll = relationship("Poll", back_populates="choices")
    votes = relationship("Vote", back_populates="choice", cascade="all, delete")


class Vote(Base):
    __tablename__ = "votes"
    id = Column(String, primary_key=True, default=gen_id)
    choice_id = Column(String, ForeignKey("choices.id"))
    username = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.now(timezone.utc))
    choice = relationship("Choice", back_populates="votes")
