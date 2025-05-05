from fastapi import APIRouter
from src.services.extract_tags import extract_tags
from src.models.tags_model import TagRequest, TagResponse
router = APIRouter()

@router.post("/tag/extract", response_model=TagResponse)
async def extract_keyword(payload: TagRequest):
    tags = extract_tags(payload.text)
    return {"tags": tags}
