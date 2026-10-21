from fastapi import FastAPI, HTTPException
from sqlmodel import SQLModel, Field, Session, create_engine, func, select

class Idea(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    body: str = ""
    author: str = ""

class Vote(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    idea_id: int = Field(foreign_key="idea.id")
    voter: str

# SQLModel classes with table=True SKIP validation — a bad body reaches the
# database and you get a 500 instead of a 422. So each request body gets its
# own non-table class. It also keeps `id` and `idea_id` out of what a client
# may send: the database assigns the first, and the URL supplies the second.
class IdeaCreate(SQLModel):
    title: str
    body: str = ""
    author: str = ""

class VoteCreate(SQLModel):
    voter: str

# echo=True prints every SQL statement the ORM sends. Turn it on to answer the
# check-in's SQL question.
engine = create_engine("sqlite:///app.db")
SQLModel.metadata.create_all(engine)
app = FastAPI()

@app.get("/ideas")
def list_ideas():
    # The class 10 query, through the ORM. isouter=True makes it a LEFT JOIN,
    # which keeps ideas with no votes; counting Vote.id rather than rows makes
    # their count 0 instead of 1.
    stmt = (
        select(Idea, func.count(Vote.id))
        .join(Vote, isouter=True)
        .group_by(Idea.id)
        .order_by(Idea.id)
    )
    with Session(engine) as s:
        return [{**idea.model_dump(), "vote_count": n} for idea, n in s.exec(stmt)]

@app.post("/ideas", status_code=201)
def create_idea(payload: IdeaCreate):
    idea = Idea(**payload.model_dump())
    with Session(engine) as s:
        s.add(idea); s.commit(); s.refresh(idea)
        return idea

@app.get("/ideas/{idea_id}")
def get_idea(idea_id: int):
    with Session(engine) as s:
        idea = s.get(Idea, idea_id)
        if not idea:
            raise HTTPException(404, "no such idea")
        votes = s.exec(select(Vote).where(Vote.idea_id == idea_id)).all()
        return {**idea.model_dump(), "votes": votes}

@app.post("/ideas/{idea_id}/vote", status_code=201)
def vote(idea_id: int, payload: VoteCreate):
    with Session(engine) as s:
        if not s.get(Idea, idea_id):
            raise HTTPException(404, "no such idea")
        vote = Vote(idea_id=idea_id, **payload.model_dump())
        s.add(vote); s.commit(); s.refresh(vote)
        return vote
