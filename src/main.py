from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field as PydanticField
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Session, SQLModel, create_engine, func, select


class Idea(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    body: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# One row per vote. idea_id points back at the idea it's for.
# The unique constraint means one vote per voter per idea, enforced by the DB.
class Vote(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("idea_id", "voter"),)

    id: int | None = Field(default=None, primary_key=True)
    idea_id: int = Field(foreign_key="idea.id")
    voter: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Request bodies. A separate non-table class, because table=True classes skip
# validation and a bad POST would reach the database and 500.
class IdeaCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)  # "   " counts as empty

    title: str = PydanticField(min_length=1, max_length=200)
    body: str = ""


class VoteCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    voter: str = PydanticField(min_length=1, max_length=100)


engine = create_engine("sqlite:///app.db", echo=True)
SQLModel.metadata.create_all(engine)

app = FastAPI()


@app.get("/ideas")
def list_ideas():
    with Session(engine) as s:
        ideas = s.exec(select(Idea)).all()
        result = []
        for idea in ideas:
            # One COUNT query per idea. Simple, but it's one extra query for
            # every idea on the board (a single LEFT JOIN would do it in one).
            n = s.exec(select(func.count(Vote.id)).where(Vote.idea_id == idea.id)).one()
            result.append({**idea.model_dump(), "vote_count": n})
        return result


@app.post("/ideas", status_code=201)
def create_idea(payload: IdeaCreate):
    idea = Idea(title=payload.title, body=payload.body)
    with Session(engine) as s:
        s.add(idea)
        s.commit()
        s.refresh(idea)
        return idea


@app.get("/ideas/{idea_id}")
def get_idea(idea_id: int):
    with Session(engine) as s:
        idea = s.get(Idea, idea_id)
        if idea is None:
            raise HTTPException(404, "no such idea")
        votes = s.exec(select(Vote).where(Vote.idea_id == idea_id)).all()
        return {**idea.model_dump(), "votes": votes, "vote_count": len(votes)}


@app.post("/ideas/{idea_id}/vote", status_code=201)
def vote(idea_id: int, payload: VoteCreate):
    with Session(engine) as s:
        # Check the idea exists first, so a vote on a missing idea is a 404.
        if s.get(Idea, idea_id) is None:
            raise HTTPException(404, "no such idea")
        already = s.exec(
            select(Vote).where(Vote.idea_id == idea_id, Vote.voter == payload.voter)
        ).first()
        if already is not None:
            raise HTTPException(409, "already voted for this idea")
        v = Vote(idea_id=idea_id, voter=payload.voter)
        s.add(v)
        s.commit()
        s.refresh(v)
        return v
