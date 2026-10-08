from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field as PydanticField
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Session, SQLModel, create_engine, func, select


# =============================================================================
# TABLES — what gets stored in the database (each line = one column)
# =============================================================================

# Idea table: one row per idea on the board.
class Idea(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)  # database picks the id
    title: str
    body: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Vote table: one row per vote. idea_id links each vote to its idea,
# so one idea can have many votes.
class Vote(SQLModel, table=True):
    # Rule: the same voter can't vote on the same idea twice.
    __table_args__ = (UniqueConstraint("idea_id", "voter"),)

    id: int | None = Field(default=None, primary_key=True)
    idea_id: int = Field(foreign_key="idea.id")  # points at idea.id
    voter: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# INPUT CHECKERS — what a valid request body looks like
# Bad input gets rejected with a 422 before any of our code runs.
# (Kept separate from the tables because table classes skip these checks.)
# =============================================================================

# Body for POST /ideas: title is required, 1-200 characters.
class IdeaCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)  # trim spaces, so "   " is empty

    title: str = PydanticField(min_length=1, max_length=200)
    body: str = ""


# Body for POST /ideas/{id}/vote: voter is required, 1-100 characters.
class VoteCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    voter: str = PydanticField(min_length=1, max_length=100)


# =============================================================================
# SETUP — connect to the database file and create the app
# =============================================================================

engine = create_engine("sqlite:///app.db", echo=True)  # echo=True prints every SQL query
SQLModel.metadata.create_all(engine)                   # make the tables if they don't exist

app = FastAPI()


# =============================================================================
# ENDPOINTS — one function per URL
# =============================================================================

# GET /ideas — list every idea, each with its vote_count.
@app.get("/ideas")
def list_ideas():
    with Session(engine) as s:
        ideas = s.exec(select(Idea)).all()  # 1) get all ideas
        result = []
        for idea in ideas:
            # 2) count this idea's votes (one COUNT query per idea)
            n = s.exec(select(func.count(Vote.id)).where(Vote.idea_id == idea.id)).one()
            result.append({**idea.model_dump(), "vote_count": n})  # 3) idea + its count
        return result


# POST /ideas — create a new idea and return it with its new id (201).
@app.post("/ideas", status_code=201)
def create_idea(payload: IdeaCreate):
    idea = Idea(title=payload.title, body=payload.body)
    with Session(engine) as s:
        s.add(idea)      # stage it
        s.commit()       # save it
        s.refresh(idea)  # reload it so we get the id the database assigned
        return idea


# GET /ideas/{id} — one idea plus its list of votes. 404 if it doesn't exist.
@app.get("/ideas/{idea_id}")
def get_idea(idea_id: int):
    with Session(engine) as s:
        idea = s.get(Idea, idea_id)  # look it up by id (None if missing)
        if idea is None:
            raise HTTPException(404, "no such idea")
        votes = s.exec(select(Vote).where(Vote.idea_id == idea_id)).all()  # its votes
        return {**idea.model_dump(), "votes": votes, "vote_count": len(votes)}


# POST /ideas/{id}/vote — record a vote (201).
# 404 if the idea doesn't exist, 409 if this voter already voted on it.
@app.post("/ideas/{idea_id}/vote", status_code=201)
def vote(idea_id: int, payload: VoteCreate):
    with Session(engine) as s:
        # Check 1: does the idea exist?
        if s.get(Idea, idea_id) is None:
            raise HTTPException(404, "no such idea")

        # Check 2: has this voter already voted on this idea?
        already = s.exec(
            select(Vote).where(Vote.idea_id == idea_id, Vote.voter == payload.voter)
        ).first()
        if already is not None:
            raise HTTPException(409, "already voted for this idea")

        # Passed both checks: save the vote and return it.
        v = Vote(idea_id=idea_id, voter=payload.voter)
        s.add(v)
        s.commit()
        s.refresh(v)
        return v
