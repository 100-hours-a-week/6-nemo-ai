from fastapi import APIRouter
from src.services.v1.tag_extraction import extract_tags
from src.schemas.v1.tag_extraction import TagRequest, TagResponse

router = APIRouter()

@router.post("/tag/extract", response_model=TagResponse)
def extract_keyword(payload: TagRequest) -> TagResponse:
    tags = extract_tags(payload.text)
    return TagResponse(tags=tags)
