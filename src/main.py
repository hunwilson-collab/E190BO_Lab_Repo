
from fastapi import FastAPI
from sqlmodel import SQLModel, Field, Session, create_engine, select


class Idea(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    body: str = ""


engine = create_engine("sqlite:///app.db", echo=True)
SQLModel.metadata.create_all(engine)
app = FastAPI()


@app.get("/ideas")
def list_ideas():
    with Session(engine) as s:
        return s.exec(select(Idea)).all()
