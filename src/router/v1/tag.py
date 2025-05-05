from fastapi import APIRouter
from pydantic import BaseModel
from src.services.extract_tags import extract_tags

router = APIRouter()

# 요청 데이터 모델
class TagRequest(BaseModel):
    text: str

# 응답 데이터 모델
class TagResponse(BaseModel):
    tags: list[str]

@router.post("/tag/extract", response_model=TagResponse)
async def extract_keyword(payload: TagRequest):
    tags = extract_tags(payload.text)
    return {"tags": tags}
