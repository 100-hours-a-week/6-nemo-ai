from fastapi import APIRouter, HTTPException, Request
from src.services.v2.tag_extraction import extract_tags
from src.schemas.v1.tag_extraction import TagRequest, TagResponse
from src.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()
router = APIRouter()

@router.post("/tag/extract", response_model=TagResponse)
async def extract_keyword(payload: TagRequest, request: Request):
    ai_logger.info("[AI-v2] [POST /tag/extract] 키워드 추출 요청 수신", extra={"text_preview": payload.text[:30]})

    try:
        tags = await extract_tags(payload.text)
        ai_logger.info("[AI-v2] [태그 추출] 태그 추출 성공", extra={"tag_count": len(tags)})
        return TagResponse(tags=tags)
    except Exception:
        ai_logger.exception("[AI-v2] [태그 추출 실패] 예외 발생", extra={
            "endpoint": request.url.path,
            "text_preview": payload.text[:30]
        })
        raise HTTPException(status_code=500, detail="태그 추출 중 오류가 발생했습니다.")
