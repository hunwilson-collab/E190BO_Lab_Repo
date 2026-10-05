from fastapi import FastAPI
app = FastAPI()


@app.get("/ideas")
def list_ideas():
    return [{"id": 1, "title": "Automatic plant waterer"}]
