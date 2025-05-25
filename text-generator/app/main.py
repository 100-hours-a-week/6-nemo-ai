from fastapi import FastAPI, Request
from pydantic import BaseModel
from model import generate_text

app = FastAPI()


class GenerationInput(BaseModel):
    name: str
    goal: str
    category: str
    period: str


@app.post("/generate")
async def generate(data: GenerationInput):
    result = generate_text(data.dict())
    return result
