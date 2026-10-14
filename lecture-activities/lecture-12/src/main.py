# The idea board, ready to ship, for the class build-along. You won't need to
# change this file today: everything you write is next to src/, not in it.
#
# Three things make it ready to ship:
#   - the database comes from the DATABASE_URL environment variable, and falls
#     back to a SQLite file, app.db, when it isn't set;
#   - the first line of the log says which database, with the password
#     starred out;
#   - GET /health answers 200 only when the database does.
# There's no votes table, so every vote_count is 0.
#
# Run it without Docker, from src/:  uvicorn main:app --reload
import logging
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlmodel import SQLModel, Field, Session, create_engine, select

class Idea(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    body: str = ""

class IdeaCreate(SQLModel):
    title: str
    body: str = ""

def database_url():
    url = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    # psycopg (version 3) is the driver installed, so say so.
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url

engine = create_engine(database_url())
# Say which database this is, with the password starred out.
logging.getLogger("uvicorn.error").info("Database: %r", engine.url)
SQLModel.metadata.create_all(engine)

app = FastAPI()

@app.get("/health")
def health():
    with engine.connect() as conn:            # can we reach the database?
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}

@app.get("/ideas")
def list_ideas():
    with Session(engine) as s:
        return [{**i.model_dump(), "vote_count": 0} for i in s.exec(select(Idea))]

@app.post("/ideas", status_code=201)
def create_idea(payload: IdeaCreate):
    idea = Idea(**payload.model_dump())
    with Session(engine) as s:
        s.add(idea)
        s.commit()
        s.refresh(idea)
        return {**idea.model_dump(), "vote_count": 0}

app.mount("/", StaticFiles(directory="web", html=True), name="web")
