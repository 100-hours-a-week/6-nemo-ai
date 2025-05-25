from fastapi import FastAPI
from pydantic import BaseModel
from model import extract_tags

# 입력 모델 정의
class TextInput(BaseModel):
    text: str

# FastAPI 앱 생성
app = FastAPI()

# POST 요청 처리 엔드포인트
@app.post("/embed")
async def embed(input: TextInput):
    tags = extract_tags(input.text)
    return {"tags": tags}
