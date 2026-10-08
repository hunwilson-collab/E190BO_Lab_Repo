from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field as PydanticField
from sqlmodel import Field, Session, SQLModel, create_engine, select


class Idea(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    body: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Request body. A separate non-table class, because table=True classes skip
# validation and a bad POST would reach the database and 500.
class IdeaCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)  # "   " counts as empty

    title: str = PydanticField(min_length=1, max_length=200)
    body: str = ""


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
