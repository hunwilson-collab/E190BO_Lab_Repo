from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field as PydanticField
from sqlmodel import Field, Session, SQLModel, create_engine, select


class Idea(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    body: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# One row per vote. idea_id points back at the idea it's for.
class Vote(SQLModel, table=True):
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
        # No votes table yet, so every idea has 0 votes for now.
        return [{**idea.model_dump(), "vote_count": 0} for idea in ideas]


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
        return {**idea.model_dump(), "votes": votes}


@app.post("/ideas/{idea_id}/vote", status_code=201)
def vote(idea_id: int, payload: VoteCreate):
    with Session(engine) as s:
        # Check the idea exists first, so a vote on a missing idea is a 404.
        if s.get(Idea, idea_id) is None:
            raise HTTPException(404, "no such idea")
        v = Vote(idea_id=idea_id, voter=payload.voter)
        s.add(v)
        s.commit()
        s.refresh(v)
        return v
