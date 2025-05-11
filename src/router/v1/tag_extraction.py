from fastapi import APIRouter, HTTPException
from src.services.v1.tag_extraction import extract_tags
from src.schemas.v1.tag_extraction import TagRequest, TagResponse
from src.core.logging_config import logger

router = APIRouter()

@router.post("/tag/extract", response_model=TagResponse)
def extract_keyword(payload: TagRequest) -> TagResponse:
  
    logger.info("[POST /tag/extract] 키워드 추출 요청 수신", extra={"text_preview": payload.text[:30]})

    try:
        tags = extract_tags(payload.text)
        logger.info("[태그 추출] 태그 추출 성공", extra={"tag_count": len(tags)})
        return TagResponse(tags=tags)
    except Exception:
        logger.exception("[태그 추출] 태그 추출 중 오류 발생")
        raise HTTPException(status_code=500, detail="태그 추출 중 오류가 발생했습니다.")
