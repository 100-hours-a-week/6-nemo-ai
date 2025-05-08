from fastapi import APIRouter, HTTPException
from src.services.v1.tag_extraction import extract_tags
from src.schemas.v1.tag_extraction import TagRequest, TagResponse

router = APIRouter()

@router.post("/tag/extract", response_model=TagResponse)
def extract_keyword(payload: TagRequest) -> TagResponse:
    try:
        tags = extract_tags(payload.text)
        return TagResponse(tags=tags)
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception:
        raise HTTPException(status_code=500, detail="태그 추출 중 오류가 발생했습니다.")
