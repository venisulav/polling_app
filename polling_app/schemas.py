from typing import List

from pydantic import BaseModel


class ChoiceCreate(BaseModel):
    text: str


class PollCreate(BaseModel):
    title: str
    question: str
    choices: List[ChoiceCreate]


class ChoiceOut(BaseModel):
    id: str
    text: str
    votes: int


class PollOut(BaseModel):
    id: str
    title: str
    question: str
    choices: List[ChoiceOut]


class VoteCreate(BaseModel):
    username: str
    choice_id: str


class ResultOut(BaseModel):
    poll_id: str
    results: List[ChoiceOut]
