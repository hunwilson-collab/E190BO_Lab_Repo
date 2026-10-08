# A stand-in for your Lab 5 API, for the class build-along.
#
# It answers GET /ideas and POST /ideas in exactly the shapes CONTRACT.md
# promises (§1 and §2), from a list in memory instead of a database. Your page
# can't tell the difference: all it ever sees is HTTP and JSON. Because the
# list lives in memory, every restart (including --reload) starts it over.
#
# Run it from this folder:  uvicorn main:app --reload
from fastapi import FastAPI, HTTPException
from sqlmodel import SQLModel
from fastapi.staticfiles import StaticFiles

app = FastAPI()
ideas = [
    {"id": 1, "title": "Automatic plant waterer", "body": "", "vote_count": 2},
    {"id": 2, "title": "Sticker vending machine", "body": "", "vote_count": 3},
    {"id": 3, "title": "Bike lock that texts you", "body": "", "vote_count": 0},
]


class IdeaCreate(SQLModel):        # what a client may send: no id
    title: str
    body: str = ""


@app.get("/ideas")
def list_ideas():
    raise HTTPException(500)
    return ideas


@app.post("/ideas", status_code=201)
def create_idea(payload: IdeaCreate):
    idea = {"id": len(ideas) + 1, **payload.model_dump(), "vote_count": 0}
    ideas.append(idea)
    return idea


app.mount("/", StaticFiles(directory="web", html=True), name="web")
